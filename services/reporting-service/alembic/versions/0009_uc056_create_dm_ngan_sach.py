"""UC-056: create curated.dm_ngan_sach table (Tra cứu dữ liệu ngân sách)

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-13

"""
from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema curated — bảng data mart ngân sách đã chuẩn hoá (dùng chung
    # schema với dm_gia/dm_tai_san, an toàn nếu đã được tạo trước đó).
    op.execute("CREATE SCHEMA IF NOT EXISTS curated")

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "dm_ngan_sach" not in inspector.get_table_names(schema="curated"):
        op.create_table(
            "dm_ngan_sach",
            sa.Column(
                "id",
                sa.Integer(),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column(
                "don_vi_code",
                sa.String(length=50),
                nullable=False,
            ),
            sa.Column(
                "don_vi_ten",
                sa.String(length=255),
                nullable=False,
            ),
            sa.Column(
                "khoan_muc_code",
                sa.String(length=50),
                nullable=False,
            ),
            sa.Column(
                "khoan_muc_ten",
                sa.String(length=255),
                nullable=False,
            ),
            sa.Column(
                "ky",
                sa.String(length=4),
                nullable=False,
            ),
            sa.Column(
                "thu",
                sa.Float(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "chi",
                sa.Float(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "tam_ung",
                sa.Float(),
                nullable=False,
                server_default="0",
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

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(
            "dm_ngan_sach",
            schema="curated",
        )
    }

    if "ix_curated_dm_ngan_sach_don_vi_code" not in existing_indexes:
        op.create_index(
            "ix_curated_dm_ngan_sach_don_vi_code",
            "dm_ngan_sach",
            ["don_vi_code"],
            schema="curated",
        )

    if "ix_curated_dm_ngan_sach_khoan_muc_code" not in existing_indexes:
        op.create_index(
            "ix_curated_dm_ngan_sach_khoan_muc_code",
            "dm_ngan_sach",
            ["khoan_muc_code"],
            schema="curated",
        )

    if "ix_curated_dm_ngan_sach_ky" not in existing_indexes:
        op.create_index(
            "ix_curated_dm_ngan_sach_ky",
            "dm_ngan_sach",
            ["ky"],
            schema="curated",
        )

    # Seed dữ liệu mẫu.
    dm_ngan_sach_table = sa.table(
        "dm_ngan_sach",
        sa.column("don_vi_code", sa.String),
        sa.column("don_vi_ten", sa.String),
        sa.column("khoan_muc_code", sa.String),
        sa.column("khoan_muc_ten", sa.String),
        sa.column("ky", sa.String),
        sa.column("thu", sa.Float),
        sa.column("chi", sa.Float),
        sa.column("tam_ung", sa.Float),
        sa.column("don_vi_tinh", sa.String),
        sa.column("nguon", sa.String),
        schema="curated",
    )

    don_vi_list = [
        ("SO_TC", "Sở Tài chính"),
        ("P_TC_HUYEN", "Phòng Tài chính - Kế hoạch huyện"),
    ]
    khoan_muc_list = [
        ("KM_SNKT", "Sự nghiệp kinh tế"),
        ("KM_SNGD", "Sự nghiệp giáo dục"),
    ]
    ky_list = ["2024", "2025", "2026"]

    seed_rows = []
    base = 1000
    for dv_code, dv_ten in don_vi_list:
        for km_code, km_ten in khoan_muc_list:
            for i, ky in enumerate(ky_list):
                seed_rows.append(
                    {
                        "don_vi_code": dv_code,
                        "don_vi_ten": dv_ten,
                        "khoan_muc_code": km_code,
                        "khoan_muc_ten": km_ten,
                        "ky": ky,
                        "thu": base + i * 50,
                        "chi": base * 0.8 + i * 40,
                        "tam_ung": base * 0.1 + i * 5,
                        "don_vi_tinh": "triệu đồng",
                        "nguon": "TABMIS",
                    }
                )

    existing = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM curated.dm_ngan_sach
            WHERE don_vi_code = 'SO_TC'
              AND nguon = 'TABMIS'
            LIMIT 1
            """
        )
    ).first()

    if not existing:
        op.bulk_insert(dm_ngan_sach_table, seed_rows)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "dm_ngan_sach" not in inspector.get_table_names(schema="curated"):
        return

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(
            "dm_ngan_sach",
            schema="curated",
        )
    }

    if "ix_curated_dm_ngan_sach_ky" in existing_indexes:
        op.drop_index(
            "ix_curated_dm_ngan_sach_ky",
            table_name="dm_ngan_sach",
            schema="curated",
        )

    if "ix_curated_dm_ngan_sach_khoan_muc_code" in existing_indexes:
        op.drop_index(
            "ix_curated_dm_ngan_sach_khoan_muc_code",
            table_name="dm_ngan_sach",
            schema="curated",
        )

    if "ix_curated_dm_ngan_sach_don_vi_code" in existing_indexes:
        op.drop_index(
            "ix_curated_dm_ngan_sach_don_vi_code",
            table_name="dm_ngan_sach",
            schema="curated",
        )

    op.drop_table("dm_ngan_sach", schema="curated")