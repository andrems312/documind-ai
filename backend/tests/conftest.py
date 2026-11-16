"""Fixtures compartilhadas.

As variáveis de ambiente de teste são definidas ANTES de importar a aplicação, para que
`Settings` não dependa de um `.env` real. Testes que precisam de banco de verdade usam
`TEST_DATABASE_URL` e são pulados quando ela não existe.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

TEST_JWT_SECRET = "segredo-de-teste-com-pelo-menos-32-caracteres!!"

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:1/documind_test")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.core.config import Settings, get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


def make_token(
    user_id: uuid.UUID | None = None,
    *,
    email: str = "ana@example.com",
    full_name: str = "Ana Souza",
    expires_in: int = 3600,
    secret: str = TEST_JWT_SECRET,
    audience: str = "authenticated",
) -> tuple[uuid.UUID, str]:
    uid = user_id or uuid.uuid4()
    now = datetime.now(UTC)
    claims = {
        "sub": str(uid),
        "aud": audience,
        "role": "authenticated",
        "email": email,
        "user_metadata": {"full_name": full_name},
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return uid, jwt.encode(claims, secret, algorithm="HS256")


@pytest.fixture(scope="session")
def settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
