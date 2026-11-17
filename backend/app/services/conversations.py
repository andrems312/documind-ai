"""Regras de negócio de conversas. Toda leitura/escrita filtra por `user_id` (posse)."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, UnprocessableError
from app.db.models import Conversation, ConversationDocument, Document, Message
from app.schemas.conversations import (
    CitationRead,
    ConversationDetail,
    ConversationRead,
    MessageRead,
)

DEFAULT_TITLE = "Nova conversa"


async def _document_ids_by_conversation(
    db: AsyncSession, conversation_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    result: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    if not conversation_ids:
        return result
    rows = await db.execute(
        select(ConversationDocument.conversation_id, ConversationDocument.document_id).where(
            ConversationDocument.conversation_id.in_(conversation_ids)
        )
    )
    for conversation_id, document_id in rows:
        result[conversation_id].append(document_id)
    return result


def _to_read(conversation: Conversation, document_ids: list[uuid.UUID]) -> ConversationRead:
    return ConversationRead(
        id=conversation.id,
        title=conversation.title,
        document_ids=document_ids,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


async def create_conversation(
    db: AsyncSession, user_id: uuid.UUID, document_ids: list[uuid.UUID], title: str | None
) -> ConversationRead:
    if document_ids:
        owned = set(
            (
                await db.scalars(
                    select(Document.id).where(
                        Document.user_id == user_id, Document.id.in_(document_ids)
                    )
                )
            ).all()
        )
        missing = [str(d) for d in document_ids if d not in owned]
        if missing:
            raise UnprocessableError(
                "Um ou mais documentos não foram encontrados.", details={"document_ids": missing}
            )

    conversation = Conversation(user_id=user_id, title=(title or DEFAULT_TITLE).strip())
    db.add(conversation)
    await db.flush()
    db.add_all(
        ConversationDocument(conversation_id=conversation.id, document_id=d) for d in document_ids
    )
    await db.flush()
    await db.refresh(conversation)
    return _to_read(conversation, list(document_ids))


async def get_owned(
    db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
    )
    if conversation is None:
        raise NotFoundError("Conversa não encontrada.")
    return conversation


async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[ConversationRead]:
    conversations = (
        await db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
    ).all()
    docs = await _document_ids_by_conversation(db, [c.id for c in conversations])
    return [_to_read(c, docs.get(c.id, [])) for c in conversations]


async def get_detail(
    db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID
) -> ConversationDetail:
    conversation = await get_owned(db, user_id, conversation_id)
    messages = (
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .options(selectinload(Message.citations))
            .order_by(Message.created_at)
        )
    ).all()
    cited_ids = {c.document_id for m in messages for c in m.citations}
    titles: dict[uuid.UUID, str] = {}
    if cited_ids:
        titles = dict(
            (
                await db.execute(
                    select(Document.id, Document.title).where(Document.id.in_(cited_ids))
                )
            )
            .tuples()
            .all()
        )
    docs = await _document_ids_by_conversation(db, [conversation.id])
    base = _to_read(conversation, docs.get(conversation.id, []))
    return ConversationDetail(
        **base.model_dump(),
        messages=[
            MessageRead(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                citations=[
                    CitationRead(
                        id=c.id,
                        rank=c.rank,
                        document_id=c.document_id,
                        document_title=titles.get(c.document_id, "Documento"),
                        page_number=c.page_number,
                        excerpt=c.excerpt,
                        score=c.score,
                    )
                    for c in m.citations
                ],
            )
            for m in messages
        ],
    )


async def rename_conversation(
    db: AsyncSession, conversation: Conversation, title: str
) -> ConversationRead:
    conversation.title = title.strip()
    await db.flush()
    await db.refresh(conversation)
    docs = await _document_ids_by_conversation(db, [conversation.id])
    return _to_read(conversation, docs.get(conversation.id, []))


async def delete_conversation(db: AsyncSession, conversation: Conversation) -> None:
    await db.delete(conversation)
    await db.flush()
