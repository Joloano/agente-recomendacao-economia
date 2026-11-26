from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import CheckConstraint, Engine, inspect

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
    """Toda FK precisa de um índice que comece pela sua primeira coluna."""
    inspetor = inspect(engine)
    for tabela in TABELAS:
        indices = [tuple(i["column_names"]) for i in inspetor.get_indexes(tabela)] + [
            tuple(u["column_names"]) for u in inspetor.get_unique_constraints(tabela)
        ]
        for fk in inspetor.get_foreign_keys(tabela):
            colunas = tuple(fk["constrained_columns"])
            # Um índice que comece pela 1ª coluna da FK já atende as buscas e as exclusões.
            coberta = any(indice[:1] == colunas[:1] for indice in indices)
            assert coberta, f"{tabela}: FK {colunas} sem índice"


def test_checks_dos_modelos_existem_no_banco(engine: Engine) -> None:
    """compare_metadata não compara CHECKs; este teste cobre essa lacuna pelos nomes."""
    inspetor = inspect(engine)
    for tabela in Base.metadata.sorted_tables:
        esperados = {
            c.name for c in tabela.constraints if isinstance(c, CheckConstraint) and c.name
        }
        no_banco = {c["name"] for c in inspetor.get_check_constraints(tabela.name)}
        assert esperados <= no_banco, f"{tabela.name}: CHECKs faltando {esperados - no_banco}"


def test_downgrade_desfaz_tudo_e_upgrade_refaz(engine: Engine, url_banco: str) -> None:
    config = configuracao_alembic(url_banco)
    try:
        command.downgrade(config, "base")
        assert not TABELAS & set(inspect(engine).get_table_names())
    finally:
        # Mesmo se falhar, devolve o banco ao estado esperado pelos outros testes.
        command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) >= TABELAS
