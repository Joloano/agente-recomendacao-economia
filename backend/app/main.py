"""Ponto de entrada ASGI. Execute com `uvicorn app.main:app`."""

from app.fabrica import criar_app

app = criar_app()
