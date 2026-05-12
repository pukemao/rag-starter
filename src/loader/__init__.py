"""Document loader helpers built on top of LangChain.

The public API intentionally lives in this package so callers do not need to
remember the concrete LangChain loader class for each file type.
"""

from .base import LoaderSpec
from .registry import (
    get_loader,
    lazy_load_documents,
    load_documents,
    loader_for_extension,
    supported_extensions,
)
from .utils import LoaderDependencyError, UnsupportedFormatError

__all__ = [
    "LoaderDependencyError",
    "LoaderSpec",
    "UnsupportedFormatError",
    "get_loader",
    "lazy_load_documents",
    "load_documents",
    "loader_for_extension",
    "supported_extensions",
]
