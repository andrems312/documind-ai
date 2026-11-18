from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class DocumentStats(BaseModel):
    total: int = 0
    ready: int = 0
    processing: int = 0
    failed: int = 0


class UsagePoint(BaseModel):
    day: date
    prompt_tokens: int = 0
    completion_tokens: int = 0
    events: int = 0


class StatsOverview(BaseModel):
    documents: DocumentStats
    pages_indexed: int = 0
    chunks: int = 0
    conversations: int = 0
    questions: int = 0
    analyses: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    usage_by_kind: dict[str, int]
    daily_usage: list[UsagePoint]
