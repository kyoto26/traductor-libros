from models.document import Document


def reconstruct(document: Document) -> str:
    paragraphs = [
        block.translated_text if block.translated_text is not None else block.text
        for block in document.all_blocks()
    ]
    return "\n\n".join(paragraphs)
