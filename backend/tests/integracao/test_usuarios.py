"""Gestão de usuários pelo admin e o próprio perfil, contra o PostgreSQL real."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao
from app.core.config import Ambiente, Configuracoes, obter_configuracoes
from app.core.seguranca import gerar_hash
from app.fabrica import criar_app
from app.modelos import Papel, Usuario

CONFIG = Configuracoes(_env_file=None, ambiente=Ambiente.TESTE, jwt_segredo="t" * 48)
SENHA = "uma senha bem longa"


@pytest.fixture
def cliente(sessao: Session) -> Iterator[TestClient]:
    app: FastAPI = criar_app(CONFIG)
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[obter_configuracoes] = lambda: CONFIG
    with TestClient(app) as cliente:
        yield cliente


def _criar(sessao: Session, email: str, papel: Papel = Papel.CLIENTE, **extra: Any) -> Usuario:
    usuario = Usuario(
        nome=extra.pop("nome", "Pessoa"),
        email=email,
        senha_hash=gerar_hash(SENHA),
        papel=papel,
        **extra,
    )
    sessao.add(usuario)
    sessao.flush()
    return usuario


def _auth(cliente: TestClient, email: str) -> dict[str, str]:
    resposta = cliente.post("/api/v1/auth/login", data={"username": email, "password": SENHA})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
def admin(sessao: Session) -> Usuario:
    return _criar(sessao, "chefe@exemplo.com", Papel.ADMIN, nome="Chefe")


@pytest.fixture
def h_admin(cliente: TestClient, admin: Usuario) -> dict[str, str]:
    return _auth(cliente, admin.email)


# ---------- acesso ----------
@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        ("get", "/api/v1/admin/usuarios"),
        ("post", "/api/v1/admin/usuarios"),
        ("get", "/api/v1/admin/usuarios/00000000-0000-0000-0000-000000000000"),
        ("patch", "/api/v1/admin/usuarios/00000000-0000-0000-0000-000000000000"),
        ("delete", "/api/v1/admin/usuarios/00000000-0000-0000-0000-000000000000"),
    ],
)
def test_rotas_de_admin_recusam_cliente(
    cliente: TestClient, sessao: Session, metodo: str, caminho: str
) -> None:
    _criar(sessao, "ana@exemplo.com")
    h = _auth(cliente, "ana@exemplo.com")

    assert getattr(cliente, metodo)(caminho, headers=h).status_code == 403
    assert getattr(cliente, metodo)(caminho).status_code == 401


# ---------- listagem ----------
def test_lista_paginada_com_filtros(
    cliente: TestClient, sessao: Session, h_admin: dict[str, str]
) -> None:
    for i in range(5):
        _criar(sessao, f"cliente{i}@exemplo.com", nome=f"Cliente {i}")
    _criar(sessao, "inativo@exemplo.com", nome="Bia Inativa", ativo=False)

    pagina = cliente.get("/api/v1/admin/usuarios?tamanho=2&pagina=2", headers=h_admin).json()
    busca = cliente.get("/api/v1/admin/usuarios?busca=BIA", headers=h_admin).json()
    admins = cliente.get("/api/v1/admin/usuarios?papel=admin", headers=h_admin).json()
    inativos = cliente.get("/api/v1/admin/usuarios?ativo=false", headers=h_admin).json()

    assert (pagina["total"], pagina["pagina"], pagina["tamanho"], len(pagina["itens"])) == (
        7,
        2,
        2,
        2,
    )
    assert [u["email"] for u in busca["itens"]] == ["inativo@exemplo.com"]
    assert [u["email"] for u in admins["itens"]] == ["chefe@exemplo.com"]
    assert inativos["total"] == 1


def test_paginacao_recusa_valores_invalidos(cliente: TestClient, h_admin: dict[str, str]) -> None:
    assert cliente.get("/api/v1/admin/usuarios?tamanho=101", headers=h_admin).status_code == 422
    assert cliente.get("/api/v1/admin/usuarios?pagina=0", headers=h_admin).status_code == 422


# ---------- criação, edição e exclusão ----------
def test_admin_cria_outro_admin(cliente: TestClient, h_admin: dict[str, str]) -> None:
    resposta = cliente.post(
        "/api/v1/admin/usuarios",
        json={"nome": "Nova", "email": "Nova@Exemplo.com", "senha": SENHA, "papel": "admin"},
        headers=h_admin,
    )

    assert resposta.status_code == 201
    assert resposta.json()["papel"] == "admin"
    assert resposta.json()["email"] == "nova@exemplo.com"


def test_criacao_pelo_admin_tambem_segue_a_politica_de_senha(
    cliente: TestClient, h_admin: dict[str, str]
) -> None:
    resposta = cliente.post(
        "/api/v1/admin/usuarios",
        json={"nome": "Nova", "email": "nova@exemplo.com", "senha": "1234567890"},
        headers=h_admin,
    )

    assert resposta.status_code == 422


def test_promover_desativar_e_reativar(
    cliente: TestClient, sessao: Session, h_admin: dict[str, str]
) -> None:
    ana = _criar(sessao, "ana@exemplo.com")
    url = f"/api/v1/admin/usuarios/{ana.id}"

    promovida = cliente.patch(url, json={"papel": "admin"}, headers=h_admin)
    desativada = cliente.patch(url, json={"ativo": False}, headers=h_admin)

    assert promovida.json()["papel"] == "admin"
    assert desativada.json()["ativo"] is False
    assert (
        cliente.post(
            "/api/v1/auth/login", data={"username": "ana@exemplo.com", "password": SENHA}
        ).status_code
        == 401
    )
    assert cliente.patch(url, json={"ativo": True}, headers=h_admin).json()["ativo"] is True


def test_atualizacao_vazia_e_campos_desconhecidos_sao_recusados(
    cliente: TestClient, sessao: Session, h_admin: dict[str, str]
) -> None:
    ana = _criar(sessao, "ana@exemplo.com")
    url = f"/api/v1/admin/usuarios/{ana.id}"

    assert cliente.patch(url, json={}, headers=h_admin).status_code == 422
    assert cliente.patch(url, json={"senha_hash": "x"}, headers=h_admin).status_code == 422


def test_email_em_uso_e_409(cliente: TestClient, sessao: Session, h_admin: dict[str, str]) -> None:
    ana = _criar(sessao, "ana@exemplo.com")
    _criar(sessao, "bia@exemplo.com")

    resposta = cliente.patch(
        f"/api/v1/admin/usuarios/{ana.id}", json={"email": "bia@exemplo.com"}, headers=h_admin
    )

    assert resposta.status_code == 409


def test_excluir_usuario(cliente: TestClient, sessao: Session, h_admin: dict[str, str]) -> None:
    ana = _criar(sessao, "ana@exemplo.com")

    assert cliente.delete(f"/api/v1/admin/usuarios/{ana.id}", headers=h_admin).status_code == 204
    assert cliente.get(f"/api/v1/admin/usuarios/{ana.id}", headers=h_admin).status_code == 404


# ---------- último admin ----------
@pytest.mark.parametrize("mudanca", [{"papel": "cliente"}, {"ativo": False}])
def test_ultimo_admin_nao_pode_ser_rebaixado_nem_desativado(
    cliente: TestClient, admin: Usuario, h_admin: dict[str, str], mudanca: dict[str, Any]
) -> None:
    resposta = cliente.patch(f"/api/v1/admin/usuarios/{admin.id}", json=mudanca, headers=h_admin)

    assert resposta.status_code == 409
    assert "pelo menos um administrador" in resposta.json()["detail"]


def test_com_outro_admin_o_rebaixamento_e_permitido(
    cliente: TestClient, sessao: Session, admin: Usuario, h_admin: dict[str, str]
) -> None:
    outro = _criar(sessao, "outro@exemplo.com", Papel.ADMIN)

    resposta = cliente.patch(
        f"/api/v1/admin/usuarios/{outro.id}", json={"papel": "cliente"}, headers=h_admin
    )

    assert resposta.status_code == 200


def test_admin_desativado_nao_conta_como_outro_admin(
    cliente: TestClient, sessao: Session, admin: Usuario, h_admin: dict[str, str]
) -> None:
    _criar(sessao, "inativo@exemplo.com", Papel.ADMIN, ativo=False)

    resposta = cliente.patch(
        f"/api/v1/admin/usuarios/{admin.id}", json={"papel": "cliente"}, headers=h_admin
    )

    assert resposta.status_code == 409


def test_admin_nao_exclui_a_propria_conta_pela_rota_de_admin(
    cliente: TestClient, admin: Usuario, h_admin: dict[str, str]
) -> None:
    assert cliente.delete(f"/api/v1/admin/usuarios/{admin.id}", headers=h_admin).status_code == 409


# ---------- próprio perfil ----------
def test_cliente_edita_o_proprio_perfil(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com", nome="Ana")
    h = _auth(cliente, "ana@exemplo.com")

    resposta = cliente.patch("/api/v1/usuarios/eu", json={"nome": "Ana Maria"}, headers=h)

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Ana Maria"
    assert cliente.get("/api/v1/usuarios/eu", headers=h).json()["nome"] == "Ana Maria"


def test_cliente_nao_se_promove_pelo_perfil(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com")
    h = _auth(cliente, "ana@exemplo.com")

    resposta = cliente.patch("/api/v1/usuarios/eu", json={"papel": "admin"}, headers=h)

    assert resposta.status_code == 422


def test_troca_de_senha(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com")
    h = _auth(cliente, "ana@exemplo.com")
    nova = "outra frase bem comprida"

    errada = cliente.post(
        "/api/v1/usuarios/eu/senha",
        json={"senha_atual": "não é esta senha", "nova_senha": nova},
        headers=h,
    )
    igual = cliente.post(
        "/api/v1/usuarios/eu/senha", json={"senha_atual": SENHA, "nova_senha": SENHA}, headers=h
    )
    certa = cliente.post(
        "/api/v1/usuarios/eu/senha", json={"senha_atual": SENHA, "nova_senha": nova}, headers=h
    )

    assert errada.status_code == 401
    assert igual.status_code == 422
    assert certa.status_code == 204
    login = cliente.post(
        "/api/v1/auth/login", data={"username": "ana@exemplo.com", "password": nova}
    )
    assert login.status_code == 200
