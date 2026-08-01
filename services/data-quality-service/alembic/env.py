import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.db.session import Base  # noqa: E402
from app.infrastructure.db import models  # noqa: E402,F401

config = context.config

database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Nhiều service dùng chung 1 database Postgres (khác nhau bởi schema — xem
# ARCHITECTURE.md mục 2), nhưng bảng theo dõi phiên bản migration mặc định
# của Alembic (`alembic_version`) lại nằm ở schema `public` dùng chung cho
# TẤT CẢ service. Nếu không đặt tên riêng, data-quality-service sẽ đọc
# nhầm revision đã stamp bởi service khác -> lỗi "Can't locate revision
# identified by '...'". Mỗi service phải có version_table riêng (cùng quy
# ước với ingestion-service: "alembic_version_ingestion").
VERSION_TABLE = "alembic_version_data_quality"


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()