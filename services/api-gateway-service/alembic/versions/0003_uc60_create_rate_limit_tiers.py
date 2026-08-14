"""UC-060: create service_tiers + rate_limit_policies + burst_policies tables
(Quản lý giới hạn tần suất + gói dịch vụ)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-14

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_tiers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_service_tiers_code",
        "service_tiers",
        ["code"],
        unique=True,
        schema="gateway",
    )

    op.create_table(
        "rate_limit_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tier_id",
            sa.Integer(),
            sa.ForeignKey("gateway.service_tiers.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("requests_per_second", sa.Integer(), nullable=False),
        sa.Column("requests_per_day", sa.Integer(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_rate_limit_policies_tier_id",
        "rate_limit_policies",
        ["tier_id"],
        unique=True,
        schema="gateway",
    )

    op.create_table(
        "burst_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tier_id",
            sa.Integer(),
            sa.ForeignKey("gateway.service_tiers.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("burst_limit", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("throttle_policy", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_burst_policies_tier_id",
        "burst_policies",
        ["tier_id"],
        unique=True,
        schema="gateway",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gateway_burst_policies_tier_id", table_name="burst_policies", schema="gateway"
    )
    op.drop_table("burst_policies", schema="gateway")

    op.drop_index(
        "ix_gateway_rate_limit_policies_tier_id",
        table_name="rate_limit_policies",
        schema="gateway",
    )
    op.drop_table("rate_limit_policies", schema="gateway")

    op.drop_index(
        "ix_gateway_service_tiers_code", table_name="service_tiers", schema="gateway"
    )
    op.drop_table("service_tiers", schema="gateway")