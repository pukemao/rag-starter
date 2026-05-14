"""SQLAlchemy database setup for local structured storage."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import settings

from .models import Base


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path and raw_path != ":memory:":
        Path(raw_path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    url = database_url or settings.database.url
    _ensure_sqlite_parent(url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    pool_kwargs = {"poolclass": StaticPool} if url in {"sqlite:///:memory:", "sqlite://"} else {}
    engine = create_engine(url, connect_args=connect_args, **pool_kwargs)
    init_database(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_chat_messages(engine)


def _migrate_chat_messages(engine: Engine) -> None:
    inspector = inspect(engine)
    if "chat_messages" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("chat_messages")}
    if "attachments_json" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE chat_messages ADD COLUMN attachments_json TEXT"))
