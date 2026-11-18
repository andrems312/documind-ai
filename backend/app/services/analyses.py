"""Leitura, listagem, exclusão e exportação de análises. Tudo filtrado por `user_id`."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import Analysis, Document
from app.schemas.analyses import AnalysisListItem, AnalysisRead

REMOVED_TITLE = "Documento removido"


async def _titles_for(
    db: AsyncSession, document_ids: list[uuid.UUID]
) -> list[str]:
    if not document_ids:
        return []
    rows = await db.execute(
        select(Document.id, Document.title).where(Document.id.in_(document_ids))
    )
    by_id = {doc_id: title for doc_id, title in rows}
    return [by_id.get(doc_id, REMOVED_TITLE) for doc_id in document_ids]


def _to_read(analysis: Analysis, titles: list[str]) -> AnalysisRead:
    return AnalysisRead(
        id=analysis.id,
        type=analysis.type,
        document_ids=list(analysis.document_ids),
        document_titles=titles,
        title=analysis.title,
        content=analysis.content,
        model=analysis.model,
        created_at=analysis.created_at,
    )


async def list_analyses(db: AsyncSession, user_id: uuid.UUID) -> list[AnalysisListItem]:
    analyses = (
        await db.scalars(
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc())
        )
    ).all()
    all_ids = list({d for a in analyses for d in a.document_ids})
    titles = await _titles_for(db, all_ids)
    title_by_id = dict(zip(all_ids, titles, strict=True))
    return [
        AnalysisListItem(
            id=a.id,
            type=a.type,
            document_ids=list(a.document_ids),
            document_titles=[title_by_id.get(d, REMOVED_TITLE) for d in a.document_ids],
            title=a.title,
            created_at=a.created_at,
        )
        for a in analyses
    ]


async def get_owned(db: AsyncSession, user_id: uuid.UUID, analysis_id: uuid.UUID) -> Analysis:
    analysis = await db.scalar(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    )
    if analysis is None:
        raise NotFoundError("Análise não encontrada.")
    return analysis


async def get_detail(db: AsyncSession, user_id: uuid.UUID, analysis_id: uuid.UUID) -> AnalysisRead:
    analysis = await get_owned(db, user_id, analysis_id)
    titles = await _titles_for(db, list(analysis.document_ids))
    return _to_read(analysis, titles)


async def delete_analysis(db: AsyncSession, analysis: Analysis) -> None:
    await db.delete(analysis)
    await db.flush()
