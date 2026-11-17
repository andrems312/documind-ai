"""Orquestração do RAG: pergunta → recuperação → resposta em streaming → citações persistidas.

Fluxo:
1. Persiste a pergunta e carrega o histórico recente da conversa.
2. Se houver histórico, reescreve a pergunta como autônoma (só para a busca).
3. Gera o embedding da busca e executa a recuperação híbrida nos documentos da conversa.
4. Sem trechos relevantes → abstenção imediata, sem chamar o LLM (nada a fundamentar).
5. Caso contrário, envia contexto numerado ao LLM e repassa os tokens em streaming.
6. Valida as citações contra os trechos enviados, persiste resposta + citações + uso.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import func, select, update

from app.ai.guards import NO_ANSWER, is_abstention, sanitize_citations
from app.ai.prompts import build_answer_messages, build_condense_messages
from app.ai.providers import ChatMessage, ChatProvider, EmbeddingProvider
from app.ai.retrieval import RetrievedChunk, fit_to_budget, hybrid_search
from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.db.models import (
    Conversation,
    ConversationDocument,
    Message,
    MessageCitation,
    MessageRole,
    UsageEvent,
    UsageKind,
)
from app.db.session import SessionFactory, session_scope
from app.schemas.conversations import CitationRead, MessageRead

log = get_logger(__name__)

DEFAULT_TITLE = "Nova conversa"


def title_from_question(question: str, limit: int = 80) -> str:
    clean = " ".join(question.split())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


class RagService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: SessionFactory,
        embedder: EmbeddingProvider,
        chat: ChatProvider,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.embedder = embedder
        self.chat = chat

    async def stream_answer(
        self, *, user_id: uuid.UUID, conversation_id: uuid.UUID, question: str
    ) -> AsyncIterator[dict[str, Any]]:
        try:
            history, document_ids = await self._persist_question(conversation_id, question)
            yield {"type": "status", "stage": "retrieving"}

            search_query = question
            if history:
                search_query = await self._condense(history, question)

            embedding = (await self.embedder.embed([search_query])).vectors[0]
            async with session_scope(self.session_factory) as db:
                retrieved = await hybrid_search(
                    db,
                    user_id=user_id,
                    query_text=search_query,
                    query_embedding=embedding,
                    document_ids=document_ids,
                    candidates=self.settings.rag_candidates,
                    top_k=self.settings.rag_top_k,
                    min_similarity=self.settings.rag_min_similarity,
                )
            sources = fit_to_budget(retrieved, self.settings.rag_context_tokens)
            log.info(
                "rag_retrieval",
                conversation_id=str(conversation_id),
                retrieved=len(retrieved),
                used=len(sources),
                rewritten=search_query != question,
            )

            if not sources:
                yield {"type": "token", "delta": NO_ANSWER}
                message = await self._persist_answer(
                    user_id, conversation_id, NO_ANSWER, [], (0, 0), abstained=True
                )
                yield {"type": "done", "message": message, "abstained": True, "grounded": True}
                return

            yield {"type": "status", "stage": "generating", "sources": len(sources)}
            messages = build_answer_messages(history, question, sources)
            parts: list[str] = []
            usage = (0, 0)
            async for event in self.chat.stream(
                messages,
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            ):
                if event.delta:
                    parts.append(event.delta)
                    yield {"type": "token", "delta": event.delta}
                if event.prompt_tokens is not None:
                    usage = (event.prompt_tokens, event.completion_tokens or 0)

            content, used = sanitize_citations("".join(parts), len(sources))
            abstained = not used and is_abstention(content)
            if abstained:
                content = NO_ANSWER
            elif not content:
                content = NO_ANSWER
                abstained = True
            cited = [(rank, sources[rank - 1]) for rank in used]
            message = await self._persist_answer(
                user_id, conversation_id, content, cited, usage, abstained=abstained
            )
            yield {
                "type": "done",
                "message": message,
                "abstained": abstained,
                "grounded": abstained or bool(cited),
            }
        except AppError as exc:
            log.warning("rag_failed", conversation_id=str(conversation_id), error=exc.message)
            yield {"type": "error", "code": exc.code, "message": exc.message}
        except Exception:
            log.exception("rag_unexpected_error", conversation_id=str(conversation_id))
            yield {
                "type": "error",
                "code": "internal_error",
                "message": "Erro inesperado ao gerar a resposta. Tente novamente.",
            }

    # ------------------------------------------------------------------ etapas
    async def _persist_question(
        self, conversation_id: uuid.UUID, question: str
    ) -> tuple[list[ChatMessage], list[uuid.UUID]]:
        limit = self.settings.rag_history_messages
        async with session_scope(self.session_factory) as db:
            conversation = await db.get(Conversation, conversation_id)
            if conversation is None:
                raise AppError("Conversa não encontrada.")
            recent = (
                (
                    await db.scalars(
                        select(Message)
                        .where(Message.conversation_id == conversation_id)
                        .order_by(Message.created_at.desc())
                        .limit(limit)
                    )
                ).all()
                if limit
                else []
            )
            history: list[ChatMessage] = [
                {"role": m.role.value, "content": m.content}  # type: ignore[typeddict-item]
                for m in reversed(recent)
            ]
            document_ids = list(
                (
                    await db.scalars(
                        select(ConversationDocument.document_id).where(
                            ConversationDocument.conversation_id == conversation_id
                        )
                    )
                ).all()
            )
            db.add(
                Message(conversation_id=conversation_id, role=MessageRole.USER, content=question)
            )
            values: dict[str, Any] = {"updated_at": func.now()}
            if conversation.title == DEFAULT_TITLE:
                values["title"] = title_from_question(question)
            await db.execute(
                update(Conversation).where(Conversation.id == conversation_id).values(**values)
            )
        return history, document_ids

    async def _condense(self, history: list[ChatMessage], question: str) -> str:
        try:
            result = await self.chat.complete(
                build_condense_messages(history, question), temperature=0.0, max_tokens=200
            )
        except AppError as exc:
            log.warning("rag_condense_failed", error=exc.message)
            return question
        rewritten = result.content.strip().strip('"').strip()
        return rewritten or question

    async def _persist_answer(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        content: str,
        cited: list[tuple[int, RetrievedChunk]],
        usage: tuple[int, int],
        *,
        abstained: bool,
    ) -> dict[str, Any]:
        async with session_scope(self.session_factory) as db:
            message = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=content,
                model=None if abstained and not usage[0] else self.chat.model,
                prompt_tokens=usage[0],
                completion_tokens=usage[1],
            )
            db.add(message)
            await db.flush()
            citations = [
                MessageCitation(
                    message_id=message.id,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    page_number=chunk.page_number,
                    excerpt=chunk.content,
                    score=round(chunk.similarity, 4),
                    rank=rank,
                )
                for rank, chunk in cited
            ]
            db.add_all(citations)
            db.add(
                UsageEvent(
                    user_id=user_id,
                    kind=UsageKind.QUESTION,
                    prompt_tokens=usage[0],
                    completion_tokens=usage[1],
                )
            )
            await db.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(updated_at=func.now())
            )
            await db.flush()
            await db.refresh(message, attribute_names=["created_at"])
            titles = {chunk.document_id: chunk.document_title for _, chunk in cited}
            return MessageRead(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                citations=[
                    CitationRead(
                        id=c.id,
                        rank=c.rank,
                        document_id=c.document_id,
                        document_title=titles[c.document_id],
                        page_number=c.page_number,
                        excerpt=c.excerpt,
                        score=c.score,
                    )
                    for c in citations
                ],
            ).model_dump(mode="json")
