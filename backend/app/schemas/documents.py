from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.db.models import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    original_filename: str
    file_size: int
    page_count: int | None
    processed_pages: int
    status: DocumentStatus
    error_message: str | None
    folder_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def progress(self) -> float:
        """Fração processada (0 a 1), para a barra de progresso do frontend."""
        if self.status == DocumentStatus.READY:
            return 1.0
        if not self.page_count:
            return 0.0
        return round(min(self.processed_pages / self.page_count, 1.0), 3)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    # Enviar folder_id: null move o documento para fora de qualquer pasta.
    folder_id: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("O título não pode ficar vazio.")
        return stripped


class DocumentPageRead(BaseModel):
    document_id: uuid.UUID
    page_number: int
    page_count: int
    text: str
