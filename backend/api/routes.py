import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from api.security import (
    FileTooLargeError,
    get_max_upload_size,
    sanitize_filename,
    validate_file_type,
)
from extractors.txt_extractor import extract as extract_txt
from reconstructors.txt_reconstructor import reconstruct as reconstruct_txt

router = APIRouter()

_CHUNK_SIZE = 1024 * 1024  # 1 MB
_EXPECTED_EXT = ".txt"


@router.post("/translate-txt")
async def translate_txt(request: Request, file: UploadFile = File(...)):
    original_filename = file.filename or ""
    if not original_filename.lower().endswith(_EXPECTED_EXT):
        raise HTTPException(
            status_code=400,
            detail=f"Se esperaba un archivo {_EXPECTED_EXT}, se recibió: {original_filename!r}",
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

    with tempfile.TemporaryDirectory(prefix="traductor-docs-") as tmp_dir:
        tmp_path = Path(tmp_dir) / safe_filename

        total_read = 0
        type_validated = False

        with open(tmp_path, "wb") as tmp_file:
            while True:
                chunk = await file.read(_CHUNK_SIZE)
                if not chunk:
                    break

                total_read += len(chunk)
                # Capa 2: chequeo autoritativo sobre bytes reales leídos,
                # cubre Content-Length ausente o falseado.
                if total_read > max_size:
                    raise FileTooLargeError(
                        f"El archivo supera el límite de {max_size} bytes."
                    )

                if not type_validated:
                    validate_file_type(chunk, _EXPECTED_EXT)
                    type_validated = True

                tmp_file.write(chunk)

        # Archivo vacío (0 bytes): no hay contenido que inspeccionar con
        # libmagic; se acepta igual, txt_extractor.py ya maneja este caso.

        document = extract_txt(tmp_path)

        # Simulación de traducción: todavía no hay LLM conectado.
        for block in document.all_blocks():
            block.translated_text = block.text

        translated_text = reconstruct_txt(document)

    return {"translated_text": translated_text}
