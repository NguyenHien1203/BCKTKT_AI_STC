"""create users table (UC-02)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-23

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=100), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "org_unit_id",
            sa.Integer(),
            sa.ForeignKey("identity.org_units.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="STAFF"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema="identity",
    )
    op.create_index("ix_identity_users_username", "users", ["username"], schema="identity")


def downgrade() -> None:
    op.drop_index("ix_identity_users_username", table_name="users", schema="identity")
    op.drop_table("users", schema="identity")
