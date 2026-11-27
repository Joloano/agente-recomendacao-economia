import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base, ComId, tipo_enum


class FinalidadeToken(StrEnum):
    VERIFICACAO_EMAIL = "verificacao_email"
    RECUPERACAO_SENHA = "recuperacao_senha"


class TokenConta(ComId, Base):
    """Token de uso único enviado por e-mail (verificação de e-mail e recuperação de senha).

    Só o hash SHA-256 fica no banco: quem ler a tabela não consegue usar os links.
    """

    __tablename__ = "token_conta"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), index=True
    )
    finalidade: Mapped[FinalidadeToken] = mapped_column(
        tipo_enum(FinalidadeToken, "finalidade_token")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # Para a verificação de e-mail: o endereço que o link confirma (o usuário pode trocá-lo antes).
    email_alvo: Mapped[str | None] = mapped_column(String(254))
    expira_em: Mapped[datetime]
    usado_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
