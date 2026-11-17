from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models import MessageRole


class CitationRead(BaseModel):
    id: uuid.UUID
    rank: int
    document_id: uuid.UUID
    document_title: str
    page_number: int
    excerpt: str
    score: float | None


class MessageRead(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
    citations: list[CitationRead] = []


class ConversationCreate(BaseModel):
    document_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=20,
        description="Documentos consultados. Lista vazia = toda a biblioteca do usuário.",
    )
    title: str | None = Field(default=None, min_length=1, max_length=160)

    @field_validator("document_ids")
    @classmethod
    def _dedupe(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        return list(dict.fromkeys(value))


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class ConversationRead(BaseModel):
    id: uuid.UUID
    title: str
    document_ids: list[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A pergunta não pode ser vazia.")
        return value
