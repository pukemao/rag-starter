"""Markdown document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="markdown",
    title="Markdown",
    extensions=(".md", ".markdown", ".mdx"),
    module=__name__,
    dependencies=("langchain-community", "unstructured"),
    description="Loads Markdown with LangChain UnstructuredMarkdownLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredMarkdownLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.markdown"),
        "UnstructuredMarkdownLoader",
        SPEC.dependencies,
        **kwargs,
    )
