from __future__ import annotations

import uuid

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int
    excerpt: str
    similarity: float
    score: float


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchResultItem]
