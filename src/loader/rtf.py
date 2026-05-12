"""Rich Text Format document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="rtf",
    title="RTF",
    extensions=(".rtf",),
    module=__name__,
    dependencies=("langchain-community", "unstructured"),
    description="Loads RTF documents with LangChain UnstructuredRTFLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredRTFLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.rtf"),
        "UnstructuredRTFLoader",
        SPEC.dependencies,
        **kwargs,
    )
