from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.banco import obter_sessao
from app.core.config import Ambiente, Configuracoes
from app.main import criar_app


@pytest.fixture
def configuracoes() -> Configuracoes:
    return Configuracoes(ambiente=Ambiente.TESTE, _env_file=None)


@pytest.fixture
def app(configuracoes: Configuracoes) -> FastAPI:
    return criar_app(configuracoes)


@pytest.fixture
def sessao_memoria() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with Session(engine) as sessao:
        yield sessao


@pytest.fixture
def cliente(app: FastAPI, sessao_memoria: Session) -> Iterator[TestClient]:
    app.dependency_overrides[obter_sessao] = lambda: sessao_memoria
    with TestClient(app) as cliente:
        yield cliente
