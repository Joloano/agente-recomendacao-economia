"""Limite de tentativas no login e no cadastro (#137), contra o PostgreSQL real."""

import threading
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, select, update
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao
from app.core.config import Ambiente, Configuracoes, obter_configuracoes
from app.core.seguranca import gerar_hash
from app.fabrica import criar_app
from app.modelos import TentativaAcesso, Usuario
from app.servicos.limite import LimitadorTentativas, MuitasTentativas, normalizar_ip

CONFIG = Configuracoes(_env_file=None, ambiente=Ambiente.TESTE, jwt_segredo="t" * 48)
SENHA = "uma senha bem longa"
ERRADA = "senha errada demais"


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


def test_sexta_tentativa_bloqueia_ate_a_senha_certa(cliente: TestClient, ana: Usuario) -> None:
    falhas = [_login(cliente, ana.email, ERRADA) for _ in range(5)]
    bloqueada = cliente.post("/api/v1/auth/login", data={"username": ana.email, "password": SENHA})

    assert falhas == [401] * 5
    assert bloqueada.status_code == 429
    assert 0 < int(bloqueada.headers["retry-after"]) <= 15 * 60
    assert "Muitas tentativas" in bloqueada.json()["detail"]


@pytest.mark.parametrize(
    "variantes",
    [
        ["ana@ＥＸＥＭＰＬＯ.com", "ana@exemplo.ｃｏｍ", "ana@exemplo。com", "ANA@Exemplo.com"],
        ["ana@bücher.de", "ana@xn--bcher-kva.de", "ana@bücher.de", "ANA@BÜCHER.DE"],
    ],
)
def test_variantes_do_mesmo_email_somam_no_mesmo_contador(
    cliente: TestClient, variantes: list[str]
) -> None:
    respostas = [_login(cliente, variantes[i % len(variantes)], ERRADA) for i in range(6)]

    assert respostas == [401] * 5 + [429]


def test_bloqueio_de_um_email_nao_afeta_outro(
    cliente: TestClient, ana: Usuario, sessao: Session
) -> None:
    sessao.add(Usuario(nome="Bia", email="bia@exemplo.com", senha_hash=gerar_hash(SENHA)))
    sessao.flush()
    for _ in range(5):
        _login(cliente, ana.email, ERRADA)

    assert _login(cliente, "bia@exemplo.com", SENHA) == 200


def test_acerto_zera_as_falhas_do_email(cliente: TestClient, ana: Usuario) -> None:
    for _ in range(4):
        _login(cliente, ana.email, ERRADA)
    assert _login(cliente, ana.email, SENHA) == 200

    assert [_login(cliente, ana.email, ERRADA) for _ in range(5)] == [401] * 5


def test_limite_por_ip_vale_para_varios_emails(cliente: TestClient) -> None:
    respostas = [_login(cliente, f"pessoa{i}@exemplo.com", "x" * 12) for i in range(51)]

    assert respostas[:50] == [401] * 50
    assert respostas[50] == 429


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
    _login(cliente, "ana@exemplo.com", ERRADA)

    chaves = sessao.scalars(select(TentativaAcesso.chave)).all()
    assert len(chaves) == 3  # e-mail+IP, e-mail e IP
    assert all("ana" not in chave and len(chave) == 64 for chave in chaves)


def test_janela_expirada_libera_e_a_limpeza_remove_o_vencido(sessao: Session) -> None:
    limitador = LimitadorTentativas(sessao, CONFIG)
    for _ in range(5):
        limitador.reservar("login", email="ana@exemplo.com", ip="1.2.3.4")
    sessao.execute(update(TentativaAcesso).values(momento=func.now() - timedelta(hours=2)))

    limitador.reservar("login", email="ana@exemplo.com", ip="1.2.3.4")  # janela passou
    removidas = limitador.limpar()

    assert removidas == 15
    assert len(sessao.scalars(select(TentativaAcesso)).all()) == 3


@pytest.mark.parametrize(
    ("ip", "esperado"),
    [
        ("203.0.113.9", "203.0.113.9"),
        ("::ffff:203.0.113.9", "203.0.113.9"),
        ("2001:db8:abcd:12:1::5", "2001:db8:abcd:12::/64"),
        ("2001:db8:abcd:12:ffff::9", "2001:db8:abcd:12::/64"),
        ("testclient", "testclient"),
    ],
)
def test_ip_normalizado(ip: str, esperado: str) -> None:
    assert normalizar_ip(ip) == esperado


def test_rajada_simultanea_nao_passa_do_limite(engine: Engine) -> None:
    """20 tentativas ao mesmo tempo para o mesmo e-mail+IP: no máximo 5 passam (falha fechada)."""
    barreira = threading.Barrier(20)
    aceitas: list[bool] = []
    trava = threading.Lock()

    def tentar() -> None:
        with Session(engine, expire_on_commit=False) as sessao:
            barreira.wait()
            try:
                LimitadorTentativas(sessao, CONFIG).reservar(
                    "login", email="rajada@exemplo.com", ip="198.51.100.7"
                )
                resultado = True
            except MuitasTentativas:
                resultado = False
        with trava:
            aceitas.append(resultado)

    try:
        threads = [threading.Thread(target=tentar) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(aceitas) == 20
        # Falha fechada: no pior caso recusa a mais (até todas), nunca deixa passar a mais.
        assert sum(aceitas) <= 5
    finally:
        with Session(engine) as limpeza:
            limpeza.execute(delete(TentativaAcesso))
            limpeza.commit()


def test_relogio_do_banco_define_a_espera(sessao: Session) -> None:
    limitador = LimitadorTentativas(sessao, CONFIG)
    for _ in range(5):
        limitador.reservar("login", email="ana@exemplo.com", ip="1.2.3.4")
    sessao.execute(update(TentativaAcesso).values(momento=func.now() - timedelta(minutes=10)))

    with pytest.raises(MuitasTentativas) as erro:
        limitador.reservar("login", email="ana@exemplo.com", ip="1.2.3.4")

    assert 4 * 60 < erro.value.segundos <= 5 * 60 + 1
