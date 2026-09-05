import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, Response, UploadFile

from api.security import (
    FileTooLargeError,
    get_max_upload_size,
    sanitize_filename,
    validate_file_type,
)
from db.database import DATA_DIR
from db.models import (
    create_job,
    get_job,
    mark_completed,
    mark_failed,
    mark_processing,
    update_progress,
)
from extractors.epub_extractor import extract as extract_epub
from extractors.pdf_extractor import extract as extract_pdf
from extractors.txt_extractor import extract as extract_txt
from models.document import Document
from reconstructors.epub_reconstructor import reconstruct as reconstruct_epub
from reconstructors.pdf_reconstructor import reconstruct as reconstruct_pdf
from reconstructors.txt_reconstructor import reconstruct as reconstruct_txt
from translator.glossary import Glossary
from translator.pipeline import translate_document

logger = logging.getLogger(__name__)

router = APIRouter()

_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB
_JOBS_DIR = DATA_DIR / "jobs"


def _reconstruct_txt_to_file(document: Document, output_path: Path) -> None:
    output_path.write_text(reconstruct_txt(document), encoding="utf-8")


# format -> (extract, reconstruct(document, output_path), media_type, output_ext)
_FORMAT_CONFIG = {
    "txt": (extract_txt, _reconstruct_txt_to_file, "text/plain", ".txt"),
    "epub": (extract_epub, reconstruct_epub, "application/epub+zip", ".epub"),
    "pdf": (extract_pdf, reconstruct_pdf, "application/pdf", ".pdf"),
}


async def _receive_upload(
    request: Request, file: UploadFile, expected_ext: str, tmp_dir: Path
) -> Path:
    original_filename = file.filename or ""
    if not original_filename.lower().endswith(expected_ext):
        raise HTTPException(
            status_code=400,
            detail=f"Se esperaba un archivo {expected_ext}, se recibió: {original_filename!r}",
        )

    safe_filename = sanitize_filename(original_filename)
    max_size = get_max_upload_size()

    # Capa 1: chequeo barato usando el header (no confiable por sí solo:
    # puede faltar o venir falseado, ver nota en Content-Length más abajo).
    content_length = request.headers.get("content-length")
    if content_length is not None and content_length.isdigit():
        if int(content_length) > max_size:
            raise FileTooLargeError(
                f"Content-Length ({content_length} bytes) supera el límite de {max_size} bytes."
            )

    tmp_path = tmp_dir / safe_filename
    total_read = 0
    type_validated = False

    with open(tmp_path, "wb") as tmp_file:
        while True:
            chunk = await file.read(_UPLOAD_CHUNK_SIZE)
            if not chunk:
                break

            total_read += len(chunk)
            # Capa 2: chequeo autoritativo sobre bytes reales leídos, cubre
            # Content-Length ausente o falseado.
            if total_read > max_size:
                raise FileTooLargeError(
                    f"El archivo supera el límite de {max_size} bytes."
                )

            if not type_validated:
                validate_file_type(chunk, expected_ext)
                type_validated = True

            tmp_file.write(chunk)

    # Archivo vacío (0 bytes): no hay contenido que inspeccionar con
    # libmagic; se acepta igual, cada extractor ya maneja este caso.

    return tmp_path


def _run_job(job_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        logger.error("Job %r no encontrado al iniciar el procesamiento en background.", job_id)
        return

    extract, reconstruct, _media_type, _output_ext = _FORMAT_CONFIG[job.format]

    try:
        mark_processing(job_id)

        document = extract(job.input_path)

        # Optional for now — no endpoint accepts a user-supplied glossary yet.
        glossary: Glossary | None = None

        def on_progress(done: int, total: int) -> None:
            update_progress(job_id, done, total)

        translate_document(document, glossary=glossary, on_progress=on_progress)

        output_path = _JOBS_DIR / job_id / f"output{_output_ext}"
        reconstruct(document, output_path)

        mark_completed(job_id, str(output_path))
    except Exception as exc:
        # Deliberately broad: this is a background task with no request to
        # attach an HTTP error response to. Unlike the rest of the codebase
        # (where we're careful to catch specific exceptions), a job must
        # never be left stuck in "processing" because of an uncaught
        # exception — any failure here needs to end in status='failed'.
        logger.exception("Job %r falló durante el procesamiento en background.", job_id)
        mark_failed(job_id, str(exc))


async def _start_job(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    job_format: str,
    expected_ext: str,
) -> dict:
    job_id = str(uuid.uuid4())
    job_dir = _JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        input_path = await _receive_upload(request, file, expected_ext, job_dir)
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise

    create_job(job_id, job_format, input_path.name, str(input_path))
    background_tasks.add_task(_run_job, job_id)

    return {"job_id": job_id}


@router.post("/translate-txt", status_code=202)
async def translate_txt(
    request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    return await _start_job(request, file, background_tasks, "txt", ".txt")


@router.post("/translate-epub", status_code=202)
async def translate_epub(
    request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    return await _start_job(request, file, background_tasks, "epub", ".epub")


@router.post("/translate-pdf", status_code=202)
async def translate_pdf(
    request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    return await _start_job(request, file, background_tasks, "pdf", ".pdf")


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No existe un job con id {job_id!r}.")

    response = {
        "job_id": job.id,
        "status": job.status,
        "translated_blocks": job.translated_blocks,
        "total_blocks": job.total_blocks,
    }
    if job.status == "failed":
        response["error"] = job.error_message

    return response


@router.get("/download/{job_id}")
async def download_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No existe un job con id {job_id!r}.")

    if job.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"El job {job_id!r} todavía no está listo para descargar (status: {job.status!r}).",
        )

    _extract, _reconstruct, media_type, _output_ext = _FORMAT_CONFIG[job.format]
    output_bytes = Path(job.output_path).read_bytes()
    download_name = f"translated_{job.original_filename}"

    return Response(
        content=output_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
