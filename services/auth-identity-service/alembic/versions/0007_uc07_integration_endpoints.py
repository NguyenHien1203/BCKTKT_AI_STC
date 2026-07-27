"""UC-07: integration_endpoints (cấu hình tích hợp Keycloak/LGSP)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_endpoints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("endpoint_type", sa.String(length=20), nullable=False, unique=True),
        sa.Column("base_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("extra_config", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_checked_at", sa.String(length=40), nullable=True),
        sa.Column("last_check_message", sa.Text(), nullable=False, server_default=""),
        schema="identity",
    )
    op.create_index(
        "ix_identity_integration_endpoints_endpoint_type",
        "integration_endpoints",
        ["endpoint_type"],
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_integration_endpoints_endpoint_type",
        table_name="integration_endpoints",
        schema="identity",
    )
    op.drop_table("integration_endpoints", schema="identity")