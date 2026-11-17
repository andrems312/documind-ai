"""Supabase Storage via API REST, autenticado com a service role (somente no backend).

Endpoints usados (Storage API):
- POST   /storage/v1/object/{bucket}/{path}   upload
- GET    /storage/v1/object/{bucket}/{path}   download autenticado
- DELETE /storage/v1/object/{bucket}/{path}   exclusão
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.storage.base import StorageError, ensure_safe_path

log = get_logger(__name__)


class SupabaseStorage:
    def __init__(
        self,
        *,
        base_url: str,
        service_role_key: str,
        bucket: str,
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.bucket = bucket
        self._client = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/storage/v1",
            headers={"Authorization": f"Bearer {service_role_key}", "apikey": service_role_key},
            timeout=timeout,
            transport=transport,
        )

    def _url(self, path: str) -> str:
        return f"/object/{self.bucket}/{ensure_safe_path(path)}"

    async def put(self, path: str, data: bytes, content_type: str = "application/pdf") -> None:
        response = await self._client.post(
            self._url(path),
            content=data,
            headers={"Content-Type": content_type, "x-upsert": "true"},
        )
        self._raise_for_status(response, "enviar o arquivo")

    async def get(self, path: str) -> bytes:
        response = await self._client.get(self._url(path))
        self._raise_for_status(response, "baixar o arquivo")
        return response.content

    async def delete(self, path: str) -> None:
        response = await self._client.delete(self._url(path))
        if response.status_code == 404:
            return
        self._raise_for_status(response, "excluir o arquivo")

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _raise_for_status(response: httpx.Response, action: str) -> None:
        if response.is_success:
            return
        log.error(
            "supabase_storage_error",
            status=response.status_code,
            body=response.text[:300],
            action=action,
        )
        raise StorageError(f"Falha ao {action} no armazenamento ({response.status_code}).")
