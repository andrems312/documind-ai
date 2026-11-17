import json

import httpx
import pytest

from app.ai.openrouter import OpenRouterClient
from app.core.exceptions import ExternalServiceError


async def _no_sleep(_: float) -> None:
    return None


def _client(handler, *, dim: int = 3, key: str = "sk-test") -> OpenRouterClient:
    return OpenRouterClient(
        api_key=key,
        base_url="https://openrouter.test/api/v1",
        chat_model="openai/gpt-test",
        embedding_model="openai/emb-test",
        embedding_dim=dim,
        app_url="http://localhost:3000",
        transport=httpx.MockTransport(handler),
        sleep=_no_sleep,
    )


async def test_embed_sorts_by_index_and_sends_auth_headers() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["referer"] = request.headers["http-referer"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0, 1, 0]},
                    {"index": 0, "embedding": [1, 0, 0]},
                ],
                "usage": {"prompt_tokens": 7},
            },
        )

    result = await _client(handler).embed(["a", "b"])
    assert result.vectors == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    assert result.prompt_tokens == 7
    assert seen["auth"] == "Bearer sk-test"
    assert seen["referer"] == "http://localhost:3000"
    assert seen["body"] == {"model": "openai/emb-test", "input": ["a", "b"]}


async def test_embed_rejects_wrong_dimension() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1, 2]}]})

    with pytest.raises(ExternalServiceError, match="EMBEDDING_DIM=3"):
        await _client(handler).embed(["a"])


async def test_retries_on_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"error": {"message": "slow down"}})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 1}}
        )

    result = await _client(handler).complete([], temperature=0, max_tokens=10)
    assert result.content == "ok"
    assert calls["n"] == 3


async def test_maps_401_to_clear_message_without_retry() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    with pytest.raises(ExternalServiceError, match="Chave do OpenRouter inválida"):
        await _client(handler).complete([], temperature=0, max_tokens=10)
    assert calls["n"] == 1


async def test_missing_key_fails_before_any_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("não deveria chamar a rede")

    with pytest.raises(ExternalServiceError, match="OPENROUTER_API_KEY"):
        await _client(handler, key="").embed(["a"])


async def test_stream_parses_sse_ignoring_comments_and_reads_usage() -> None:
    body = (
        ": OPENROUTER PROCESSING\n\n"
        'data: {"choices":[{"delta":{"content":"Olá"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":", mundo"}}]}\n\n'
        'data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":12,"completion_tokens":3}}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is True
        return httpx.Response(
            200, content=body.encode(), headers={"content-type": "text/event-stream"}
        )

    events = [e async for e in _client(handler).stream([], temperature=0, max_tokens=10)]
    assert "".join(e.delta for e in events) == "Olá, mundo"
    assert events[-1].prompt_tokens == 12 and events[-1].completion_tokens == 3


async def test_stream_raises_on_midstream_error() -> None:
    body = 'data: {"choices":[{"delta":{"content":"a"}}]}\n\ndata: {"error":{"message":"boom"}}\n\n'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body.encode())

    with pytest.raises(ExternalServiceError, match="boom"):
        async for _ in _client(handler).stream([], temperature=0, max_tokens=10):
            pass
