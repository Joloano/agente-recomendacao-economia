"""Gestão de usuários pelo admin e o próprio perfil, contra o PostgreSQL real."""

import threading
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao
from app.core.config import Ambiente, Configuracoes, obter_configuracoes
from app.core.erros import Conflito
from app.core.seguranca import gerar_hash
from app.esquemas.usuarios import UsuarioAtualizacaoAdmin
from app.fabrica import criar_app
from app.modelos import Papel, Usuario
from app.servicos.usuarios import ServicoUsuarios

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


# ---------- último admin e a própria conta ----------
@pytest.mark.parametrize("mudanca", [{"papel": "cliente"}, {"ativo": False}])
def test_admin_nao_rebaixa_nem_desativa_a_si_mesmo(
    cliente: TestClient, admin: Usuario, h_admin: dict[str, str], mudanca: dict[str, Any]
) -> None:
    resposta = cliente.patch(f"/api/v1/admin/usuarios/{admin.id}", json=mudanca, headers=h_admin)

    assert resposta.status_code == 409
    assert "própria conta" in resposta.json()["detail"]


def test_admin_nao_exclui_a_propria_conta_pela_rota_de_admin(
    cliente: TestClient, admin: Usuario, h_admin: dict[str, str]
) -> None:
    assert cliente.delete(f"/api/v1/admin/usuarios/{admin.id}", headers=h_admin).status_code == 409


def test_com_outro_admin_o_rebaixamento_e_permitido(
    cliente: TestClient, sessao: Session, admin: Usuario, h_admin: dict[str, str]
) -> None:
    outro = _criar(sessao, "outro@exemplo.com", Papel.ADMIN)

    resposta = cliente.patch(
        f"/api/v1/admin/usuarios/{outro.id}", json={"papel": "cliente"}, headers=h_admin
    )

    assert resposta.status_code == 200


@pytest.mark.parametrize("operacao", ["rebaixar", "desativar", "excluir"])
def test_ultimo_admin_ativo_e_protegido_no_servico(sessao: Session, operacao: str) -> None:
    unico = _criar(sessao, "unico@exemplo.com", Papel.ADMIN)
    _criar(sessao, "inativo@exemplo.com", Papel.ADMIN, ativo=False)  # inativo não conta
    solicitante = _criar(sessao, "outro@exemplo.com")
    servico = ServicoUsuarios(sessao)

    with pytest.raises(Conflito, match="pelo menos um administrador"):
        if operacao == "excluir":
            servico.excluir(unico.id, solicitante)
        else:
            mudanca = {"papel": "cliente"} if operacao == "rebaixar" else {"ativo": False}
            servico.atualizar(unico.id, UsuarioAtualizacaoAdmin(**mudanca), solicitante)


def test_dois_admins_se_rebaixando_ao_mesmo_tempo_deixa_um_admin(engine: Engine) -> None:
    """Concorrência real: duas conexões, cada admin tentando rebaixar o outro."""
    with Session(engine) as preparo:
        a = Usuario(nome="A", email="a-conc@exemplo.com", senha_hash="h", papel=Papel.ADMIN)
        b = Usuario(nome="B", email="b-conc@exemplo.com", senha_hash="h", papel=Papel.ADMIN)
        preparo.add_all([a, b])
        preparo.commit()
        ids = (a.id, b.id)
    barreira = threading.Barrier(2)
    resultados: list[str] = []

    def rebaixar(alvo: uuid.UUID, solicitante_id: uuid.UUID) -> None:
        with Session(engine) as sessao:
            solicitante = sessao.get_one(Usuario, solicitante_id)
            barreira.wait()
            try:
                ServicoUsuarios(sessao).atualizar(
                    alvo, UsuarioAtualizacaoAdmin(papel=Papel.CLIENTE), solicitante
                )
                resultados.append("ok")
            except Conflito:
                resultados.append("409")

    try:
        threads = [
            threading.Thread(target=rebaixar, args=(ids[1], ids[0])),
            threading.Thread(target=rebaixar, args=(ids[0], ids[1])),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert sorted(resultados) == ["409", "ok"]
        with Session(engine) as conferencia:
            admins = conferencia.scalars(
                select(Usuario).where(Usuario.id.in_(ids), Usuario.papel == Papel.ADMIN)
            ).all()
            assert len(admins) == 1
    finally:
        with Session(engine) as limpeza:
            limpeza.execute(delete(Usuario).where(Usuario.id.in_(ids)))
            limpeza.commit()


# ---------- validações de atualização e busca ----------
@pytest.mark.parametrize("corpo", [{"email": None}, {"nome": None}, {"papel": None}])
def test_null_explicito_e_recusado(
    cliente: TestClient, sessao: Session, h_admin: dict[str, str], corpo: dict[str, Any]
) -> None:
    ana = _criar(sessao, "ana@exemplo.com")

    resposta = cliente.patch(f"/api/v1/admin/usuarios/{ana.id}", json=corpo, headers=h_admin)

    assert resposta.status_code == 422


def test_busca_trata_curingas_como_texto(
    cliente: TestClient, sessao: Session, h_admin: dict[str, str]
) -> None:
    _criar(sessao, "ana@exemplo.com", nome="Ana")
    _criar(sessao, "com_sublinhado@exemplo.com", nome="Bia")

    sublinhado = cliente.get("/api/v1/admin/usuarios?busca=_", headers=h_admin).json()
    porcento = cliente.get("/api/v1/admin/usuarios?busca=%25", headers=h_admin).json()

    assert [u["email"] for u in sublinhado["itens"]] == ["com_sublinhado@exemplo.com"]
    assert porcento["total"] == 0


def test_pagina_informa_total_de_paginas(cliente: TestClient, h_admin: dict[str, str]) -> None:
    corpo = cliente.get("/api/v1/admin/usuarios?tamanho=1", headers=h_admin).json()

    assert corpo["paginas"] == corpo["total"]


# ---------- próprio perfil ----------
def test_cliente_edita_o_proprio_perfil(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com", nome="Ana")
    h = _auth(cliente, "ana@exemplo.com")

    resposta = cliente.patch("/api/v1/usuarios/eu", json={"nome": "Ana Maria"}, headers=h)

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Ana Maria"
    assert cliente.get("/api/v1/usuarios/eu", headers=h).json()["nome"] == "Ana Maria"


def test_perfil_vazio_e_recusado(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com")
    h = _auth(cliente, "ana@exemplo.com")

    assert cliente.patch("/api/v1/usuarios/eu", json={}, headers=h).status_code == 422


def test_trocar_email_exige_a_senha_atual(cliente: TestClient, sessao: Session) -> None:
    _criar(sessao, "ana@exemplo.com")
    _criar(sessao, "bia@exemplo.com")
    h = _auth(cliente, "ana@exemplo.com")
    url = "/api/v1/usuarios/eu"

    sem_senha = cliente.patch(url, json={"email": "nova@exemplo.com"}, headers=h)
    senha_errada = cliente.patch(
        url, json={"email": "nova@exemplo.com", "senha_atual": "errada errada"}, headers=h
    )
    em_uso = cliente.patch(url, json={"email": "bia@exemplo.com", "senha_atual": SENHA}, headers=h)
    certo = cliente.patch(url, json={"email": "nova@exemplo.com", "senha_atual": SENHA}, headers=h)

    assert (sem_senha.status_code, senha_errada.status_code, em_uso.status_code) == (401, 401, 409)
    assert certo.status_code == 200
    assert certo.json()["email"] == "nova@exemplo.com"


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
