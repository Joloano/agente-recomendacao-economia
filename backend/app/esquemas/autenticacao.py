"""Esquemas (Pydantic) de entrada e saída da autenticação."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.modelos.enums import Papel

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


def _minusculo(email: str) -> str:
    return email.lower()


Email = Annotated[EmailStr, AfterValidator(_minusculo)]


class RegistroEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Nome
    email: Email
    senha: Annotated[str, Field(min_length=1, max_length=256)]


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    papel: Papel
    ativo: bool
    criado_em: datetime


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - tipo do token, não um segredo
    expira_em: datetime
