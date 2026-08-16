"""Alembic environment configuration for the sysadmin schema.

Uses a sync engine (psycopg2) for migrations. The version table is
stored in the sysadmin schema to avoid collision with other services
(e.g. PersonalAssistant) sharing the same database.

**What autogenerate compares is not decided here.** It lives in
``sysadmin.metadata.COMPARISON_OPTS`` — the exclusions, the schema
filter and the comparison flags — because ``tests/test_schema_drift.py``
certifies this configuration and a second copy of it is `SNAG-DB-003`:
an exclusion present only in the test leaves that guard green while this
file goes on proposing ``op.drop_table`` for a live table. Importing the
module is also what makes ``Base.metadata`` complete, so the models are
detected by the same import that supplies the rules.

What stays here is connection setup — the URL, the schema creation and
the search_path — which the guard cannot share because it may not issue
DDL, and whose drift fails loudly rather than silently.
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

# Importing this module imports every model (completing Base.metadata)
# and carries the one copy of the autogenerate comparison rules.
from sysadmin.metadata import COMPARISON_OPTS

# Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> str:
    """Get the sync database URL from application config."""
    app_config = get_config()
    return app_config.database.sync_url


def run_migrations_offline() -> None:
    """Run migrations in offline mode (generates SQL scripts)."""
    url = get_url()
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **COMPARISON_OPTS,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection."""
    # Ensure sysadmin schema exists before running migrations.
    # search_path stays on public so sysadmin tables reflect under their
    # explicit schema name during autogenerate (see
    # sysadmin.metadata.include_name). tests/test_schema_drift.py issues
    # the same SET for the same reason, and deliberately does not share
    # it: this half is DDL the guard must never run.
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS sysadmin"))
    connection.execute(text("SET search_path TO public"))
    connection.commit()

    context.configure(
        connection=connection,
        **COMPARISON_OPTS,
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
