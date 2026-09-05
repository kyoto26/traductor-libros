from dataclasses import dataclass, field
from typing import Any, Literal, Optional


@dataclass
class Block:
    id: str
    type: Literal["heading", "paragraph", "list_item", "image"]
    text: str
    order: int
    translated_text: Optional[str] = None

    # Implementation detail of HTML/bs4-based extractors (currently
    # epub_extractor.py): holds a reference to the BeautifulSoup tag this
    # block's text came from, so a matching reconstructor can locate and
    # mutate that exact tag in place. NOT part of the intermediate
    # representation's contract — chunker.py, prompt_builder.py and
    # llm_client.py must never read or depend on this field. txt (and any
    # future non-HTML format) leaves it as None.
    source_element: Any | None = None

    # Implementation detail of pdf_extractor.py: the 1-indexed page a block
    # started on (a block spanning a page break keeps its starting page).
    # Low-commitment provenance info, NOT tied to any particular
    # reconstruction strategy — unlike source_element/source_soup above,
    # this doesn't assume how (or whether) pdf_reconstructor.py will use
    # the original file at all. Not part of the intermediate
    # representation's contract.
    page_number: int | None = None

    # Implementation detail of pdf_extractor.py, only set on type == "image"
    # blocks: the image's raw bytes in their original encoding, its
    # extension (e.g. "png", used to pick a filename pdf_reconstructor.py
    # can reference from HTML), and its original pixel dimensions (a sizing
    # hint for the reconstructor, not a layout instruction). Same rule as
    # the other extractor-specific fields above: not part of the
    # intermediate representation's contract. `text` is empty for image
    # blocks — chunker.py filters type == "image" out before translation,
    # so they never reach prompt_builder.py or llm_client.py.
    image_data: bytes | None = None
    image_ext: str | None = None
    image_width: int | None = None
    image_height: int | None = None


@dataclass
class Chapter:
    id: str
    title: Optional[str]
    blocks: list[Block] = field(default_factory=list)

    # Same rule as Block.source_element above: HTML/bs4-extractor-specific,
    # holds the parsed BeautifulSoup tree for this chapter. Not part of the
    # intermediate representation's contract.
    source_soup: Any | None = None

    # Same rule again: the original archive entry name this chapter's
    # content came from (e.g. "chap1.xhtml"), needed by a matching
    # reconstructor to know which entry to replace when rebuilding the
    # container archive. Not part of the intermediate representation's
    # contract.
    source_file_name: str | None = None


@dataclass
class Document:
    metadata: dict
    chapters: list[Chapter] = field(default_factory=list)

    def all_blocks(self) -> list[Block]:
        blocks: list[Block] = []
        for chapter in self.chapters:
            blocks.extend(sorted(chapter.blocks, key=lambda b: b.order))
        return blocks
