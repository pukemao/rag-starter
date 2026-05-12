"""YAML document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .text import create_loader as create_text_loader

SPEC = LoaderSpec(
    key="yaml",
    title="YAML",
    extensions=(".yaml", ".yml"),
    module=__name__,
    dependencies=("langchain-community",),
    description="Loads YAML as plain text with LangChain TextLoader.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a text loader for YAML files."""

    return create_text_loader(file_path, **kwargs)
