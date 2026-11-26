from fastapi import APIRouter

from app.api.v1.rotas import autenticacao, saude

router = APIRouter(prefix="/api/v1")
router.include_router(saude.router)
router.include_router(autenticacao.router)
