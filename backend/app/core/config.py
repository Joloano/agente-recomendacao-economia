"""Configuração da aplicação, lida apenas de variáveis de ambiente (12-factor).

A validação acontece na subida: se faltar algo ou houver segredo padrão em
produção, a aplicação não sobe.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VALORES_INSEGUROS = {
    "",
    "troque-esta-senha",
    "troque-esta-senha-forte",
    "troque-por-um-segredo-longo-e-aleatorio",
}
TAMANHO_MINIMO_SEGREDO_JWT = 32


class Ambiente(StrEnum):
    DEV = "dev"
    TESTE = "teste"
    STAGING = "staging"
    PRODUCAO = "producao"


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ambiente: Ambiente = Ambiente.DEV
    nome_app: str = "Agente Recomendador de Energia e Água"
    log_nivel: str = "INFO"
    cors_origens: list[str] = Field(default_factory=lambda: ["http://localhost:4200"])

    postgres_host: str = "localhost"
    postgres_porta: int = 5432
    postgres_db: str = "agente"
    postgres_usuario: str = "agente"
    postgres_senha: SecretStr = SecretStr("troque-esta-senha")

    jwt_segredo: SecretStr = SecretStr("troque-por-um-segredo-longo-e-aleatorio")
    jwt_algoritmo: str = "HS256"
    jwt_expiracao_minutos: int = Field(default=30, gt=0)
    jwt_refresh_expiracao_dias: int = Field(default=7, gt=0)

    admin_nome: str = "Administrador"
    admin_email: str = "admin@exemplo.com"
    admin_senha: SecretStr = SecretStr("troque-esta-senha-forte")

    url_frontend: str = "http://localhost:4200"

    @property
    def url_banco(self) -> str:
        senha = self.postgres_senha.get_secret_value()
        return (
            f"postgresql+psycopg://{self.postgres_usuario}:{senha}"
            f"@{self.postgres_host}:{self.postgres_porta}/{self.postgres_db}"
        )

    @property
    def eh_producao(self) -> bool:
        return self.ambiente in {Ambiente.STAGING, Ambiente.PRODUCAO}

    @model_validator(mode="after")
    def _exigir_segredos_em_producao(self) -> "Configuracoes":
        if not self.eh_producao:
            return self
        segredos = {
            "POSTGRES_SENHA": self.postgres_senha,
            "JWT_SEGREDO": self.jwt_segredo,
            "ADMIN_SENHA": self.admin_senha,
        }
        inseguros = [
            nome
            for nome, valor in segredos.items()
            if valor.get_secret_value() in VALORES_INSEGUROS
        ]
        if inseguros:
            raise ValueError(f"Defina valores seguros para: {', '.join(inseguros)}")
        if len(self.jwt_segredo.get_secret_value()) < TAMANHO_MINIMO_SEGREDO_JWT:
            raise ValueError(
                f"JWT_SEGREDO precisa ter pelo menos {TAMANHO_MINIMO_SEGREDO_JWT} caracteres"
            )
        return self


@lru_cache
def obter_configuracoes() -> Configuracoes:
    """Dependência do FastAPI; em testes, sobrescreva com `app.dependency_overrides`."""
    return Configuracoes()
