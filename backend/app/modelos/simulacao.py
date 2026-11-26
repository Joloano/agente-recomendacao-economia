import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.agente.simulacao import Resposta
from app.modelos.base import Base, ComDatas, ComId, Nota, Quantidade, tipo_enum
from app.modelos.enums import RecursoSimulacao, StatusRecomendacao, StatusSimulacao

if TYPE_CHECKING:
    from app.modelos.equipamento import Equipamento
    from app.modelos.residencia import Residencia
    from app.modelos.usuario import Usuario


class Simulacao(ComId, ComDatas, Base):
    __tablename__ = "simulacao"

    residencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("residencia.id", ondelete="CASCADE"), index=True
    )
    recurso: Mapped[RecursoSimulacao] = mapped_column(
        tipo_enum(RecursoSimulacao, "recurso_simulacao")
    )
    status: Mapped[StatusSimulacao] = mapped_column(
        tipo_enum(StatusSimulacao, "status_simulacao"), default=StatusSimulacao.ATIVA
    )
    # Nulos quando o recurso não faz parte da simulação.
    consumo_inicial_energia: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    consumo_estimado_energia: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    consumo_inicial_agua: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    consumo_estimado_agua: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    encerrada_em: Mapped[datetime | None]

    residencia: Mapped["Residencia"] = relationship(back_populates="simulacoes")
    recomendacoes: Mapped[list["Recomendacao"]] = relationship(
        back_populates="simulacao", cascade="all, delete-orphan", order_by="Recomendacao.posicao"
    )


class Recomendacao(ComId, ComDatas, Base):
    __tablename__ = "recomendacao"
    __table_args__ = (
        UniqueConstraint("simulacao_id", "equipamento_id", name="uq_recomendacao_por_simulacao"),
        CheckConstraint("posicao > 0", name="posicao_positiva"),
    )

    simulacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulacao.id", ondelete="CASCADE"), index=True
    )
    equipamento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipamento.id", ondelete="CASCADE"), index=True
    )
    nota_economia: Mapped[Nota]
    nota_conforto: Mapped[Nota]
    nota_flexibilidade: Mapped[Nota]
    nota_baixo_esforco: Mapped[Nota]
    utilidade: Mapped[Nota]
    posicao: Mapped[int]
    status: Mapped[StatusRecomendacao] = mapped_column(
        tipo_enum(StatusRecomendacao, "status_recomendacao"), default=StatusRecomendacao.PENDENTE
    )

    simulacao: Mapped[Simulacao] = relationship(back_populates="recomendacoes")
    equipamento: Mapped["Equipamento"] = relationship()
    feedback: Mapped["Feedback | None"] = relationship(
        back_populates="recomendacao", cascade="all, delete-orphan", uselist=False
    )


class Feedback(ComId, Base):
    __tablename__ = "feedback"

    recomendacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recomendacao.id", ondelete="CASCADE"), unique=True
    )
    # SET NULL: o histórico de economia sobrevive à exclusão (anonimização, LGPD).
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), index=True
    )
    resposta: Mapped[Resposta] = mapped_column(tipo_enum(Resposta, "resposta"))
    consumo_antes: Mapped[Quantidade]
    consumo_depois: Mapped[Quantidade]
    registrado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    recomendacao: Mapped[Recomendacao] = relationship(back_populates="feedback")
    usuario: Mapped["Usuario | None"] = relationship()
