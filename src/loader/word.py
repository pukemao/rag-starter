"""Microsoft Word document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="word",
    title="Word",
    extensions=(".doc", ".docx"),
    module=__name__,
    dependencies=("langchain-community", "unstructured", "python-docx"),
    description="Loads Word documents with LangChain UnstructuredWordDocumentLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredWordDocumentLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.word_document"),
        "UnstructuredWordDocumentLoader",
        SPEC.dependencies,
        **kwargs,
    )
