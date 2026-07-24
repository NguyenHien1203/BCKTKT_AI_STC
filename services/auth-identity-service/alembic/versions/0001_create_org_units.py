"""create identity schema and org_units table (UC-01)

Revision ID: 0001
Revises:
Create Date: 2026-07-23

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")
    op.create_table(
        "org_units",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit_type", sa.String(length=20), nullable=False),
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("identity.org_units.id"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema="identity",
    )
    op.create_index(
        "ix_identity_org_units_code", "org_units", ["code"], schema="identity"
    )


def downgrade() -> None:
    op.drop_index("ix_identity_org_units_code", table_name="org_units", schema="identity")
    op.drop_table("org_units", schema="identity")
