"""Directory loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import load_documents, supported_extensions


def iter_supported_files(directory: str | Path, *, recursive: bool = True) -> list[Path]:
    """Return files with extensions registered in this package."""

    root = Path(directory)
    pattern = "**/*" if recursive else "*"
    supported = set(supported_extensions())
    return sorted(path for path in root.glob(pattern) if path.is_file() and path.suffix.lower() in supported)


def load_directory(directory: str | Path, *, recursive: bool = True, **loader_kwargs: Any) -> list[Any]:
    """Load every supported file under a directory."""

    documents: list[Any] = []
    for path in iter_supported_files(directory, recursive=recursive):
        documents.extend(load_documents(path, **loader_kwargs))
    return documents
