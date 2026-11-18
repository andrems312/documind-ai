"""Agregações para o dashboard. Tudo filtrado por `user_id`."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Analysis,
    Conversation,
    Document,
    DocumentChunk,
    DocumentStatus,
    Message,
    MessageRole,
    UsageEvent,
    UsageKind,
)
from app.schemas.stats import DocumentStats, StatsOverview, UsagePoint

DAILY_WINDOW_DAYS = 14


async def overview(db: AsyncSession, user_id: uuid.UUID) -> StatsOverview:
    status_rows = await db.execute(
        select(Document.status, func.count())
        .where(Document.user_id == user_id)
        .group_by(Document.status)
    )
    by_status = {status: count for status, count in status_rows}
    documents = DocumentStats(
        total=sum(by_status.values()),
        ready=by_status.get(DocumentStatus.READY, 0),
        processing=by_status.get(DocumentStatus.UPLOADED, 0)
        + by_status.get(DocumentStatus.PROCESSING, 0),
        failed=by_status.get(DocumentStatus.FAILED, 0),
    )

    pages_indexed = (
        await db.scalar(
            select(func.coalesce(func.sum(Document.page_count), 0)).where(
                Document.user_id == user_id, Document.status == DocumentStatus.READY
            )
        )
    ) or 0
    chunks = (
        await db.scalar(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.user_id == user_id)
        )
    ) or 0
    conversations = (
        await db.scalar(
            select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        )
    ) or 0
    questions = (
        await db.scalar(
            select(func.count())
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.user_id == user_id, Message.role == MessageRole.USER)
        )
    ) or 0
    analyses = (
        await db.scalar(
            select(func.count()).select_from(Analysis).where(Analysis.user_id == user_id)
        )
    ) or 0

    token_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
            ).where(UsageEvent.user_id == user_id)
        )
    ).one()

    kind_rows = await db.execute(
        select(UsageEvent.kind, func.count())
        .where(UsageEvent.user_id == user_id)
        .group_by(UsageEvent.kind)
    )
    usage_by_kind = {kind.value: count for kind, count in kind_rows}
    for kind in UsageKind:
        usage_by_kind.setdefault(kind.value, 0)

    daily_usage = await _daily_usage(db, user_id)

    return StatsOverview(
        documents=documents,
        pages_indexed=int(pages_indexed),
        chunks=int(chunks),
        conversations=int(conversations),
        questions=int(questions),
        analyses=int(analyses),
        prompt_tokens=int(token_row[0]),
        completion_tokens=int(token_row[1]),
        usage_by_kind=usage_by_kind,
        daily_usage=daily_usage,
    )


async def _daily_usage(db: AsyncSession, user_id: uuid.UUID) -> list[UsagePoint]:
    today = date.today()
    start = today - timedelta(days=DAILY_WINDOW_DAYS - 1)
    day = cast(UsageEvent.created_at, Date).label("day")
    rows = await db.execute(
        select(
            day,
            func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
            func.count(),
        )
        .where(UsageEvent.user_id == user_id, cast(UsageEvent.created_at, Date) >= start)
        .group_by(day)
    )
    found = {
        row[0]: UsagePoint(
            day=row[0], prompt_tokens=int(row[1]), completion_tokens=int(row[2]), events=int(row[3])
        )
        for row in rows
    }
    return [
        found.get(start + timedelta(days=offset), UsagePoint(day=start + timedelta(days=offset)))
        for offset in range(DAILY_WINDOW_DAYS)
    ]
