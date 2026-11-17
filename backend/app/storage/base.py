"""Interface de armazenamento de arquivos e fábrica a partir das Settings.

Caminhos são sempre relativos e no formato `<user_id>/<document_id>.pdf`; a validação do formato
fica em cada implementação para impedir path traversal.
"""

from __future__ import annotations

import re
from typing import Protocol

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError

_SAFE_PATH = re.compile(r"^[0-9a-f-]{36}/[0-9a-f-]{36}\.pdf$")


class StorageError(ExternalServiceError):
    code = "storage_error"


def ensure_safe_path(path: str) -> str:
    if not _SAFE_PATH.fullmatch(path):
        raise ValueError(f"Caminho de armazenamento inválido: {path!r}")
    return path


def object_path(user_id: object, document_id: object) -> str:
    return ensure_safe_path(f"{user_id}/{document_id}.pdf")


class StorageBackend(Protocol):
    async def put(self, path: str, data: bytes, content_type: str = "application/pdf") -> None: ...

    async def get(self, path: str) -> bytes: ...

    async def delete(self, path: str) -> None: ...

    async def aclose(self) -> None: ...


def build_storage(settings: Settings) -> StorageBackend:
    if settings.storage_backend == "supabase":
        from app.storage.supabase import SupabaseStorage

        if not settings.supabase_service_role_key:
            raise RuntimeError(
                "STORAGE_BACKEND=supabase exige SUPABASE_SERVICE_ROLE_KEY no .env do backend."
            )
        return SupabaseStorage(
            base_url=str(settings.supabase_url),
            service_role_key=settings.supabase_service_role_key,
            bucket=settings.supabase_storage_bucket,
            timeout=settings.http_timeout_seconds,
        )

    from app.storage.local import LocalStorage

    return LocalStorage(settings.local_storage_dir)
