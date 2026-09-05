from translator.chunker import Chunk

_GLOSSARY_INSTRUCTION = (
    "Usa exactamente estas traducciones para los siguientes términos, "
    "sin importar el contexto:"
)

_PREVIOUS_CONTEXT_TEMPLATE = (
    "Este es el final del fragmento anterior, solo para mantener "
    'coherencia — NO lo traduzcas ni lo incluyas en tu respuesta: "{context}"'
)


def _format_glossary(glossary: dict[str, str] | None) -> str | None:
    if not glossary:
        return None

    terms = "\n".join(
        f"- {term} → {translation}" for term, translation in glossary.items()
    )
    return f"{_GLOSSARY_INSTRUCTION}\n{terms}"


def _format_previous_context(context: str | None) -> str | None:
    if not context:
        return None

    return _PREVIOUS_CONTEXT_TEMPLATE.format(context=context)


def build_translation_request(
    chunk: Chunk,
    glossary: dict[str, str] | None = None,
) -> tuple[str, str | None]:
    # Glossary first (hard rule the model must follow), previous-chunk
    # context second (soft coherence hint) — kept as separate labeled
    # sections instead of one blended sentence, so a model that already
    # struggles with ambiguous instructions doesn't confuse a rule with
    # a hint.
    sections = [
        section
        for section in (
            _format_glossary(glossary),
            _format_previous_context(chunk.context),
        )
        if section is not None
    ]

    formatted_context = "\n\n".join(sections) if sections else None
    return chunk.text, formatted_context
