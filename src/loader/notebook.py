"""Jupyter Notebook document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="notebook",
    title="Jupyter Notebook",
    extensions=(".ipynb",),
    module=__name__,
    dependencies=("langchain-community", "nbformat"),
    description="Loads notebooks with LangChain NotebookLoader.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a LangChain NotebookLoader."""

    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.notebook"),
        "NotebookLoader",
        SPEC.dependencies,
        **kwargs,
    )
