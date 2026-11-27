"""tokens de conta, verificação de e-mail e revogação de sessões

Revision ID: 7d3a1b6e9c42
Revises: 5c1e2f9a7b30
Create Date: 2026-11-27 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d3a1b6e9c42"
down_revision: str | Sequence[str] | None = "5c1e2f9a7b30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuario", sa.Column("email_verificado_em", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "usuario",
        sa.Column("credenciais_alteradas_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "token_conta",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column(
            "finalidade",
            sa.Enum(
                "verificacao_email",
                "recuperacao_senha",
                name="finalidade_token",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("email_alvo", sa.String(length=254), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_token_conta_usuario_id_usuario"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_token_conta")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_token_conta_token_hash")),
    )
    op.create_index(op.f("ix_token_conta_usuario_id"), "token_conta", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_token_conta_usuario_id"), table_name="token_conta")
    op.drop_table("token_conta")
    op.drop_column("usuario", "credenciais_alteradas_em")
    op.drop_column("usuario", "email_verificado_em")
