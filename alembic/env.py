from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from common_core.db import Base

# Import models based on MIGRATION_TARGET environment variable
# This prevents table name conflicts when running migrations for a specific target
_migration_target = os.environ.get("MIGRATION_TARGET", "plant").lower()

if _migration_target == "hq":
    from apps.hq_backend import models as hq_models  # noqa: F401
else:
    # Default to plant models
    from apps.plant_backend import models as plant_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    # Prefer explicit SQLALCHEMY_DATABASE_URL, otherwise fall back to env used by services.
    url = os.environ.get("SQLALCHEMY_DATABASE_URL")
    if url:
        return url
    # Plant/HQ services already expose unified DATABASE_URLs via env in docker-compose.
    return os.environ.get("DATABASE_URL", "")


def run_migrations_offline() -> None:
    url = get_url()
    if not url:
        raise RuntimeError("DATABASE_URL / SQLALCHEMY_DATABASE_URL must be set for Alembic migrations")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    if not url:
        raise RuntimeError("DATABASE_URL / SQLALCHEMY_DATABASE_URL must be set for Alembic migrations")

    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
