"""TOML document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="toml",
    title="TOML",
    extensions=(".toml",),
    module=__name__,
    dependencies=("langchain-community",),
    description="Loads TOML files with LangChain TOMLLoader when available.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a LangChain TOMLLoader."""

    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.toml"),
        "TomlLoader",
        SPEC.dependencies,
        **kwargs,
    )
