"""Business API for chat/session/settings persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .database import create_session_factory
from .models import ChatMessageModel, ChatSessionModel, UserSettingsModel, utc_now

DEFAULT_USER_ID = "local"


@dataclass(slots=True)
class StoredChatMessage:
    id: str
    role: str
    content: str
    mode: str | None
    references: list[dict] = field(default_factory=list)
    attachments: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class StoredChatSession:
    id: str
    title: str
    messages: list[StoredChatMessage]
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class StoredUserSettings:
    show_rag_references: bool = True
    chat_background_image: str = ""
    chat_background_opacity: float = 0.2
    updated_at: datetime = field(default_factory=utc_now)


class StorageService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None, user_id: str = DEFAULT_USER_ID) -> None:
        self._session_factory = session_factory or create_session_factory()
        self.user_id = user_id

    def list_sessions(self) -> list[StoredChatSession]:
        with self._session_factory() as db:
            rows = db.scalars(
                select(ChatSessionModel)
                .where(ChatSessionModel.user_id == self.user_id)
                .order_by(ChatSessionModel.updated_at.desc())
            ).all()
            return [self._to_session(row, include_messages=False) for row in rows]

    def get_session(self, session_id: str) -> StoredChatSession | None:
        with self._session_factory() as db:
            row = db.get(ChatSessionModel, session_id)
            if row is None or row.user_id != self.user_id:
                return None
            return self._to_session(row, include_messages=True)

    def delete_session(self, session_id: str) -> bool:
        with self._session_factory() as db:
            row = db.get(ChatSessionModel, session_id)
            if row is None or row.user_id != self.user_id:
                return False
            db.delete(row)
            db.commit()
            return True

    def save_completed_turn(
        self,
        *,
        user_content: str,
        assistant_content: str,
        mode: str,
        session_id: str | None = None,
        title: str | None = None,
        references: list[dict] | None = None,
        attachments: list[dict] | None = None,
        user_attachments: list[dict] | None = None,
    ) -> StoredChatSession:
        now = utc_now()
        with self._session_factory() as db:
            session = db.get(ChatSessionModel, session_id) if session_id else None
            if session is None or session.user_id != self.user_id:
                session = ChatSessionModel(
                    id=session_id or uuid4().hex,
                    user_id=self.user_id,
                    title=title or self._title_from_message(user_content),
                    created_at=now,
                    updated_at=now,
                )
                db.add(session)
            else:
                session.updated_at = now
                if title:
                    session.title = title

            db.add(
                ChatMessageModel(
                    id=uuid4().hex,
                    session_id=session.id,
                    role="user",
                    content=user_content,
                    mode=mode,
                    attachments_json=json.dumps(user_attachments or [], ensure_ascii=False),
                    created_at=now,
                )
            )
            db.add(
                ChatMessageModel(
                    id=uuid4().hex,
                    session_id=session.id,
                    role="assistant",
                    content=assistant_content,
                    mode=mode,
                    references_json=json.dumps(references or [], ensure_ascii=False),
                    attachments_json=json.dumps(attachments or [], ensure_ascii=False),
                    created_at=now,
                )
            )
            db.commit()
            db.refresh(session)
            return self._to_session(session, include_messages=True)

    def get_settings(self) -> StoredUserSettings:
        with self._session_factory() as db:
            row = db.get(UserSettingsModel, self.user_id)
            if row is None:
                row = UserSettingsModel(user_id=self.user_id)
                db.add(row)
                db.commit()
                db.refresh(row)
            return self._to_settings(row)

    def update_settings(
        self,
        *,
        show_rag_references: bool | None = None,
        chat_background_image: str | None = None,
        chat_background_opacity: float | None = None,
    ) -> StoredUserSettings:
        with self._session_factory() as db:
            row = db.get(UserSettingsModel, self.user_id)
            if row is None:
                row = UserSettingsModel(user_id=self.user_id)
                db.add(row)
            if show_rag_references is not None:
                row.show_rag_references = show_rag_references
            if chat_background_image is not None:
                row.chat_background_image = chat_background_image
            if chat_background_opacity is not None:
                row.chat_background_opacity = min(1.0, max(0.05, chat_background_opacity))
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._to_settings(row)

    @staticmethod
    def _title_from_message(message: str) -> str:
        compact = " ".join(message.strip().split())
        return f"{compact[:24]}..." if len(compact) > 24 else compact or "新会话"

    @staticmethod
    def _to_message(row: ChatMessageModel) -> StoredChatMessage:
        references = StorageService._parse_json_list(row.references_json)
        attachments = StorageService._parse_json_list(row.attachments_json)
        return StoredChatMessage(
            id=row.id,
            role=row.role,
            content=row.content,
            mode=row.mode,
            references=references,
            attachments=attachments,
            created_at=row.created_at,
        )

    @staticmethod
    def _parse_json_list(raw: str | None) -> list[dict]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def _to_session(self, row: ChatSessionModel, *, include_messages: bool) -> StoredChatSession:
        return StoredChatSession(
            id=row.id,
            title=row.title,
            messages=[self._to_message(message) for message in row.messages] if include_messages else [],
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_settings(row: UserSettingsModel) -> StoredUserSettings:
        return StoredUserSettings(
            show_rag_references=row.show_rag_references,
            chat_background_image=row.chat_background_image,
            chat_background_opacity=row.chat_background_opacity,
            updated_at=row.updated_at,
        )
