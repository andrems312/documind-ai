from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AnalysisType(enum.StrEnum):
    SUMMARY = "summary"
    KEY_INFO = "key_info"
    COMPARISON = "comparison"


class Analysis(UUIDPrimaryKeyMixin, Base):
    """Resultado persistido de resumo, extração de informações ou comparação."""

    __tablename__ = "analyses"
    __table_args__ = (Index("ix_analyses_user_id_created_at", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[AnalysisType] = mapped_column(
        Enum(AnalysisType, name="analysis_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    document_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
