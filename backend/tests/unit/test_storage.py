import uuid

import httpx
import pytest

from app.storage.base import StorageError, object_path
from app.storage.local import LocalStorage
from app.storage.supabase import SupabaseStorage

USER = uuid.UUID("11111111-1111-1111-1111-111111111111")
DOC = uuid.UUID("22222222-2222-2222-2222-222222222222")


async def test_local_storage_roundtrip(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    path = object_path(USER, DOC)
    await storage.put(path, b"%PDF-1.7 conteudo")
    assert await storage.get(path) == b"%PDF-1.7 conteudo"
    await storage.delete(path)
    with pytest.raises(StorageError):
        await storage.get(path)
    await storage.delete(path)  # idempotente


@pytest.mark.parametrize("path", ["../segredo.pdf", f"{USER}/../../x.pdf", "abc/def.pdf"])
async def test_unsafe_paths_are_rejected(tmp_path, path: str) -> None:
    with pytest.raises(ValueError):
        await LocalStorage(tmp_path).put(path, b"x")


async def test_supabase_storage_requests() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, content=b"%PDF-data")
        return httpx.Response(200, json={})

    storage = SupabaseStorage(
        base_url="https://ref.supabase.co",
        service_role_key="service-key",
        bucket="documents",
        transport=httpx.MockTransport(handler),
    )
    path = object_path(USER, DOC)
    await storage.put(path, b"%PDF-data")
    assert await storage.get(path) == b"%PDF-data"
    await storage.delete(path)
    await storage.aclose()

    expected_url = f"https://ref.supabase.co/storage/v1/object/documents/{path}"
    assert [(r.method, str(r.url)) for r in requests] == [
        ("POST", expected_url),
        ("GET", expected_url),
        ("DELETE", expected_url),
    ]
    assert requests[0].headers["authorization"] == "Bearer service-key"
    assert requests[0].headers["apikey"] == "service-key"
    assert requests[0].headers["content-type"] == "application/pdf"


async def test_supabase_storage_error_is_wrapped() -> None:
    storage = SupabaseStorage(
        base_url="https://ref.supabase.co",
        service_role_key="k",
        bucket="documents",
        transport=httpx.MockTransport(lambda r: httpx.Response(403, json={"error": "denied"})),
    )
    with pytest.raises(StorageError, match="403"):
        await storage.get(object_path(USER, DOC))
