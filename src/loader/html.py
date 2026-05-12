"""HTML document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="html",
    title="HTML",
    extensions=(".html", ".htm"),
    module=__name__,
    dependencies=("langchain-community", "beautifulsoup4"),
    description="Loads HTML with LangChain BSHTMLLoader.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a LangChain BSHTMLLoader."""

    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.html_bs"),
        "BSHTMLLoader",
        SPEC.dependencies,
        **kwargs,
    )
