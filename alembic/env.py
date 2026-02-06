"""Alembic environment configuration for the sysadmin schema.

Uses a sync engine (psycopg2) for migrations. The search_path is set
to 'sysadmin,public' so all operations target the correct schema.
The version table is stored in the sysadmin schema to avoid collision
with other services (e.g. PersonalAssistant) sharing the same database.
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging.config import fileConfig

from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Connection

from alembic import context

# Import all models so Alembic can detect them for autogenerate
from sysadmin.models import Base  # noqa: F401
from sysadmin.models import (  # noqa: F401
    AgentRun,
    Alert,
    FilesystemAudit,
    LogEntry,
    LogSummary,
    ProjectSnapshot,
    ResourceSnapshot,
    RetentionConfig,
    ServiceHealth,
)
from sysadmin.config import get_config

# Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Get the sync database URL from application config."""
    app_config = get_config()
    return app_config.database.sync_url


def include_object(object, name, type_, reflected, compare_to):
    """Only include objects from the sysadmin schema in autogenerate."""
    if type_ == "table":
        # Skip tables not in our schema
        schema = getattr(object, "schema", None)
        if schema and schema != "sysadmin":
            return False
        # Skip alembic's own version table
        if name == "alembic_version":
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in offline mode (generates SQL scripts)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="sysadmin",
        include_schemas=True,
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection."""
    # Ensure sysadmin schema exists before running migrations
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS sysadmin"))
    connection.execute(text("SET search_path TO sysadmin, public"))
    connection.commit()

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema="sysadmin",
        include_schemas=True,
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode with a sync engine."""
    url = get_url()
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
