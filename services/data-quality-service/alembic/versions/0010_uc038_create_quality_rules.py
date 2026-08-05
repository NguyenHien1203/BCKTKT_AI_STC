"""UC-038: create quality_rules + quality_rule_versions +
quality_score_configs + quality_score_config_versions (Quản lý quy tắc
kiểm tra chất lượng)

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("field_names_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rule_type", sa.String(length=20), nullable=False),
        sa.Column("params_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_rules_dataset_id", "quality_rules", ["dataset_id"], schema="curated"
    )
    op.create_index(
        "ix_curated_quality_rules_rule_type", "quality_rules", ["rule_type"], schema="curated"
    )
    op.create_index(
        "ix_curated_quality_rules_is_active", "quality_rules", ["is_active"], schema="curated"
    )

    op.create_table(
        "quality_rule_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "rule_id",
            sa.Integer(),
            sa.ForeignKey("curated.quality_rules.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("field_names_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rule_type", sa.String(length=20), nullable=False),
        sa.Column("params_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_rule_versions_rule_id",
        "quality_rule_versions",
        ["rule_id"],
        schema="curated",
    )

    op.create_table(
        "quality_score_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("pass_threshold", sa.Float(), nullable=False),
        sa.Column("rule_type_weights_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_unique_constraint(
        "uq_curated_quality_score_configs_dataset_id",
        "quality_score_configs",
        ["dataset_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_score_configs_dataset_id",
        "quality_score_configs",
        ["dataset_id"],
        schema="curated",
    )

    op.create_table(
        "quality_score_config_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "config_id",
            sa.Integer(),
            sa.ForeignKey("curated.quality_score_configs.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("pass_threshold", sa.Float(), nullable=False),
        sa.Column("rule_type_weights_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_score_config_versions_config_id",
        "quality_score_config_versions",
        ["config_id"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_quality_score_config_versions_config_id",
        table_name="quality_score_config_versions",
        schema="curated",
    )
    op.drop_table("quality_score_config_versions", schema="curated")

    op.drop_index(
        "ix_curated_quality_score_configs_dataset_id",
        table_name="quality_score_configs",
        schema="curated",
    )
    op.drop_constraint(
        "uq_curated_quality_score_configs_dataset_id",
        "quality_score_configs",
        schema="curated",
        type_="unique",
    )
    op.drop_table("quality_score_configs", schema="curated")

    op.drop_index(
        "ix_curated_quality_rule_versions_rule_id",
        table_name="quality_rule_versions",
        schema="curated",
    )
    op.drop_table("quality_rule_versions", schema="curated")

    op.drop_index(
        "ix_curated_quality_rules_is_active", table_name="quality_rules", schema="curated"
    )
    op.drop_index(
        "ix_curated_quality_rules_rule_type", table_name="quality_rules", schema="curated"
    )
    op.drop_index(
        "ix_curated_quality_rules_dataset_id", table_name="quality_rules", schema="curated"
    )
    op.drop_table("quality_rules", schema="curated")