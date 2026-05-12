"""Registry that maps file extensions to concrete loader modules."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import UnsupportedFormatError, normalize_extension

_LOADER_MODULES = (
    "src.loader.text",
    "src.loader.csv",
    "src.loader.tsv",
    "src.loader.json",
    "src.loader.pdf",
    "src.loader.markdown",
    "src.loader.html",
    "src.loader.mhtml",
    "src.loader.xml",
    "src.loader.word",
    "src.loader.powerpoint",
    "src.loader.excel",
    "src.loader.email",
    "src.loader.chm",
    "src.loader.epub",
    "src.loader.odt",
    "src.loader.org",
    "src.loader.rst",
    "src.loader.rtf",
    "src.loader.subtitle",
    "src.loader.image",
    "src.loader.notebook",
    "src.loader.toml",
    "src.loader.yaml",
    "src.loader.source_code",
)


def _load_specs() -> tuple[LoaderSpec, ...]:
    specs: list[LoaderSpec] = []
    for module_name in _LOADER_MODULES:
        module = import_module(module_name)
        specs.append(module.SPEC)
    return tuple(specs)


LOADER_SPECS = _load_specs()
EXTENSION_REGISTRY: dict[str, LoaderSpec] = {
    extension: spec for spec in LOADER_SPECS for extension in spec.extensions
}


def supported_extensions() -> tuple[str, ...]:
    """Return all registered file extensions."""

    return tuple(sorted(EXTENSION_REGISTRY))


def loader_for_extension(path_or_extension: str | Path) -> LoaderSpec:
    """Return loader metadata for a path or extension."""

    extension = normalize_extension(path_or_extension)
    try:
        return EXTENSION_REGISTRY[extension]
    except KeyError as exc:
        supported = ", ".join(supported_extensions())
        raise UnsupportedFormatError(f"暂不支持扩展名 {extension}。已支持: {supported}") from exc


def get_loader(file_path: str | Path, **kwargs: Any) -> Any:
    """Create the LangChain loader registered for ``file_path``."""

    spec = loader_for_extension(file_path)
    module = import_module(spec.module)
    return module.create_loader(file_path, **kwargs)


def load_documents(file_path: str | Path, **kwargs: Any) -> list[Any]:
    """Load documents from a single file eagerly."""

    return list(get_loader(file_path, **kwargs).load())


def lazy_load_documents(file_path: str | Path, **kwargs: Any) -> Any:
    """Yield documents from a single file lazily when supported."""

    loader = get_loader(file_path, **kwargs)
    if hasattr(loader, "lazy_load"):
        yield from loader.lazy_load()
    else:
        yield from loader.load()
