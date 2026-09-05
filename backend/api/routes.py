import logging
import re
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
from translator.chunker import Chunk, create_chunks
from translator.glossary import Glossary
from translator.llm_client import get_translator
from translator.prompt_builder import build_translation_request

logger = logging.getLogger(__name__)

router = APIRouter()

_CHUNK_SIZE = 1024 * 1024  # 1 MB
_EXPECTED_EXT = ".txt"

# Same tolerance as the paragraph split used when extracting the source
# document (a blank line may carry stray whitespace), applied here to the
# model's translated output so a small formatting slip doesn't count as a
# structure mismatch.
_TRANSLATED_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def _apply_translation(chunk: Chunk, translated_text: str) -> None:
    if len(chunk.blocks) == 1:
        chunk.blocks[0].translated_text = translated_text
        return

    parts = [
        part.strip()
        for part in _TRANSLATED_PARAGRAPH_SPLIT_RE.split(translated_text.strip())
    ]

    if len(parts) == len(chunk.blocks):
        for block, part in zip(chunk.blocks, parts):
            block.translated_text = part
        return

    # The model didn't preserve the paragraph count we asked for. Rather
    # than guessing a wrong per-block mapping (or leaving some blocks as
    # None, which would silently fall back to the original Spanish text and
    # produce a mixed-language document), the whole translation goes on the
    # first block and the rest are left blank — no content is lost or
    # duplicated, only the fine-grained paragraph split for this chunk.
    logger.warning(
        "Translated chunk has %d paragraph(s) but expected %d (chunk starting "
        "at block %r); assigning the full translation to the first block.",
        len(parts),
        len(chunk.blocks),
        chunk.blocks[0].id,
    )
    chunk.blocks[0].translated_text = translated_text.strip()
    for block in chunk.blocks[1:]:
        block.translated_text = ""


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

        # Optional for now — no endpoint accepts a user-supplied glossary yet.
        glossary: Glossary | None = None

        translator = get_translator()
        try:
            for chunk in create_chunks(document):
                relevant_terms = (
                    glossary.find_matches(chunk.text) if glossary else None
                )
                text, context = build_translation_request(
                    chunk, glossary=relevant_terms
                )
                result = translator.translate(text=text, context=context)
                _apply_translation(chunk, result.text)
        finally:
            translator.close()

        translated_text = reconstruct_txt(document)

    return {"translated_text": translated_text}
