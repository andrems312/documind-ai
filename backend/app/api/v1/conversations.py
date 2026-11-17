from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentProfile, DbDep, RagDep
from app.core.rate_limit import limiter
from app.schemas.conversations import (
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
    ConversationUpdate,
    MessageCreate,
)
from app.services import conversations as service

router = APIRouter()


@router.post(
    "",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma conversa sobre um conjunto de documentos",
)
async def create_conversation(
    payload: ConversationCreate, profile: CurrentProfile, db: DbDep
) -> ConversationRead:
    return await service.create_conversation(db, profile.id, payload.document_ids, payload.title)


@router.get("", response_model=list[ConversationRead], summary="Lista as conversas")
async def list_conversations(profile: CurrentProfile, db: DbDep) -> list[ConversationRead]:
    return await service.list_conversations(db, profile.id)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="Histórico completo com citações",
)
async def get_conversation(
    conversation_id: uuid.UUID, profile: CurrentProfile, db: DbDep
) -> ConversationDetail:
    return await service.get_detail(db, profile.id, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationRead, summary="Renomeia")
async def rename_conversation(
    conversation_id: uuid.UUID, payload: ConversationUpdate, profile: CurrentProfile, db: DbDep
) -> ConversationRead:
    conversation = await service.get_owned(db, profile.id, conversation_id)
    return await service.rename_conversation(db, conversation, payload.title)


@router.delete(
    "/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclui a conversa"
)
async def delete_conversation(
    conversation_id: uuid.UUID, profile: CurrentProfile, db: DbDep
) -> Response:
    conversation = await service.get_owned(db, profile.id, conversation_id)
    await service.delete_conversation(db, conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _sse(event: dict[str, object]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post(
    "/{conversation_id}/messages",
    summary="Envia uma pergunta e recebe a resposta em streaming (Server-Sent Events)",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": (
                "Eventos JSON em linhas `data:`: `status`, `token` (delta), "
                "`done` (mensagem persistida com citações) ou `error`."
            ),
        }
    },
)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    profile: CurrentProfile,
    db: DbDep,
    rag: RagDep,
) -> StreamingResponse:
    # Posse verificada antes de abrir o stream; o gerador usa sessões próprias.
    await service.get_owned(db, profile.id, conversation_id)
    user_id = profile.id
    await db.commit()

    async def events() -> AsyncIterator[str]:
        async for event in rag.stream_answer(
            user_id=user_id, conversation_id=conversation_id, question=payload.content
        ):
            yield _sse(event)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
