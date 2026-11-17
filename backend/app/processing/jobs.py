"""Execução em segundo plano dos jobs de processamento, dentro do próprio processo da API.

- Jobs ficam na tabela `processing_jobs` (duráveis): os que estavam na fila ou em execução quando a
  API parou são retomados no startup.
- Concorrência limitada por semáforo; falhas transitórias (serviços externos) são retentadas com
  espera crescente; erros do documento (ex.: PDF digitalizado) falham de imediato, com mensagem.
- A interface (`schedule`, `resume_pending`, `aclose`) permite trocar por um worker externo
  (arq/Celery) sem alterar as rotas.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

from sqlalchemy import func, select, update

from app.core.exceptions import AppError, ExternalServiceError
from app.core.logging import get_logger
from app.db.models import Document, DocumentStatus, JobStatus, ProcessingJob
from app.db.session import session_scope
from app.processing.pipeline import DocumentGone, PipelineContext, process_document

log = get_logger(__name__)

GENERIC_FAILURE = "Falha inesperada ao processar o documento. Tente reprocessar."


class JobRunner:
    def __init__(
        self,
        ctx: PipelineContext,
        *,
        concurrency: int = 2,
        max_attempts: int = 3,
        retry_base_delay: float = 5.0,
    ) -> None:
        self.ctx = ctx
        self.max_attempts = max_attempts
        self.retry_base_delay = retry_base_delay
        self._semaphore = asyncio.Semaphore(concurrency)
        self._tasks: set[asyncio.Task[None]] = set()
        self._closing = False

    # ------------------------------------------------------------------ API pública
    def schedule(self, job_id: uuid.UUID) -> None:
        """Agenda um job já gravado (e commitado) no banco."""
        if not self._closing:
            self._spawn(self._run(job_id))

    async def resume_pending(self) -> int:
        async with session_scope(self.ctx.session_factory) as db:
            await db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.status == JobStatus.RUNNING)
                .values(status=JobStatus.QUEUED)
            )
            job_ids = (
                await db.scalars(
                    select(ProcessingJob.id)
                    .where(ProcessingJob.status == JobStatus.QUEUED)
                    .order_by(ProcessingJob.created_at)
                )
            ).all()
        for job_id in job_ids:
            self.schedule(job_id)
        if job_ids:
            log.info("jobs_resumed", count=len(job_ids))
        return len(job_ids)

    async def wait_idle(self) -> None:
        """Aguarda todos os jobs em andamento (inclusive retentativas). Útil em testes."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def aclose(self) -> None:
        self._closing = True
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*list(self._tasks), return_exceptions=True)

    # ------------------------------------------------------------------ internos
    def _spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, job_id: uuid.UUID) -> None:
        async with self._semaphore:
            claimed = await self._claim(job_id)
            if claimed is None:
                return
            document_id, attempt = claimed
            log.info(
                "job_started", job_id=str(job_id), document_id=str(document_id), attempt=attempt
            )
            try:
                await process_document(self.ctx, document_id)
            except DocumentGone:
                log.info("job_document_gone", job_id=str(job_id))
            except Exception as exc:
                await self._handle_failure(job_id, document_id, attempt, exc)
            else:
                await self._finish(job_id, JobStatus.DONE)
                log.info("job_done", job_id=str(job_id), document_id=str(document_id))

    async def _claim(self, job_id: uuid.UUID) -> tuple[uuid.UUID, int] | None:
        async with session_scope(self.ctx.session_factory) as db:
            job = await db.get(ProcessingJob, job_id, with_for_update=True)
            if job is None or job.status != JobStatus.QUEUED:
                return None
            job.status = JobStatus.RUNNING
            job.attempts += 1
            job.started_at = func.now()
            return job.document_id, job.attempts

    async def _finish(self, job_id: uuid.UUID, status: JobStatus, error: str | None = None) -> None:
        async with session_scope(self.ctx.session_factory) as db:
            await db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.id == job_id)
                .values(status=status, finished_at=func.now(), last_error=error)
            )

    async def _handle_failure(
        self, job_id: uuid.UUID, document_id: uuid.UUID, attempt: int, exc: Exception
    ) -> None:
        message = exc.message if isinstance(exc, AppError) else GENERIC_FAILURE
        retryable = isinstance(exc, ExternalServiceError) and attempt < self.max_attempts
        log_fn = log.warning if retryable or isinstance(exc, AppError) else log.exception
        log_fn("job_failed", job_id=str(job_id), attempt=attempt, retry=retryable, error=str(exc))

        async with session_scope(self.ctx.session_factory) as db:
            job = await db.get(ProcessingJob, job_id)
            if job is None:  # documento excluído (cascade)
                return
            job.last_error = message[:2000]
            if retryable:
                job.status = JobStatus.QUEUED
            else:
                job.status = JobStatus.FAILED
                job.finished_at = func.now()
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(status=DocumentStatus.FAILED, error_message=message[:2000])
                )

        if retryable:
            self._spawn(self._retry_later(job_id, self.retry_base_delay * attempt))

    async def _retry_later(self, job_id: uuid.UUID, delay: float) -> None:
        await asyncio.sleep(delay)
        await self._run(job_id)
