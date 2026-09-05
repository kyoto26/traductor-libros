import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_TERM_LENGTH = 100
_MAX_TRANSLATION_LENGTH = 100

# Newlines/control chars are stripped rather than just discouraged: in the
# "- term -> translation" line format prompt_builder.py generates, a newline
# is what would let an attacker fake a new, separate instruction line. With
# no newlines allowed, whatever ends up in `term`/`translation` is trapped
# inside a single "- ..." line and can't impersonate a fresh instruction.
_CONTROL_CHARS_RE = re.compile(r"[\r\n\t\x00-\x1f]+")

# WEAK DEFENSE, DOCUMENTED ON PURPOSE: this is a denylist of common prompt
# injection phrasing, not a real security boundary. It stops the laziest
# attempts (this exact phrasing, in these languages) but is trivially
# bypassed by paraphrasing, typos, another language, or splitting the
# payload across `term` and `translation` so neither half matches alone.
# There is no reliable way to distinguish a short, grammatically plausible
# instruction from a legitimate glossary term using text patterns alone —
# once a term/translation is short enough to pass the length check, it's
# indistinguishable at the character level from real instruction text. The
# structural defense above (no newlines, capped length) is what actually
# limits the blast radius; this pattern list is best-effort on top of it.
_SUSPICIOUS_PATTERNS = [
    re.compile(r"ignor\w*.{0,30}instruccion", re.IGNORECASE),
    re.compile(r"ignore.{0,30}instructions", re.IGNORECASE),
    re.compile(r"disregard.{0,30}(instructions|rules|prompt)", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"act[uú]a\s+como", re.IGNORECASE),
]


class GlossaryError(Exception):
    """Raised when the glossary source itself is malformed (bad JSON, wrong
    shape). Not raised for individual bad entries within an otherwise valid
    glossary — those are skipped with a warning instead, see _sanitize_entry.
    """


def _is_suspicious(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SUSPICIOUS_PATTERNS)


def _sanitize_entry(term: str, translation: str) -> tuple[str, str] | None:
    clean_term = _CONTROL_CHARS_RE.sub(" ", term).strip()
    clean_translation = _CONTROL_CHARS_RE.sub(" ", translation).strip()

    if not clean_term or not clean_translation:
        logger.warning("Skipping glossary entry with empty term or translation.")
        return None

    if len(clean_term) > _MAX_TERM_LENGTH or len(clean_translation) > _MAX_TRANSLATION_LENGTH:
        logger.warning(
            "Skipping glossary entry %r -> %r: exceeds the %d-character limit.",
            term,
            translation,
            _MAX_TERM_LENGTH,
        )
        return None

    if _is_suspicious(clean_term) or _is_suspicious(clean_translation):
        logger.warning(
            "Skipping glossary entry %r -> %r: matches a suspicious instruction-like pattern.",
            term,
            translation,
        )
        return None

    return clean_term, clean_translation


class Glossary:
    def __init__(self, entries: dict[str, str]):
        self._entries = entries

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Glossary":
        entries: dict[str, str] = {}
        for term, translation in data.items():
            sanitized = _sanitize_entry(str(term), str(translation))
            if sanitized is None:
                continue
            clean_term, clean_translation = sanitized
            entries[clean_term] = clean_translation

        return cls(entries)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "Glossary":
        path = Path(path)

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GlossaryError(f"No se pudo leer el glosario desde {path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise GlossaryError(
                f"El glosario en {path} debe ser un objeto JSON término -> traducción."
            )

        return cls.from_dict(raw)

    def find_matches(self, text: str) -> dict[str, str]:
        matches: dict[str, str] = {}
        for term, translation in self._entries.items():
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            if pattern.search(text):
                matches[term] = translation

        return matches

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return bool(self._entries)
