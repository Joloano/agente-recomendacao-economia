import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.agente.dominio import Essencialidade, Recurso
from app.modelos.base import Base, ComDatas, ComId, Quantidade, tipo_enum

if TYPE_CHECKING:
    from app.modelos.residencia import Residencia

_ESCALAS = ("impacto_conforto_1a5", "flexibilidade_1a5", "esforco_1a5")


class Categoria(ComId, ComDatas, Base):
    __tablename__ = "categoria"
    __table_args__ = (UniqueConstraint("nome", "recurso", name="uq_categoria_nome_recurso"),)

    nome: Mapped[str] = mapped_column(String(60))
    recurso: Mapped[Recurso] = mapped_column(tipo_enum(Recurso, "recurso"))
    descricao_acao: Mapped[str] = mapped_column(String(500))


class Equipamento(ComId, ComDatas, Base):
    __tablename__ = "equipamento"
    __table_args__ = (
        *(CheckConstraint(f"{c} BETWEEN 1 AND 5", name=f"{c}_entre_1_e_5") for c in _ESCALAS),
        CheckConstraint(
            "consumo_diario_estimado >= 0 AND economia_potencial >= 0 AND horas_uso_diario >= 0",
            name="valores_nao_negativos",
        ),
        CheckConstraint("horas_uso_diario <= 24", name="horas_no_maximo_24"),
        # Energia exige potência; água exige vazão.
        CheckConstraint(
            "(recurso = 'energia' AND potencia_kw IS NOT NULL AND vazao_litros_min IS NULL) OR "
            "(recurso = 'agua' AND vazao_litros_min IS NOT NULL AND potencia_kw IS NULL)",
            name="medida_conforme_recurso",
        ),
    )

    residencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("residencia.id", ondelete="CASCADE"), index=True
    )
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categoria.id", ondelete="RESTRICT"), index=True
    )
    nome: Mapped[str] = mapped_column(String(120))
    recurso: Mapped[Recurso] = mapped_column(tipo_enum(Recurso, "recurso"))
    potencia_kw: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    vazao_litros_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    horas_uso_diario: Mapped[Quantidade]
    consumo_diario_estimado: Mapped[Quantidade]
    reducao_uso: Mapped[bool]
    essencialidade: Mapped[Essencialidade] = mapped_column(
        tipo_enum(Essencialidade, "essencialidade")
    )
    impacto_conforto_1a5: Mapped[int]
    flexibilidade_1a5: Mapped[int]
    esforco_1a5: Mapped[int]
    economia_potencial: Mapped[Quantidade]

    residencia: Mapped["Residencia"] = relationship(back_populates="equipamentos")
    categoria: Mapped[Categoria] = relationship()
