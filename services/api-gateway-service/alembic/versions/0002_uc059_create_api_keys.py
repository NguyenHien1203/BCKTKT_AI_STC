"""UC-059: create api_keys + api_key_usage_logs tables (Quản lý API key)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-14

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("consumer_name", sa.String(length=255), nullable=False),
        sa.Column("consumer_code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("scope", sa.String(length=500), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
        sa.Column("grace_expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "previous_key_id",
            sa.Integer(),
            sa.ForeignKey("gateway.api_keys.id"),
            nullable=True,
        ),
        sa.Column(
            "rotated_to_id",
            sa.Integer(),
            sa.ForeignKey("gateway.api_keys.id"),
            nullable=True,
        ),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_keys_consumer_code",
        "api_keys",
        ["consumer_code"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_keys_key_prefix",
        "api_keys",
        ["key_prefix"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_keys_key_hash",
        "api_keys",
        ["key_hash"],
        unique=True,
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_keys_status",
        "api_keys",
        ["status"],
        schema="gateway",
    )

    op.create_table(
        "api_key_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "api_key_id",
            sa.Integer(),
            sa.ForeignKey("gateway.api_keys.id"),
            nullable=False,
        ),
        sa.Column("endpoint_path", sa.String(length=500), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False, server_default="GET"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("consumer_ip", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "called_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_key_usage_logs_api_key_id",
        "api_key_usage_logs",
        ["api_key_id"],
        schema="gateway",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gateway_api_key_usage_logs_api_key_id",
        table_name="api_key_usage_logs",
        schema="gateway",
    )
    op.drop_table("api_key_usage_logs", schema="gateway")

    op.drop_index("ix_gateway_api_keys_status", table_name="api_keys", schema="gateway")
    op.drop_index("ix_gateway_api_keys_key_hash", table_name="api_keys", schema="gateway")
    op.drop_index("ix_gateway_api_keys_key_prefix", table_name="api_keys", schema="gateway")
    op.drop_index(
        "ix_gateway_api_keys_consumer_code", table_name="api_keys", schema="gateway"
    )
    op.drop_table("api_keys", schema="gateway")