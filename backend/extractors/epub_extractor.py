import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from ebooklib import epub

from extractors.zip_safety import validate_zip_safety
from models.document import Block, Chapter, Document

_CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

_BLOCK_TAG_TYPES = {tag: "heading" for tag in _HEADING_TAGS}
_BLOCK_TAG_TYPES["p"] = "paragraph"
_BLOCK_TAG_TYPES["li"] = "list_item"

# Tags that don't map to a Block type on their own but still carry
# translatable text in real-world EPUBs (table cells, blockquotes, loose
# text sitting directly in a <div> with no wrapping <p>). Treated as
# "paragraph", the closest existing type, so this text isn't silently
# dropped — losing translatable content is worse than an imperfect type.
_FALLBACK_PARAGRAPH_TAGS = {"td", "th", "blockquote", "div"}

_ALL_TEXT_TAGS = list(set(_BLOCK_TAG_TYPES) | _FALLBACK_PARAGRAPH_TAGS)


class EpubParsingError(Exception):
    """Raised when an EPUB can't be parsed. Wraps ebooklib/lxml's
    unpredictable failure modes (malformed XML, broken manifest references,
    etc.) into one clear, user-facing error instead of a raw traceback.
    """


def _clean_text(tag) -> str:
    # get_text(strip=True) strips each text fragment individually before
    # joining them, which destroys genuine inter-word whitespace that lives
    # in its own text node (e.g. the space before "<em>enfasis</em>" in
    # "con <em>enfasis</em>." becomes "conenfasis."). Passing a fixed
    # separator instead just moves the bug: it inserts a space between
    # EVERY fragment pair regardless of whether one existed in the source,
    # producing wrong spacing before punctuation (e.g. "enfasis .").
    # Calling get_text() with no separator and no per-fragment stripping
    # preserves exactly the whitespace the source actually has between
    # inline elements; the split()+join pass only collapses incidental
    # whitespace from pretty-printed/indented source XML.
    return " ".join(tag.get_text().split())


def _extract_blocks(soup: BeautifulSoup, chapter_id: str) -> list[Block]:
    blocks: list[Block] = []

    for tag in soup.find_all(_ALL_TEXT_TAGS):
        # Skip a container that has a nested text-bearing tag of its own
        # (a <li> wrapping a nested <ul>, a <div> wrapping a <p>, etc.) —
        # the nested tag is captured separately when find_all reaches it,
        # so extracting the container's text too would duplicate content.
        if tag.find(_ALL_TEXT_TAGS) is not None:
            continue

        text = _clean_text(tag)
        if not text:
            continue

        blocks.append(
            Block(
                id=f"{chapter_id}-b{len(blocks)}",
                type=_BLOCK_TAG_TYPES.get(tag.name, "paragraph"),
                text=text,
                order=len(blocks),
                source_element=tag,
            )
        )

    return blocks


def _resolve_opf_dir(zip_file: zipfile.ZipFile) -> str:
    # item.file_name is relative to the OPF's own location, not to the ZIP
    # root — real EPUBs commonly nest content under "EPUB/", "OEBPS/", or no
    # subfolder at all. ebooklib resolves this internally while reading
    # (EpubReader.opf_dir) but never exposes it on the returned EpubBook, so
    # it has to be re-derived here the same way ebooklib does: read
    # META-INF/container.xml, which always points at the real OPF path.
    container_xml = zip_file.read("META-INF/container.xml")
    root = ElementTree.fromstring(container_xml)
    rootfile = root.find(".//c:rootfile", _CONTAINER_NS)
    if rootfile is None or not rootfile.get("full-path"):
        raise EpubParsingError(
            "META-INF/container.xml no tiene un <rootfile full-path=...> válido."
        )

    return posixpath.dirname(rootfile.get("full-path"))


def _is_content_document(item) -> bool:
    # EpubNav is a subclass of EpubHtml (the navigation document is valid,
    # translatable-looking HTML) but it's a table of contents, not book
    # content, so it must be excluded explicitly rather than relying on
    # isinstance(item, epub.EpubHtml) alone.
    return isinstance(item, epub.EpubHtml) and not isinstance(item, epub.EpubNav)


def _extract_chapters(book: epub.EpubBook, opf_dir: str) -> list[Chapter]:
    chapters: list[Chapter] = []

    for idref, _linear in book.spine:
        item = book.get_item_with_id(idref)
        if item is None:
            raise EpubParsingError(
                f"El spine referencia un item inexistente en el manifest: {idref!r}."
            )
        if not _is_content_document(item):
            continue

        chapter_id = f"ch-{len(chapters)}"
        # Parsed as XML (not HTML) because EPUB content documents are
        # well-formed XHTML; this also keeps self-closing tags (like <img/>)
        # intact, which a future reconstructor will need when serializing
        # source_soup back out.
        soup = BeautifulSoup(item.get_content(), "lxml-xml")
        blocks = _extract_blocks(soup, chapter_id)

        title = blocks[0].text if blocks and blocks[0].type == "heading" else None

        chapters.append(
            Chapter(
                id=chapter_id,
                title=title,
                blocks=blocks,
                source_soup=soup,
                source_file_name=posixpath.join(opf_dir, item.file_name),
            )
        )

    return chapters


def extract(file_path: str | Path) -> Document:
    file_path = Path(file_path)

    # Raises ZipSafetyError (zip bomb / zip slip) before anything else ever
    # touches the file's content. Left uncaught here — it's already a clear,
    # specific error and shouldn't be folded into EpubParsingError below.
    # A file that isn't a ZIP at all (an EPUB is always a ZIP container)
    # raises zipfile.BadZipFile instead, which IS wrapped below — from the
    # caller's perspective that's just another way for the EPUB to be
    # invalid.
    try:
        zip_file = validate_zip_safety(file_path, file_path.parent)
    except zipfile.BadZipFile as exc:
        raise EpubParsingError(f"El archivo no es un EPUB/ZIP válido: {exc}") from exc

    try:
        with zip_file:  # only needed for the safety check + opf_dir lookup;
            opf_dir = _resolve_opf_dir(zip_file)  # ebooklib opens its own

        book = epub.read_epub(str(file_path))
        chapters = _extract_chapters(book, opf_dir)
    except EpubParsingError:
        raise
    except Exception as exc:
        # Deliberately broad, unlike the narrow provider-specific catches in
        # llm_client.py: ebooklib/lxml don't expose a documented, enumerable
        # set of failure modes for a malformed EPUB, and this is a boundary
        # where parsing an untrusted, potentially adversarial file must
        # never leak a raw traceback to the caller.
        raise EpubParsingError(f"No se pudo procesar el EPUB: {exc}") from exc

    return Document(
        # source_path lets epub_reconstructor.py copy every unchanged entry
        # (CSS, fonts, images, OPF, NCX, nav) byte-for-byte from the
        # original archive instead of regenerating the container.
        metadata={"formato_original": "epub", "source_path": str(file_path)},
        chapters=chapters,
    )
