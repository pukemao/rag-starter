"""JSON and JSON Lines document loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .base import LoaderSpec
from .utils import import_loader_class

SPEC = LoaderSpec(
    key="json",
    title="JSON / JSONL",
    extensions=(".json", ".jsonl", ".ndjson"),
    module=__name__,
    dependencies=("langchain-community", "jq"),
    description="Loads JSON with LangChain JSONLoader; jq_schema defaults to '.'.",
)


def create_loader(
    file_path: str | Path,
    *,
    jq_schema: str = ".",
    content_key: str | None = None,
    metadata_func: Callable[..., dict[str, Any]] | None = None,
    text_content: bool = False,
    json_lines: bool | None = None,
    **kwargs: Any,
) -> Any:
    """Create a LangChain JSONLoader.

    ``json_lines`` defaults to True for ``.jsonl`` and ``.ndjson`` files.
    """

    path = Path(file_path)
    if json_lines is None:
        json_lines = path.suffix.lower() in {".jsonl", ".ndjson"}

    loader_cls = import_loader_class(
        ("langchain_community.document_loaders", "langchain_community.document_loaders.json_loader"),
        "JSONLoader",
        SPEC.dependencies,
    )
    return loader_cls(
        str(path),
        jq_schema=jq_schema,
        content_key=content_key,
        metadata_func=metadata_func,
        text_content=text_content,
        json_lines=json_lines,
        **kwargs,
    )
