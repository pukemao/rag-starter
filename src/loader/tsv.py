"""TSV document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="tsv",
    title="TSV",
    extensions=(".tsv",),
    module=__name__,
    dependencies=("langchain-community", "unstructured"),
    description="Loads tab-separated values with LangChain UnstructuredTSVLoader.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredTSVLoader."""

    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.tsv"),
        "UnstructuredTSVLoader",
        SPEC.dependencies,
        **kwargs,
    )
