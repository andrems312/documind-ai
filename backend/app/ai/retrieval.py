"""Recuperação híbrida de trechos: busca vetorial (pgvector, cosseno) + full-text em português,
combinadas por Reciprocal Rank Fusion (RRF).

Por que híbrida: embeddings capturam significado; o full-text acerta termos exatos (números de
cláusula, siglas, nomes próprios) que a busca vetorial às vezes ranqueia mal.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk, DocumentStatus

RRF_K = 60
MAX_CHUNKS_PER_PAGE = 2


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int
    chunk_index: int
    content: str
    token_count: int
    similarity: float
    text_rank: float | None
    score: float


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[uuid.UUID]], k: int = RRF_K
) -> dict[uuid.UUID, float]:
    scores: dict[uuid.UUID, float] = defaultdict(float)
    for ranking in rankings:
        for position, item in enumerate(ranking, start=1):
            scores[item] += 1.0 / (k + position)
    return dict(scores)


def fit_to_budget(chunks: Sequence[RetrievedChunk], max_tokens: int) -> list[RetrievedChunk]:
    """Mantém a ordem de relevância e para quando o orçamento de tokens do contexto estoura."""
    selected: list[RetrievedChunk] = []
    used = 0
    for chunk in chunks:
        if used + chunk.token_count > max_tokens and selected:
            break
        selected.append(chunk)
        used += chunk.token_count
    return selected


async def hybrid_search(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    query_text: str,
    query_embedding: list[float],
    document_ids: Sequence[uuid.UUID] | None = None,
    candidates: int = 20,
    top_k: int = 8,
    min_similarity: float = 0.25,
) -> list[RetrievedChunk]:
    # Mais candidatos no HNSW compensam os filtros por usuário/documento aplicados após o índice.
    await db.execute(text(f"SET LOCAL hnsw.ef_search = {max(40, candidates * 4)}"))

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = (1 - distance).label("similarity")
    columns = (
        DocumentChunk.id,
        DocumentChunk.document_id,
        Document.title,
        DocumentChunk.page_number,
        DocumentChunk.chunk_index,
        DocumentChunk.content,
        DocumentChunk.token_count,
        similarity,
    )
    filters = [DocumentChunk.user_id == user_id, Document.status == DocumentStatus.READY]
    if document_ids:
        filters.append(DocumentChunk.document_id.in_(list(document_ids)))

    vector_rows = (
        await db.execute(
            select(*columns)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(*filters)
            .order_by(distance)
            .limit(candidates)
        )
    ).all()

    tsquery = func.websearch_to_tsquery("portuguese", query_text)
    rank = func.ts_rank_cd(DocumentChunk.tsv, tsquery).label("text_rank")
    text_rows = (
        await db.execute(
            select(*columns, rank)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(*filters, DocumentChunk.tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(candidates)
        )
    ).all()

    rows = {row.id: row for row in vector_rows}
    text_ranks: dict[uuid.UUID, float] = {}
    for row in text_rows:
        rows.setdefault(row.id, row)
        text_ranks[row.id] = float(row.text_rank)

    fused = reciprocal_rank_fusion([[r.id for r in vector_rows], [r.id for r in text_rows]])

    results: list[RetrievedChunk] = []
    per_page: dict[tuple[uuid.UUID, int], int] = defaultdict(int)
    for chunk_id in sorted(fused, key=lambda cid: fused[cid], reverse=True):
        row = rows[chunk_id]
        sim = float(row.similarity)
        # Relevância mínima: semelhança vetorial suficiente OU todos os termos no full-text.
        if sim < min_similarity and chunk_id not in text_ranks:
            continue
        page_key = (row.document_id, row.page_number)
        if per_page[page_key] >= MAX_CHUNKS_PER_PAGE:
            continue
        per_page[page_key] += 1
        results.append(
            RetrievedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                document_title=row.title,
                page_number=row.page_number,
                chunk_index=row.chunk_index,
                content=row.content,
                token_count=row.token_count,
                similarity=sim,
                text_rank=text_ranks.get(chunk_id),
                score=fused[chunk_id],
            )
        )
        if len(results) >= top_k:
            break
    return results
