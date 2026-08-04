"""UC-037: create catalog_change_audit_logs (Phê duyệt thay đổi danh mục
nhạy cảm — bước 4 "Ghi lý do phê duyệt -> Hệ thống lưu vào nhật ký")

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_change_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "request_id",
            sa.Integer(),
            sa.ForeignKey("curated.catalog_change_requests.id"),
            nullable=False,
        ),
        sa.Column(
            "entry_id",
            sa.Integer(),
            sa.ForeignKey("curated.catalog_entries.id"),
            nullable=False,
        ),
        sa.Column("catalog_type", sa.String(length=30), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("decided_by", sa.String(length=255), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("diff_snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_change_audit_logs_request_id",
        "catalog_change_audit_logs",
        ["request_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_change_audit_logs_entry_id",
        "catalog_change_audit_logs",
        ["entry_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_change_audit_logs_catalog_type",
        "catalog_change_audit_logs",
        ["catalog_type"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_change_audit_logs_action",
        "catalog_change_audit_logs",
        ["action"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_catalog_change_audit_logs_action",
        table_name="catalog_change_audit_logs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_catalog_change_audit_logs_catalog_type",
        table_name="catalog_change_audit_logs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_catalog_change_audit_logs_entry_id",
        table_name="catalog_change_audit_logs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_catalog_change_audit_logs_request_id",
        table_name="catalog_change_audit_logs",
        schema="curated",
    )
    op.drop_table("catalog_change_audit_logs", schema="curated")