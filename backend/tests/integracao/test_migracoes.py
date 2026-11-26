from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect

from app.modelos import Base
from tests.integracao.conftest import configuracao_alembic

TABELAS = {
    "usuario",
    "residencia",
    "preferencia",
    "categoria",
    "equipamento",
    "simulacao",
    "recomendacao",
    "feedback",
}


def test_upgrade_cria_todas_as_tabelas(engine: Engine) -> None:
    assert set(inspect(engine).get_table_names()) >= TABELAS


def test_migracoes_estao_em_sincronia_com_os_modelos(engine: Engine) -> None:
    with engine.connect() as conexao:
        diferencas = compare_metadata(MigrationContext.configure(conexao), Base.metadata)

    assert diferencas == [], "Gere uma migração: alembic revision --autogenerate"


def test_chaves_estrangeiras_tem_indice(engine: Engine) -> None:
    inspetor = inspect(engine)
    for tabela in TABELAS:
        indexadas = {tuple(i["column_names"]) for i in inspetor.get_indexes(tabela)} | {
            tuple(u["column_names"]) for u in inspetor.get_unique_constraints(tabela)
        }
        for fk in inspetor.get_foreign_keys(tabela):
            assert tuple(fk["constrained_columns"]) in indexadas, f"{tabela}: FK sem índice"


def test_downgrade_desfaz_tudo_e_upgrade_refaz(engine: Engine, url_banco: str) -> None:
    config = configuracao_alembic(url_banco)

    command.downgrade(config, "base")
    assert not TABELAS & set(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) >= TABELAS
