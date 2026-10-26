# 迁移环境。只由 P3 一人执行迁移，其他人不要改本文件。
from __future__ import annotations

import contextlib
import importlib
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.db import Base

# 让 autogenerate 能看到全部模块的表定义。
# 新增模块时把模块名加进这个列表，否则迁移会漏表。
MODULE_NAMES = [
    "identity",
    "catalog",
    "routes",
    "moderation",
    "community",
    "planner",
    "media",
    "notifications",
    "audit",
]

for name in MODULE_NAMES:
    with contextlib.suppress(ModuleNotFoundError):
        importlib.import_module(f"app.modules.{name}.models")

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
