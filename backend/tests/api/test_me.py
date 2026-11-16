"""Rota /me: autenticação e perfil.

Os testes sem banco substituem a dependência de sessão e o serviço de perfil; o teste
com banco real roda apenas quando TEST_DATABASE_URL está definida.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest

from app.api import deps
from app.db.models import Profile
from tests.conftest import make_token


class _FakeSession:
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


async def _fake_get_db():
    yield _FakeSession()


@pytest.fixture
def no_db(app, monkeypatch):
    app.dependency_overrides[deps.get_db] = _fake_get_db

    async def fake_ensure_profile(_db, user):
        return Profile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    monkeypatch.setattr(deps, "ensure_profile", fake_ensure_profile)
    yield
    app.dependency_overrides.clear()


async def test_me_requires_token(client, no_db) -> None:
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_me_rejects_invalid_token(client, no_db) -> None:
    response = await client.get("/api/v1/me", headers={"Authorization": "Bearer abc"})
    assert response.status_code == 401


async def test_me_returns_profile_from_token(client, no_db) -> None:
    uid, token = make_token(email="ana@example.com", full_name="Ana Souza")
    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(uid)
    assert body["email"] == "ana@example.com"
    assert body["full_name"] == "Ana Souza"


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL ausente")
async def test_me_roundtrip_with_real_database(settings) -> None:
    """Cria o perfil no primeiro acesso, atualiza o nome e lê de volta."""
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    real_settings = settings.model_copy(update={"database_url": os.environ["TEST_DATABASE_URL"]})
    app = create_app(real_settings)
    uid, token = make_token(uuid.uuid4(), email="teste-db@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/api/v1/me", headers=headers)
        assert first.status_code == 200, first.text
        assert first.json()["id"] == str(uid)

        patched = await client.patch(
            "/api/v1/me", headers=headers, json={"full_name": "Nome Atualizado"}
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["full_name"] == "Nome Atualizado"

        again = await client.get("/api/v1/me", headers=headers)
        assert again.json()["full_name"] == "Nome Atualizado"
    await app.state.engine.dispose()
