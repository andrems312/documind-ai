"""Chat com RAG de ponta a ponta: recuperação híbrida real (pgvector + full-text) e streaming SSE.

Os provedores de IA são determinísticos (tests/fakes.py); banco, SQL vetorial, pipeline,
validação de citações e persistência são os reais.
"""

from __future__ import annotations

import uuid

from app.ai.guards import NO_ANSWER
from app.ai.retrieval import hybrid_search
from tests.integration.conftest import parse_sse, upload
from tests.pdfs import contract_pdf, make_pdf


async def _ready_document(app, api, headers, data: bytes | None = None, name="contrato.pdf"):
    created = (await upload(api, headers, data or contract_pdf(), name=name)).json()
    await app.state.job_runner.wait_idle()
    return created["id"]


async def _ask(api, headers, conversation_id: str, question: str):
    response = await api.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": question},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return parse_sse(response.text)


async def test_answer_streams_tokens_and_cites_the_right_page(integration_app, api, user_a) -> None:
    document_id = await _ready_document(integration_app, api, user_a)
    conversation = (
        await api.post(
            "/api/v1/conversations", headers=user_a, json={"document_ids": [document_id]}
        )
    ).json()
    assert conversation["title"] == "Nova conversa"

    events = await _ask(api, user_a, conversation["id"], "Qual é o prazo de vigência do contrato?")
    types = [e["type"] for e in events]
    assert types[0] == "status" and "token" in types and types[-1] == "done"

    done = events[-1]
    message = done["message"]
    assert done["abstained"] is False and done["grounded"] is True
    assert message["role"] == "assistant"
    assert "[1]" in message["content"]
    assert "[9]" not in message["content"]  # citação inexistente removida pelo guard
    citation = message["citations"][0]
    assert citation["rank"] == 1
    assert citation["page_number"] == 2
    assert citation["document_id"] == document_id
    assert "24 meses" in citation["excerpt"]

    streamed = "".join(e["delta"] for e in events if e["type"] == "token")
    assert "[9]" in streamed  # o texto bruto chegou em streaming; o persistido foi saneado

    detail = (await api.get(f"/api/v1/conversations/{conversation['id']}", headers=user_a)).json()
    assert detail["title"] == "Qual é o prazo de vigência do contrato?"
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["citations"][0]["page_number"] == 2
    assert detail["messages"][1]["citations"][0]["document_title"] == "contrato"


async def test_unrelated_question_abstains_without_calling_the_llm(
    integration_app, api, user_a
) -> None:
    document_id = await _ready_document(integration_app, api, user_a)
    conversation = (
        await api.post(
            "/api/v1/conversations", headers=user_a, json={"document_ids": [document_id]}
        )
    ).json()
    chat = integration_app.state.chat

    events = await _ask(
        api, user_a, conversation["id"], "Quem venceu a final do campeonato mundial?"
    )
    done = events[-1]
    assert done["type"] == "done"
    assert done["abstained"] is True
    assert done["message"]["content"] == NO_ANSWER
    assert done["message"]["citations"] == []
    assert chat.stream_calls == []


async def test_follow_up_question_is_rewritten_with_history(integration_app, api, user_a) -> None:
    document_id = await _ready_document(integration_app, api, user_a)
    conversation = (
        await api.post(
            "/api/v1/conversations", headers=user_a, json={"document_ids": [document_id]}
        )
    ).json()
    await _ask(api, user_a, conversation["id"], "Qual é o valor mensal dos serviços?")
    events = await _ask(api, user_a, conversation["id"], "E qual é a multa por rescisão?")

    chat = integration_app.state.chat
    assert len(chat.complete_calls) == 1  # reescrita contextual só quando há histórico
    assert events[-1]["message"]["citations"][0]["page_number"] == 3
    last_prompt = chat.stream_calls[-1]
    assert [m["role"] for m in last_prompt[:3]] == ["system", "user", "assistant"]


async def test_conversation_only_searches_its_documents(integration_app, api, user_a) -> None:
    contract = await _ready_document(integration_app, api, user_a)
    other = await _ready_document(
        integration_app,
        api,
        user_a,
        make_pdf(["Manual de jardinagem: regue as orquídeas duas vezes por semana."]),
        name="manual.pdf",
    )
    conversation = (
        await api.post("/api/v1/conversations", headers=user_a, json={"document_ids": [other]})
    ).json()
    events = await _ask(api, user_a, conversation["id"], "Qual é o prazo de vigência do contrato?")
    assert events[-1]["abstained"] is True

    library = (await api.post("/api/v1/conversations", headers=user_a, json={})).json()
    events = await _ask(api, user_a, library["id"], "Qual é o prazo de vigência do contrato?")
    assert events[-1]["message"]["citations"][0]["document_id"] == contract


async def test_conversations_are_isolated_between_users(
    integration_app, api, user_a, user_b
) -> None:
    document_id = await _ready_document(integration_app, api, user_a)
    conversation = (
        await api.post(
            "/api/v1/conversations", headers=user_a, json={"document_ids": [document_id]}
        )
    ).json()
    url = f"/api/v1/conversations/{conversation['id']}"

    assert (await api.get(url, headers=user_b)).status_code == 404
    send = await api.post(f"{url}/messages", headers=user_b, json={"content": "Oi?"})
    assert send.status_code == 404
    assert (await api.get("/api/v1/conversations", headers=user_b)).json() == []
    # B não pode criar conversa sobre documento de A
    forbidden = await api.post(
        "/api/v1/conversations", headers=user_b, json={"document_ids": [document_id]}
    )
    assert forbidden.status_code == 422


async def test_rename_and_delete_conversation(integration_app, api, user_a) -> None:
    conversation = (await api.post("/api/v1/conversations", headers=user_a, json={})).json()
    url = f"/api/v1/conversations/{conversation['id']}"
    renamed = await api.patch(url, headers=user_a, json={"title": "Análise do contrato"})
    assert renamed.json()["title"] == "Análise do contrato"
    assert (await api.delete(url, headers=user_a)).status_code == 204
    assert (await api.get(url, headers=user_a)).status_code == 404


async def test_empty_question_is_rejected(api, user_a) -> None:
    conversation = (await api.post("/api/v1/conversations", headers=user_a, json={})).json()
    response = await api.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=user_a,
        json={"content": "   "},
    )
    assert response.status_code == 422


async def test_hybrid_search_matches_exact_terms_via_full_text(integration_app, api, user_a):
    await _ready_document(integration_app, api, user_a)
    embedder = integration_app.state.embedder
    owner = uuid.UUID((await api.get("/api/v1/me", headers=user_a)).json()["id"])
    query = "foro Curitiba"
    async with integration_app.state.session_factory() as db:
        # vetor sem relação nenhuma com o texto: só o full-text pode encontrar o trecho
        results = await hybrid_search(
            db,
            user_id=owner,
            query_text=query,
            query_embedding=embedder.vector("zzz"),
            min_similarity=0.99,
        )
    assert results, "o full-text deveria encontrar o termo exato"
    assert results[0].page_number == 3
    assert results[0].text_rank is not None
