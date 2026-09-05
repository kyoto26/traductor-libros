import logging
import math
from dataclasses import dataclass

from models.document import Block, Document

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TOKENS = 1000
_DEFAULT_CONTEXT_CHARS = 200

# Sin el tokenizer exacto de cada proveedor (llama3.1 vs. Claude), se usa la
# heurística estándar de ~4 caracteres por token. Es independiente del modelo
# pero aproximada: el conteo real puede variar hasta un 20-30% respecto a
# esta estimación, así que max_tokens debe elegirse con margen.
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


def create_chunks(
    document: Document,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    context_chars: int = _DEFAULT_CONTEXT_CHARS,
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

    for block in document.all_blocks():
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
