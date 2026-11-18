"""Fixtures compartilhadas.

As variáveis de ambiente de teste são definidas ANTES de importar a aplicação, para que
`Settings` não dependa de um `.env` real (variáveis do processo têm precedência sobre o `.env`).

Testes de integração usam um Postgres real com pgvector indicado por `TEST_DATABASE_URL` e são
pulados quando ela não existe. O banco é recriado do zero e migrado com o Alembic uma vez por
sessão de testes.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

TEST_JWT_SECRET = "segredo-de-teste-com-pelo-menos-32-caracteres!!"
BACKEND_DIR = Path(__file__).resolve().parents[1]

os.environ["APP_ENV"] = "test"
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:1/documind_test")
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_JWT_SECRET"] = TEST_JWT_SECRET
os.environ["STORAGE_BACKEND"] = "local"
os.environ["OPENROUTER_API_KEY"] = ""
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


def auth_headers(user_id: uuid.UUID | None = None, **kwargs: str) -> dict[str, str]:
    _, token = make_token(user_id, **kwargs)  # type: ignore[arg-type]
    return {"Authorization": f"Bearer {token}"}


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


# --------------------------------------------------------------------------- integração
@pytest.fixture(scope="session")
def test_database_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """URL do Postgres de teste: `TEST_DATABASE_URL` se definida, senão um `pgserver` embutido.

    O `pgserver` (Postgres + pgvector via pip) permite rodar os testes de integração localmente
    sem Docker, inclusive no Windows. É iniciado uma vez por sessão e encerrado ao final.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return
    try:
        import pgserver
    except ModuleNotFoundError:
        pytest.skip("TEST_DATABASE_URL não definida e pgserver indisponível")

    pgdata = tmp_path_factory.mktemp("pgdata")
    server = pgserver.get_server(pgdata)
    try:
        server.psql("CREATE DATABASE documind_test")
        yield server.get_uri(database="documind_test")
    finally:
        server.cleanup()


@pytest.fixture(scope="session")
def migrated_db_url(test_database_url: str) -> str:
    """Recria o schema do banco de teste e aplica todas as migrações (uma vez por sessão)."""
    url = test_database_url
    database_name = url.rsplit("/", 1)[-1].split("?", 1)[0]
    if "test" not in database_name.lower():
        pytest.exit(
            f"TEST_DATABASE_URL aponta para o banco {database_name!r}. Os testes APAGAM o schema; "
            "use um banco cujo nome contenha 'test' (ex.: documind_test).",
            returncode=2,
        )

    import asyncpg
    from alembic.config import Config

    from alembic import command

    async def reset() -> None:
        conn = await asyncpg.connect(url.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            await conn.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
        finally:
            await conn.close()

    asyncio.run(reset())
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["configure_logger"] = False
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")
    return url
