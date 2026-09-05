import logging
import math
from dataclasses import dataclass

from models.document import Block, Document

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TOKENS = 1000
_DEFAULT_CONTEXT_CHARS = 200

# Without each provider's exact tokenizer (llama3.1 vs. Claude), we use the
# standard heuristic of ~4 characters per token. It's model-agnostic but
# approximate: the real count can vary by up to 20-30% from this estimate,
# so max_tokens should be chosen with some margin.
_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / _CHARS_PER_TOKEN)


def _join_block_texts(blocks: list[Block]) -> str:
    return "\n\n".join(block.text for block in blocks)


@dataclass
class Chunk:
    blocks: list[Block]
    context: str | None = None

    @property
    def text(self) -> str:
        return _join_block_texts(self.blocks)


def _build_context(previous_chunk: Chunk | None, context_chars: int) -> str | None:
    if previous_chunk is None:
        return None

    combined = previous_chunk.text
    if not combined:
        return None

    return combined[-context_chars:]


def _create_chapter_chunks(
    blocks: list[Block],
    max_tokens: int,
    context_chars: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_blocks: list[Block] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current_blocks, current_tokens
        previous_chunk = chunks[-1] if chunks else None
        chunks.append(
            Chunk(
                blocks=current_blocks,
                context=_build_context(previous_chunk, context_chars),
            )
        )
        current_blocks = []
        current_tokens = 0

    for block in blocks:
        block_tokens = _estimate_tokens(block.text)

        if block_tokens > max_tokens:
            logger.warning(
                "El bloque %r tiene ~%d tokens estimados y supera el límite "
                "de %d por sí solo; se enviará en su propio chunk sin cortarlo.",
                block.id,
                block_tokens,
                max_tokens,
            )

        if current_blocks and current_tokens + block_tokens > max_tokens:
            flush()

        current_blocks.append(block)
        current_tokens += block_tokens

    if current_blocks:
        flush()

    return chunks


def create_chunks(
    document: Document,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    context_chars: int = _DEFAULT_CONTEXT_CHARS,
) -> list[Chunk]:
    # Chunking runs per chapter, never spanning a chapter boundary — a chunk
    # mixing blocks from two different chapters (easy to hit with several
    # short chapters that together still fit under max_tokens) would send
    # them to the LLM as one translation unit, with no way to know where one
    # chapter's content ends and the next begins when mapping the result
    # back. Chapter-per-chapter also means each chapter's first chunk always
    # starts with context=None, instead of leaking trailing text from a
    # previous, unrelated chapter as if it were coherence context.
    chunks: list[Chunk] = []

    for chapter in document.chapters:
        # Image blocks (pdf_extractor.py) carry no translatable text — they
        # never reach a chunk, so they never reach prompt_builder.py or
        # llm_client.py either. Excluding them here, once, means nothing
        # downstream in the translation pipeline needs to know they exist.
        translatable_blocks = [b for b in chapter.blocks if b.type != "image"]
        sorted_blocks = sorted(translatable_blocks, key=lambda b: b.order)
        chunks.extend(_create_chapter_chunks(sorted_blocks, max_tokens, context_chars))

    return chunks
