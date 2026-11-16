"""Importa todos os modelos para que o metadata esteja completo (Alembic e relacionamentos)."""

from app.db.models.analysis import Analysis, AnalysisType
from app.db.models.conversation import (
    Conversation,
    ConversationDocument,
    Message,
    MessageCitation,
    MessageRole,
)
from app.db.models.document import Document, DocumentChunk, DocumentPage, DocumentStatus
from app.db.models.folder import Folder
from app.db.models.processing_job import JobStatus, ProcessingJob
from app.db.models.profile import Profile
from app.db.models.usage_event import UsageEvent, UsageKind

__all__ = [
    "Analysis",
    "AnalysisType",
    "Conversation",
    "ConversationDocument",
    "Document",
    "DocumentChunk",
    "DocumentPage",
    "DocumentStatus",
    "Folder",
    "JobStatus",
    "Message",
    "MessageCitation",
    "MessageRole",
    "ProcessingJob",
    "Profile",
    "UsageEvent",
    "UsageKind",
]
