"""Compiled HTML Help document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="chm",
    title="Compiled HTML Help",
    extensions=(".chm",),
    module=__name__,
    dependencies=("langchain-community", "unstructured", "pychm"),
    description="Loads CHM files with LangChain UnstructuredCHMLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredCHMLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.chm"),
        "UnstructuredCHMLoader",
        SPEC.dependencies,
        **kwargs,
    )
