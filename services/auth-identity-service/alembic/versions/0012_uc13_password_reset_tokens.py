"""UC-13: password_reset_tokens (Đổi mật khẩu / Cấp lại mật khẩu)

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-28

"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.String(length=40), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="identity",
    )
    op.create_index(
        "ix_identity_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
        schema="identity",
    )
    op.create_index(
        "ix_identity_password_reset_tokens_token",
        "password_reset_tokens",
        ["token"],
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_password_reset_tokens_token",
        table_name="password_reset_tokens",
        schema="identity",
    )
    op.drop_index(
        "ix_identity_password_reset_tokens_user_id",
        table_name="password_reset_tokens",
        schema="identity",
    )
    op.drop_table("password_reset_tokens", schema="identity")