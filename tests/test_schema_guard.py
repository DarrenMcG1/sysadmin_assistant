"""The startup schema-revision check (SNAG-DB-001, gap 1).

Migration 009 was written, committed and never applied; two minutes
later the daemon restarted and began writing a status value the database
rejected, and ``service_health`` took no rows for 39 hours.  Nothing
applies migrations here and nothing checked — ``verify_connection``
proves the database answers, and the drift guard skips
``alembic_version`` and does not diff CHECK constraints.

These tests pin the three things that make the guard worth having: that
it reads the head the same way ``alembic upgrade head`` does, that every
way of not-knowing fails **closed**, and that the failure is
distinguishable from the others by its message.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.schema_guard import (
    ALEMBIC_DIR,
    VERSION_TABLE,
    SchemaRevisionError,
    packaged_head,
    verify_schema_revision,
)


class TestPackagedHead:
    def test_reads_this_checkout_s_head(self):
        """Not a fixture — the real migration directory.

        A mocked head would pass while the guard pointed at nothing,
        which is the failure mode being defended against.
        """
        head = packaged_head()
        assert head
        assert (ALEMBIC_DIR / "versions").is_dir()

    def test_it_agrees_with_alembic_s_own_script_directory(self):
        """The guard must not be a second implementation of the graph."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config()
        cfg.set_main_option("script_location", str(ALEMBIC_DIR))
        assert packaged_head() == ScriptDirectory.from_config(cfg).get_heads()[0]

    def test_an_unreadable_script_directory_fails_closed(self, tmp_path):
        """"The guard could not run" must not read as "the schema is fine"."""
        with pytest.raises(SchemaRevisionError, match="cannot read migration scripts"):
            packaged_head(tmp_path / "definitely-not-here")

    def test_a_branched_history_is_refused(self):
        """`alembic upgrade head` cannot run against two heads.

        A service that started anyway would be permanently unable to
        migrate and would never say so.
        """
        fake = MagicMock()
        fake.get_heads.return_value = ("aaa", "bbb")
        with patch("sysadmin.core.schema_guard.ScriptDirectory") as sd:
            sd.from_config.return_value = fake
            with pytest.raises(SchemaRevisionError, match="2 heads"):
                packaged_head()

    def test_no_heads_at_all_is_also_refused(self):
        fake = MagicMock()
        fake.get_heads.return_value = ()
        with patch("sysadmin.core.schema_guard.ScriptDirectory") as sd:
            sd.from_config.return_value = fake
            with pytest.raises(SchemaRevisionError, match="0 heads"):
                packaged_head()


def _patch(head: str, live: str | None):
    return (
        patch("sysadmin.core.schema_guard.packaged_head", return_value=head),
        patch("sysadmin.core.schema_guard.live_revision",
              new_callable=AsyncMock, return_value=live),
    )


class TestVerifySchemaRevision:
    @pytest.mark.asyncio
    async def test_matching_revisions_pass_and_return_it(self):
        head_p, live_p = _patch("011", "011")
        with head_p, live_p:
            assert await verify_schema_revision() == "011"

    @pytest.mark.asyncio
    async def test_a_behind_database_refuses_and_names_both_revisions(self):
        """The exact SNAG-DB-001 condition: live 008, packaged 009."""
        head_p, live_p = _patch("009", "008")
        with head_p, live_p, pytest.raises(SchemaRevisionError) as exc:
            await verify_schema_revision()

        message = str(exc.value)
        assert "008" in message and "009" in message
        assert "alembic upgrade head" in message

    @pytest.mark.asyncio
    async def test_an_ahead_database_is_also_refused(self):
        """Code older than the schema is a mismatch in the other direction.

        A rollback that redeployed the previous release would otherwise
        run against columns and constraints it does not know about.
        """
        head_p, live_p = _patch("009", "011")
        with head_p, live_p, pytest.raises(SchemaRevisionError):
            await verify_schema_revision()

    @pytest.mark.asyncio
    async def test_an_unmigrated_database_gets_its_own_message(self):
        """Distinct from a mismatch — nobody has ever run a migration."""
        head_p, live_p = _patch("011", None)
        with head_p, live_p, pytest.raises(SchemaRevisionError,
                                           match="never been migrated"):
            await verify_schema_revision()

    @pytest.mark.asyncio
    async def test_an_unreadable_head_propagates_rather_than_passing(self):
        with patch("sysadmin.core.schema_guard.packaged_head",
                   side_effect=SchemaRevisionError("no scripts")):
            with pytest.raises(SchemaRevisionError):
                await verify_schema_revision()

    def test_the_error_is_a_runtime_error(self):
        """An uncaught escape from the lifespan must still stop startup."""
        assert issubclass(SchemaRevisionError, RuntimeError)


class TestStartupWiring:
    def test_the_lifespan_calls_it_and_does_not_swallow_it(self):
        """Deliberately un-``try``ed, unlike the unit-failure resolve.

        A stale alert row is worth less than a boot, so that one is
        caught. A schema mismatch is the opposite: serving against it is
        what cost 39 hours, and the unit entering ``failed`` is how
        ``sysadmin-failed.service`` gets to announce it.
        """
        source = Path("sysadmin/main.py").read_text()
        assert "await verify_schema_revision()" in source

        # Indentation, not a grep for "try:" — the first version of this
        # assertion searched the preceding text and matched the *comment*
        # explaining why there is no try, which is a test that passes or
        # fails on prose. The call sits at the lifespan's own body level;
        # wrapping it in anything would indent it further.
        call_lines = [
            line for line in source.splitlines()
            if line.strip() == "await verify_schema_revision()"
        ]
        assert call_lines == ["    await verify_schema_revision()"], (
            "verify_schema_revision is nested inside a block — refusing "
            f"to start is the point. Found: {call_lines!r}"
        )

    def test_it_runs_after_the_connection_is_verified(self):
        """"Does it answer" and "is it the right schema" are two questions.

        The second needs a connection, so the order is not cosmetic.
        """
        source = Path("sysadmin/main.py").read_text()
        assert source.index("await verify_connection()") < source.index(
            "await verify_schema_revision()"
        )


class TestVersionTableLookup:
    def test_the_table_name_is_named_once(self):
        """Greppable against the drift guard, which skips it by name."""
        assert VERSION_TABLE == "alembic_version"

    def test_the_query_is_schema_qualified(self):
        """The ``projects`` DB holds another app's alembic_version.

        Resolving through ``search_path`` could compare this code
        against a stranger's revision and pass.
        """
        source = Path("sysadmin/core/schema_guard.py").read_text()
        assert "{schema}.{VERSION_TABLE}" in source
        assert "database.schema_" in source
