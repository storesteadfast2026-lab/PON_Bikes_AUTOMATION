"""Safe file-transfer helpers for the existing Translogic integration.

These helpers deliberately do not decide business readiness. They only inspect the
configured filesystem, discover the real numbered import-file pattern, and perform
an explicit, verified copy after the calling view has obtained operator confirmation.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path

NUMBERED_IMPORT_PATTERN = re.compile(r"^(.*?)([1-5])(\.[^.]+)$", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_numbered_import_set(directory: Path) -> dict:
    """Discover exactly one coherent real file set numbered 1..5.

    No product/import filename is assumed. A valid set is five existing files that
    share the same prefix and extension and differ only by a final number 1..5.
    If zero or multiple complete sets exist, the result is intentionally not ready.
    """
    directory = Path(directory)
    result = {
        "available": False,
        "directory": str(directory),
        "pattern": "",
        "extension": "",
        "files": [],
        "oldest": None,
        "reason": "",
    }
    if not directory.is_dir():
        result["reason"] = "The configured Translogic import directory is not accessible from PON."
        return result

    groups: dict[tuple[str, str], dict[int, Path]] = {}
    display_prefix: dict[tuple[str, str], str] = {}
    display_extension: dict[tuple[str, str], str] = {}
    try:
        entries = list(directory.iterdir())
    except OSError as exc:
        result["reason"] = f"The Translogic import directory could not be read: {exc}"
        return result

    for path in entries:
        if not path.is_file():
            continue
        match = NUMBERED_IMPORT_PATTERN.match(path.name)
        if not match:
            continue
        prefix, number_text, extension = match.groups()
        key = (prefix.casefold(), extension.casefold())
        groups.setdefault(key, {})[int(number_text)] = path
        display_prefix.setdefault(key, prefix)
        display_extension.setdefault(key, extension)

    complete = []
    for key, numbered in groups.items():
        if set(numbered) == {1, 2, 3, 4, 5}:
            complete.append((key, numbered))

    if not complete:
        result["reason"] = "No single complete numbered Translogic file set (1-5) was found."
        return result
    if len(complete) > 1:
        patterns = [f"{display_prefix[key]}{{1-5}}{display_extension[key]}" for key, _ in complete]
        result["reason"] = "Multiple complete numbered file sets were found: " + ", ".join(sorted(patterns))
        return result

    key, numbered = complete[0]
    files = []
    for number in range(1, 6):
        path = numbered[number]
        stat = path.stat()
        files.append(
            {
                "number": number,
                "name": path.name,
                "path": str(path),
                "mtime": stat.st_mtime,
                "size": stat.st_size,
            }
        )
    oldest = min(files, key=lambda item: (item["mtime"], item["name"].casefold()))
    result.update(
        {
            "available": True,
            "pattern": f"{display_prefix[key]}{{1-5}}{display_extension[key]}",
            "extension": display_extension[key].lower(),
            "files": files,
            "oldest": oldest,
            "reason": "",
        }
    )
    return result


def copy_file_verified(source: Path, destination: Path) -> dict:
    """Copy a file atomically where possible and verify destination SHA-256."""
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise FileNotFoundError(f"Source file does not exist: {source}")
    if not destination.parent.is_dir():
        raise FileNotFoundError(f"Destination folder does not exist: {destination.parent}")

    source_hash = sha256_file(source)
    existed = destination.exists()
    previous_hash = sha256_file(destination) if existed and destination.is_file() else ""
    previous_mtime = destination.stat().st_mtime if existed else None

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.name}.",
            suffix=".pon-copy",
            dir=str(destination.parent),
            delete=False,
        ) as temp_handle:
            temp_path = Path(temp_handle.name)
            with source.open("rb") as source_handle:
                shutil.copyfileobj(source_handle, temp_handle, length=1024 * 1024)
            temp_handle.flush()
            os.fsync(temp_handle.fileno())

        if sha256_file(temp_path) != source_hash:
            raise OSError("Temporary destination verification failed before replacement.")
        os.replace(temp_path, destination)
        temp_path = None
        destination_hash = sha256_file(destination)
        if destination_hash != source_hash:
            raise OSError("Destination verification failed after copy.")
        return {
            "source_sha256": source_hash,
            "destination_sha256": destination_hash,
            "replaced": existed,
            "previous_sha256": previous_hash,
            "previous_mtime": previous_mtime,
            "size": destination.stat().st_size,
        }
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
