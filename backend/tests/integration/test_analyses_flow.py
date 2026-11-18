"""Análises: resumo, informações-chave, comparação, listagem, exportação e isolamento."""

from __future__ import annotations

import uuid

from app.db.models import Document, DocumentStatus
from tests.integration.conftest import upload
from tests.pdfs import contract_pdf, make_pdf


async def _ready(app, api, headers, data: bytes | None = None, name="contrato.pdf") -> str:
    created = (await upload(api, headers, data or contract_pdf(), name=name)).json()
    await app.state.job_runner.wait_idle()
    return created["id"]


async def test_summary_is_generated_and_persisted(integration_app, api, user_a) -> None:
    document_id = await _ready(integration_app, api, user_a)
    response = await api.post(
        "/api/v1/analyses/summary", headers=user_a, json={"document_ids": [document_id]}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "summary"
    assert body["document_titles"] == ["contrato"]
    assert body["content"]
    assert body["title"].startswith("Resumo:")

    listed = (await api.get("/api/v1/analyses", headers=user_a)).json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]
    assert "content" not in listed[0]

    detail = (await api.get(f"/api/v1/analyses/{body['id']}", headers=user_a)).json()
    assert detail["content"] == body["content"]


async def test_key_info_and_comparison(integration_app, api, user_a) -> None:
    doc_a = await _ready(integration_app, api, user_a)
    doc_b = await _ready(
        integration_app,
        api,
        user_a,
        make_pdf(["Manual de jardinagem: regue as orquídeas duas vezes por semana."]),
        name="manual.pdf",
    )

    key_info = await api.post(
        "/api/v1/analyses/key-info", headers=user_a, json={"document_ids": [doc_a]}
    )
    assert key_info.status_code == 201
    assert key_info.json()["type"] == "key_info"

    comparison = await api.post(
        "/api/v1/analyses/comparison", headers=user_a, json={"document_ids": [doc_a, doc_b]}
    )
    assert comparison.status_code == 201
    body = comparison.json()
    assert body["type"] == "comparison"
    assert len(body["document_titles"]) == 2


async def test_comparison_requires_two_documents(integration_app, api, user_a) -> None:
    document_id = await _ready(integration_app, api, user_a)
    response = await api.post(
        "/api/v1/analyses/comparison", headers=user_a, json={"document_ids": [document_id]}
    )
    assert response.status_code == 422


async def test_analysis_rejects_unprocessed_document(integration_app, api, user_a) -> None:
    # Documento em processamento (status != ready) inserido direto, sem corrida com o worker.
    owner = uuid.UUID((await api.get("/api/v1/me", headers=user_a)).json()["id"])
    doc_id = uuid.uuid4()
    async with integration_app.state.session_factory() as db:
        db.add(
            Document(
                id=doc_id,
                user_id=owner,
                title="Pendente",
                original_filename="pendente.pdf",
                storage_path=f"{owner}/{doc_id}.pdf",
                file_size=10,
                sha256="a" * 64,
                page_count=3,
                status=DocumentStatus.PROCESSING,
            )
        )
        await db.commit()

    response = await api.post(
        "/api/v1/analyses/summary", headers=user_a, json={"document_ids": [str(doc_id)]}
    )
    assert response.status_code == 422


async def test_export_markdown_and_pdf(integration_app, api, user_a) -> None:
    document_id = await _ready(integration_app, api, user_a)
    analysis = (
        await api.post(
            "/api/v1/analyses/summary", headers=user_a, json={"document_ids": [document_id]}
        )
    ).json()

    md = await api.get(f"/api/v1/analyses/{analysis['id']}/export?format=md", headers=user_a)
    assert md.status_code == 200
    assert md.headers["content-type"].startswith("text/markdown")
    assert md.text.startswith("# Resumo:")
    assert "attachment" in md.headers["content-disposition"]

    pdf = await api.get(f"/api/v1/analyses/{analysis['id']}/export?format=pdf", headers=user_a)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")


async def test_analyses_are_isolated_between_users(integration_app, api, user_a, user_b) -> None:
    document_id = await _ready(integration_app, api, user_a)
    analysis = (
        await api.post(
            "/api/v1/analyses/summary", headers=user_a, json={"document_ids": [document_id]}
        )
    ).json()

    assert (await api.get("/api/v1/analyses", headers=user_b)).json() == []
    assert (await api.get(f"/api/v1/analyses/{analysis['id']}", headers=user_b)).status_code == 404
    # B não pode analisar documento de A
    denied = await api.post(
        "/api/v1/analyses/summary", headers=user_b, json={"document_ids": [document_id]}
    )
    assert denied.status_code == 422

    assert (
        await api.delete(f"/api/v1/analyses/{analysis['id']}", headers=user_a)
    ).status_code == 204
