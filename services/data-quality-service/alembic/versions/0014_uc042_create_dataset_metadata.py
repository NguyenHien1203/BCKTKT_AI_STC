"""UC-042: create dataset_metadata + dataset_metadata_versions (Đăng ký
siêu dữ liệu tập dữ liệu)

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_metadata",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "sensitivity_level", sa.String(length=20), nullable=False, server_default="INTERNAL"
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_unique_constraint(
        "uq_curated_dataset_metadata_dataset_id",
        "dataset_metadata",
        ["dataset_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_dataset_metadata_dataset_id",
        "dataset_metadata",
        ["dataset_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_dataset_metadata_sensitivity_level",
        "dataset_metadata",
        ["sensitivity_level"],
        schema="curated",
    )

    op.create_table(
        "dataset_metadata_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_metadata_id",
            sa.Integer(),
            sa.ForeignKey("curated.dataset_metadata.id"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sensitivity_level", sa.String(length=20), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_dataset_metadata_versions_dataset_metadata_id",
        "dataset_metadata_versions",
        ["dataset_metadata_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_dataset_metadata_versions_dataset_id",
        "dataset_metadata_versions",
        ["dataset_id"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_dataset_metadata_versions_dataset_id",
        table_name="dataset_metadata_versions",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_dataset_metadata_versions_dataset_metadata_id",
        table_name="dataset_metadata_versions",
        schema="curated",
    )
    op.drop_table("dataset_metadata_versions", schema="curated")

    op.drop_index(
        "ix_curated_dataset_metadata_sensitivity_level",
        table_name="dataset_metadata",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_dataset_metadata_dataset_id",
        table_name="dataset_metadata",
        schema="curated",
    )
    op.drop_constraint(
        "uq_curated_dataset_metadata_dataset_id",
        "dataset_metadata",
        schema="curated",
        type_="unique",
    )
    op.drop_table("dataset_metadata", schema="curated")