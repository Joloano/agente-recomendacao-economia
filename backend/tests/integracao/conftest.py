"""Testes de integração com PostgreSQL real.

Defina `TESTE_BANCO_URL` (ex.: postgresql+psycopg://agente:agente@localhost:5432/agente_teste)
para rodá-los; sem a variável, são pulados. O CI sempre a define.
O banco é recriado do zero pelas migrações a cada sessão de testes.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

URL = os.environ.get("TESTE_BANCO_URL")
PASTA_BACKEND = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(URL is None, reason="TESTE_BANCO_URL não definida")


def configuracao_alembic(url: str) -> Config:
    config = Config(str(PASTA_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(PASTA_BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def url_banco() -> str:
    if URL is None:
        pytest.skip("TESTE_BANCO_URL não definida")
    return URL


@pytest.fixture(scope="session")
def engine(url_banco: str) -> Iterator[Engine]:
    config = configuracao_alembic(url_banco)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(url_banco)
    yield engine
    engine.dispose()


@pytest.fixture
def sessao(engine: Engine) -> Iterator[Session]:
    """Sessão dentro de uma transação desfeita ao fim de cada teste."""
    with engine.connect() as conexao:
        transacao = conexao.begin()
        with Session(bind=conexao, join_transaction_mode="create_savepoint") as sessao:
            yield sessao
        transacao.rollback()
