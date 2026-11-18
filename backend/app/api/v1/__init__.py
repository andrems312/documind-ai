from fastapi import APIRouter

from app.api.v1 import (
    analyses,
    conversations,
    documents,
    folders,
    health,
    me,
    search,
    stats,
)

router = APIRouter()
router.include_router(health.router, tags=["Sistema"])
router.include_router(me.router, prefix="/me", tags=["Perfil"])
router.include_router(stats.router, prefix="/stats", tags=["Estatísticas"])
router.include_router(folders.router, prefix="/folders", tags=["Pastas"])
router.include_router(documents.router, prefix="/documents", tags=["Documentos"])
router.include_router(conversations.router, prefix="/conversations", tags=["Conversas"])
router.include_router(analyses.router, prefix="/analyses", tags=["Análises"])
router.include_router(search.router, prefix="/search", tags=["Busca"])
