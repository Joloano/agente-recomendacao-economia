"""Esquemas (Pydantic) de entrada e saída da autenticação."""

import unicodedata
import uuid
from datetime import datetime
from typing import Annotated, Literal

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.modelos.enums import Papel


def _sem_controle(texto: str) -> str:
    # O PostgreSQL não aceita o byte 0x00 em texto; outros controles não fazem sentido aqui.
    if any(unicodedata.category(c) == "Cc" for c in texto):
        raise ValueError("não pode conter caracteres de controle")
    return texto


def _sem_invisiveis(texto: str) -> str:
    # Cf: inversão bidi (U+202E) e caracteres de largura zero falsificariam a exibição do nome.
    if any(unicodedata.category(c) == "Cf" for c in texto):
        raise ValueError("não pode conter caracteres invisíveis ou de controle de direção")
    return texto


Nome = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=120),
    AfterValidator(_sem_controle),
    AfterValidator(_sem_invisiveis),
]


def normalizar_email(email: str) -> str:
    """Mesma normalização no cadastro e no login: IDN, Unicode (NFC) e minúsculas.

    Levanta ValueError se o e-mail for inválido.
    """
    try:
        valido = validate_email(email.strip(), check_deliverability=False)
    except EmailNotValidError as erro:
        raise ValueError(str(erro)) from erro
    return valido.normalized.lower()


Email = Annotated[EmailStr, AfterValidator(normalizar_email)]

# A política (tamanho, senhas comuns...) é aplicada no serviço, que conhece o e-mail.
SenhaTexto = Annotated[str, Field(min_length=1, max_length=256), AfterValidator(_sem_controle)]


class RegistroEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Nome
    email: Email
    senha: SenhaTexto


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
