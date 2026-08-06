"""UC-040: Xử lý ngoại lệ chất lượng -- thêm cột kết quả xử lý vào
quality_exception_queue (resolution_action/corrected_fields_json/
resolution_reason/resolved_at)

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quality_exception_queue",
        sa.Column("resolution_action", sa.String(length=20), nullable=True),
        schema="curated",
    )
    op.add_column(
        "quality_exception_queue",
        sa.Column("corrected_fields_json", sa.Text(), nullable=True),
        schema="curated",
    )
    op.add_column(
        "quality_exception_queue",
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        schema="curated",
    )
    op.add_column(
        "quality_exception_queue",
        sa.Column("resolved_at", sa.String(length=40), nullable=True),
        schema="curated",
    )


def downgrade() -> None:
    op.drop_column("quality_exception_queue", "resolved_at", schema="curated")
    op.drop_column("quality_exception_queue", "resolution_reason", schema="curated")
    op.drop_column("quality_exception_queue", "corrected_fields_json", schema="curated")
    op.drop_column("quality_exception_queue", "resolution_action", schema="curated")