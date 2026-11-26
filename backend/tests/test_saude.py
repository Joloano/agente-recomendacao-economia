from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.banco import obter_sessao


@pytest.fixture
def cliente_sem_banco(app: FastAPI) -> Iterator[TestClient]:
    sessao = MagicMock()
    sessao.execute.side_effect = OperationalError("SELECT 1", {}, Exception("conexão recusada"))
    app.dependency_overrides[obter_sessao] = lambda: sessao
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def test_saude_ok_quando_o_banco_responde(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "banco": "ok"}


def test_saude_503_quando_o_banco_esta_fora(cliente_sem_banco: TestClient) -> None:
    resposta = cliente_sem_banco.get("/api/v1/health")

    assert resposta.status_code == 503
    assert resposta.json() == {"status": "degradado", "banco": "indisponivel"}


def test_documentacao_openapi_disponivel(cliente: TestClient) -> None:
    assert cliente.get("/docs").status_code == 200
    esquema = cliente.get("/api/v1/openapi.json").json()
    assert "/api/v1/health" in esquema["paths"]


def test_cors_permite_apenas_origens_configuradas(cliente: TestClient) -> None:
    def preflight(origem: str) -> dict[str, str]:
        return dict(
            cliente.options(
                "/api/v1/health",
                headers={"Origin": origem, "Access-Control-Request-Method": "GET"},
            ).headers
        )

    permitido = preflight("http://localhost:4200")
    negado = preflight("https://site-malicioso.com")

    assert permitido["access-control-allow-origin"] == "http://localhost:4200"
    assert "access-control-allow-credentials" not in permitido
    assert "access-control-allow-origin" not in negado


def test_liveness_nao_depende_do_banco(cliente_sem_banco: TestClient) -> None:
    resposta = cliente_sem_banco.get("/api/v1/health/live")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
