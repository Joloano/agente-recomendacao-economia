"""Configuração da aplicação, lida apenas de variáveis de ambiente (12-factor).

A validação acontece na subida: em staging e produção, variáveis essenciais precisam
ser definidas explicitamente e segredos fracos ou padrão impedem a aplicação de subir.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy import URL

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]
VALORES_INSEGUROS = {
    "",
    "troque-esta-senha",
    "troque-esta-senha-forte",
    "troque-por-um-segredo-longo-e-aleatorio",
}
TAMANHO_MINIMO_SENHA = 12
TAMANHO_MINIMO_SEGREDO_JWT = 32
OBRIGATORIAS_EM_PRODUCAO = (
    "postgres_host",
    "postgres_db",
    "postgres_usuario",
    "postgres_senha",
    "jwt_segredo",
    "admin_email",
    "admin_senha",
    "cors_origens",
    "url_frontend",
)


HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}  # noqa: S104


def _eh_origem_valida(origem: str) -> bool:
    partes = urlparse(origem)
    return (
        partes.scheme in {"http", "https"}
        and bool(partes.hostname)
        and partes.path == ""
        and not partes.query
        and not partes.fragment
    )


class Ambiente(StrEnum):
    DEV = "dev"
    TESTE = "teste"
    STAGING = "staging"
    PRODUCAO = "producao"


class ConfiguracoesBanco(BaseSettings):
    """Só o acesso ao banco: é o que o Alembic e o serviço `migrar` recebem (menor privilégio)."""

    model_config = SettingsConfigDict(
        env_file=(RAIZ_REPOSITORIO / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = "localhost"
    postgres_porta: int = 5432
    postgres_db: str = "agente"
    postgres_usuario: str = "agente"
    postgres_senha: SecretStr = SecretStr("troque-esta-senha")
    postgres_timeout_conexao_s: int = Field(default=5, gt=0)

    @property
    def url_banco(self) -> URL:
        # URL.create escapa a senha e a esconde em logs (repr mostra ***).
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_usuario,
            password=self.postgres_senha.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_porta,
            database=self.postgres_db,
        )


class Configuracoes(ConfiguracoesBanco):
    """Configuração completa da API."""

    # Seguro por padrão: sem AMBIENTE definido, valem as exigências de produção.
    ambiente: Ambiente = Ambiente.PRODUCAO
    nome_app: str = "Agente Recomendador de Energia e Água"
    log_nivel: str = "INFO"
    cors_origens: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:4200"]
    )

    jwt_segredo: SecretStr = SecretStr("troque-por-um-segredo-longo-e-aleatorio")
    # Só HMAC: com segredo compartilhado, outro algoritmo (ou "none") seria uma brecha.
    jwt_algoritmo: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_expiracao_minutos: int = Field(default=30, gt=0)
    jwt_refresh_expiracao_dias: int = Field(default=7, gt=0)

    admin_nome: str = "Administrador"
    admin_email: EmailStr = "admin@exemplo.com"
    admin_senha: SecretStr = SecretStr("troque-esta-senha-forte")

    email_provedor: Literal["smtp", "memoria"] = "smtp"
    email_remetente: EmailStr = "nao-responda@exemplo.com"
    smtp_host: str = "localhost"
    smtp_porta: int = 1025
    smtp_usuario: str = ""
    smtp_senha: SecretStr = SecretStr("")
    # nenhuma (só desenvolvimento, ex.: Mailpit) | starttls (porta 587) | ssl (SMTPS, porta 465)
    smtp_seguranca: Literal["nenhuma", "starttls", "ssl"] = "starttls"
    smtp_timeout_s: int = Field(default=10, gt=0)

    url_frontend: str = "http://localhost:4200"

    @field_validator("cors_origens", mode="before")
    @classmethod
    def _separar_origens(cls, valor: Any) -> Any:
        """Aceita `a,b` (formato do .env) ou uma lista."""
        if isinstance(valor, str):
            valor = [origem.strip() for origem in valor.split(",") if origem.strip()]
        for origem in valor if isinstance(valor, list) else []:
            if origem != "*" and not _eh_origem_valida(origem):
                raise ValueError(
                    f"Origem de CORS inválida: {origem!r}. Use http(s)://host[:porta], "
                    "sem caminho nem barra final."
                )
        return valor

    @property
    def eh_producao(self) -> bool:
        return self.ambiente in {Ambiente.STAGING, Ambiente.PRODUCAO}

    @model_validator(mode="after")
    def _login_smtp_exige_criptografia(self) -> "Configuracoes":
        if self.smtp_usuario and self.smtp_seguranca == "nenhuma":
            raise ValueError("Login SMTP sem STARTTLS/SSL mandaria a senha em texto puro")
        return self

    @model_validator(mode="after")
    def _validar_producao(self) -> "Configuracoes":
        if "*" in self.cors_origens:
            raise ValueError("CORS_ORIGENS não pode conter '*'; liste as origens permitidas")
        if not self.eh_producao:
            return self
        problemas = [
            *self._faltando_em_producao(),
            *self._segredos_fracos(),
            *self._origens_locais(),
            *self._email_inseguro(),
        ]
        if problemas:
            raise ValueError("Configuração inválida para produção: " + "; ".join(problemas))
        return self

    def _faltando_em_producao(self) -> list[str]:
        faltando = [n.upper() for n in OBRIGATORIAS_EM_PRODUCAO if n not in self.model_fields_set]
        return [f"defina {', '.join(faltando)}"] if faltando else []

    def _segredos_fracos(self) -> list[str]:
        problemas = []
        for nome, valor, minimo in (
            ("POSTGRES_SENHA", self.postgres_senha, TAMANHO_MINIMO_SENHA),
            ("ADMIN_SENHA", self.admin_senha, TAMANHO_MINIMO_SENHA),
            ("JWT_SEGREDO", self.jwt_segredo, TAMANHO_MINIMO_SEGREDO_JWT),
        ):
            segredo = valor.get_secret_value()
            if segredo in VALORES_INSEGUROS or len(segredo) < minimo:
                problemas.append(f"{nome} precisa de um valor próprio com {minimo}+ caracteres")
        return problemas

    def _email_inseguro(self) -> list[str]:
        if self.email_provedor != "smtp":
            return []
        problemas = []
        if self.smtp_seguranca == "nenhuma":
            problemas.append("SMTP_SEGURANCA precisa ser starttls ou ssl")
        if self.smtp_host in {"localhost", "127.0.0.1", "mailpit"}:
            problemas.append("SMTP_HOST precisa apontar para o provedor de e-mail")
        return problemas

    def _origens_locais(self) -> list[str]:
        locais = [o for o in self.cors_origens if urlparse(o).hostname in HOSTS_LOCAIS]
        return [f"CORS_ORIGENS não pode apontar para {', '.join(locais)}"] if locais else []


@lru_cache
def obter_configuracoes() -> Configuracoes:
    """Dependência do FastAPI; em testes, sobrescreva com `app.dependency_overrides`."""
    return Configuracoes()
