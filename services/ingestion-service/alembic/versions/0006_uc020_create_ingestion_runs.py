"""UC-020: create ingestion_runs table (Xem lịch đầy đủ dữ liệu + lịch sử chạy)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("staging.dataset_catalog.id"),
            nullable=False,
        ),
        sa.Column(
            "scheduled_task_id",
            sa.Integer(),
            sa.ForeignKey("staging.scheduled_tasks.id"),
            nullable=True,
        ),
        sa.Column("trigger", sa.String(length=20), nullable=False, server_default="MANUAL"),
        sa.Column("sync_mode", sa.String(length=20), nullable=False, server_default="FULL"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="RUNNING"),
        sa.Column("started_at", sa.String(length=40), nullable=False),
        sa.Column("finished_at", sa.String(length=40), nullable=True),
        sa.Column("records_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_loaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("control_totals", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("log_entries", sa.Text(), nullable=False, server_default="[]"),
        schema="staging",
    )
    op.create_index(
        "ix_staging_ingestion_runs_dataset_id",
        "ingestion_runs",
        ["dataset_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_ingestion_runs_scheduled_task_id",
        "ingestion_runs",
        ["scheduled_task_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_ingestion_runs_status",
        "ingestion_runs",
        ["status"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_ingestion_runs_started_at",
        "ingestion_runs",
        ["started_at"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_ingestion_runs_started_at", table_name="ingestion_runs", schema="staging"
    )
    op.drop_index(
        "ix_staging_ingestion_runs_status", table_name="ingestion_runs", schema="staging"
    )
    op.drop_index(
        "ix_staging_ingestion_runs_scheduled_task_id",
        table_name="ingestion_runs",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_ingestion_runs_dataset_id", table_name="ingestion_runs", schema="staging"
    )
    op.drop_table("ingestion_runs", schema="staging")