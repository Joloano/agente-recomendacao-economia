from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.base import Base, ComDatas, ComId, tipo_enum
from app.modelos.enums import Papel

if TYPE_CHECKING:
    from app.modelos.residencia import Residencia


class Usuario(ComId, ComDatas, Base):
    __tablename__ = "usuario"

    nome: Mapped[str] = mapped_column(String(120))
    # E-mail guardado em minúsculas pela camada de serviço; único.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[Papel] = mapped_column(tipo_enum(Papel, "papel"), default=Papel.CLIENTE)
    ativo: Mapped[bool] = mapped_column(default=True)

    residencias: Mapped[list["Residencia"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
