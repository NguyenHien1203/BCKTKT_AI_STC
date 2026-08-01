"""UC-029: create curated schema and structured-parsing tables (Phân tích dữ liệu có cấu trúc)

Revision ID: 0001
Revises:
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS curated")

    op.create_table(
        "parsing_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("ingestion_run_id", sa.Integer(), nullable=True),
        sa.Column("data_source_id", sa.Integer(), nullable=True),
        sa.Column("source_format", sa.String(length=20), nullable=False),
        sa.Column("raw_object_key", sa.String(length=500), nullable=False),
        sa.Column("schema_fields_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("field_mapping_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="RECEIVED"),
        sa.Column("records_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_parsed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "mapping_event_published", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("log_entries_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.String(length=40), nullable=False),
        sa.Column("completed_at", sa.String(length=40), nullable=True),
        schema="curated",
    )
    op.create_index(
        "ix_curated_parsing_jobs_dataset_id",
        "parsing_jobs",
        ["dataset_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_parsing_jobs_ingestion_run_id",
        "parsing_jobs",
        ["ingestion_run_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_parsing_jobs_status",
        "parsing_jobs",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "stg_structured_rows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "parsing_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.parsing_jobs.id"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("raw_data_json", sa.Text(), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_stg_structured_rows_parsing_job_id",
        "stg_structured_rows",
        ["parsing_job_id"],
        schema="curated",
    )

    op.create_table(
        "parsed_structured_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "parsing_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.parsing_jobs.id"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("mapped_fields_json", sa.Text(), nullable=False),
        sa.Column("has_error", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="curated",
    )
    op.create_index(
        "ix_curated_parsed_structured_records_parsing_job_id",
        "parsed_structured_records",
        ["parsing_job_id"],
        schema="curated",
    )

    op.create_table(
        "parsing_row_errors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "parsing_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.parsing_jobs.id"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_parsing_row_errors_parsing_job_id",
        "parsing_row_errors",
        ["parsing_job_id"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_parsing_row_errors_parsing_job_id",
        table_name="parsing_row_errors",
        schema="curated",
    )
    op.drop_table("parsing_row_errors", schema="curated")

    op.drop_index(
        "ix_curated_parsed_structured_records_parsing_job_id",
        table_name="parsed_structured_records",
        schema="curated",
    )
    op.drop_table("parsed_structured_records", schema="curated")

    op.drop_index(
        "ix_curated_stg_structured_rows_parsing_job_id",
        table_name="stg_structured_rows",
        schema="curated",
    )
    op.drop_table("stg_structured_rows", schema="curated")

    op.drop_index("ix_curated_parsing_jobs_status", table_name="parsing_jobs", schema="curated")
    op.drop_index(
        "ix_curated_parsing_jobs_ingestion_run_id", table_name="parsing_jobs", schema="curated"
    )
    op.drop_index(
        "ix_curated_parsing_jobs_dataset_id", table_name="parsing_jobs", schema="curated"
    )
    op.drop_table("parsing_jobs", schema="curated")