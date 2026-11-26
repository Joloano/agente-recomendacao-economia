"""Regressões da revisão de segurança da autenticação (PR #130)."""

import unicodedata
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao
from app.core.config import Ambiente, Configuracoes, obter_configuracoes
from app.core.seguranca import gerar_hash
from app.esquemas.autenticacao import RegistroEntrada
from app.fabrica import criar_app
from app.modelos import Usuario
from app.servicos.autenticacao import ServicoAutenticacao

CONFIG = Configuracoes(_env_file=None, ambiente=Ambiente.TESTE, jwt_segredo="t" * 48)
SENHA = "uma senha bem longa"


@pytest.fixture
def cliente(sessao: Session) -> Iterator[TestClient]:
    app: FastAPI = criar_app(CONFIG)
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[obter_configuracoes] = lambda: CONFIG
    with TestClient(app) as cliente:
        yield cliente


def _registrar(cliente: TestClient, **dados: str) -> int:
    corpo = {"nome": "Ana", "email": "ana@exemplo.com", "senha": SENHA, **dados}
    return int(cliente.post("/api/v1/auth/registrar", json=corpo).status_code)


def _login(cliente: TestClient, email: str, senha: str = SENHA) -> int:
    resposta = cliente.post("/api/v1/auth/login", data={"username": email, "password": senha})
    return int(resposta.status_code)


@pytest.mark.parametrize(
    "dados",
    [
        {"nome": "Bi\x00a"},
        {"nome": "Bi\x07a"},
        {"nome": chr(0x202E) + "Admin"},  # inversão bidi
        {"nome": "An\u200ba"},  # largura zero
        {"senha": "uma senha\x00 bem longa"},
    ],
)
def test_caracteres_de_controle_e_invisiveis_dao_422(
    cliente: TestClient, dados: dict[str, str]
) -> None:
    assert _registrar(cliente, **dados) == 422


@pytest.mark.parametrize("senha", ["password123", "PASSWORD123", "ｐａｓｓｗｏｒｄ１２３"])
def test_senha_comum_e_recusada_em_qualquer_forma(cliente: TestClient, senha: str) -> None:
    assert _registrar(cliente, senha=senha) == 422


def test_login_aceita_email_em_punycode_e_nfd(cliente: TestClient) -> None:
    assert _registrar(cliente, email="ana@bücher.de") == 201

    assert _login(cliente, "ana@xn--bcher-kva.de") == 200
    assert _login(cliente, unicodedata.normalize("NFD", "ANA@BÜCHER.DE")) == 200


def test_login_com_email_invalido_da_401_generico(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/api/v1/auth/login", data={"username": "sem arroba", "password": SENHA}
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "E-mail ou senha incorretos."


def test_senha_gigante_no_login_da_401(cliente: TestClient) -> None:
    assert _registrar(cliente) == 201

    assert _login(cliente, "ana@exemplo.com", "a" * 600) == 401


def test_nfkc_formas_diferentes_da_mesma_senha_conferem(cliente: TestClient) -> None:
    senha_largura_total = "ｕｍａ ｓｅｎｈａ ｂｅｍ ｌｏｎｇａ"  # NFKC → "uma senha bem longa"
    assert _registrar(cliente, senha=senha_largura_total) == 201

    assert _login(cliente, "ana@exemplo.com", SENHA) == 200


def test_token_invalido_anuncia_invalid_token(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/auth/eu", headers={"Authorization": "Bearer lixo"})

    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == 'Bearer error="invalid_token"'


def test_outra_violacao_de_integridade_nao_vira_409() -> None:
    sessao = MagicMock()
    erro = IntegrityError("INSERT", {}, Exception("x"))
    erro.orig = MagicMock(diag=MagicMock(constraint_name="ck_usuario_email_minusculo"))
    sessao.commit.side_effect = erro

    with pytest.raises(IntegrityError):
        ServicoAutenticacao(sessao).registrar(
            RegistroEntrada(nome="Ana", email="ana@exemplo.com", senha=SENHA)
        )


def test_hash_antigo_e_recalculado_no_login(
    sessao: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    usuario = Usuario(nome="Ana", email="ana@exemplo.com", senha_hash=gerar_hash(SENHA))
    sessao.add(usuario)
    sessao.flush()
    hash_antigo = usuario.senha_hash
    monkeypatch.setattr("app.servicos.autenticacao.precisa_rehash", lambda _h: True)

    ServicoAutenticacao(sessao).autenticar("ana@exemplo.com", SENHA)

    assert usuario.senha_hash != hash_antigo
