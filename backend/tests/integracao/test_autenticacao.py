"""Rotas de autenticação e regras de acesso contra o PostgreSQL real."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencias import AdminDep, UsuarioDep, garantir_acesso
from app.core.banco import obter_sessao
from app.core.config import Ambiente, Configuracoes, obter_configuracoes
from app.core.seguranca import criar_token_acesso, gerar_hash
from app.fabrica import criar_app
from app.modelos import Papel, Usuario

CONFIG = Configuracoes(_env_file=None, ambiente=Ambiente.TESTE, jwt_segredo="t" * 48)
SENHA = "uma senha bem longa"

# Rotas só para os testes: exercitam as dependências como as rotas reais farão.
rotas_teste = APIRouter(prefix="/api/v1/teste")


@rotas_teste.get("/admin")
def area_admin(admin: AdminDep) -> dict[str, str]:
    return {"ok": admin.email}


@rotas_teste.get("/recursos/{dono_id}")
def recurso_de(dono_id: uuid.UUID, usuario: UsuarioDep) -> dict[str, str]:
    garantir_acesso(usuario, dono_id, "Residência")
    return {"ok": str(dono_id)}


@pytest.fixture
def app(sessao: Session) -> FastAPI:
    app = criar_app(CONFIG)
    app.include_router(rotas_teste)
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[obter_configuracoes] = lambda: CONFIG
    return app


@pytest.fixture
def cliente(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as cliente:
        yield cliente


def _criar(
    sessao: Session, email: str, papel: Papel = Papel.CLIENTE, ativo: bool = True
) -> Usuario:
    usuario = Usuario(
        nome="Pessoa", email=email, senha_hash=gerar_hash(SENHA), papel=papel, ativo=ativo
    )
    sessao.add(usuario)
    sessao.flush()
    return usuario


def _token(cliente: TestClient, email: str, senha: str = SENHA) -> str:
    resposta = cliente.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resposta.status_code == 200, resposta.text
    return str(resposta.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------- cadastro ----------
def test_cadastro_cria_cliente_com_email_minusculo(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/api/v1/auth/registrar",
        json={"nome": "  Ana  ", "email": "Ana@Exemplo.COM", "senha": SENHA},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["email"] == "ana@exemplo.com"
    assert corpo["nome"] == "Ana"
    assert corpo["papel"] == "cliente"
    assert "senha" not in corpo and "senha_hash" not in corpo


def test_cadastro_nao_permite_escolher_o_papel(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/api/v1/auth/registrar",
        json={"nome": "Ana", "email": "ana@exemplo.com", "senha": SENHA, "papel": "admin"},
    )

    assert resposta.status_code == 422


def test_cadastro_com_email_repetido_e_409(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com")

    resposta = cliente.post(
        "/api/v1/auth/registrar", json={"nome": "Ana", "email": "ANA@exemplo.com", "senha": SENHA}
    )

    assert resposta.status_code == 409
    assert "já está cadastrado" in resposta.json()["detail"]


def test_cadastro_com_senha_fraca_e_422(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/api/v1/auth/registrar", json={"nome": "Ana", "email": "ana@exemplo.com", "senha": "123"}
    )

    assert resposta.status_code == 422
    assert "pelo menos 10" in resposta.json()["detail"]


# ---------- login ----------
def test_login_devolve_token_que_da_acesso_ao_eu(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com")

    token = _token(cliente, "  ANA@exemplo.com ")
    resposta = cliente.get("/api/v1/auth/eu", headers=_auth(token))

    assert resposta.status_code == 200
    assert resposta.json()["email"] == "ana@exemplo.com"


@pytest.mark.parametrize("caso", ["senha-errada", "email-inexistente", "conta-inativa"])
def test_login_invalido_e_401_com_a_mesma_mensagem(
    cliente: TestClient, sessao: Session, caso: str
) -> None:
    _criar(sessao, "ana@exemplo.com", ativo=caso != "conta-inativa")
    email = "bia@exemplo.com" if caso == "email-inexistente" else "ana@exemplo.com"
    senha = "senha errada demais" if caso == "senha-errada" else SENHA

    resposta = cliente.post("/api/v1/auth/login", data={"username": email, "password": senha})

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "E-mail ou senha incorretos."
    assert resposta.headers["www-authenticate"] == "Bearer"


# ---------- token nas rotas protegidas ----------
def test_sem_token_e_401_em_portugues(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/auth/eu")

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Entre na sua conta para continuar."
    assert resposta.headers["www-authenticate"] == "Bearer"


def test_token_expirado_e_401(cliente: TestClient, sessao: Session) -> None:
    usuario = _criar(sessao, "ana@exemplo.com")
    antigo = datetime.now(UTC) - timedelta(days=1)
    token, _ = criar_token_acesso(usuario.id, usuario.papel, CONFIG, agora=antigo)

    assert cliente.get("/api/v1/auth/eu", headers=_auth(token)).status_code == 401


def test_conta_desativada_depois_do_login_perde_acesso(
    cliente: TestClient, sessao: Session
) -> None:
    usuario = _criar(sessao, "ana@exemplo.com")
    token = _token(cliente, "ana@exemplo.com")

    usuario.ativo = False
    sessao.flush()

    assert cliente.get("/api/v1/auth/eu", headers=_auth(token)).status_code == 401


# ---------- papéis e posse ----------
def test_rota_de_admin_com_cliente_e_403(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com")
    token = _token(cliente, "ana@exemplo.com")

    resposta = cliente.get("/api/v1/teste/admin", headers=_auth(token))

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Você não tem permissão para acessar esta área."


def test_papel_vem_do_banco_e_nao_do_token(cliente: TestClient, sessao: Session) -> None:
    admin = _criar(sessao, "chefe@exemplo.com", papel=Papel.ADMIN)
    token = _token(cliente, "chefe@exemplo.com")
    assert cliente.get("/api/v1/teste/admin", headers=_auth(token)).status_code == 200

    admin.papel = Papel.CLIENTE  # rebaixado: vale na próxima requisição
    sessao.flush()

    assert cliente.get("/api/v1/teste/admin", headers=_auth(token)).status_code == 403


def test_cliente_acessando_dado_alheio_e_404(cliente: TestClient, sessao: Session) -> None:
    ana = _criar(sessao, "ana@exemplo.com")
    bia = _criar(sessao, "bia@exemplo.com")
    token = _token(cliente, "ana@exemplo.com")

    proprio = cliente.get(f"/api/v1/teste/recursos/{ana.id}", headers=_auth(token))
    alheio = cliente.get(f"/api/v1/teste/recursos/{bia.id}", headers=_auth(token))

    assert proprio.status_code == 200
    assert alheio.status_code == 404
    assert alheio.json()["detail"] == "Residência não encontrado(a)."


def test_admin_acessa_dado_de_qualquer_cliente(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "chefe@exemplo.com", papel=Papel.ADMIN)
    bia = _criar(sessao, "bia@exemplo.com")
    token = _token(cliente, "chefe@exemplo.com")

    resposta = cliente.get(f"/api/v1/teste/recursos/{bia.id}", headers=_auth(token))

    assert resposta.status_code == 200
