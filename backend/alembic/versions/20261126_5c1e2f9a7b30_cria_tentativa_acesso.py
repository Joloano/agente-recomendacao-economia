"""cria tentativa_acesso (limite de tentativas)

Revision ID: 5c1e2f9a7b30
Revises: 86290e487499
Create Date: 2026-11-26 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c1e2f9a7b30"
down_revision: str | Sequence[str] | None = "86290e487499"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tentativa_acesso",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("acao", sa.String(length=20), nullable=False),
        sa.Column("chave", sa.String(length=64), nullable=False),
        sa.Column(
            "momento", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tentativa_acesso")),
    )
    op.create_index(
        "ix_tentativa_acesso_acao_chave_momento",
        "tentativa_acesso",
        ["acao", "chave", "momento"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tentativa_acesso_momento"), "tentativa_acesso", ["momento"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tentativa_acesso_momento"), table_name="tentativa_acesso")
    op.drop_index("ix_tentativa_acesso_acao_chave_momento", table_name="tentativa_acesso")
    op.drop_table("tentativa_acesso")
