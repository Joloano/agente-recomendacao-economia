"""Esquemas da gestão de usuários (admin) e do próprio perfil."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.esquemas.autenticacao import Email, Nome, SenhaTexto
from app.modelos.enums import Papel


class _AtualizacaoParcial(BaseModel):
    """Só os campos enviados mudam; enviar `null` ou nenhum campo é erro (não um no-op)."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validar_campos_enviados(self) -> Self:
        enviados = self.model_fields_set - {"senha_atual"}
        if not enviados:
            raise ValueError("Envie ao menos um campo para atualizar.")
        nulos = sorted(campo for campo in enviados if getattr(self, campo) is None)
        if nulos:
            raise ValueError(f"Estes campos não podem ser nulos: {', '.join(nulos)}.")
        return self


class UsuarioCriacao(BaseModel):
    """Criação pelo admin: pode escolher o papel."""

    model_config = ConfigDict(extra="forbid")

    nome: Nome
    email: Email
    senha: SenhaTexto
    papel: Papel = Papel.CLIENTE


class UsuarioAtualizacaoAdmin(_AtualizacaoParcial):
    nome: Nome | None = None
    email: Email | None = None
    papel: Papel | None = None
    ativo: bool | None = None


class PerfilAtualizacao(_AtualizacaoParcial):
    """O próprio usuário só muda nome e e-mail (papel e situação, nunca).

    Trocar o e-mail exige `senha_atual`: um token roubado não basta para tomar a conta.
    """

    nome: Nome | None = None
    email: Email | None = None
    senha_atual: Annotated[str | None, Field(max_length=256)] = None


class TrocaSenha(BaseModel):
    model_config = ConfigDict(extra="forbid")

    senha_atual: Annotated[str, Field(min_length=1, max_length=256)]
    nova_senha: SenhaTexto
