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
from sysadmin.core.config import get_config

# Import all models so Alembic can detect them for autogenerate
from sysadmin.metadata import Base

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
        if schema != "sysadmin":
            return False
        # Skip alembic's own version table
        if name == "alembic_version":
            return False
    return True


def include_name(name, type_, parent_names):
    """Restrict schema reflection to the sysadmin schema.

    The models' metadata carries an explicit ``schema="sysadmin"``, so
    autogenerate must reflect sysadmin tables under that explicit name.
    Without this (and with search_path pointed at sysadmin), the same
    tables were reflected twice — once as ``sysadmin.x`` and once as
    default-schema ``x`` — producing phantom add/remove diffs.
    """
    if type_ == "schema":
        return name == "sysadmin"
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
        include_name=include_name,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection."""
    # Ensure sysadmin schema exists before running migrations.
    # search_path stays on public so sysadmin tables reflect under their
    # explicit schema name during autogenerate (see include_name).
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS sysadmin"))
    connection.execute(text("SET search_path TO public"))
    connection.commit()

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema="sysadmin",
        include_schemas=True,
        include_object=include_object,
        include_name=include_name,
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
