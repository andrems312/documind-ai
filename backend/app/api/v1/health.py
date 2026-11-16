from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.logging import get_logger
from app.schemas.health import HealthResponse

router = APIRouter()
log = get_logger(__name__)


@router.get("/health", response_model=HealthResponse, summary="Status da API e dependências")
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    checks: dict[str, str] = {}

    try:
        async with request.app.state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 — o health nunca deve derrubar a API
        log.warning("health_database_error", error=str(exc))
        checks["database"] = "error"

    checks["openrouter"] = "configured" if settings.openrouter_api_key else "missing"
    checks["supabase_storage"] = "configured" if settings.supabase_service_role_key else "missing"

    status = "ok" if checks["database"] == "ok" else "degraded"
    return HealthResponse(
        status=status, version=request.app.version, environment=settings.app_env, checks=checks
    )
