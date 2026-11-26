from datetime import datetime

from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base, ComId


class TentativaAcesso(ComId, Base):
    """Registro curto de tentativas, para o limite de tentativas (#137).

    `chave` é um HMAC do e-mail ou do IP (nunca o valor em claro: minimização da LGPD).
    As linhas vivem só durante a janela do limite e são apagadas depois.
    """

    __tablename__ = "tentativa_acesso"
    __table_args__ = (Index("ix_tentativa_acesso_acao_chave_momento", "acao", "chave", "momento"),)

    acao: Mapped[str] = mapped_column(String(20))
    chave: Mapped[str] = mapped_column(String(64))
    momento: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
