"""UC-024: create stg_van_ban table (Tiếp nhận thủ công văn bản từ QLVBĐH)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stg_van_ban",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "data_source_id",
            sa.Integer(),
            sa.ForeignKey("staging.sources.id"),
            nullable=False,
        ),
        sa.Column("so_ky_hieu", sa.String(255), nullable=False),
        sa.Column("loai_van_ban", sa.String(255), nullable=False, server_default=""),
        sa.Column("trich_yeu", sa.Text(), nullable=False, server_default=""),
        sa.Column("ngay_ban_hanh", sa.String(40), nullable=False, server_default=""),
        sa.Column("don_vi_ban_hanh", sa.String(255), nullable=False, server_default=""),
        sa.Column("raw_object_key", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RECEIVED"),
        sa.Column("ocr_event_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("uploaded_by", sa.String(255), nullable=False, server_default=""),
        sa.Column("uploaded_at", sa.String(40), nullable=False),
        schema="staging",
    )
    op.create_index(
        "ix_staging_stg_van_ban_data_source_id",
        "stg_van_ban",
        ["data_source_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_stg_van_ban_so_ky_hieu",
        "stg_van_ban",
        ["so_ky_hieu"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_stg_van_ban_status",
        "stg_van_ban",
        ["status"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_stg_van_ban_status", table_name="stg_van_ban", schema="staging"
    )
    op.drop_index(
        "ix_staging_stg_van_ban_so_ky_hieu", table_name="stg_van_ban", schema="staging"
    )
    op.drop_index(
        "ix_staging_stg_van_ban_data_source_id", table_name="stg_van_ban", schema="staging"
    )
    op.drop_table("stg_van_ban", schema="staging")