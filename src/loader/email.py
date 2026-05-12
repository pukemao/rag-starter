"""Email document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="email",
    title="Email",
    extensions=(".eml", ".msg"),
    module=__name__,
    dependencies=("langchain-community", "unstructured"),
    description="Loads email files with LangChain UnstructuredEmailLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredEmailLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.email"),
        "UnstructuredEmailLoader",
        SPEC.dependencies,
        **kwargs,
    )
