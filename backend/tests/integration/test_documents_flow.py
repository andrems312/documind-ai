"""Fluxo completo de documentos contra Postgres + pgvector reais."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import func, select

from app.db.models import DocumentChunk, DocumentPage, ProcessingJob
from tests.integration.conftest import upload
from tests.pdfs import contract_pdf, make_pdf


async def _count(app, model, document_id) -> int:
    async with app.state.session_factory() as db:
        return await db.scalar(
            select(func.count()).select_from(model).where(model.document_id == document_id)
        )


async def test_upload_is_processed_into_pages_and_chunks(integration_app, api, user_a) -> None:
    response = await upload(api, user_a, contract_pdf(), name="Contrato_ACME.pdf")
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["title"] == "Contrato ACME"
    assert created["status"] == "uploaded"
    assert created["page_count"] == 3

    await integration_app.state.job_runner.wait_idle()

    detail = (await api.get(f"/api/v1/documents/{created['id']}", headers=user_a)).json()
    assert detail["status"] == "ready", detail
    assert detail["processed_pages"] == 3
    assert detail["progress"] == 1.0
    assert detail["processed_at"] is not None

    document_id = uuid.UUID(created["id"])
    assert await _count(integration_app, DocumentPage, document_id) == 3
    assert await _count(integration_app, DocumentChunk, document_id) >= 3

    page = (await api.get(f"/api/v1/documents/{created['id']}/pages/2", headers=user_a)).json()
    assert page["page_count"] == 3
    assert "prazo de vigência" in page["text"]
    assert "ACME Consultoria" not in page["text"]  # cabeçalho repetido removido

    async with integration_app.state.session_factory() as db:
        job = await db.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id))
        assert job is not None and job.status.value == "done" and job.attempts == 1

    listing = (await api.get("/api/v1/documents", headers=user_a)).json()
    assert [d["id"] for d in listing] == [created["id"]]
    ready_only = (await api.get("/api/v1/documents?status=failed", headers=user_a)).json()
    assert ready_only == []


async def test_duplicate_upload_returns_conflict(integration_app, api, user_a) -> None:
    data = contract_pdf()  # mesmos bytes: o PyMuPDF gera arquivos diferentes a cada chamada
    first = await upload(api, user_a, data)
    second = await upload(api, user_a, data, name="copia.pdf")
    assert second.status_code == 409
    assert second.json()["error"]["details"]["document_id"] == first.json()["id"]
    await integration_app.state.job_runner.wait_idle()


async def test_invalid_file_is_rejected_and_nothing_is_stored(integration_app, api, user_a) -> None:
    response = await upload(api, user_a, b"nao sou um pdf de verdade", name="falso.pdf")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unprocessable"
    storage_dir = Path(integration_app.state.settings.local_storage_dir)
    assert not any(storage_dir.rglob("*.pdf"))


async def test_scanned_pdf_fails_with_clear_message(integration_app, api, user_a) -> None:
    created = (await upload(api, user_a, make_pdf(["", ""]), name="scan.pdf")).json()
    await integration_app.state.job_runner.wait_idle()
    detail = (await api.get(f"/api/v1/documents/{created['id']}", headers=user_a)).json()
    assert detail["status"] == "failed"
    assert "OCR" in detail["error_message"]


async def test_documents_are_isolated_between_users(integration_app, api, user_a, user_b) -> None:
    data = contract_pdf()
    created = (await upload(api, user_a, data)).json()
    await integration_app.state.job_runner.wait_idle()
    doc_url = f"/api/v1/documents/{created['id']}"

    assert (await api.get(doc_url, headers=user_b)).status_code == 404
    assert (await api.get(f"{doc_url}/file", headers=user_b)).status_code == 404
    assert (await api.get(f"{doc_url}/pages/1", headers=user_b)).status_code == 404
    assert (await api.delete(doc_url, headers=user_b)).status_code == 404
    assert (await api.get("/api/v1/documents", headers=user_b)).json() == []
    # o mesmo arquivo pode ser enviado por outro usuário (dedupe é por usuário)
    assert (await upload(api, user_b, data)).status_code == 201
    await integration_app.state.job_runner.wait_idle()


async def test_requests_without_token_are_rejected(api) -> None:
    assert (await api.get("/api/v1/documents")).status_code == 401


async def test_download_rename_reprocess_and_delete(integration_app, api, user_a) -> None:
    data = contract_pdf()
    created = (await upload(api, user_a, data)).json()
    await integration_app.state.job_runner.wait_idle()
    doc_url = f"/api/v1/documents/{created['id']}"
    document_id = uuid.UUID(created["id"])

    file_response = await api.get(f"{doc_url}/file", headers=user_a)
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "application/pdf"
    assert file_response.content == data

    renamed = await api.patch(doc_url, headers=user_a, json={"title": "Contrato renovado"})
    assert renamed.json()["title"] == "Contrato renovado"

    chunks_before = await _count(integration_app, DocumentChunk, document_id)
    reprocess = await api.post(f"{doc_url}/reprocess", headers=user_a)
    assert reprocess.status_code == 202
    await integration_app.state.job_runner.wait_idle()
    assert (await api.get(doc_url, headers=user_a)).json()["status"] == "ready"
    assert await _count(integration_app, DocumentChunk, document_id) == chunks_before

    storage_dir = Path(integration_app.state.settings.local_storage_dir)
    assert len(list(storage_dir.rglob("*.pdf"))) == 1
    assert (await api.delete(doc_url, headers=user_a)).status_code == 204
    assert (await api.get(doc_url, headers=user_a)).status_code == 404
    assert await _count(integration_app, DocumentChunk, document_id) == 0
    assert not any(storage_dir.rglob("*.pdf"))
