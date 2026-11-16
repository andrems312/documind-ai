from fastapi import APIRouter

from app.api.v1 import health, me

router = APIRouter()
router.include_router(health.router, tags=["Sistema"])
router.include_router(me.router, prefix="/me", tags=["Perfil"])
