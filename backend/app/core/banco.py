"""Conexão com o PostgreSQL (SQLAlchemy 2)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_configuracoes


@lru_cache
def obter_engine() -> Engine:
    return create_engine(obter_configuracoes().url_banco, pool_pre_ping=True)


@lru_cache
def _fabrica_sessao() -> sessionmaker[Session]:
    return sessionmaker(bind=obter_engine(), autoflush=False, expire_on_commit=False)


def obter_sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with _fabrica_sessao()() as sessao:
        yield sessao
