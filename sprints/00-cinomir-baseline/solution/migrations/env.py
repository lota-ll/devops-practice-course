"""Alembic працює синхронно. psycopg 3 приймає той самий URL postgresql+psycopg:// і в sync."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from cinomir import models  # noqa: F401  (реєструє таблиці в Base.metadata)
from cinomir.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

url = os.environ.get("DATABASE_URL", "postgresql+psycopg://cinomir:cinomir@localhost:5432/cinomir")
# Тести використовують sqlite+aiosqlite — для Alembic потрібен синхронний драйвер
config.set_main_option("sqlalchemy.url", url.replace("+aiosqlite", ""))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql` — показати SQL без підключення до БД."""
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
