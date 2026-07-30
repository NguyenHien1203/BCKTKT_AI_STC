"""UC-021: add retry_of_run_id column to ingestion_runs (Chạy lại phiên ingest lỗi)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_runs",
        sa.Column(
            "retry_of_run_id",
            sa.Integer(),
            sa.ForeignKey("staging.ingestion_runs.id"),
            nullable=True,
        ),
        schema="staging",
    )
    op.create_index(
        "ix_staging_ingestion_runs_retry_of_run_id",
        "ingestion_runs",
        ["retry_of_run_id"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_ingestion_runs_retry_of_run_id",
        table_name="ingestion_runs",
        schema="staging",
    )
    op.drop_column("ingestion_runs", "retry_of_run_id", schema="staging")