"""UC-030: create OCR tables (Phân tích PDF/bản quét + OCR)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ocr_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("van_ban_intake_id", sa.Integer(), nullable=True),
        sa.Column("data_source_id", sa.Integer(), nullable=True),
        sa.Column("so_ky_hieu", sa.String(length=255), nullable=True),
        sa.Column("raw_object_key", sa.String(length=500), nullable=False),
        sa.Column(
            "engine_requested", sa.String(length=20), nullable=False, server_default="PADDLEOCR"
        ),
        sa.Column("engine_used", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="RECEIVED"),
        sa.Column("pages_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("table_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "ocr_completed_published", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "parsing_requested_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("log_entries_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.String(length=40), nullable=False),
        sa.Column("completed_at", sa.String(length=40), nullable=True),
        schema="curated",
    )
    op.create_index(
        "ix_curated_ocr_jobs_van_ban_intake_id",
        "ocr_jobs",
        ["van_ban_intake_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_ocr_jobs_status",
        "ocr_jobs",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "ocr_extracted_tables",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "ocr_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.ocr_jobs.id"),
            nullable=False,
        ),
        sa.Column("table_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("rows_json", sa.Text(), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_ocr_extracted_tables_ocr_job_id",
        "ocr_extracted_tables",
        ["ocr_job_id"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_ocr_extracted_tables_ocr_job_id",
        table_name="ocr_extracted_tables",
        schema="curated",
    )
    op.drop_table("ocr_extracted_tables", schema="curated")

    op.drop_index("ix_curated_ocr_jobs_status", table_name="ocr_jobs", schema="curated")
    op.drop_index(
        "ix_curated_ocr_jobs_van_ban_intake_id", table_name="ocr_jobs", schema="curated"
    )
    op.drop_table("ocr_jobs", schema="curated")