"""EPUB document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="epub",
    title="EPUB",
    extensions=(".epub",),
    module=__name__,
    dependencies=("langchain-community", "unstructured", "pandoc"),
    description="Loads EPUB books with LangChain UnstructuredEPubLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredEPubLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.epub"),
        "UnstructuredEPubLoader",
        SPEC.dependencies,
        **kwargs,
    )
