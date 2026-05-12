"""OpenDocument Text loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="odt",
    title="OpenDocument Text",
    extensions=(".odt",),
    module=__name__,
    dependencies=("langchain-community", "unstructured"),
    description="Loads ODT documents with LangChain UnstructuredODTLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredODTLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.odt"),
        "UnstructuredODTLoader",
        SPEC.dependencies,
        **kwargs,
    )
