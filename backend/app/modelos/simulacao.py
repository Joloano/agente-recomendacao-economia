import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.agente.simulacao import Resposta
from app.modelos.base import Base, ComDatas, ComId, Nota, Quantidade, tipo_enum
from app.modelos.enums import RecursoSimulacao, StatusRecomendacao, StatusSimulacao

if TYPE_CHECKING:
    from app.modelos.equipamento import Equipamento
    from app.modelos.residencia import Residencia
    from app.modelos.usuario import Usuario

_CONSUMO_ENERGIA = "consumo_inicial_energia IS NOT NULL AND consumo_estimado_energia IS NOT NULL"
_SEM_ENERGIA = "consumo_inicial_energia IS NULL AND consumo_estimado_energia IS NULL"
_CONSUMO_AGUA = "consumo_inicial_agua IS NOT NULL AND consumo_estimado_agua IS NOT NULL"
_SEM_AGUA = "consumo_inicial_agua IS NULL AND consumo_estimado_agua IS NULL"


class Simulacao(ComId, ComDatas, Base):
    __tablename__ = "simulacao"
    __table_args__ = (
        CheckConstraint(
            f"(recurso = 'energia' AND {_CONSUMO_ENERGIA} AND {_SEM_AGUA}) OR "
            f"(recurso = 'agua' AND {_CONSUMO_AGUA} AND {_SEM_ENERGIA}) OR "
            f"(recurso = 'ambos' AND {_CONSUMO_ENERGIA} AND {_CONSUMO_AGUA})",
            name="consumo_conforme_recurso",
        ),
        CheckConstraint(
            "COALESCE(consumo_inicial_energia, 0) >= 0"
            " AND COALESCE(consumo_estimado_energia, 0) >= 0"
            " AND COALESCE(consumo_inicial_agua, 0) >= 0"
            " AND COALESCE(consumo_estimado_agua, 0) >= 0",
            name="consumo_nao_negativo",
        ),
        CheckConstraint(
            "(status = 'encerrada') = (encerrada_em IS NOT NULL)", name="encerramento_coerente"
        ),
        # Alvo da FK composta da recomendação.
        UniqueConstraint("id", "residencia_id", name="uq_simulacao_id_residencia"),
        Index("ix_simulacao_residencia_criado_em", "residencia_id", "criado_em"),
        # No máximo uma simulação ativa por residência.
        Index(
            "uq_simulacao_uma_ativa_por_residencia",
            "residencia_id",
            unique=True,
            postgresql_where=text("status = 'ativa'"),
        ),
    )

    residencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("residencia.id", ondelete="CASCADE")
    )
    recurso: Mapped[RecursoSimulacao] = mapped_column(
        tipo_enum(RecursoSimulacao, "recurso_simulacao")
    )
    status: Mapped[StatusSimulacao] = mapped_column(
        tipo_enum(StatusSimulacao, "status_simulacao"),
        default=StatusSimulacao.ATIVA,
        server_default=StatusSimulacao.ATIVA.value,
    )
    # Nulos quando o recurso não faz parte da simulação.
    consumo_inicial_energia: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    consumo_estimado_energia: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    consumo_inicial_agua: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    consumo_estimado_agua: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    encerrada_em: Mapped[datetime | None]

    residencia: Mapped["Residencia"] = relationship(back_populates="simulacoes")
    recomendacoes: Mapped[list["Recomendacao"]] = relationship(
        back_populates="simulacao",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Recomendacao.posicao",
    )


class Recomendacao(ComId, ComDatas, Base):
    """`residencia_id` amarra simulação e equipamento à mesma residência (FKs compostas)."""

    __tablename__ = "recomendacao"
    __table_args__ = (
        UniqueConstraint("simulacao_id", "equipamento_id", name="uq_recomendacao_por_simulacao"),
        # Adiável: a reordenação troca posições dentro da mesma transação.
        UniqueConstraint(
            "simulacao_id",
            "posicao",
            name="uq_recomendacao_posicao",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("posicao > 0", name="posicao_positiva"),
        ForeignKeyConstraint(
            ["simulacao_id", "residencia_id"],
            ["simulacao.id", "simulacao.residencia_id"],
            ondelete="CASCADE",
            name="fk_recomendacao_simulacao_mesma_residencia",
        ),
        # Sem ondelete: equipamento com recomendações não pode ser apagado (use removido_em).
        ForeignKeyConstraint(
            ["equipamento_id", "residencia_id"],
            ["equipamento.id", "equipamento.residencia_id"],
            name="fk_recomendacao_equipamento_mesma_residencia",
        ),
    )

    residencia_id: Mapped[uuid.UUID] = mapped_column(index=True)
    simulacao_id: Mapped[uuid.UUID] = mapped_column()
    equipamento_id: Mapped[uuid.UUID] = mapped_column(index=True)
    nota_economia: Mapped[Nota]
    nota_conforto: Mapped[Nota]
    nota_flexibilidade: Mapped[Nota]
    nota_baixo_esforco: Mapped[Nota]
    utilidade: Mapped[Nota]
    posicao: Mapped[int]
    status: Mapped[StatusRecomendacao] = mapped_column(
        tipo_enum(StatusRecomendacao, "status_recomendacao"),
        default=StatusRecomendacao.PENDENTE,
        server_default=StatusRecomendacao.PENDENTE.value,
    )

    simulacao: Mapped[Simulacao] = relationship(
        back_populates="recomendacoes",
        foreign_keys=[simulacao_id],
        primaryjoin="Recomendacao.simulacao_id == Simulacao.id",
    )
    equipamento: Mapped["Equipamento"] = relationship(
        foreign_keys=[equipamento_id], primaryjoin="Recomendacao.equipamento_id == Equipamento.id"
    )
    feedback: Mapped["Feedback | None"] = relationship(
        back_populates="recomendacao",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )


class Feedback(ComId, Base):
    """Imutável: registrado uma vez por recomendação, por isso sem `atualizado_em`."""

    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("consumo_antes >= 0 AND consumo_depois >= 0", name="consumo_nao_negativo"),
    )

    recomendacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recomendacao.id", ondelete="CASCADE"), unique=True
    )
    # SET NULL: se a conta de quem respondeu (ex.: um membro da família) for excluída,
    # o histórico da residência continua. Excluir o dono apaga a residência inteira.
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), index=True
    )
    resposta: Mapped[Resposta] = mapped_column(tipo_enum(Resposta, "resposta"))
    consumo_antes: Mapped[Quantidade]
    consumo_depois: Mapped[Quantidade]
    registrado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    recomendacao: Mapped[Recomendacao] = relationship(back_populates="feedback")
    usuario: Mapped["Usuario | None"] = relationship()


@event.listens_for(Recomendacao, "before_insert")
def _herdar_residencia(_mapper: object, _conexao: object, alvo: Recomendacao) -> None:
    """Preenche `residencia_id` a partir da simulação; as FKs compostas conferem o equipamento."""
    if alvo.residencia_id is None and alvo.simulacao is not None:
        alvo.residencia_id = alvo.simulacao.residencia_id
