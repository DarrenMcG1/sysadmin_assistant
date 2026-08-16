"""Schema drift guard.

Asserts that Alembic autogenerate against the live sysadmin schema
produces an EMPTY diff — i.e. the SQLAlchemy models and the migrated
database have not drifted apart.

Connects to the real local postgres (peer auth). Skips gracefully when
the database is unreachable so CI without postgres does not fail.

The comparison itself is **not** configured here. It arrives whole from
``sysadmin.metadata.COMPARISON_OPTS``, the same object ``alembic/env.py``
splats into ``context.configure`` — so this guard certifies the migration
tool's actual comparison rather than a hand-copy of them that could be
weaker. It used to mirror them (`SNAG-DB-003`), and a mirror that had
lost an exclusion or a comparison flag would pass while blind. The one
thing still issued by hand is the search_path, which each caller owns
because ``env.py`` pairs it with DDL this test may not run.
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


@pytest.mark.skipif(
    not _db_available(),
    reason="local postgres (projects DB) not reachable — drift guard needs the real schema",
)
def test_models_match_migrated_schema():
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from sysadmin.metadata import COMPARISON_OPTS, Base

    engine = create_engine(SYNC_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SET search_path TO public"))
            context = MigrationContext.configure(conn, opts=dict(COMPARISON_OPTS))
            diff = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diff == [], (
        "Alembic autogenerate found schema drift between the models and the "
        f"migrated database — create a migration.\nDiff:\n{diff}"
    )
