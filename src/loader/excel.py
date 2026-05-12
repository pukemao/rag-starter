"""Microsoft Excel document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="excel",
    title="Excel",
    extensions=(".xls", ".xlsx"),
    module=__name__,
    dependencies=("langchain-community", "unstructured", "openpyxl"),
    description="Loads spreadsheets with LangChain UnstructuredExcelLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredExcelLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.excel"),
        "UnstructuredExcelLoader",
        SPEC.dependencies,
        **kwargs,
    )
