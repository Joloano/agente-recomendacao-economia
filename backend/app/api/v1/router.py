from fastapi import APIRouter

from app.api.v1.rotas import autenticacao, saude, usuarios

router = APIRouter(prefix="/api/v1")
router.include_router(saude.router)
router.include_router(autenticacao.router)
router.include_router(usuarios.perfil)
router.include_router(usuarios.admin)
