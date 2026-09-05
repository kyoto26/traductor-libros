import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile

from api.security import (
    FileTooLargeError,
    get_max_upload_size,
    sanitize_filename,
    validate_file_type,
)
from extractors.epub_extractor import extract as extract_epub
from extractors.txt_extractor import extract as extract_txt
from reconstructors.epub_reconstructor import reconstruct as reconstruct_epub
from reconstructors.txt_reconstructor import reconstruct as reconstruct_txt
from translator.glossary import Glossary
from translator.pipeline import translate_document

router = APIRouter()

_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB


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


@router.post("/translate-txt")
async def translate_txt(request: Request, file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory(prefix="traductor-docs-") as tmp_dir:
        tmp_path = await _receive_upload(request, file, ".txt", Path(tmp_dir))

        document = extract_txt(tmp_path)

        # Optional for now — no endpoint accepts a user-supplied glossary yet.
        glossary: Glossary | None = None
        translate_document(document, glossary=glossary)

        translated_text = reconstruct_txt(document)

    return {"translated_text": translated_text}


@router.post("/translate-epub")
async def translate_epub(request: Request, file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory(prefix="traductor-docs-") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        tmp_path = await _receive_upload(request, file, ".epub", tmp_dir_path)

        document = extract_epub(tmp_path)

        # Optional for now — no endpoint accepts a user-supplied glossary yet.
        glossary: Glossary | None = None
        translate_document(document, glossary=glossary)

        output_path = tmp_dir_path / "translated.epub"
        reconstruct_epub(document, output_path)

        # Read into memory before the TemporaryDirectory context closes and
        # deletes output_path — a FileResponse would try to stream the file
        # from disk after the handler returns, by which point it would
        # already be gone. See README (Fase 5-adjacent note) for revisiting
        # this with FileResponse + BackgroundTask if the size limit grows
        # enough that buffering the whole file in memory stops being fine.
        output_bytes = output_path.read_bytes()

    download_name = f"translated_{tmp_path.name}"
    return Response(
        content=output_bytes,
        media_type="application/epub+zip",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
