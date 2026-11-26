from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.erros import Conflito, NaoEncontrado, registrar_tratadores


class Entrada(BaseModel):
    peso: float = Field(ge=0, le=1)


def _app_de_teste() -> FastAPI:
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

    return app


cliente = TestClient(_app_de_teste())


def test_validacao_vira_problema_rfc7807_com_campos() -> None:
    resposta = cliente.post("/validar", json={"peso": 2})

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == "application/problem+json"
    corpo = resposta.json()
    assert corpo["status"] == 422
    assert corpo["detail"] == "Dados inválidos."
    assert corpo["instance"] == "/validar"
    assert corpo["erros"][0]["campo"] == "peso"


def test_erro_de_dominio_usa_status_da_classe() -> None:
    resposta = cliente.get("/nao-encontrado")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Residência não encontrada."
    assert cliente.get("/conflito").status_code == 409


def test_rota_inexistente_tambem_responde_no_formato_padrao() -> None:
    resposta = cliente.get("/nao-existe")

    assert resposta.status_code == 404
    assert resposta.json()["title"] == "Not Found"
