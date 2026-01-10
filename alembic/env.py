from logging.config import fileConfig
from alembic import context

from db_handler.db.engine import sync_engine
from db_handler.db.models import Base

# Alembic Config object
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using synchronous engine."""


    with sync_engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=False,
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()