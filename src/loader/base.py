"""Shared loader metadata types."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol


class LangChainLoader(Protocol):
    """Minimal protocol implemented by LangChain document loaders."""

    def load(self) -> list[Any]:
        """Load all documents eagerly."""

    def lazy_load(self) -> Iterator[Any]:
        """Load documents lazily when supported by the underlying loader."""


@dataclass(frozen=True, slots=True)
class LoaderSpec:
    """Metadata used to route a file extension to a loader module."""

    key: str
    title: str
    extensions: tuple[str, ...]
    module: str
    dependencies: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        normalized = tuple(ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in self.extensions)
        object.__setattr__(self, "extensions", normalized)
