"""CSV document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="csv",
    title="CSV",
    extensions=(".csv",),
    module=__name__,
    dependencies=("langchain-community",),
    description="Loads comma-separated values with LangChain CSVLoader.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a LangChain CSVLoader."""

    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.csv_loader"),
        "CSVLoader",
        SPEC.dependencies,
        **kwargs,
    )
