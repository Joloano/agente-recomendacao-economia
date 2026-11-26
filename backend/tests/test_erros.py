from collections.abc import Iterator

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.erros import Conflito, NaoEncontrado, registrar_tratadores


class Entrada(BaseModel):
    peso: float = Field(ge=0, le=1)


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    app = FastAPI()
    registrar_tratadores(app)

    @app.post("/validar")
    def validar(entrada: Entrada) -> Entrada:
        return entrada

    @app.get("/nao-encontrado")
    def nao_encontrado() -> None:
        raise NaoEncontrado("Residência não encontrada.")

    @app.get("/conflito")
    def conflito() -> None:
        raise Conflito("Recomendação já respondida.")

    @app.get("/protegida")
    def protegida() -> None:
        raise HTTPException(401, "Token ausente.", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/detalhe-estruturado")
    def detalhe_estruturado() -> None:
        raise HTTPException(400, detail={"codigo": "X1"})

    with TestClient(app) as cliente:
        yield cliente


def test_validacao_vira_problema_rfc7807_com_campos(cliente: TestClient) -> None:
    resposta = cliente.post("/validar", json={"peso": 2})

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == "application/problem+json"
    corpo = resposta.json()
    assert corpo["status"] == 422
    assert corpo["detail"] == "Dados inválidos."
    assert corpo["instance"] == "/validar"
    assert corpo["erros"][0]["campo"] == "peso"


def test_erro_de_dominio_usa_status_da_classe(cliente: TestClient) -> None:
    resposta = cliente.get("/nao-encontrado")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Residência não encontrada."
    assert cliente.get("/conflito").status_code == 409


def test_rota_inexistente_tambem_responde_no_formato_padrao(cliente: TestClient) -> None:
    resposta = cliente.get("/nao-existe")

    assert resposta.status_code == 404
    assert resposta.json()["title"] == "Not Found"


def test_cabecalhos_da_excecao_sao_preservados(cliente: TestClient) -> None:
    nao_autorizado = cliente.get("/protegida")
    metodo_invalido = cliente.delete("/validar")

    assert nao_autorizado.status_code == 401
    assert nao_autorizado.headers["www-authenticate"] == "Bearer"
    assert metodo_invalido.status_code == 405
    assert metodo_invalido.headers["allow"] == "POST"


def test_detalhe_estruturado_vai_para_campo_de_extensao(cliente: TestClient) -> None:
    corpo = cliente.get("/detalhe-estruturado").json()

    assert corpo["detail"] == "Bad Request"
    assert corpo["dados"] == {"codigo": "X1"}
