"""Verificação de e-mail, recuperação de senha e revogação de sessões (#90)."""

import re
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao
from app.core.config import Ambiente, Configuracoes, obter_configuracoes
from app.core.seguranca import gerar_hash
from app.fabrica import criar_app
from app.integracoes.email import EnviadorMemoria, ServicoEmail, obter_servico_email
from app.modelos import TokenConta, Usuario

CONFIG = Configuracoes(
    _env_file=None,
    ambiente=Ambiente.TESTE,
    jwt_segredo="t" * 48,
    url_frontend="https://app.exemplo.com",
    smtp_seguranca="nenhuma",
)
SENHA = "uma senha bem longa"
NOVA = "outra frase bem comprida"


@pytest.fixture
def caixa() -> EnviadorMemoria:
    return EnviadorMemoria()


@pytest.fixture
def cliente(sessao: Session, caixa: EnviadorMemoria) -> Iterator[TestClient]:
    app: FastAPI = criar_app(CONFIG)
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[obter_configuracoes] = lambda: CONFIG
    app.dependency_overrides[obter_servico_email] = lambda: ServicoEmail(caixa, CONFIG)
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def ana(sessao: Session) -> Usuario:
    usuario = Usuario(nome="Ana", email="ana@exemplo.com", senha_hash=gerar_hash(SENHA))
    sessao.add(usuario)
    sessao.flush()
    return usuario


def _token_do_email(caixa: EnviadorMemoria, assunto: str) -> str:
    mensagem = next(m for m in reversed(caixa.enviadas) if m.assunto == assunto)
    achado = re.search(r"token=([A-Za-z0-9_-]+)", mensagem.texto)
    assert achado, "o e-mail não trouxe o link com o token"
    return achado.group(1)


def _auth(cliente: TestClient, email: str, senha: str = SENHA) -> dict[str, str]:
    resposta = cliente.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


# ---------- cadastro e verificação ----------
def test_cadastro_envia_boas_vindas_e_link_de_verificacao(
    cliente: TestClient, caixa: EnviadorMemoria
) -> None:
    resposta = cliente.post(
        "/api/v1/auth/registrar",
        json={"nome": "Bia", "email": "bia@exemplo.com", "senha": SENHA},
    )

    assert resposta.status_code == 201
    assert resposta.json()["email_verificado_em"] is None
    assert {m.modelo for m in caixa.enviadas} == {"boas_vindas", "verificacao_email"}
    token = _token_do_email(caixa, "Confirme seu e-mail")

    confirmado = cliente.post("/api/v1/auth/verificacao/confirmar", json={"token": token})
    reuso = cliente.post("/api/v1/auth/verificacao/confirmar", json={"token": token})

    assert confirmado.status_code == 200
    assert confirmado.json()["email_verificado_em"] is not None
    assert reuso.status_code == 422
    assert "inválido ou expirou" in reuso.json()["detail"]


def test_novo_pedido_invalida_o_link_anterior(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    h = _auth(cliente, ana.email)
    cliente.post("/api/v1/auth/verificacao/solicitar", headers=h)
    primeiro = _token_do_email(caixa, "Confirme seu e-mail")
    cliente.post("/api/v1/auth/verificacao/solicitar", headers=h)
    segundo = _token_do_email(caixa, "Confirme seu e-mail")

    antigo = cliente.post("/api/v1/auth/verificacao/confirmar", json={"token": primeiro})
    novo = cliente.post("/api/v1/auth/verificacao/confirmar", json={"token": segundo})

    assert (antigo.status_code, novo.status_code) == (422, 200)


def test_link_de_verificacao_nao_vale_depois_de_trocar_o_email(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    h = _auth(cliente, ana.email)
    cliente.post("/api/v1/auth/verificacao/solicitar", headers=h)
    token = _token_do_email(caixa, "Confirme seu e-mail")
    ana.email = "outro@exemplo.com"
    sessao.flush()

    resposta = cliente.post("/api/v1/auth/verificacao/confirmar", json={"token": token})

    assert resposta.status_code == 422


@pytest.mark.parametrize("token", ["curto", "x" * 43, "com espaço e símbolos!!!!!!!!!!!"])
def test_token_invalido_e_recusado(cliente: TestClient, token: str) -> None:
    resposta = cliente.post("/api/v1/auth/verificacao/confirmar", json={"token": token})

    assert resposta.status_code == 422


def test_token_expirado_e_recusado(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    token = _token_do_email(caixa, "Redefinição de senha")
    sessao.execute(update(TokenConta).values(expira_em=func.now() - timedelta(seconds=1)))

    resposta = cliente.post(
        "/api/v1/auth/senha/redefinir", json={"token": token, "nova_senha": NOVA}
    )

    assert resposta.status_code == 422


def test_banco_guarda_so_o_hash_do_token(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    token = _token_do_email(caixa, "Redefinição de senha")

    hashes = sessao.scalars(select(TokenConta.token_hash)).all()
    assert token not in hashes and all(len(h) == 64 for h in hashes)


# ---------- recuperação de senha ----------
def test_esqueci_senha_nao_revela_se_o_email_existe(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    existe = cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    nao_existe = cliente.post("/api/v1/auth/senha/esqueci", json={"email": "ninguem@exemplo.com"})

    assert existe.status_code == nao_existe.status_code == 202
    assert existe.content == nao_existe.content
    assert [m.para for m in caixa.enviadas] == [ana.email]


def test_redefinir_troca_a_senha_e_derruba_sessoes_antigas(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    sessao_antiga = _auth(cliente, ana.email)
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    token = _token_do_email(caixa, "Redefinição de senha")

    fraca = cliente.post(
        "/api/v1/auth/senha/redefinir", json={"token": token, "nova_senha": "1234567890"}
    )
    certa = cliente.post("/api/v1/auth/senha/redefinir", json={"token": token, "nova_senha": NOVA})
    reuso = cliente.post("/api/v1/auth/senha/redefinir", json={"token": token, "nova_senha": NOVA})

    assert fraca.status_code == 422  # senha fraca não consome o link
    assert certa.status_code == 204
    assert reuso.status_code == 422
    eu = cliente.get("/api/v1/auth/eu", headers=sessao_antiga)
    assert eu.status_code == 401
    assert eu.json()["detail"] == "Sua senha foi alterada. Entre novamente."
    nova_sessao = _auth(cliente, ana.email, NOVA)
    assert cliente.get("/api/v1/auth/eu", headers=nova_sessao).json()["email_verificado_em"]


def test_troca_de_senha_pelo_perfil_tambem_derruba_sessoes(
    cliente: TestClient, ana: Usuario
) -> None:
    outra_sessao = _auth(cliente, ana.email)
    h = _auth(cliente, ana.email)

    resposta = cliente.post(
        "/api/v1/usuarios/eu/senha", json={"senha_atual": SENHA, "nova_senha": NOVA}, headers=h
    )

    assert resposta.status_code == 204
    assert cliente.get("/api/v1/auth/eu", headers=outra_sessao).status_code == 401
    assert (
        cliente.get("/api/v1/auth/eu", headers=_auth(cliente, ana.email, NOVA)).status_code == 200
    )


def test_trocar_email_avisa_o_antigo_e_pede_confirmacao_do_novo(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    h = _auth(cliente, ana.email)

    resposta = cliente.patch(
        "/api/v1/usuarios/eu", json={"email": "nova@exemplo.com", "senha_atual": SENHA}, headers=h
    )

    assert resposta.status_code == 200
    assert resposta.json()["email_verificado_em"] is None
    destinos = {(m.modelo, m.para) for m in caixa.enviadas}
    assert ("alerta", "ana@exemplo.com") in destinos
    assert ("verificacao_email", "nova@exemplo.com") in destinos


def test_pedidos_de_recuperacao_tem_limite(cliente: TestClient, ana: Usuario) -> None:
    respostas = [
        cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email}).status_code
        for _ in range(4)
    ]

    assert respostas == [202, 202, 202, 429]
