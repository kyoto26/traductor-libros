from dataclasses import dataclass, field
from typing import Any, Literal, Optional


@dataclass
class Block:
    id: str
    type: Literal["heading", "paragraph", "list_item"]
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
