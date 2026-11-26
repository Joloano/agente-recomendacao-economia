"""Ponto de entrada da API. Execute com `uvicorn app.main:app`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import router as router_v1
from app.core.config import Configuracoes, obter_configuracoes
from app.core.erros import registrar_tratadores


def criar_app(configuracoes: Configuracoes | None = None) -> FastAPI:
    config = configuracoes or obter_configuracoes()
    app = FastAPI(
        title=config.nome_app,
        version=__version__,
        description="API REST do agente que recomenda ações de economia de energia e água.",
        docs_url="/docs",
        openapi_url="/api/v1/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origens,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_tratadores(app)
    app.include_router(router_v1)
    return app


app = criar_app()
