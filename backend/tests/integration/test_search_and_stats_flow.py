"""Busca semântica global e dashboard de estatísticas, de ponta a ponta."""

from __future__ import annotations

from tests.integration.conftest import upload
from tests.pdfs import contract_pdf, make_pdf


async def _ready(app, api, headers, data: bytes | None = None, name="contrato.pdf") -> str:
    created = (await upload(api, headers, data or contract_pdf(), name=name)).json()
    await app.state.job_runner.wait_idle()
    return created["id"]


async def test_search_finds_exact_term(integration_app, api, user_a) -> None:
    document_id = await _ready(integration_app, api, user_a)
    response = await api.get("/api/v1/search", headers=user_a, params={"q": "foro Curitiba"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    top = body["results"][0]
    assert top["document_id"] == document_id
    assert top["page_number"] == 3
    assert "Curitiba" in top["excerpt"]


async def test_search_can_filter_by_folder(integration_app, api, user_a) -> None:
    contract = await _ready(integration_app, api, user_a)
    await _ready(
        integration_app,
        api,
        user_a,
        make_pdf(["Cláusula 5. Fica eleito o foro da comarca de Curitiba."]),
        name="outro.pdf",
    )
    folder = (await api.post("/api/v1/folders", headers=user_a, json={"name": "Só este"})).json()
    await api.patch(
        f"/api/v1/documents/{contract}", headers=user_a, json={"folder_id": folder["id"]}
    )

    scoped = (
        await api.get(
            "/api/v1/search",
            headers=user_a,
            params={"q": "foro Curitiba", "folder_id": folder["id"]},
        )
    ).json()
    assert scoped["count"] >= 1
    assert {r["document_id"] for r in scoped["results"]} == {contract}


async def test_search_is_isolated_between_users(integration_app, api, user_a, user_b) -> None:
    await _ready(integration_app, api, user_a)
    empty = (await api.get("/api/v1/search", headers=user_b, params={"q": "foro Curitiba"})).json()
    assert empty["results"] == []


async def test_stats_overview_reflects_activity(integration_app, api, user_a) -> None:
    before = (await api.get("/api/v1/stats/overview", headers=user_a)).json()
    assert before["documents"]["total"] == 0

    document_id = await _ready(integration_app, api, user_a)
    await api.post("/api/v1/analyses/summary", headers=user_a, json={"document_ids": [document_id]})

    after = (await api.get("/api/v1/stats/overview", headers=user_a)).json()
    assert after["documents"]["total"] == 1
    assert after["documents"]["ready"] == 1
    assert after["pages_indexed"] == 3
    assert after["chunks"] >= 1
    assert after["analyses"] == 1
    assert after["usage_by_kind"]["upload"] == 1
    assert after["usage_by_kind"]["summary"] == 1
    assert len(after["daily_usage"]) == 14
    assert sum(point["events"] for point in after["daily_usage"]) >= 2
