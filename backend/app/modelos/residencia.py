import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modelos.base import Base, ComDatas, ComId, Dinheiro, Peso, Quantidade

if TYPE_CHECKING:
    from app.modelos.equipamento import Equipamento
    from app.modelos.simulacao import Simulacao
    from app.modelos.usuario import Usuario


class Residencia(ComId, ComDatas, Base):
    __tablename__ = "residencia"
    __table_args__ = (
        CheckConstraint("numero_moradores > 0", name="moradores_positivo"),
        CheckConstraint(
            "meta_energia_kwh_dia >= 0 AND meta_agua_litros_dia >= 0", name="metas_nao_negativas"
        ),
        CheckConstraint(
            "tarifa_energia_rs_kwh >= 0 AND tarifa_agua_rs_m3 >= 0", name="tarifas_nao_negativas"
        ),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(120))
    numero_moradores: Mapped[int]
    meta_energia_kwh_dia: Mapped[Quantidade]
    meta_agua_litros_dia: Mapped[Quantidade]
    tarifa_energia_rs_kwh: Mapped[Dinheiro]
    tarifa_agua_rs_m3: Mapped[Dinheiro]
    perfil_morador: Mapped[str | None] = mapped_column(String(40))

    usuario: Mapped["Usuario"] = relationship(back_populates="residencias")
    preferencia: Mapped["Preferencia | None"] = relationship(
        back_populates="residencia", cascade="all, delete-orphan", uselist=False
    )
    equipamentos: Mapped[list["Equipamento"]] = relationship(
        back_populates="residencia", cascade="all, delete-orphan"
    )
    simulacoes: Mapped[list["Simulacao"]] = relationship(
        back_populates="residencia", cascade="all, delete-orphan"
    )


class Preferencia(ComId, ComDatas, Base):
    """Pesos de prioridade dos moradores. A soma = 1 é validada no domínio (`Pesos`)."""

    __tablename__ = "preferencia"
    __table_args__ = (
        CheckConstraint(
            "peso_economia BETWEEN 0 AND 1 AND peso_conforto BETWEEN 0 AND 1 "
            "AND peso_flexibilidade BETWEEN 0 AND 1 AND peso_baixo_esforco BETWEEN 0 AND 1",
            name="pesos_entre_0_e_1",
        ),
    )

    residencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("residencia.id", ondelete="CASCADE"), unique=True
    )
    peso_economia: Mapped[Peso]
    peso_conforto: Mapped[Peso]
    peso_flexibilidade: Mapped[Peso]
    peso_baixo_esforco: Mapped[Peso]

    residencia: Mapped[Residencia] = relationship(back_populates="preferencia")
