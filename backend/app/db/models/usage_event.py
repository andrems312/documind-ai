from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class UsageKind(enum.StrEnum):
    UPLOAD = "upload"
    QUESTION = "question"
    SUMMARY = "summary"
    KEY_INFO = "key_info"
    COMPARISON = "comparison"
    SEARCH = "search"


class UsageEvent(UUIDPrimaryKeyMixin, Base):
    """Evento de uso para o dashboard de estatísticas e controle de custo."""

    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_user_id_created_at", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[UsageKind] = mapped_column(
        Enum(UsageKind, name="usage_kind", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
