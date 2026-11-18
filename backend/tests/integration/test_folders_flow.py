"""Pastas: CRUD, mover documentos, filtrar, contagem e isolamento entre usuários."""

from __future__ import annotations

from tests.integration.conftest import upload
from tests.pdfs import contract_pdf


async def _document(api, headers, name="contrato.pdf"):
    return (await upload(api, headers, contract_pdf(), name=name)).json()


async def test_folder_crud_and_document_move(integration_app, api, user_a) -> None:
    folder = (
        await api.post(
            "/api/v1/folders", headers=user_a, json={"name": "Contratos", "color": "#7C6CF6"}
        )
    ).json()
    assert folder["name"] == "Contratos"
    assert folder["color"] == "#7c6cf6"
    assert folder["document_count"] == 0

    document = await _document(api, user_a)
    moved = await api.patch(
        f"/api/v1/documents/{document['id']}", headers=user_a, json={"folder_id": folder["id"]}
    )
    assert moved.status_code == 200
    assert moved.json()["folder_id"] == folder["id"]

    listed = (await api.get("/api/v1/folders", headers=user_a)).json()
    assert listed[0]["document_count"] == 1

    in_folder = (
        await api.get(f"/api/v1/documents?folder_id={folder['id']}", headers=user_a)
    ).json()
    assert [d["id"] for d in in_folder] == [document["id"]]

    # Tirar da pasta
    out = await api.patch(
        f"/api/v1/documents/{document['id']}", headers=user_a, json={"folder_id": None}
    )
    assert out.json()["folder_id"] is None


async def test_deleting_folder_keeps_documents(integration_app, api, user_a) -> None:
    folder = (await api.post("/api/v1/folders", headers=user_a, json={"name": "Temp"})).json()
    document = await _document(api, user_a)
    await api.patch(
        f"/api/v1/documents/{document['id']}", headers=user_a, json={"folder_id": folder["id"]}
    )

    assert (await api.delete(f"/api/v1/folders/{folder['id']}", headers=user_a)).status_code == 204

    still_there = await api.get(f"/api/v1/documents/{document['id']}", headers=user_a)
    assert still_there.status_code == 200
    assert still_there.json()["folder_id"] is None


async def test_duplicate_folder_name_is_rejected(integration_app, api, user_a) -> None:
    await api.post("/api/v1/folders", headers=user_a, json={"name": "Jurídico"})
    dup = await api.post("/api/v1/folders", headers=user_a, json={"name": "jurídico"})
    assert dup.status_code == 409


async def test_invalid_color_is_rejected(integration_app, api, user_a) -> None:
    bad = await api.post("/api/v1/folders", headers=user_a, json={"name": "X", "color": "roxo"})
    assert bad.status_code == 422


async def test_folders_are_isolated_between_users(integration_app, api, user_a, user_b) -> None:
    folder = (await api.post("/api/v1/folders", headers=user_a, json={"name": "De A"})).json()
    assert (await api.get("/api/v1/folders", headers=user_b)).json() == []
    assert (
        await api.patch(f"/api/v1/folders/{folder['id']}", headers=user_b, json={"name": "x"})
    ).status_code == 404
    assert (await api.delete(f"/api/v1/folders/{folder['id']}", headers=user_b)).status_code == 404

    # B não pode mover seu documento para uma pasta de A
    document = await _document(api, user_b)
    denied = await api.patch(
        f"/api/v1/documents/{document['id']}", headers=user_b, json={"folder_id": folder["id"]}
    )
    assert denied.status_code == 404
