"""Cliente HTTP do OpenRouter (API compatível com OpenAI) para chat, streaming e embeddings.

- Retry com backoff exponencial em 429/5xx e falhas de rede (no streaming, apenas antes do
  primeiro byte de resposta).
- Erros convertidos em `ExternalServiceError` com mensagens em português.
- Valida a dimensão dos embeddings contra `EMBEDDING_DIM` para não gravar vetores incompatíveis.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx

from app.ai.providers import ChatCompletion, ChatMessage, ChatStreamEvent, EmbeddingBatch
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

log = get_logger(__name__)

_RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
_STATUS_MESSAGES = {
    400: "O OpenRouter rejeitou a requisição. Verifique o modelo configurado.",
    401: "Chave do OpenRouter inválida. Confira OPENROUTER_API_KEY.",
    402: "Créditos insuficientes na conta do OpenRouter.",
    403: "O OpenRouter recusou o conteúdo (moderação) ou o acesso ao modelo.",
    404: "Modelo não encontrado no OpenRouter. Confira LLM_MODEL e EMBEDDING_MODEL.",
    429: "Limite de requisições do OpenRouter atingido. Tente novamente em instantes.",
}


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        chat_model: str,
        embedding_model: str,
        embedding_dim: int,
        app_url: str = "",
        app_name: str = "DocuMind AI",
        timeout: float = 60.0,
        max_retries: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.model = chat_model
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self._api_key = api_key
        self._max_retries = max_retries
        self._sleep = sleep
        headers = {"X-Title": app_name}
        if app_url:
            headers["HTTP-Referer"] = app_url
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(timeout, connect=10.0),
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------ embeddings
    async def embed(self, texts: list[str]) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch(vectors=[])
        data = await self._post_json("/embeddings", {"model": self.embedding_model, "input": texts})
        try:
            items = sorted(data["data"], key=lambda item: item["index"])
            vectors = [list(map(float, item["embedding"])) for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceError("Resposta de embeddings inválida do OpenRouter.") from exc

        if len(vectors) != len(texts):
            raise ExternalServiceError(
                f"O OpenRouter retornou {len(vectors)} embeddings para {len(texts)} textos."
            )
        wrong = next((len(v) for v in vectors if len(v) != self.embedding_dim), None)
        if wrong is not None:
            raise ExternalServiceError(
                f"O modelo {self.embedding_model} gera vetores de dimensão {wrong}, mas "
                f"EMBEDDING_DIM={self.embedding_dim}. Ajuste a configuração e a migração."
            )
        usage = data.get("usage") or {}
        return EmbeddingBatch(vectors=vectors, prompt_tokens=int(usage.get("prompt_tokens") or 0))

    # ------------------------------------------------------------------ chat
    def _chat_payload(
        self, messages: list[ChatMessage], temperature: float, max_tokens: int, stream: bool
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stream:
            payload["stream"] = True
            payload["usage"] = {"include": True}
        return payload

    async def complete(
        self, messages: list[ChatMessage], *, temperature: float, max_tokens: int
    ) -> ChatCompletion:
        data = await self._post_json(
            "/chat/completions", self._chat_payload(messages, temperature, max_tokens, False)
        )
        try:
            content = data["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ExternalServiceError("Resposta de chat inválida do OpenRouter.") from exc
        usage = data.get("usage") or {}
        return ChatCompletion(
            content=content,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )

    async def stream(
        self, messages: list[ChatMessage], *, temperature: float, max_tokens: int
    ) -> AsyncIterator[ChatStreamEvent]:
        self._require_key()
        payload = self._chat_payload(messages, temperature, max_tokens, True)

        for attempt in range(self._max_retries + 1):
            try:
                async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
                    if resp.status_code != 200:
                        body = (await resp.aread()).decode(errors="replace")
                        if resp.status_code in _RETRY_STATUS and attempt < self._max_retries:
                            await self._backoff(attempt, resp.status_code)
                            continue
                        raise self._error_for(resp.status_code, body)

                    async for event in self._parse_sse(resp):
                        yield event
                    return
            except httpx.TransportError as exc:
                if attempt < self._max_retries:
                    await self._backoff(attempt, None)
                    continue
                raise ExternalServiceError("Não foi possível conectar ao OpenRouter.") from exc

    @staticmethod
    async def _parse_sse(resp: httpx.Response) -> AsyncIterator[ChatStreamEvent]:
        async for line in resp.aiter_lines():
            if not line or line.startswith(":") or not line.startswith("data:"):
                continue  # comentários de keep-alive (": OPENROUTER PROCESSING") e linhas vazias
            raw = line[5:].strip()
            if raw == "[DONE]":
                return
            try:
                chunk = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "error" in chunk:
                message = (chunk["error"] or {}).get("message", "erro desconhecido")
                raise ExternalServiceError(f"O modelo interrompeu a resposta: {message}")
            choices = chunk.get("choices") or []
            delta = ((choices[0].get("delta") or {}).get("content") or "") if choices else ""
            usage = chunk.get("usage")
            if delta:
                yield ChatStreamEvent(delta=delta)
            if usage:
                yield ChatStreamEvent(
                    prompt_tokens=int(usage.get("prompt_tokens") or 0),
                    completion_tokens=int(usage.get("completion_tokens") or 0),
                )

    # ------------------------------------------------------------------ infraestrutura
    def _require_key(self) -> None:
        if not self._api_key:
            raise ExternalServiceError(
                "OPENROUTER_API_KEY não está configurada no backend. "
                "Crie uma chave em https://openrouter.ai/settings/keys e adicione ao .env."
            )

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_key()
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(path, json=payload)
            except httpx.TransportError as exc:
                if attempt < self._max_retries:
                    await self._backoff(attempt, None)
                    continue
                raise ExternalServiceError("Não foi possível conectar ao OpenRouter.") from exc

            if response.status_code in _RETRY_STATUS and attempt < self._max_retries:
                await self._backoff(attempt, response.status_code)
                continue
            if not response.is_success:
                raise self._error_for(response.status_code, response.text)
            try:
                data: dict[str, Any] = response.json()
            except ValueError as exc:
                raise ExternalServiceError("Resposta inválida do OpenRouter.") from exc
            if "error" in data and not data.get("choices") and not data.get("data"):
                code = (data["error"] or {}).get("code")
                raise self._error_for(code if isinstance(code, int) else 502, response.text)
            return data
        raise ExternalServiceError("O OpenRouter não respondeu após várias tentativas.")

    async def _backoff(self, attempt: int, status: int | None) -> None:
        delay = min(8.0, 0.5 * 2**attempt) + random.uniform(0, 0.25)
        log.warning("openrouter_retry", attempt=attempt + 1, status=status, delay=round(delay, 2))
        await self._sleep(delay)

    @staticmethod
    def _error_for(status: int, body: str) -> ExternalServiceError:
        log.error("openrouter_error", status=status, body=body[:500])
        message = _STATUS_MESSAGES.get(status, f"Falha no OpenRouter (HTTP {status}).")
        return ExternalServiceError(message, details={"status": status})
