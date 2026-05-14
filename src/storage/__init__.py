"""Local structured persistence for chat sessions and user settings."""

from .database import create_session_factory, init_database
from .service import StorageService

__all__ = ["StorageService", "create_session_factory", "init_database"]
