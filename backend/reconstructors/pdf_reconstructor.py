import html
from pathlib import Path

import pymupdf

from models.document import Document

_MEDIABOX = pymupdf.paper_rect("a4")
_MARGIN = 54  # 0.75in — page size/margins are fixed, not carried over from the
# original PDF: this is Option 2 (a fluid, reflowed document), so there is no
# "original layout" being preserved in the first place.


class PdfReconstructionError(Exception):
    """Raised when a translated Document can't be rendered into a PDF."""


def _build_html_and_archive(document: Document) -> tuple[str, pymupdf.Archive]:
    parts: list[str] = []
    archive_entries: list[tuple[bytes, str]] = []
    in_list = False
    seen_first_heading = False

    def close_list_if_open() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    for block in document.all_blocks():
        if block.type == "image":
            close_list_if_open()
            filename = f"{block.id}.{block.image_ext}"
            archive_entries.append((block.image_data, filename))
            parts.append(f'<img src="{html.escape(filename)}"/>')
            continue

        text = block.translated_text if block.translated_text is not None else block.text
        escaped = html.escape(text)

        if block.type == "list_item":
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{escaped}</li>")
            continue

        close_list_if_open()

        if block.type == "heading":
            # No level info survives in Block (unlike EPUB's real h1-h6):
            # the first heading in the document — already used as the
            # chapter title — renders as <h1>, every other heading as <h2>.
            tag = "h2" if seen_first_heading else "h1"
            seen_first_heading = True
            parts.append(f"<{tag}>{escaped}</{tag}>")
        else:
            parts.append(f"<p>{escaped}</p>")

    close_list_if_open()

    return "".join(parts), pymupdf.Archive(archive_entries)


def reconstruct(document: Document, output_path: str | Path) -> None:
    output_path = Path(output_path)

    try:
        html_content, archive = _build_html_and_archive(document)
        story = pymupdf.Story(html=html_content, archive=archive)

        where = pymupdf.Rect(
            _MARGIN, _MARGIN, _MEDIABOX.width - _MARGIN, _MEDIABOX.height - _MARGIN
        )
        writer = pymupdf.DocumentWriter(str(output_path))

        more = 1
        while more:
            device = writer.begin_page(_MEDIABOX)
            more, _ = story.place(where)
            story.draw(device)
            writer.end_page()

        writer.close()
    except Exception as exc:
        # Same reasoning as the extractors: Story/DocumentWriter don't
        # expose a documented, enumerable set of failure modes, so any
        # failure here is wrapped into one clear error instead of a raw
        # traceback.
        raise PdfReconstructionError(f"No se pudo generar el PDF: {exc}") from exc
