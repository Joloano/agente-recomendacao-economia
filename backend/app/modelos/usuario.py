from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.base import Base, ComDatas, ComId, tipo_enum
from app.modelos.enums import Papel

if TYPE_CHECKING:
    from app.modelos.residencia import Residencia


class Usuario(ComId, ComDatas, Base):
    """Excluir um usuário apaga todas as suas residências e o histórico delas (direito de
    eliminação, LGPD). Para manter estatísticas, a política de anonimização fica na #92."""

    __tablename__ = "usuario"
    __table_args__ = (
        # Unicidade sem diferenciar maiúsculas: o e-mail só entra em minúsculas.
        CheckConstraint("email = lower(email)", name="email_minusculo"),
    )

    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[Papel] = mapped_column(
        tipo_enum(Papel, "papel"), default=Papel.CLIENTE, server_default=Papel.CLIENTE.value
    )
    ativo: Mapped[bool] = mapped_column(default=True, server_default=true())
    email_verificado_em: Mapped[datetime | None]
    # Troca de e-mail pedida pelo próprio usuário: só vale depois que o novo endereço confirmar.
    email_pendente: Mapped[str | None] = mapped_column(String(254))
    # Sobe a cada troca/redefinição de senha ou de e-mail: tokens com versão antiga deixam de valer.
    versao_credenciais: Mapped[int] = mapped_column(default=0, server_default="0")

    residencias: Mapped[list["Residencia"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
