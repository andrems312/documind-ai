"""Fábrica da aplicação FastAPI do DocuMind AI."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.ai.openrouter import OpenRouterClient
from app.ai.providers import ChatProvider, EmbeddingProvider
from app.ai.rag import RagService
from app.api.v1 import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.core.security import JWTVerifier
from app.db.session import create_engine, create_session_factory
from app.processing.jobs import JobRunner
from app.processing.pipeline import PipelineContext
from app.storage.base import StorageBackend, build_storage

API_VERSION = "0.2.0"
log = get_logger("documind")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    log.info(
        "startup",
        env=settings.app_env,
        storage=settings.storage_backend,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
        openrouter_configured=bool(settings.openrouter_api_key),
    )
    try:
        await app.state.job_runner.resume_pending()
    except Exception as exc:  # banco indisponível no startup não deve impedir a API de subir
        log.error("jobs_resume_failed", error=str(exc))
    yield
    await app.state.job_runner.aclose()
    await app.state.storage.aclose()
    for resource in app.state.closeables:
        await resource.aclose()
    await app.state.engine.dispose()
    log.info("shutdown")


def create_app(
    settings: Settings | None = None,
    *,
    embedder: EmbeddingProvider | None = None,
    chat: ChatProvider | None = None,
    storage: StorageBackend | None = None,
) -> FastAPI:
    """Cria a aplicação. Provedores podem ser injetados (testes, outros gateways)."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=API_VERSION,
        description=(
            "API do DocuMind AI: upload de PDFs, pipeline RAG (pgvector + OpenRouter) "
            "e chat com citações. Autenticação via token do Supabase Auth (Bearer)."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Estado compartilhado (criado aqui, não no lifespan, para que os testes não dependam dele).
    app.state.settings = settings
    app.state.engine = create_engine(str(settings.database_url))
    app.state.session_factory = create_session_factory(app.state.engine)
    app.state.jwt_verifier = JWTVerifier(settings)
    app.state.limiter = limiter
    app.state.closeables = []

    if embedder is None or chat is None:
        openrouter = OpenRouterClient(
            api_key=settings.openrouter_api_key,
            base_url=str(settings.openrouter_base_url),
            chat_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            embedding_dim=settings.embedding_dim,
            app_url=settings.app_public_url,
            app_name=settings.app_name,
            timeout=settings.http_timeout_seconds,
        )
        app.state.closeables.append(openrouter)
        embedder = embedder or openrouter
        chat = chat or openrouter

    app.state.storage = storage or build_storage(settings)
    app.state.embedder = embedder
    app.state.chat = chat
    pipeline = PipelineContext(
        session_factory=app.state.session_factory,
        storage=app.state.storage,
        embedder=embedder,
        settings=settings,
    )
    app.state.job_runner = JobRunner(
        pipeline,
        concurrency=settings.worker_concurrency,
        max_attempts=settings.job_max_attempts,
    )
    app.state.rag = RagService(
        settings=settings,
        session_factory=app.state.session_factory,
        embedder=embedder,
        chat=chat,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limited",
                    "message": "Muitas requisições em pouco tempo. Aguarde um instante.",
                    "details": {"limit": str(exc.detail)},
                }
            },
        )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id, method=request.method, path=request.url.path
        )
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path not in {"/api/v1/health"}:
            log.info("request", status=response.status_code, duration_ms=duration_ms)
        return response

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
