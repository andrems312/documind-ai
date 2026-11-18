"""Busca semântica global: híbrida (vetorial + full-text) em toda a biblioteca do usuário."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import EmbeddingProvider
from app.ai.retrieval import hybrid_search
from app.core.config import Settings
from app.db.models import Document, UsageEvent, UsageKind
from app.schemas.search import SearchResponse, SearchResultItem


async def search(
    db: AsyncSession,
    embedder: EmbeddingProvider,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    query: str,
    folder_id: uuid.UUID | None = None,
    limit: int = 20,
) -> SearchResponse:
    query = query.strip()
    document_ids: list[uuid.UUID] | None = None
    if folder_id is not None:
        document_ids = list(
            (
                await db.scalars(
                    select(Document.id).where(
                        Document.user_id == user_id, Document.folder_id == folder_id
                    )
                )
            ).all()
        )
        if not document_ids:
            return SearchResponse(query=query, count=0, results=[])

    batch = await embedder.embed([query])
    retrieved = await hybrid_search(
        db,
        user_id=user_id,
        query_text=query,
        query_embedding=batch.vectors[0],
        document_ids=document_ids,
        candidates=settings.rag_candidates,
        top_k=limit,
        min_similarity=settings.rag_min_similarity,
    )
    db.add(UsageEvent(user_id=user_id, kind=UsageKind.SEARCH, prompt_tokens=batch.prompt_tokens))
    results = [
        SearchResultItem(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            page_number=chunk.page_number,
            excerpt=chunk.content,
            similarity=round(chunk.similarity, 4),
            score=round(chunk.score, 6),
        )
        for chunk in retrieved
    ]
    return SearchResponse(query=query, count=len(results), results=results)
