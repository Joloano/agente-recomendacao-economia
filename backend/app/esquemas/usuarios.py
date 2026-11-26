"""Esquemas da gestão de usuários (admin) e do próprio perfil."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.esquemas.autenticacao import Email, Nome, SenhaTexto
from app.modelos.enums import Papel


class UsuarioCriacao(BaseModel):
    """Criação pelo admin: pode escolher o papel."""

    model_config = ConfigDict(extra="forbid")

    nome: Nome
    email: Email
    senha: SenhaTexto
    papel: Papel = Papel.CLIENTE


class UsuarioAtualizacaoAdmin(BaseModel):
    """Atualização parcial pelo admin: só os campos enviados mudam."""

    model_config = ConfigDict(extra="forbid")

    nome: Nome | None = None
    email: Email | None = None
    papel: Papel | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def _algum_campo(self) -> "UsuarioAtualizacaoAdmin":
        if not self.model_fields_set:
            raise ValueError("Envie ao menos um campo para atualizar.")
        return self


class PerfilAtualizacao(BaseModel):
    """O próprio usuário só muda nome e e-mail (papel e ativo, nunca)."""

    model_config = ConfigDict(extra="forbid")

    nome: Nome | None = None
    email: Email | None = None


class TrocaSenha(BaseModel):
    model_config = ConfigDict(extra="forbid")

    senha_atual: Annotated[str, Field(min_length=1, max_length=256)]
    nova_senha: SenhaTexto
