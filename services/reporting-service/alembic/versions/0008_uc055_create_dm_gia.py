"""UC-055: create curated schema + dm_gia table (Tra cứu dữ liệu giá)

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-13

"""
from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema curated — bảng data mart giá đã chuẩn hoá
    op.execute("CREATE SCHEMA IF NOT EXISTS curated")

    # Tránh lỗi nếu bảng đã được tạo trước đó.
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "dm_gia" not in inspector.get_table_names(schema="curated"):
        op.create_table(
            "dm_gia",
            sa.Column(
                "id",
                sa.Integer(),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column(
                "mat_hang_code",
                sa.String(length=50),
                nullable=False,
            ),
            sa.Column(
                "mat_hang_name",
                sa.String(length=255),
                nullable=False,
            ),
            sa.Column(
                "dia_ban_code",
                sa.String(length=50),
                nullable=False,
            ),
            sa.Column(
                "dia_ban_name",
                sa.String(length=255),
                nullable=False,
            ),
            sa.Column(
                "ky",
                sa.String(length=7),
                nullable=False,
            ),
            sa.Column(
                "gia",
                sa.Float(),
                nullable=False,
            ),
            sa.Column(
                "don_vi_tinh",
                sa.String(length=50),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "nguon",
                sa.String(length=100),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "published_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            schema="curated",
        )

    # Tạo index nếu chưa tồn tại.
    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(
            "dm_gia",
            schema="curated",
        )
    }

    if "ix_curated_dm_gia_mat_hang_code" not in existing_indexes:
        op.create_index(
            "ix_curated_dm_gia_mat_hang_code",
            "dm_gia",
            ["mat_hang_code"],
            schema="curated",
        )

    if "ix_curated_dm_gia_dia_ban_code" not in existing_indexes:
        op.create_index(
            "ix_curated_dm_gia_dia_ban_code",
            "dm_gia",
            ["dia_ban_code"],
            schema="curated",
        )

    if "ix_curated_dm_gia_ky" not in existing_indexes:
        op.create_index(
            "ix_curated_dm_gia_ky",
            "dm_gia",
            ["ky"],
            schema="curated",
        )

    # Seed dữ liệu mẫu.
    dm_gia_table = sa.table(
        "dm_gia",
        sa.column("mat_hang_code", sa.String),
        sa.column("mat_hang_name", sa.String),
        sa.column("dia_ban_code", sa.String),
        sa.column("dia_ban_name", sa.String),
        sa.column("ky", sa.String),
        sa.column("gia", sa.Float),
        sa.column("don_vi_tinh", sa.String),
        sa.column("nguon", sa.String),
        schema="curated",
    )

    gia_theo_thang = {
        "2026-05": 24500,
        "2026-06": 24800,
        "2026-07": 25200,
        "2026-08": 25000,
    }

    seed_rows = []

    for ky, gia in gia_theo_thang.items():
        seed_rows.append(
            {
                "mat_hang_code": "GAO-ST25",
                "mat_hang_name": "Gạo ST25",
                "dia_ban_code": "HN",
                "dia_ban_name": "TP. Hà Nội",
                "ky": ky,
                "gia": gia,
                "don_vi_tinh": "đồng/kg",
                "nguon": "QL_GIA",
            }
        )

        seed_rows.append(
            {
                "mat_hang_code": "GAO-ST25",
                "mat_hang_name": "Gạo ST25",
                "dia_ban_code": "HCM",
                "dia_ban_name": "TP. Hồ Chí Minh",
                "ky": ky,
                "gia": gia - 300,
                "don_vi_tinh": "đồng/kg",
                "nguon": "QL_GIA",
            }
        )

    # Chỉ seed nếu chưa có dữ liệu mẫu.
    existing = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM curated.dm_gia
            WHERE mat_hang_code = 'GAO-ST25'
              AND nguon = 'QL_GIA'
            LIMIT 1
            """
        )
    ).first()

    if not existing:
        op.bulk_insert(dm_gia_table, seed_rows)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "dm_gia" not in inspector.get_table_names(schema="curated"):
        return

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(
            "dm_gia",
            schema="curated",
        )
    }

    if "ix_curated_dm_gia_ky" in existing_indexes:
        op.drop_index(
            "ix_curated_dm_gia_ky",
            table_name="dm_gia",
            schema="curated",
        )

    if "ix_curated_dm_gia_dia_ban_code" in existing_indexes:
        op.drop_index(
            "ix_curated_dm_gia_dia_ban_code",
            table_name="dm_gia",
            schema="curated",
        )

    if "ix_curated_dm_gia_mat_hang_code" in existing_indexes:
        op.drop_index(
            "ix_curated_dm_gia_mat_hang_code",
            table_name="dm_gia",
            schema="curated",
        )

    op.drop_table("dm_gia", schema="curated")