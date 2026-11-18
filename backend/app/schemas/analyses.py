from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import AnalysisType


class AnalysisCreate(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)


class AnalysisRead(BaseModel):
    id: uuid.UUID
    type: AnalysisType
    document_ids: list[uuid.UUID]
    document_titles: list[str]
    title: str
    content: str
    model: str | None
    created_at: datetime


class AnalysisListItem(BaseModel):
    id: uuid.UUID
    type: AnalysisType
    document_ids: list[uuid.UUID]
    document_titles: list[str]
    title: str
    created_at: datetime
