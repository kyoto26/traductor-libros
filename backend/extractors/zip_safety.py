import zipfile
from pathlib import Path

_DEFAULT_MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024  # 500 MB
_DEFAULT_MAX_COMPRESSION_RATIO = 100
_DEFAULT_MAX_ENTRY_COUNT = 10_000


class ZipSafetyError(Exception):
    """Base class for zip bomb / zip slip validation failures."""


class ZipBombError(ZipSafetyError):
    pass


class ZipSlipError(ZipSafetyError):
    pass


def check_zip_bomb(
    zip_file: zipfile.ZipFile,
    max_uncompressed_size: int = _DEFAULT_MAX_UNCOMPRESSED_SIZE,
    max_compression_ratio: int = _DEFAULT_MAX_COMPRESSION_RATIO,
    max_entries: int = _DEFAULT_MAX_ENTRY_COUNT,
) -> None:
    # The ZIP central directory stores each entry's declared uncompressed
    # size (file_size) and compressed size (compress_size) as metadata, so
    # this reads infolist() only — no entry content is decompressed here.
    #
    # KNOWN LIMITATION: this trusts the central directory's declared sizes.
    # It's the same mechanism standard zip bomb detectors use, and since
    # epub_extractor.py will later read content with the same library
    # (zipfile, directly or via ebooklib) that produced these numbers, there
    # is no mismatch between what's inspected here and what actually gets
    # read. But it is not an absolute guarantee against a deliberately
    # corrupt ZIP exploiting low-level parser ambiguities — full mitigation
    # for that also requires bounded/streaming reads during the actual
    # extraction (hard-capping bytes read regardless of declared size),
    # which belongs to the real extraction step, not this pre-check.
    infolist = zip_file.infolist()

    if len(infolist) > max_entries:
        raise ZipBombError(
            f"El ZIP tiene {len(infolist)} entries, supera el límite de {max_entries}."
        )

    total_uncompressed = 0
    for info in infolist:
        total_uncompressed += info.file_size

        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > max_compression_ratio:
                raise ZipBombError(
                    f"El entry {info.filename!r} tiene un ratio de compresión de "
                    f"{ratio:.0f}x, supera el límite de {max_compression_ratio}x."
                )

    if total_uncompressed > max_uncompressed_size:
        raise ZipBombError(
            f"El ZIP descomprime a {total_uncompressed} bytes, supera el "
            f"límite de {max_uncompressed_size} bytes."
        )


def check_safe_member_names(zip_file: zipfile.ZipFile, dest_dir: Path) -> None:
    dest_dir = dest_dir.resolve()

    for info in zip_file.infolist():
        name = info.filename

        # The ZIP spec mandates "/" as the path separator; a backslash in an
        # entry name is non-conformant and exactly the kind of ambiguity
        # some zip slip variants rely on to confuse less strict parsers.
        if "\\" in name:
            raise ZipSlipError(f"Nombre de entry no válido (contiene '\\\\'): {name!r}")

        # Resolving the joined path and checking containment catches any
        # traversal trick (../, absolute paths, mixed separators) with one
        # check, instead of pattern-matching "../" as a substring, which is
        # easy to bypass with alternate encodings.
        target = (dest_dir / name).resolve()
        if not target.is_relative_to(dest_dir):
            raise ZipSlipError(
                f"El entry {name!r} apunta fuera del directorio de extracción."
            )


def validate_zip_safety(zip_path: Path, dest_dir: Path) -> zipfile.ZipFile:
    zip_file = zipfile.ZipFile(zip_path)

    try:
        check_zip_bomb(zip_file)
        check_safe_member_names(zip_file, dest_dir)
    except ZipSafetyError:
        zip_file.close()
        raise

    return zip_file
