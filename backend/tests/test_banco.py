import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core import banco
from app.core.config import Configuracoes


def test_engine_usa_driver_psycopg_e_pre_ping() -> None:
    engine = banco.criar_engine(Configuracoes(_env_file=None, postgres_timeout_conexao_s=3))

    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.pool._pre_ping


def test_obter_sessao_abre_e_fecha_uma_sessao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        banco, "fabrica_sessao", lambda: sessionmaker(bind=create_engine("sqlite://"))
    )

    gerador = banco.obter_sessao()
    sessao = next(gerador)
    assert sessao.execute(text("SELECT 1")).scalar() == 1
    with pytest.raises(StopIteration):
        next(gerador)


def test_fabrica_sessao_usa_a_configuracao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "banco-de-teste")
    banco.fabrica_sessao.cache_clear()

    fabrica = banco.fabrica_sessao()

    assert fabrica.kw["bind"].url.host == "banco-de-teste"
    banco.fabrica_sessao.cache_clear()
