"""Plain text document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="text",
    title="Plain text",
    extensions=(".txt", ".log"),
    module=__name__,
    dependencies=("langchain-community",),
    description="Loads plain text-like files with LangChain TextLoader.",
)


def create_loader(file_path: str | Path, *, encoding: str | None = "utf-8", **kwargs: Any) -> Any:
    """Create a LangChain TextLoader."""

    if encoding is not None:
        kwargs.setdefault("encoding", encoding)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.text"),
        "TextLoader",
        SPEC.dependencies,
        **kwargs,
    )
