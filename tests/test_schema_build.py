"""An empty database reaches head by the migration chain (contract §2.7).

``monitorable-project.md`` §2.7 asks a service with a database for one
test that builds an **empty** database to head on real PostgreSQL.
Session 367 ruled that it applies here, scoped to the ``sysadmin``
schema, and this file is that test.

**It is not** ``test_schema_drift.py`` **and cannot be.**  That guard
diffs the *live* schema, which was built migration by migration over
months, so a chain that no longer runs from nothing — a migration
reading a table an earlier one never created, the estate's
``gpu_leases`` defect exactly — leaves it green.  Only a build from
empty sees that, and the build is the whole point.

The drive is the operator's: ``alembic upgrade head`` through the real
``alembic/env.py``, with ``get_config`` patched to a scratch URL because
``env.py`` reads no other source.  The service never migrates at
startup; it refuses unless at head, so the startup's half of §2.7 is
:func:`~sysadmin.core.schema_guard.schema_status` reading the scratch
database, and the head assertion goes through it rather than through a
query of its own.

Two choices in the harness are the opposite of the obvious one:

1. **The Alembic ``Config`` has no ini file.**  ``env.py`` calls
   ``fileConfig`` only when ``config_file_name`` is set, and
   ``fileConfig`` disables every logger already created, which would
   reach every later test in the run that asserts on a log line.
   ``script_location`` is all the upgrade needs.
2. **The scratch database is named per run and dropped ``WITH
   (FORCE)``.**  A fixed name left behind by a killed run would make the
   next one fail at ``CREATE DATABASE`` rather than at anything it tests.

Skips without PostgreSQL, as ``test_schema_drift.py`` does, so CI (no
PostgreSQL service) does not run it.
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, text

from alembic import command
from sysadmin.core.config import get_config
from sysadmin.core.schema_guard import ALEMBIC_DIR, SchemaStatus, packaged_head

ADMIN_URL = "postgresql+psycopg2://gaddi@localhost:5432/projects"


def _db_available() -> bool:
    try:
        engine = create_engine(ADMIN_URL, connect_args={"connect_timeout": 2})
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


@dataclass(frozen=True)
class Build:
    """What the scratch database looked like either side of the upgrade."""

    url: str
    before: SchemaStatus
    after: SchemaStatus


def _scratch_config(url: str):
    """The shipped config with only the database URL changed."""
    real = get_config()
    database = real.database.model_copy(update={"sync_url": url})
    return real.model_copy(update={"database": database})


def _diff(url: str, metadata) -> list:
    """Autogenerate's diff of *metadata* against the database at *url*.

    The same opts ``env.py`` splats into ``context.configure`` and the
    same ``search_path`` it sets, so this is the comparison
    ``test_schema_drift.py`` certifies, pointed at the build.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from sysadmin.metadata import COMPARISON_OPTS

    opts = dict(COMPARISON_OPTS)
    opts["target_metadata"] = metadata
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SET search_path TO public"))
            context = MigrationContext.configure(conn, opts=opts)
            return compare_metadata(context, metadata)
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def build() -> Iterator[Build]:
    """Create an empty database, upgrade it to head, and drop it after."""
    from sysadmin.core import config as config_module
    from sysadmin.core import schema_guard

    name = f"sysadmin_build_{uuid.uuid4().hex[:12]}"
    url = ADMIN_URL.rsplit("/", 1)[0] + f"/{name}"
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")

    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        scratch = _scratch_config(url)
        with pytest.MonkeyPatch.context() as mp:
            # env.py re-imports get_config from the module on every run;
            # schema_guard bound the name at import, so both are patched.
            mp.setattr(config_module, "get_config", lambda: scratch)
            mp.setattr(schema_guard, "get_config", lambda: scratch)

            before = schema_guard.schema_status()
            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", str(ALEMBIC_DIR))
            command.upgrade(alembic_cfg, "head")
            after = schema_guard.schema_status()

        yield Build(url=url, before=before, after=after)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="local postgres not reachable — the build needs real PostgreSQL",
)


@pytest.mark.premise
class TestThePremises:
    """A database at head is evidence only if it was empty first and is the one compared."""

    def test_the_database_started_with_no_revision(self, build):
        """Ordered first: a build that began at head proves nothing about the chain.

        ``schema_status`` reads ``current`` as ``None`` for a schema
        never migrated *and* for one it could not reach; the verdict
        tells them apart, and ``mismatch`` is the one that means looked
        and found nothing.
        """
        assert build.before.verdict == "mismatch", build.before.problem
        assert build.before.current is None

    def test_the_comparison_reaches_every_mapped_table(self, build):
        """A clean diff below means nothing if the comparison sees no table.

        Against an empty ``MetaData`` the same opts must propose dropping
        every mapped table the build created.  A blindfolded comparison
        (``FROZEN_TABLES`` grown, ``include_name`` refusing the schema)
        reports nothing here and nothing below.
        """
        from sysadmin.metadata import Base

        removed = {op[1].name for op in _diff(build.url, MetaData()) if op[0] == "remove_table"}
        mapped = {table.split(".")[-1] for table in Base.metadata.tables}
        assert mapped <= removed, (
            "these mapped tables are invisible to the comparison against the "
            f"build, so drift in them cannot be reported: {sorted(mapped - removed)}"
        )


def test_the_build_reaches_the_packaged_head(build):
    """Read by the startup's own check, so it is what the service would see."""
    assert build.after.ok, build.after.problem
    assert build.after.current == packaged_head()


def test_the_built_schema_matches_the_models(build):
    from sysadmin.metadata import Base

    diff = _diff(build.url, Base.metadata)
    assert diff == [], (
        "a database built from empty by the migration chain differs from the "
        f"models, so the chain and the models disagree.\nDiff:\n{diff}"
    )
