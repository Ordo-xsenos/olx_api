from logging.config import fileConfig
from alembic import context
import logging

from db_handler.db.engine import sync_engine
from db_handler.db.models import Base

# Объект конфигурации Alembic
config = context.config

# Логирование
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
else:
    logging.basicConfig()

logger = logging.getLogger('alembic.env')

# Метаданные для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запускает миграции в офлайн-режиме (без подключения к БД)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запускает миграции в онлайн-режиме через синхронный движок."""
    with sync_engine.connect() as connection:
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
