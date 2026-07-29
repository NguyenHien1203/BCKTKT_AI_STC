"""UC-019: create scheduled_tasks table (Cấu hình tác vụ điều phối)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("staging.dataset_catalog.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sync_mode", sa.String(length=20), nullable=False, server_default="FULL"),
        sa.Column(
            "cron_expression", sa.String(length=100), nullable=False, server_default="0 0 * * *"
        ),
        sa.Column("retry_max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_delay_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("retry_backoff", sa.String(length=20), nullable=False, server_default="FIXED"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="IDLE"),
        sa.Column("last_run_at", sa.String(length=40), nullable=True),
        sa.Column("last_run_message", sa.Text(), nullable=False, server_default=""),
        schema="staging",
    )
    op.create_index(
        "ix_staging_scheduled_tasks_dataset_id",
        "scheduled_tasks",
        ["dataset_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_scheduled_tasks_code", "scheduled_tasks", ["code"], schema="staging"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_scheduled_tasks_code", table_name="scheduled_tasks", schema="staging"
    )
    op.drop_index(
        "ix_staging_scheduled_tasks_dataset_id", table_name="scheduled_tasks", schema="staging"
    )
    op.drop_table("scheduled_tasks", schema="staging")