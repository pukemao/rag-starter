"""Generic unstructured document loader fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="unstructured",
    title="Generic unstructured file",
    extensions=(".",),
    module=__name__,
    dependencies=("langchain-community", "unstructured"),
    description="Fallback factory for formats supported by UnstructuredFileLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredFileLoader for any supported file."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.unstructured"),
        "UnstructuredFileLoader",
        SPEC.dependencies,
        **kwargs,
    )
