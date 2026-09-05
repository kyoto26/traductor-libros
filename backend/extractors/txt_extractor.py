import re
from pathlib import Path

from charset_normalizer import from_bytes

from models.document import Block, Chapter, Document

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")

# Codepages legacy de un solo byte se solapan entre sí (una misma secuencia
# de bytes puede ser válida en varios), así que sin restringir candidatos
# charset-normalizer puede elegir uno de Europa del Este/Central para texto
# que en realidad es Europa Occidental. Se acota a las codificaciones
# relevantes para los idiomas que esta herramienta traduce (es/en/fr/pt/it/de).
#
# LIMITACIÓN CONOCIDA (verificada empíricamente, no solo teórica): esto NO
# garantiza rechazar un archivo en una codificación legacy fuera de este
# conjunto (p. ej. cp1250 real para polaco/checo). Los codecs de un solo byte
# tienen mapeo total (casi cualquier byte "decodifica" a algo), así que
# _decode() solo lanza ValueError cuando el score de coherencia de
# charset-normalizer descarta TODOS los candidatos occidentales — lo cual
# pasa de forma confiable con texto largo y muy distintivo, pero NO con
# texto corto o con pocos caracteres especiales: un .txt real en cp1250
# como "Dziękuję bardzo za pomoc." se decodifica en silencio como cp1252,
# dando "Dziêkujê bardzo za pomoc." (mojibake, sin ningún error). Si este
# proyecto necesita soportar idiomas de Europa Central/del Este como origen,
# hay que ampliar esta lista (o pedir la codificación al usuario en vez de
# adivinarla).
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
