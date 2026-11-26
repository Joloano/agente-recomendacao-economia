"""Base declarativa do SQLAlchemy 2 com convenção de nomes e colunas comuns."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, ClassVar

from sqlalchemy import DateTime, Enum, MetaData, Numeric, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nomes previsíveis para índices e constraints: migrações do Alembic ficam estáveis.
CONVENCAO_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Tipos reutilizáveis
Quantidade = Annotated[Decimal, mapped_column(Numeric(14, 4))]
Dinheiro = Annotated[Decimal, mapped_column(Numeric(12, 4))]
Peso = Annotated[Decimal, mapped_column(Numeric(5, 4))]
Nota = Annotated[Decimal, mapped_column(Numeric(7, 4))]


def tipo_enum(enum: type[StrEnum], nome: str) -> Enum:
    """Enum guardado como texto com CHECK (evita ALTER TYPE nas migrações)."""
    return Enum(
        enum,
        name=nome,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda membros: [m.value for m in membros],
        validate_strings=True,
    )


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_NOMES)
    type_annotation_map: ClassVar[dict[Any, Any]] = {datetime: DateTime(timezone=True)}


class ComId:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, sort_order=-100)


class ComDatas:
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now(), sort_order=100)
    atualizado_em: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), sort_order=101
    )
