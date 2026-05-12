"""MHTML document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="mhtml",
    title="MHTML",
    extensions=(".mht", ".mhtml"),
    module=__name__,
    dependencies=("langchain-community", "beautifulsoup4"),
    description="Loads archived web pages with LangChain MHTMLLoader.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a LangChain MHTMLLoader."""

    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.mhtml"),
        "MHTMLLoader",
        SPEC.dependencies,
        **kwargs,
    )
