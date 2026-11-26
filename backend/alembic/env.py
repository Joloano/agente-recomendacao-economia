"""Ambiente do Alembic: a URL vem da configuração da aplicação (variáveis de ambiente)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import obter_configuracoes
from app.modelos import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Permite sobrescrever a URL (testes) via `-x url=...` ou `config.set_main_option`.
url_externa = context.get_x_argument(as_dictionary=True).get("url") or config.get_main_option(
    "sqlalchemy.url"
)
url = url_externa or obter_configuracoes().url_banco.render_as_string(hide_password=False)
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

target_metadata = Base.metadata


def executar_offline() -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def executar_online() -> None:
    conectavel = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectavel.connect() as conexao:
        context.configure(connection=conexao, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
