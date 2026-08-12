"""UC-054: create curated.dm_tai_san (Tra cứu dữ liệu tài sản)

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-12

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema "curated" dùng chung với data-quality-service (kho dữ liệu
    # chuẩn hoá — xem ARCHITECTURE.md mục 2 + services/data-quality-service/
    # alembic/versions/0001_uc029_create_parsing_tables.py). Vì mỗi service
    # có version_table Alembic riêng, reporting-service phải tự đảm bảo
    # schema "curated" tồn tại trước khi tạo bảng `dm_tai_san` (bảng chiều
    # tài sản, đọc bởi UC-054), phòng trường hợp deploy chỉ mình
    # reporting-service (chưa chạy migration của data-quality-service).
    op.execute("CREATE SCHEMA IF NOT EXISTS curated")

    op.create_table(
        "dm_tai_san",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ma_tai_san", sa.String(length=50), nullable=False),
        sa.Column("ten_tai_san", sa.String(length=255), nullable=False),
        sa.Column("don_vi_code", sa.String(length=50), nullable=False),
        sa.Column("don_vi_ten", sa.String(length=255), nullable=False),
        sa.Column("nhom_tai_san_code", sa.String(length=50), nullable=False),
        sa.Column("nhom_tai_san_ten", sa.String(length=255), nullable=False),
        sa.Column("trang_thai", sa.String(length=30), nullable=False),
        sa.Column("nguyen_gia", sa.Float(), nullable=False, server_default="0"),
        sa.Column("gia_tri_con_lai", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ngay_dua_vao_su_dung", sa.String(length=10), nullable=True),
        sa.Column("nam_tai_chinh", sa.Integer(), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "published_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("ma_tai_san", name="uq_curated_dm_tai_san_ma_tai_san"),
        schema="curated",
    )
    op.create_index(
        "ix_curated_dm_tai_san_ma_tai_san", "dm_tai_san", ["ma_tai_san"], schema="curated"
    )
    op.create_index(
        "ix_curated_dm_tai_san_don_vi_code", "dm_tai_san", ["don_vi_code"], schema="curated"
    )
    op.create_index(
        "ix_curated_dm_tai_san_nhom_tai_san_code",
        "dm_tai_san",
        ["nhom_tai_san_code"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_dm_tai_san_trang_thai", "dm_tai_san", ["trang_thai"], schema="curated"
    )


def downgrade() -> None:
    op.drop_index("ix_curated_dm_tai_san_trang_thai", table_name="dm_tai_san", schema="curated")
    op.drop_index(
        "ix_curated_dm_tai_san_nhom_tai_san_code", table_name="dm_tai_san", schema="curated"
    )
    op.drop_index(
        "ix_curated_dm_tai_san_don_vi_code", table_name="dm_tai_san", schema="curated"
    )
    op.drop_index("ix_curated_dm_tai_san_ma_tai_san", table_name="dm_tai_san", schema="curated")
    op.drop_table("dm_tai_san", schema="curated")