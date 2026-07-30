"""UC-022: create tabmis_intake_sessions table (Tiếp nhận file thủ công TABMIS)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tabmis_intake_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("staging.dataset_catalog.id"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("raw_object_key", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RECEIVED"),
        sa.Column("control_totals", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("uploaded_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("uploaded_at", sa.String(40), nullable=False),
        sa.Column(
            "ingestion_run_id",
            sa.Integer(),
            sa.ForeignKey("staging.ingestion_runs.id"),
            nullable=True,
        ),
        schema="staging",
    )
    op.create_index(
        "ix_staging_tabmis_intake_sessions_dataset_id",
        "tabmis_intake_sessions",
        ["dataset_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_tabmis_intake_sessions_status",
        "tabmis_intake_sessions",
        ["status"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_tabmis_intake_sessions_ingestion_run_id",
        "tabmis_intake_sessions",
        ["ingestion_run_id"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_tabmis_intake_sessions_ingestion_run_id",
        table_name="tabmis_intake_sessions",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_tabmis_intake_sessions_status",
        table_name="tabmis_intake_sessions",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_tabmis_intake_sessions_dataset_id",
        table_name="tabmis_intake_sessions",
        schema="staging",
    )
    op.drop_table("tabmis_intake_sessions", schema="staging")