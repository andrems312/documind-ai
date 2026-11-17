from fastapi import APIRouter

from app.api.v1 import conversations, documents, health, me

router = APIRouter()
router.include_router(health.router, tags=["Sistema"])
router.include_router(me.router, prefix="/me", tags=["Perfil"])
router.include_router(documents.router, prefix="/documents", tags=["Documentos"])
router.include_router(conversations.router, prefix="/conversations", tags=["Conversas"])
