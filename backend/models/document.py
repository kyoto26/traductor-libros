from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class Block:
    id: str
    type: Literal["heading", "paragraph", "list_item"]
    text: str
    order: int
    translated_text: Optional[str] = None


@dataclass
class Chapter:
    id: str
    title: Optional[str]
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Document:
    metadata: dict
    chapters: list[Chapter] = field(default_factory=list)

    def all_blocks(self) -> list[Block]:
        blocks: list[Block] = []
        for chapter in self.chapters:
            blocks.extend(sorted(chapter.blocks, key=lambda b: b.order))
        return blocks
