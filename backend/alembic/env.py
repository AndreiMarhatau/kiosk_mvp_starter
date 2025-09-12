from __future__ import annotations
import os, sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---- Добавляем путь к "backend" и импортируем Base/модели ----
# env.py лежит в backend/alembic; поднимемся на один уровень к backend
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Теперь можем импортировать наш код
from app.db import Base  # <-- Declarative Base
import app.models  # noqa: F401  (важно импортировать, чтобы таблицы были зарегистрированы)

# ----------------------------------------------------------------

# это объект Alembic Config, доступ к значению sqlalchemy.url из alembic.ini
config = context.config

# настройка логгера
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# вот что нужно Alembic для автогенерации:
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Запуск миграций в оффлайн-режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,   # сравнивать типы
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Запуск миграций в онлайне (через Engine)."""
    configuration = config.get_section(config.config_ini_section)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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
