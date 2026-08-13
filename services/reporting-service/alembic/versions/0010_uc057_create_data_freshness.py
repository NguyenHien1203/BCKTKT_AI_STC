"""UC-057: create curated.data_freshness table (Hiển thị độ mới dữ liệu)

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-13

"""
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema curated — view/bảng độ mới dữ liệu theo nguồn (dùng chung
    # schema với dm_gia/dm_ngan_sach/dm_tai_san, an toàn nếu đã được tạo
    # trước đó bởi service khác — vd data-quality-service).
    op.execute("CREATE SCHEMA IF NOT EXISTS curated")

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "data_freshness" not in inspector.get_table_names(schema="curated"):
        op.create_table(
            "data_freshness",
            sa.Column(
                "id",
                sa.Integer(),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column(
                "nguon_code",
                sa.String(length=50),
                nullable=False,
            ),
            sa.Column(
                "nguon_ten",
                sa.String(length=255),
                nullable=False,
            ),
            sa.Column(
                "last_sync",
                sa.DateTime(),
                nullable=False,
            ),
            sa.Column(
                "expected_record_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "actual_record_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            schema="curated",
        )

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(
            "data_freshness",
            schema="curated",
        )
    }

    if "ix_curated_data_freshness_nguon_code" not in existing_indexes:
        op.create_index(
            "ix_curated_data_freshness_nguon_code",
            "data_freshness",
            ["nguon_code"],
            schema="curated",
        )

    existing_uniques = {
        uc["name"]
        for uc in inspector.get_unique_constraints(
            "data_freshness",
            schema="curated",
        )
    }

    if "uq_curated_data_freshness_nguon_code" not in existing_uniques:
        op.create_unique_constraint(
            "uq_curated_data_freshness_nguon_code",
            "data_freshness",
            ["nguon_code"],
            schema="curated",
        )

    # Seed dữ liệu mẫu — 4 nguồn thường gặp trong docs/use_cases_raw.txt
    # (TABMIS, QL_GIA, QL_TAI_SAN, VAN_BAN) để UC-057 có dữ liệu hiển thị
    # ngay sau khi khởi tạo — có thể cập nhật thêm qua API
    # POST /data-freshness/index.
    data_freshness_table = sa.table(
        "data_freshness",
        sa.column("nguon_code", sa.String),
        sa.column("nguon_ten", sa.String),
        sa.column("last_sync", sa.DateTime),
        sa.column("expected_record_count", sa.Integer),
        sa.column("actual_record_count", sa.Integer),
        schema="curated",
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seed_rows = [
        {
            "nguon_code": "TABMIS",
            "nguon_ten": "Hệ thống TABMIS (Ngân sách)",
            "last_sync": now - timedelta(hours=2),
            "expected_record_count": 1000,
            "actual_record_count": 1000,
        },
        {
            "nguon_code": "QL_GIA",
            "nguon_ten": "Hệ thống Quản lý Giá",
            "last_sync": now - timedelta(hours=6),
            "expected_record_count": 500,
            "actual_record_count": 480,
        },
        {
            "nguon_code": "QL_TAI_SAN",
            "nguon_ten": "Hệ thống Quản lý Tài sản công",
            "last_sync": now - timedelta(hours=30),
            "expected_record_count": 300,
            "actual_record_count": 300,
        },
        {
            "nguon_code": "VAN_BAN",
            "nguon_ten": "Kho văn bản (tiếp nhận + OCR)",
            "last_sync": now - timedelta(hours=1),
            "expected_record_count": 200,
            "actual_record_count": 150,
        },
    ]

    existing = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM curated.data_freshness
            WHERE nguon_code = 'TABMIS'
            LIMIT 1
            """
        )
    ).first()

    if not existing:
        op.bulk_insert(data_freshness_table, seed_rows)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "data_freshness" not in inspector.get_table_names(schema="curated"):
        return

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(
            "data_freshness",
            schema="curated",
        )
    }

    if "ix_curated_data_freshness_nguon_code" in existing_indexes:
        op.drop_index(
            "ix_curated_data_freshness_nguon_code",
            table_name="data_freshness",
            schema="curated",
        )

    op.drop_table("data_freshness", schema="curated")