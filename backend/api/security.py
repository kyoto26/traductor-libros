import os
import re
import unicodedata

import magic

DEFAULT_MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

_ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    ".epub": {"application/epub+zip", "application/zip"},
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
}

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_FILENAME_LENGTH = 200

# The "magic numbers" that identify a file's real type are always at
# the start; there's no need (and no benefit) to pass libmagic the
# entire file, even if the caller already holds it in memory.
_MAGIC_SNIFF_SIZE = 4096


class SecurityValidationError(Exception):
    pass


class FileTooLargeError(SecurityValidationError):
    pass


class InvalidFileTypeError(SecurityValidationError):
    pass


def get_max_upload_size() -> int:
    raw = os.environ.get("MAX_UPLOAD_SIZE")
    if raw is None:
        return DEFAULT_MAX_UPLOAD_SIZE
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_MAX_UPLOAD_SIZE


def validate_file_size(size_bytes: int) -> None:
    max_size = get_max_upload_size()
    if size_bytes > max_size:
        raise FileTooLargeError(
            f"El archivo pesa {size_bytes} bytes, supera el límite de {max_size} bytes."
        )


def validate_file_type(content: bytes, expected_ext: str) -> str:
    expected_ext = expected_ext.lower()
    allowed_mimes = _ALLOWED_MIME_TYPES.get(expected_ext)
    if allowed_mimes is None:
        raise InvalidFileTypeError(f"Extensión no soportada: {expected_ext}")

    detected_mime = magic.from_buffer(content[:_MAGIC_SNIFF_SIZE], mime=True)
    if detected_mime not in allowed_mimes:
        raise InvalidFileTypeError(
            f"El contenido real del archivo ({detected_mime}) no coincide "
            f"con lo esperado para {expected_ext} ({', '.join(sorted(allowed_mimes))})."
        )
    return detected_mime


def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(filename)
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    name, ext = os.path.splitext(filename)
    name = _SAFE_FILENAME_RE.sub("_", name).strip("._") or "archivo"
    ext = _SAFE_FILENAME_RE.sub("", ext.lower())

    safe_name = f"{name}{ext}"
    if len(safe_name) > _MAX_FILENAME_LENGTH:
        overflow = len(safe_name) - _MAX_FILENAME_LENGTH
        name = name[:-overflow] if overflow < len(name) else name[:1]
        safe_name = f"{name}{ext}"

    return safe_name
