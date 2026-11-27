"""Verificação de e-mail, troca de e-mail, recuperação de senha e revogação de sessões (#90)."""

import re
from collections.abc import Iterator
from contextlib import nullcontext
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.banco import obter_fabrica_sessao, obter_sessao
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
VERIFICACAO = "Confirme seu e-mail"
RECUPERACAO = "Redefinição de senha"


@pytest.fixture
def caixa() -> EnviadorMemoria:
    return EnviadorMemoria()


@pytest.fixture
def cliente(sessao: Session, caixa: EnviadorMemoria) -> Iterator[TestClient]:
    app: FastAPI = criar_app(CONFIG)
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[obter_configuracoes] = lambda: CONFIG
    app.dependency_overrides[obter_servico_email] = lambda: ServicoEmail(caixa, CONFIG)
    # Tarefas em segundo plano usam a mesma sessão de teste (sem fechá-la).
    app.dependency_overrides[obter_fabrica_sessao] = lambda: lambda: nullcontext(sessao)
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def ana(sessao: Session) -> Usuario:
    usuario = Usuario(nome="Ana", email="ana@exemplo.com", senha_hash=gerar_hash(SENHA))
    sessao.add(usuario)
    sessao.flush()
    return usuario


def _token(caixa: EnviadorMemoria, assunto: str, para: str | None = None) -> str:
    mensagem = next(
        m for m in reversed(caixa.enviadas) if m.assunto == assunto and para in (None, m.para)
    )
    achado = re.search(r"#token=([A-Za-z0-9_-]+)", mensagem.texto)
    assert achado, "o link precisa levar o token no fragmento (#token=)"
    return achado.group(1)


def _auth(cliente: TestClient, email: str, senha: str = SENHA) -> dict[str, str]:
    resposta = cliente.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def _confirmar(cliente: TestClient, token: str) -> int:
    resposta = cliente.post("/api/v1/auth/verificacao/confirmar", json={"token": token})
    return int(resposta.status_code)


def _redefinir(cliente: TestClient, token: str, senha: str = NOVA) -> int:
    resposta = cliente.post(
        "/api/v1/auth/senha/redefinir", json={"token": token, "nova_senha": senha}
    )
    return int(resposta.status_code)


# ---------- cadastro e verificação ----------
def test_cadastro_envia_boas_vindas_e_link_de_verificacao(
    cliente: TestClient, caixa: EnviadorMemoria
) -> None:
    resposta = cliente.post(
        "/api/v1/auth/registrar", json={"nome": "Bia", "email": "bia@exemplo.com", "senha": SENHA}
    )

    assert resposta.status_code == 201
    assert resposta.json()["email_verificado_em"] is None
    assert {m.modelo for m in caixa.enviadas} == {"boas_vindas", "verificacao_email"}
    token = _token(caixa, VERIFICACAO)
    assert (_confirmar(cliente, token), _confirmar(cliente, token)) == (200, 422)  # uso único


def test_novo_pedido_invalida_o_link_anterior(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    h = _auth(cliente, ana.email)
    cliente.post("/api/v1/auth/verificacao/solicitar", headers=h)
    primeiro = _token(caixa, VERIFICACAO)
    cliente.post("/api/v1/auth/verificacao/solicitar", headers=h)
    segundo = _token(caixa, VERIFICACAO)

    assert (_confirmar(cliente, primeiro), _confirmar(cliente, segundo)) == (422, 200)


def test_reenvio_da_verificacao_tem_limite(cliente: TestClient, ana: Usuario) -> None:
    h = _auth(cliente, ana.email)

    respostas = [
        cliente.post("/api/v1/auth/verificacao/solicitar", headers=h).status_code for _ in range(4)
    ]

    assert respostas == [202, 202, 202, 429]


@pytest.mark.parametrize("token", ["curto", "x" * 43, "com espaço e símbolos!!!!!!!!!!!"])
def test_token_inexistente_ou_mal_formado_e_recusado(cliente: TestClient, token: str) -> None:
    assert _confirmar(cliente, token) == 422


def test_token_expirado_e_recusado(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    token = _token(caixa, RECUPERACAO)
    sessao.execute(update(TokenConta).values(expira_em=func.now() - timedelta(seconds=1)))

    assert _redefinir(cliente, token) == 422


def test_banco_guarda_so_o_hash_do_token(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    token = _token(caixa, RECUPERACAO)

    hashes = sessao.scalars(select(TokenConta.token_hash)).all()
    assert token not in hashes and all(len(h) == 64 for h in hashes)


# ---------- recuperação de senha ----------
def test_esqueci_senha_responde_igual_e_so_envia_para_conta_existente(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    existe = cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    nao_existe = cliente.post("/api/v1/auth/senha/esqueci", json={"email": "ninguem@exemplo.com"})

    assert existe.status_code == nao_existe.status_code == 202
    assert existe.content == nao_existe.content == b""
    assert [m.para for m in caixa.enviadas] == [ana.email]


def test_redefinir_troca_a_senha_avisa_e_derruba_sessoes_antigas(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    sessao_antiga = _auth(cliente, ana.email)
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    token = _token(caixa, RECUPERACAO)

    fraca = _redefinir(cliente, token, "1234567890")
    certa = _redefinir(cliente, token)
    reuso = _redefinir(cliente, token)

    assert (fraca, certa, reuso) == (422, 204, 422)  # senha fraca não gasta o link
    eu = cliente.get("/api/v1/auth/eu", headers=sessao_antiga)
    assert eu.status_code == 401
    assert "foi alterado" in eu.json()["detail"]
    assert any(m.assunto == "Sua senha foi alterada" for m in caixa.enviadas)
    nova_sessao = _auth(cliente, ana.email, NOVA)
    assert cliente.get("/api/v1/auth/eu", headers=nova_sessao).json()["email_verificado_em"]


def test_conta_desativada_nao_redefine_a_senha(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    token = _token(caixa, RECUPERACAO)
    ana.ativo = False
    sessao.flush()

    assert _redefinir(cliente, token) == 422


def test_troca_de_senha_pelo_perfil_devolve_token_novo_e_derruba_as_outras(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    outra_sessao = _auth(cliente, ana.email)
    h = _auth(cliente, ana.email)

    resposta = cliente.post(
        "/api/v1/usuarios/eu/senha", json={"senha_atual": SENHA, "nova_senha": NOVA}, headers=h
    )

    assert resposta.status_code == 200
    novo = {"Authorization": f"Bearer {resposta.json()['access_token']}"}
    assert cliente.get("/api/v1/auth/eu", headers=novo).status_code == 200
    assert cliente.get("/api/v1/auth/eu", headers=outra_sessao).status_code == 401
    assert any(m.assunto == "Sua senha foi alterada" for m in caixa.enviadas)


def test_pedidos_de_recuperacao_tem_limite(cliente: TestClient, ana: Usuario) -> None:
    respostas = [
        cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email}).status_code
        for _ in range(4)
    ]

    assert respostas == [202, 202, 202, 429]


# ---------- troca de e-mail (pendente até confirmar) ----------
def _pedir_troca(cliente: TestClient, h: dict[str, str], novo: str) -> int:
    resposta = cliente.patch(
        "/api/v1/usuarios/eu", json={"email": novo, "senha_atual": SENHA}, headers=h
    )
    return int(resposta.status_code)


def test_troca_de_email_so_vale_depois_de_confirmar(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    h = _auth(cliente, ana.email)

    assert _pedir_troca(cliente, h, "nova@exemplo.com") == 200
    perfil = cliente.get("/api/v1/auth/eu", headers=h).json()
    assert (perfil["email"], perfil["email_pendente"]) == ("ana@exemplo.com", "nova@exemplo.com")
    destinos = {(m.modelo, m.para) for m in caixa.enviadas}
    assert ("alerta", "ana@exemplo.com") in destinos
    assert ("verificacao_email", "nova@exemplo.com") in destinos

    assert _confirmar(cliente, _token(caixa, VERIFICACAO, "nova@exemplo.com")) == 200
    assert cliente.get("/api/v1/auth/eu", headers=h).status_code == 401  # sessões derrubadas
    perfil = cliente.get("/api/v1/auth/eu", headers=_auth(cliente, "nova@exemplo.com")).json()
    assert (perfil["email"], perfil["email_pendente"]) == ("nova@exemplo.com", None)
    assert perfil["email_verificado_em"]


def test_link_de_recuperacao_antigo_nao_vale_depois_da_troca_de_email(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    recuperacao = _token(caixa, RECUPERACAO)
    h = _auth(cliente, ana.email)
    _pedir_troca(cliente, h, "nova@exemplo.com")
    _confirmar(cliente, _token(caixa, VERIFICACAO, "nova@exemplo.com"))

    assert _redefinir(cliente, recuperacao) == 422


def test_link_de_verificacao_para_endereco_antigo_nao_vale(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    h = _auth(cliente, ana.email)
    cliente.post("/api/v1/auth/verificacao/solicitar", headers=h)
    token = _token(caixa, VERIFICACAO, ana.email)
    ana.email = "outro@exemplo.com"  # e-mail mudou por outro caminho (ex.: admin)
    sessao.flush()

    assert _confirmar(cliente, token) == 422


def test_pedidos_de_troca_de_email_tem_limite(cliente: TestClient, ana: Usuario) -> None:
    h = _auth(cliente, ana.email)

    respostas = [_pedir_troca(cliente, h, f"novo{i}@exemplo.com") for i in range(4)]

    assert respostas == [200, 200, 200, 429]


def test_email_pendente_tomado_por_outra_conta_da_409_na_confirmacao(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    h = _auth(cliente, ana.email)
    _pedir_troca(cliente, h, "nova@exemplo.com")
    token = _token(caixa, VERIFICACAO, "nova@exemplo.com")
    sessao.add(Usuario(nome="Bia", email="nova@exemplo.com", senha_hash=gerar_hash(SENHA)))
    sessao.flush()

    resposta = cliente.post("/api/v1/auth/verificacao/confirmar", json={"token": token})

    assert resposta.status_code == 409
    assert "outra conta" in resposta.json()["detail"]


def test_redefinir_senha_descarta_troca_de_email_pendente(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario
) -> None:
    h = _auth(cliente, ana.email)
    _pedir_troca(cliente, h, "atacante@exemplo.com")
    verificacao = _token(caixa, VERIFICACAO, "atacante@exemplo.com")
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})

    assert _redefinir(cliente, _token(caixa, RECUPERACAO)) == 204
    assert _confirmar(cliente, verificacao) == 422  # o link da troca caiu junto
    perfil = cliente.get("/api/v1/auth/eu", headers=_auth(cliente, ana.email, NOVA)).json()
    assert (perfil["email"], perfil["email_pendente"]) == ("ana@exemplo.com", None)


def test_troca_de_email_pelo_admin_derruba_sessoes_e_links(
    cliente: TestClient, caixa: EnviadorMemoria, ana: Usuario, sessao: Session
) -> None:
    sessao.add(
        Usuario(
            nome="Chefe", email="chefe@exemplo.com", senha_hash=gerar_hash(SENHA), papel="admin"
        )
    )
    sessao.flush()
    sessao_da_ana = _auth(cliente, ana.email)
    cliente.post("/api/v1/auth/senha/esqueci", json={"email": ana.email})
    recuperacao = _token(caixa, RECUPERACAO)

    resposta = cliente.patch(
        f"/api/v1/admin/usuarios/{ana.id}",
        json={"email": "ana.nova@exemplo.com"},
        headers=_auth(cliente, "chefe@exemplo.com"),
    )

    assert resposta.status_code == 200
    assert resposta.json()["email_verificado_em"] is None
    assert cliente.get("/api/v1/auth/eu", headers=sessao_da_ana).status_code == 401
    assert _redefinir(cliente, recuperacao) == 422
