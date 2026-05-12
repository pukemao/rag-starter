"""Source code document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .text import create_loader as create_text_loader
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="source_code",
    title="Source code",
    extensions=(
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".kts",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".sql",
        ".css",
        ".scss",
        ".less",
        ".vue",
        ".svelte",
    ),
    module=__name__,
    dependencies=("langchain-community",),
    description="Loads Python with PythonLoader and other source files with TextLoader.",
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create a source-code loader."""

    path = Path(file_path)
    if path.suffix.lower() == ".py":
        return create_loader_instance(
            path,
            ("langchain_community.document_loaders", "langchain_community.document_loaders.python"),
            "PythonLoader",
            SPEC.dependencies,
            **kwargs,
        )
    return create_text_loader(path, **kwargs)
