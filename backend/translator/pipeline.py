import logging
import re
from typing import Callable, Optional

from models.document import Document
from translator.chunker import Chunk, create_chunks
from translator.glossary import Glossary
from translator.llm_client import get_translator
from translator.prompt_builder import build_translation_request

logger = logging.getLogger(__name__)

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
    # None, which would silently fall back to the original untranslated text
    # and produce a mixed-language document), the whole translation goes on the
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


def translate_document(
    document: Document,
    glossary: Glossary | None = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> None:
    # Format-agnostic: operates purely on Chapter/Block, so it works the
    # same whether the Document came from TXT, EPUB, or PDF.
    translator = get_translator()
    try:
        chunks = create_chunks(document)
        total_blocks = sum(len(chunk.blocks) for chunk in chunks)
        translated_blocks = 0

        if on_progress:
            on_progress(translated_blocks, total_blocks)

        for chunk in chunks:
            relevant_terms = glossary.find_matches(chunk.text) if glossary else None
            text, context = build_translation_request(chunk, glossary=relevant_terms)
            result = translator.translate(text=text, context=context)
            _apply_translation(chunk, result.text)

            # Progress resolution is per chunk, not per individual block: a
            # single translate() call is one blocking request that returns
            # everything in that chunk at once, so there's no finer-grained
            # signal available without changing how the LLM is called
            # (e.g. streaming).
            translated_blocks += len(chunk.blocks)
            if on_progress:
                on_progress(translated_blocks, total_blocks)
    finally:
        translator.close()
