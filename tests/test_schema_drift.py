"""Schema drift guard.

Asserts that Alembic autogenerate against the live sysadmin schema
produces an EMPTY diff — i.e. the SQLAlchemy models and the migrated
database have not drifted apart.

Connects to the real local postgres (peer auth). Skips gracefully when
the database is unreachable so CI without postgres does not fail.
Mirrors the autogenerate configuration in alembic/env.py.
"""

import pytest
from sqlalchemy import create_engine, text

SYNC_URL = "postgresql+psycopg2://gaddi@localhost:5432/projects"


def _db_available() -> bool:
    try:
        engine = create_engine(SYNC_URL, connect_args={"connect_timeout": 2})
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


def _include_object(object, name, type_, reflected, compare_to):
    """Mirror alembic/env.py: only sysadmin-schema tables, skip version table."""
    if type_ == "table":
        schema = getattr(object, "schema", None)
        if schema != "sysadmin":
            return False
        if name == "alembic_version":
            return False
    return True


def _include_name(name, type_, parent_names):
    """Mirror alembic/env.py: only reflect the sysadmin schema."""
    if type_ == "schema":
        return name == "sysadmin"
    return True


@pytest.mark.skipif(
    not _db_available(),
    reason="local postgres (projects DB) not reachable — drift guard needs the real schema",
)
def test_models_match_migrated_schema():
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from sysadmin.models import Base

    engine = create_engine(SYNC_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SET search_path TO public"))
            context = MigrationContext.configure(
                conn,
                opts={
                    "compare_type": True,
                    "include_schemas": True,
                    "include_object": _include_object,
                    "include_name": _include_name,
                    "version_table_schema": "sysadmin",
                    "target_metadata": Base.metadata,
                },
            )
            diff = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diff == [], (
        "Alembic autogenerate found schema drift between the models and the "
        f"migrated database — create a migration.\nDiff:\n{diff}"
    )
