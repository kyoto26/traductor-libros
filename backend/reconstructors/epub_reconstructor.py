import zipfile
from pathlib import Path

from models.document import Chapter, Document

# The EPUB/OCF spec requires the "mimetype" entry to be first in the
# archive and stored uncompressed; everything else is copied through with
# regular compression.
_MIMETYPE_ENTRY = "mimetype"


class EpubReconstructionError(Exception):
    """Raised when a translated Document can't be rebuilt into an EPUB —
    missing source info, or a chapter's original entry no longer matches
    anything in the source archive.
    """


def _apply_translations(chapter: Chapter) -> None:
    for block in chapter.blocks:
        text = block.translated_text if block.translated_text is not None else block.text

        # Wipes any nested inline tags (<em>, <strong>, <a>...) the
        # original paragraph had. This is a deliberate, known loss: blocks
        # are translated as flat text (see epub_extractor._clean_text), so
        # there is no word-level alignment between source and translation
        # that would tell us where an inline tag should land in the
        # translated sentence. The paragraph comes out as plain text.
        block.source_element.clear()
        block.source_element.append(text)


def _render_chapters(document: Document) -> dict[str, bytes]:
    rendered: dict[str, bytes] = {}

    for chapter in document.chapters:
        _apply_translations(chapter)
        rendered[chapter.source_file_name] = chapter.source_soup.encode("utf-8")

    return rendered


def reconstruct(document: Document, output_path: str | Path) -> None:
    output_path = Path(output_path)

    source_path = document.metadata.get("source_path")
    if not source_path:
        raise EpubReconstructionError(
            "document.metadata no tiene 'source_path'; ¿el Document fue "
            "creado con extractors.epub_extractor.extract()?"
        )

    rendered_chapters = _render_chapters(document)

    # Copies every entry from the original archive unchanged except the
    # chapters that were translated, instead of asking ebooklib to
    # regenerate the whole container — ebooklib's read/write round-trip
    # rebuilds the OPF/NCX/nav from its own object model and isn't
    # guaranteed to preserve everything byte-for-byte (obscure manifest
    # properties, formatting, ordering). This way CSS, fonts, images and
    # all package metadata are passed through untouched.
    with zipfile.ZipFile(source_path) as src_zip:
        original_names = {info.filename for info in src_zip.infolist()}
        missing = set(rendered_chapters) - original_names
        if missing:
            # Checked before writing anything to output_path, so a
            # mismatched chapter fails loudly instead of silently leaving
            # that chapter's original (untranslated) text in an otherwise
            # seemingly-complete output file.
            raise EpubReconstructionError(
                f"Estos capítulos no se encontraron en el ZIP original, su "
                f"traducción no se pudo escribir: {sorted(missing)}"
            )

        with zipfile.ZipFile(output_path, "w") as dst_zip:
            for info in src_zip.infolist():
                if info.filename in rendered_chapters:
                    data = rendered_chapters[info.filename]
                else:
                    data = src_zip.read(info.filename)
                compress_type = (
                    zipfile.ZIP_STORED
                    if info.filename == _MIMETYPE_ENTRY
                    else zipfile.ZIP_DEFLATED
                )
                dst_zip.writestr(info, data, compress_type=compress_type)
