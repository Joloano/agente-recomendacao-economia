"""Conexão com o PostgreSQL (SQLAlchemy 2)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Configuracoes, obter_configuracoes


def criar_engine(config: Configuracoes) -> Engine:
    # connect_timeout curto: com o banco fora, o /health responde 503 rápido em vez de travar.
    return create_engine(
        config.url_banco,
        pool_pre_ping=True,
        connect_args={"connect_timeout": config.postgres_timeout_conexao_s},
    )


@lru_cache
def fabrica_sessao() -> sessionmaker[Session]:
    return sessionmaker(
        bind=criar_engine(obter_configuracoes()), autoflush=False, expire_on_commit=False
    )


def obter_sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with fabrica_sessao()() as sessao:
        yield sessao
