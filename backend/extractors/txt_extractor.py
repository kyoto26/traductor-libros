import re
from pathlib import Path

from charset_normalizer import from_bytes

from models.document import Block, Chapter, Document

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")

# Legacy single-byte codepages overlap with each other (the same byte
# sequence can be valid in more than one), so without restricting the
# candidates charset-normalizer can pick an Eastern/Central European one
# for text that is actually Western European. This is narrowed down to
# the encodings relevant to the languages this tool translates
# (es/en/fr/pt/it/de).
#
# KNOWN LIMITATION (empirically verified, not just theoretical): this does
# NOT guarantee rejecting a file in a legacy encoding outside this set
# (e.g. real cp1250 for Polish/Czech). Single-byte codecs have a total
# mapping (almost any byte "decodes" to something), so _decode() only
# raises ValueError when charset-normalizer's coherence score rules out
# ALL Western candidates — which reliably happens with long, highly
# distinctive text, but NOT with short text or text with few special
# characters: a real .txt file in cp1250 like "Dziękuję bardzo za pomoc."
# silently decodes as cp1252, producing "Dziêkujê bardzo za pomoc."
# (mojibake, with no error at all). If this project ever needs to support
# Central/Eastern European languages as a source language, this list needs
# to be extended (or the encoding should be asked from the user instead of
# guessed).
_LIKELY_ENCODINGS = ["cp1252", "iso8859_1", "iso8859_15"]


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass

    best_match = from_bytes(raw, cp_isolation=_LIKELY_ENCODINGS).best()
    if best_match is None:
        raise ValueError(
            "No se pudo determinar la codificación del archivo de texto."
        )
    return str(best_match)


def extract(file_path: str | Path) -> Document:
    file_path = Path(file_path)
    raw = file_path.read_bytes()
    text = _decode(raw)

    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(text.strip())]
    paragraphs = [p for p in paragraphs if p]

    blocks = [
        Block(id=f"p-{i}", type="paragraph", text=paragraph, order=i)
        for i, paragraph in enumerate(paragraphs)
    ]

    chapter = Chapter(id="ch-0", title=None, blocks=blocks)

    return Document(
        metadata={"formato_original": "txt"},
        chapters=[chapter],
    )
