"""Image document loader with OCR support."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="image",
    title="Image",
    extensions=(".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".heic"),
    module=__name__,
    dependencies=("langchain-community", "unstructured", "pillow", "pytesseract"),
    description="Loads image text with LangChain UnstructuredImageLoader.",
)


def create_loader(file_path: str | Path, *, mode: str = "elements", **kwargs: Any) -> Any:
    """Create a LangChain UnstructuredImageLoader."""

    kwargs.setdefault("mode", mode)
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.image"),
        "UnstructuredImageLoader",
        SPEC.dependencies,
        **kwargs,
    )
