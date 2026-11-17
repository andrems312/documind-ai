from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.rate_limit import limiter
from app.main import create_app
from tests.conftest import auth_headers
from tests.fakes import HashingEmbedder, ScriptedChat


@pytest.fixture
async def integration_app(settings: Settings, migrated_db_url: str, tmp_path):
    limiter.reset()
    test_settings = settings.model_copy(
        update={
            "database_url": migrated_db_url,
            "storage_backend": "local",
            "local_storage_dir": str(tmp_path / "uploads"),
        }
    )
    app = create_app(
        test_settings,
        embedder=HashingEmbedder(settings.embedding_dim),
        chat=ScriptedChat(),
    )
    app.state.job_runner.retry_base_delay = 0.01
    yield app
    await app.state.job_runner.aclose()
    await app.state.engine.dispose()


@pytest.fixture
async def api(integration_app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=integration_app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30) as client:
        yield client


@pytest.fixture
def user_a() -> dict[str, str]:
    return auth_headers(uuid.uuid4(), email="ana@example.com", full_name="Ana Souza")


@pytest.fixture
def user_b() -> dict[str, str]:
    return auth_headers(uuid.uuid4(), email="bruno@example.com", full_name="Bruno Lima")


async def upload(
    client: AsyncClient, headers: dict[str, str], data: bytes, name: str = "contrato.pdf"
):
    return await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": (name, data, "application/pdf")},
    )


def parse_sse(body: str) -> list[dict[str, Any]]:
    return [
        json.loads(line[len("data: ") :]) for line in body.splitlines() if line.startswith("data: ")
    ]
