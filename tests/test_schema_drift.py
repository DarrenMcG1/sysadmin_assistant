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

**The verdict is an absence, so it carries a witness** (Session 132).
This file's whole output is ``diff == []``, and a comparison that
examined *nothing* returns exactly that — measured rather than reasoned
about: with ``FROZEN_TABLES`` widened to cover all thirteen mapped
tables, the blindfold :data:`~sysadmin.metadata.FROZEN_TABLES`' own
docstring warns about, ``compare_metadata`` returns ``[]``, byte-identical
to a clean schema.  So the guard could certify a comparison it was no
longer making, which is ``ports_checked``'s rule arriving in the one test
that stands between the models and the migrations.

:class:`TestThePremises` is the discriminating witness, and the shape is
the founding argument read backwards.  ``FROZEN_TABLES`` fails *silently*
where a missing exclusion in ``env.py`` fails loudly, so the direction
this file cannot see for itself is exactly the direction it must be told
about.  The same live connection and the same opts are pointed at an
**empty** ``MetaData``: that must report every live table as
``remove_table`` — thirteen of them today — and under the blindfold it
reports nothing at all, which is the difference the verdict below cannot
express.
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


def _diff(target=None):
    """Autogenerate's diff of *target* against the live schema.

    One statement of the drive, because the witness and the verdict must
    differ in the *metadata* alone — a witness issuing its own connection
    or its own opts would be a second comparison, free to disagree with
    the one being certified.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from sysadmin.metadata import COMPARISON_OPTS, Base

    metadata = Base.metadata if target is None else target
    opts = dict(COMPARISON_OPTS)
    opts["target_metadata"] = metadata

    engine = create_engine(SYNC_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SET search_path TO public"))
            context = MigrationContext.configure(conn, opts=opts)
            return compare_metadata(context, metadata)
    finally:
        engine.dispose()


@pytest.mark.skipif(
    not _db_available(),
    reason="local postgres (projects DB) not reachable — drift guard needs the real schema",
)
@pytest.mark.premise
class TestThePremises:
    """A clean diff is evidence only if this comparison can still see the schema."""

    def test_the_comparison_still_reaches_the_live_tables(self):
        """Ordered first, so a failure names the blindfold and not the models.

        Against an empty ``MetaData`` the same opts must propose dropping
        every live table.  A blindfolded comparison — ``FROZEN_TABLES``
        grown, ``include_object`` narrowed, ``include_name`` refusing the
        schema — reports nothing here **and** nothing below, which is the
        state the verdict cannot distinguish from health.
        """
        from sqlalchemy import MetaData

        removed = sorted(
            op[1].name for op in _diff(MetaData()) if op[0] == "remove_table"
        )
        assert removed, (
            "autogenerate proposes dropping no live table against an empty "
            "metadata, so it is not comparing this schema at all and a clean "
            "diff below would mean nothing"
        )

    def test_every_mapped_table_is_one_of_them(self):
        """The finer half: reaching *a* table is not reaching *ours*.

        The witness above holds while a single table remains visible, so
        thirteen mapped tables and one admitted one would pass it and
        leave twelve uncompared.  ``sysadmin.metadata`` owns the set, so
        it is read rather than re-typed.
        """
        from sqlalchemy import MetaData

        from sysadmin.metadata import Base

        removed = {op[1].name for op in _diff(MetaData()) if op[0] == "remove_table"}
        mapped = {table.split(".")[-1] for table in Base.metadata.tables}
        assert mapped <= removed, (
            "these mapped tables are invisible to the comparison, so drift in "
            f"them cannot be reported: {sorted(mapped - removed)}"
        )


@pytest.mark.skipif(
    not _db_available(),
    reason="local postgres (projects DB) not reachable — drift guard needs the real schema",
)
def test_models_match_migrated_schema():
    diff = _diff()

    assert diff == [], (
        "Alembic autogenerate found schema drift between the models and the "
        f"migrated database — create a migration.\nDiff:\n{diff}"
    )
