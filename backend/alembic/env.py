from __future__ import with_statement
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# import your model's MetaData object here
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.db import Base
from app.config import settings

target_metadata = Base.metadata


def _get_db_url():
    # Priority: explicit env var DATABASE_URL > settings (which itself reads ENV_FILE)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    # fallback to pydantic settings
    return getattr(settings, "DATABASE_URL", None)


def run_migrations_offline():
    url = _get_db_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured for offline migrations")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    db_url = _get_db_url()
    if not db_url:
        raise RuntimeError("DATABASE_URL is not configured for online migrations")

    connectable = engine_from_config(
        {"sqlalchemy.url": db_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
