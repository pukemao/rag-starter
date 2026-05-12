"""Utilities for lazy-loading LangChain loader classes."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any


class UnsupportedFormatError(ValueError):
    """Raised when no loader has been registered for a file extension."""


class LoaderDependencyError(ImportError):
    """Raised when a loader's optional LangChain dependency is unavailable."""


def normalize_extension(path_or_extension: str | Path) -> str:
    """Return a normalized suffix such as ``.pdf`` from a path or extension."""

    raw = str(path_or_extension).strip().lower()
    if not raw:
        raise UnsupportedFormatError("文件路径或扩展名不能为空")
    if raw.startswith(".") and "/" not in raw and "\\" not in raw:
        return raw
    suffix = Path(raw).suffix
    if not suffix:
        raise UnsupportedFormatError(f"无法从 {path_or_extension!s} 推断文件扩展名")
    return suffix.lower()


def import_loader_class(
    module_candidates: tuple[str, ...],
    class_name: str,
    dependencies: tuple[str, ...] = (),
) -> type[Any]:
    """Import a LangChain loader class only when the loader is actually used."""

    errors: list[str] = []
    for module_name in module_candidates:
        try:
            module = import_module(module_name)
        except ImportError as exc:
            errors.append(f"{module_name}: {exc}")
            continue

        loader_cls = getattr(module, class_name, None)
        if loader_cls is not None:
            return loader_cls
        errors.append(f"{module_name}: 未找到 {class_name}")

    install_hint = " ".join(dependencies) if dependencies else "langchain-community"
    raise LoaderDependencyError(
        f"无法导入 LangChain 加载器 {class_name}。请安装依赖: pip install {install_hint}. "
        f"导入错误: {'; '.join(errors)}"
    )


def create_loader_instance(
    file_path: str | Path,
    module_candidates: tuple[str, ...],
    class_name: str,
    dependencies: tuple[str, ...] = (),
    **kwargs: Any,
) -> Any:
    """Instantiate a LangChain loader with a normalized string file path."""

    loader_cls = import_loader_class(module_candidates, class_name, dependencies)
    return loader_cls(str(Path(file_path)), **kwargs)
