from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.banco import obter_sessao


def test_saude_ok_quando_o_banco_responde(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "banco": "ok"}


def test_saude_503_quando_o_banco_esta_fora(app: FastAPI) -> None:
    sessao = MagicMock()
    sessao.execute.side_effect = OperationalError("SELECT 1", {}, Exception("conexão recusada"))
    app.dependency_overrides[obter_sessao] = lambda: sessao

    resposta = TestClient(app).get("/api/v1/health")

    assert resposta.status_code == 503
    assert resposta.json() == {"status": "degradado", "banco": "indisponivel"}


def test_documentacao_openapi_disponivel(cliente: TestClient) -> None:
    assert cliente.get("/docs").status_code == 200
    esquema = cliente.get("/api/v1/openapi.json").json()
    assert "/api/v1/health" in esquema["paths"]
