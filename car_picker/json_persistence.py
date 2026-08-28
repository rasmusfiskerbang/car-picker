"""Small atomic JSON replacement primitive shared by persistence callers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


def write_json_atomically(path: Path, value: object) -> None:
    """Serialize one JSON value through a same-directory temporary file."""
    resolved_path = path.resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{resolved_path.name}.",
            suffix=".tmp",
            dir=resolved_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                value,
                temporary_file,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, resolved_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_bytes_atomically(path: Path, value: bytes) -> None:
    """Replace one file with exact bytes through a same-directory temporary file."""
    resolved_path = path.resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{resolved_path.name}.",
            suffix=".tmp",
            dir=resolved_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(value)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, resolved_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
