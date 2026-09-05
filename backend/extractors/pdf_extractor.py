import re
from collections import Counter
from pathlib import Path

import pymupdf

from models.document import Block, Chapter, Document

# A line/block whose font size is at least this many times the document's
# most common ("body") font size is treated as a heading — there's no
# semantic markup to rely on like there is in EPUB's HTML, so this is an
# approximation based on the standard font-size-histogram heuristic used
# for PDF heading detection. False positives/negatives are expected (e.g.
# a stylistically large body font, or a heading set in body-sized type).
_HEADING_SIZE_RATIO = 1.15

_BULLET_RE = re.compile(r"^[•\-\*]\s+")
_NUMBERED_RE = re.compile(r"^(?:\d+[.\)]|[a-zA-Z][.\)])\s+")

# Used to decide whether a page's trailing paragraph likely continues onto
# the next page: if it does NOT end in one of these, it's a candidate for
# merging with the next page's first paragraph.
_SENTENCE_END_RE = re.compile(r"[.!?…»\"'\)\]]\s*$")


class PdfParsingError(Exception):
    """Raised when a PDF can't be parsed, or requires a password."""


def _round_size(size: float) -> float:
    return round(size * 2) / 2  # group near-identical sizes (e.g. 11.0 vs 10.98)


def _compute_body_size(doc: pymupdf.Document) -> float:
    sizes: Counter[float] = Counter()

    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:  # skip image blocks
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        sizes[_round_size(span["size"])] += 1

    if not sizes:
        return 0.0

    return sizes.most_common(1)[0][0]


def _block_text_and_max_size(block: dict) -> tuple[str, float]:
    lines: list[str] = []
    max_size = 0.0

    for line in block["lines"]:
        line_text = "".join(span["text"] for span in line["spans"]).strip()
        if line_text:
            lines.append(line_text)
        for span in line["spans"]:
            max_size = max(max_size, span["size"])

    # Lines within a block are wrapped continuations of the same paragraph
    # (confirmed empirically: PyMuPDF already clusters wrapped lines into
    # one block), so they're joined with a space, not "\n\n".
    text = " ".join(" ".join(lines).split())
    return text, max_size


def _classify_and_clean(text: str, max_size: float, body_size: float) -> tuple[str, str]:
    if max_size >= body_size * _HEADING_SIZE_RATIO:
        return "heading", text

    marker = _BULLET_RE.match(text) or _NUMBERED_RE.match(text)
    if marker:
        return "list_item", text[marker.end():].strip()

    return "paragraph", text


def _extract_page_candidates(
    page: pymupdf.Page, body_size: float
) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []

    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue

        text, max_size = _block_text_and_max_size(block)
        if not text:
            continue

        block_type, clean_text = _classify_and_clean(text, max_size, body_size)
        if clean_text:
            candidates.append((block_type, clean_text))

    return candidates


def _ends_sentence(text: str) -> bool:
    return bool(_SENTENCE_END_RE.search(text))


def _extract_blocks(doc: pymupdf.Document, chapter_id: str) -> list[Block]:
    body_size = _compute_body_size(doc)
    blocks: list[Block] = []
    pending: dict | None = None

    def finalize_pending() -> None:
        nonlocal pending
        if pending is not None:
            blocks.append(
                Block(
                    id=f"{chapter_id}-b{len(blocks)}",
                    type=pending["type"],
                    text=pending["text"],
                    order=len(blocks),
                    page_number=pending["page_number"],
                )
            )
            pending = None

    for page in doc:
        page_number = page.number + 1  # 1-indexed, more natural for users

        for i, (block_type, text) in enumerate(_extract_page_candidates(page, body_size)):
            # Only the first candidate of a page can complete a merge with
            # whatever was left pending from the previous page — a KNOWN
            # GAP: this only catches a sentence-punctuation cue, so a word
            # split by a line-wrap hyphen across the page break (e.g.
            # "exam-" / "ple") is not reassembled into "example"; that
            # would need distinguishing a hyphenation break from a real
            # dash, which isn't attempted here.
            if (
                i == 0
                and pending is not None
                and pending["type"] == "paragraph"
                and block_type == "paragraph"
                and not _ends_sentence(pending["text"])
            ):
                pending["text"] = f"{pending['text']} {text}"
                continue

            finalize_pending()
            pending = {"type": block_type, "text": text, "page_number": page_number}

    finalize_pending()
    return blocks


def extract(file_path: str | Path) -> Document:
    file_path = Path(file_path)
    chapter_id = "ch-0"

    try:
        doc = pymupdf.open(str(file_path))
    except Exception as exc:
        raise PdfParsingError(f"No se pudo abrir el PDF: {exc}") from exc

    try:
        if doc.needs_pass:
            raise PdfParsingError("El PDF está protegido con contraseña.")

        blocks = _extract_blocks(doc, chapter_id)
    except PdfParsingError:
        raise
    except Exception as exc:
        # Deliberately broad, same reasoning as epub_extractor.py: PyMuPDF
        # doesn't expose a documented, enumerable set of failure modes for
        # a malformed PDF, and this is a boundary where parsing an
        # untrusted, potentially adversarial file must never leak a raw
        # traceback to the caller.
        raise PdfParsingError(f"No se pudo procesar el PDF: {exc}") from exc
    finally:
        doc.close()

    chapter = Chapter(
        id=chapter_id,
        title=blocks[0].text if blocks and blocks[0].type == "heading" else None,
        blocks=blocks,
    )

    return Document(metadata={"formato_original": "pdf"}, chapters=[chapter])
