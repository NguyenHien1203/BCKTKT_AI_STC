"""UC-018: create dataset_catalog + critical_fields + dataset_schema_versions
tables (Định nghĩa tập dữ liệu của nguồn)

Ghi chú: tài liệu nghiệp vụ gốc (BCKTKT) mô tả lưu vào
"metadata.dataset_catalog" / "metadata.critical_fields", nhưng theo ADR-001
(ARCHITECTURE.md mục 7) mỗi service chỉ dùng 1 schema Postgres duy nhất —
với ingestion-service là `staging`. Tên bảng vẫn giữ đúng yêu cầu nghiệp vụ,
chỉ khác schema chứa (nhất quán với `sources`, `connectors`,
`source_connections` đã tạo ở các migration trước).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_catalog",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "data_source_id",
            sa.Integer(),
            sa.ForeignKey("staging.sources.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("schema_fields", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("primary_key", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "partition_strategy", sa.String(length=20), nullable=False, server_default="NONE"
        ),
        sa.Column("partition_column", sa.String(length=255), nullable=True),
        sa.Column("current_schema_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint(
            "data_source_id", "code", name="uq_dataset_catalog_source_code"
        ),
        schema="staging",
    )
    op.create_index(
        "ix_staging_dataset_catalog_data_source_id",
        "dataset_catalog",
        ["data_source_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_dataset_catalog_code", "dataset_catalog", ["code"], schema="staging"
    )

    op.create_table(
        "critical_fields",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("staging.dataset_catalog.id"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "dataset_id", "field_name", name="uq_critical_fields_dataset_field"
        ),
        schema="staging",
    )
    op.create_index(
        "ix_staging_critical_fields_dataset_id",
        "critical_fields",
        ["dataset_id"],
        schema="staging",
    )

    op.create_table(
        "dataset_schema_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("staging.dataset_catalog.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("registered_at", sa.String(length=40), nullable=False),
        sa.UniqueConstraint(
            "dataset_id", "version", name="uq_schema_versions_dataset_version"
        ),
        schema="staging",
    )
    op.create_index(
        "ix_staging_dataset_schema_versions_dataset_id",
        "dataset_schema_versions",
        ["dataset_id"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_dataset_schema_versions_dataset_id",
        table_name="dataset_schema_versions",
        schema="staging",
    )
    op.drop_table("dataset_schema_versions", schema="staging")

    op.drop_index(
        "ix_staging_critical_fields_dataset_id", table_name="critical_fields", schema="staging"
    )
    op.drop_table("critical_fields", schema="staging")

    op.drop_index(
        "ix_staging_dataset_catalog_code", table_name="dataset_catalog", schema="staging"
    )
    op.drop_index(
        "ix_staging_dataset_catalog_data_source_id",
        table_name="dataset_catalog",
        schema="staging",
    )
    op.drop_table("dataset_catalog", schema="staging")