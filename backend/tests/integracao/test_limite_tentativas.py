"""Limite de tentativas no login e no cadastro (#137), contra o PostgreSQL real."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao
from app.core.config import Ambiente, Configuracoes, obter_configuracoes
from app.core.seguranca import gerar_hash
from app.fabrica import criar_app
from app.modelos import TentativaAcesso, Usuario
from app.servicos.limite import LimitadorTentativas

CONFIG = Configuracoes(_env_file=None, ambiente=Ambiente.TESTE, jwt_segredo="t" * 48)
SENHA = "uma senha bem longa"


@pytest.fixture
def cliente(sessao: Session) -> Iterator[TestClient]:
    app: FastAPI = criar_app(CONFIG)
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[obter_configuracoes] = lambda: CONFIG
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def ana(sessao: Session) -> Usuario:
    usuario = Usuario(nome="Ana", email="ana@exemplo.com", senha_hash=gerar_hash(SENHA))
    sessao.add(usuario)
    sessao.flush()
    return usuario


def _login(cliente: TestClient, email: str, senha: str) -> int:
    resposta = cliente.post("/api/v1/auth/login", data={"username": email, "password": senha})
    return int(resposta.status_code)


def test_sexta_falha_seguida_bloqueia_ate_a_senha_certa(cliente: TestClient, ana: Usuario) -> None:
    falhas = [_login(cliente, ana.email, "senha errada demais") for _ in range(5)]
    bloqueada = cliente.post("/api/v1/auth/login", data={"username": ana.email, "password": SENHA})

    assert falhas == [401] * 5
    assert bloqueada.status_code == 429
    assert 0 < int(bloqueada.headers["retry-after"]) <= 15 * 60
    assert "Muitas tentativas" in bloqueada.json()["detail"]


def test_bloqueio_por_email_nao_afeta_outro_email(
    cliente: TestClient, ana: Usuario, sessao: Session
) -> None:
    sessao.add(Usuario(nome="Bia", email="bia@exemplo.com", senha_hash=gerar_hash(SENHA)))
    sessao.flush()
    for _ in range(5):
        _login(cliente, ana.email, "senha errada demais")

    assert _login(cliente, "bia@exemplo.com", SENHA) == 200


def test_acerto_zera_as_falhas_do_email(cliente: TestClient, ana: Usuario) -> None:
    for _ in range(4):
        _login(cliente, ana.email, "senha errada demais")
    assert _login(cliente, ana.email, SENHA) == 200

    assert [_login(cliente, ana.email, "senha errada demais") for _ in range(4)] == [401] * 4


def test_limite_por_ip_vale_para_varios_emails(cliente: TestClient) -> None:
    respostas = [_login(cliente, f"pessoa{i}@exemplo.com", "x" * 12) for i in range(21)]

    assert respostas[:20] == [401] * 20
    assert respostas[20] == 429


def test_cadastro_limitado_por_ip(cliente: TestClient) -> None:
    respostas = [
        cliente.post(
            "/api/v1/auth/registrar",
            json={"nome": "Pessoa", "email": f"p{i}@exemplo.com", "senha": SENHA},
        ).status_code
        for i in range(11)
    ]

    assert respostas[:10] == [201] * 10
    assert respostas[10] == 429


def test_banco_guarda_hmac_e_nao_o_email(cliente: TestClient, sessao: Session) -> None:
    _login(cliente, "ana@exemplo.com", "senha errada demais")

    chaves = sessao.scalars(select(TentativaAcesso.chave)).all()
    assert chaves
    assert all("ana" not in chave and len(chave) == 64 for chave in chaves)


def test_janela_expirada_libera_e_linhas_antigas_sao_apagadas(sessao: Session) -> None:
    limitador = LimitadorTentativas(sessao, CONFIG)
    origem = {"email": "ana@exemplo.com"}
    for _ in range(5):
        limitador.registrar("login", origem)
    sessao.execute(
        update(TentativaAcesso).values(momento=datetime.now(UTC) - timedelta(minutes=16))
    )

    limitador.verificar("login", origem)  # não levanta: a janela passou
    limitador.registrar("login", origem)  # e a limpeza remove as antigas

    assert len(sessao.scalars(select(TentativaAcesso)).all()) == 1
