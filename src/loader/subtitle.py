"""Subtitle document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="subtitle",
    title="Subtitle",
    extensions=(".srt",),
    module=__name__,
    dependencies=("langchain-community", "pysrt"),
    description="Loads subtitle files with LangChain SRTLoader.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a LangChain SRTLoader."""

    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.srt"),
        "SRTLoader",
        SPEC.dependencies,
        **kwargs,
    )
