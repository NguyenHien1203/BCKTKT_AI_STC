"""UC-032: Xử lý hàng đợi chưa ánh xạ -- thêm cột kết quả xử lý vào
unmapped_value_queue (resolution_action/resolved_value/resolution_reason/
resolved_at)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "unmapped_value_queue",
        sa.Column("resolution_action", sa.String(length=20), nullable=True),
        schema="curated",
    )
    op.add_column(
        "unmapped_value_queue",
        sa.Column("resolved_value", sa.Text(), nullable=True),
        schema="curated",
    )
    op.add_column(
        "unmapped_value_queue",
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        schema="curated",
    )
    op.add_column(
        "unmapped_value_queue",
        sa.Column("resolved_at", sa.String(length=40), nullable=True),
        schema="curated",
    )


def downgrade() -> None:
    op.drop_column("unmapped_value_queue", "resolved_at", schema="curated")
    op.drop_column("unmapped_value_queue", "resolution_reason", schema="curated")
    op.drop_column("unmapped_value_queue", "resolved_value", schema="curated")
    op.drop_column("unmapped_value_queue", "resolution_action", schema="curated")