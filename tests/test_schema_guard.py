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

import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine

from sysadmin.core.config import REPO_ROOT
from sysadmin.core.schema_guard import (
    ALEMBIC_DIR,
    EXIT_STATUS,
    VERSION_TABLE,
    SchemaRevisionError,
    SchemaStatus,
    _interpret_version_rows,
    describe_mismatch,
    live_revision,
    live_revision_sync,
    main,
    packaged_head,
    schema_status,
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


# ── SNAG-DB-005 ─────────────────────────────────────────────────────────
#
# The guard above worked and the outage happened anyway: migration 013 was
# written, committed and never applied, the daemon was restarted to serve a
# new route, this guard refused, and `sysadmin.service` stayed dead for 23
# hours.  Two things were missing — the comparison was not available
# *before* the restart, and the failure named no remedy.
#
# These tests pin the second caller's three rules: that the rules are
# shared and only the connection is copied, that `unknown` is a third
# outcome rather than a flavour of failure, and that the sync path fails
# soft where the lifespan fails hard.

def _db_available() -> bool:
    """Same shape as tests/test_schema_drift.py, for the same reason."""
    try:
        from sysadmin.core.config import get_config

        engine = create_engine(get_config().database.sync_url)
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


class TestDescribeMismatch:
    """The one statement of what a mismatch is and what to say about it."""

    def test_agreement_is_not_a_problem(self):
        assert describe_mismatch("013", "013") is None

    def test_behind_names_both_revisions_and_the_remedy(self):
        problem = describe_mismatch("013", "012")
        assert problem is not None
        assert "012" in problem and "013" in problem
        assert "alembic upgrade head" in problem

    def test_never_migrated_is_its_own_message(self):
        """Distinct from a wrong revision — rule 3 of the module docstring."""
        never = describe_mismatch("013", None)
        wrong = describe_mismatch("013", "012")
        assert never is not None and wrong is not None
        assert "never been migrated" in never
        assert never != wrong

    def test_the_lifespan_raises_exactly_this_text(self):
        """Falsify by wording the exception separately: this must break.

        `verify_schema_revision` and `schema_status` are read by the same
        operator on two occasions — a startup failure and a blocked
        commit — and two statements of one fault drift.
        """
        import inspect

        from sysadmin.core import schema_guard

        source = inspect.getsource(schema_guard.verify_schema_revision)
        assert "describe_mismatch(head, current)" in source
        assert "SNAG-DB-001" not in source, (
            "verify_schema_revision is building its own message again — "
            "the wording belongs to describe_mismatch"
        )


class TestInterpretVersionRows:
    def test_no_rows_is_never_migrated(self):
        assert _interpret_version_rows([], "sysadmin") is None

    def test_one_row_is_the_revision(self):
        assert _interpret_version_rows(["013"], "sysadmin") == "013"

    def test_two_rows_is_a_branched_schema(self):
        with pytest.raises(SchemaRevisionError, match="2 rows"):
            _interpret_version_rows(["012", "013"], "sysadmin")

    def test_the_message_is_schema_qualified(self):
        """Rule 2: another application's alembic_version lives in public."""
        with pytest.raises(SchemaRevisionError, match=f"sysadmin.{VERSION_TABLE}"):
            _interpret_version_rows(["a", "b"], "sysadmin")


class TestSchemaStatus:
    """Three outcomes, and `unknown` is not a flavour of `mismatch`."""

    def test_match(self):
        with (
            patch("sysadmin.core.schema_guard.packaged_head", return_value="013"),
            patch("sysadmin.core.schema_guard.live_revision_sync", return_value="013"),
        ):
            status = schema_status()
        assert status == SchemaStatus("match", "013", "013", None)
        assert status.ok

    def test_mismatch_carries_both_revisions(self):
        with (
            patch("sysadmin.core.schema_guard.packaged_head", return_value="013"),
            patch("sysadmin.core.schema_guard.live_revision_sync", return_value="012"),
        ):
            status = schema_status()
        assert status.verdict == "mismatch"
        assert (status.head, status.current) == ("013", "012")
        assert status.problem == describe_mismatch("013", "012")
        assert not status.ok

    def test_unreachable_database_is_unknown_not_mismatch(self):
        """The rule the whole dataclass exists for.

        A driver error means nothing was learned about the schema.
        Reporting it as `mismatch` would block every commit on this box
        whenever PostgreSQL restarts; reporting it as `match` is the
        silent failure the guard family exists to remove.
        """
        with (
            patch("sysadmin.core.schema_guard.packaged_head", return_value="013"),
            patch(
                "sysadmin.core.schema_guard.live_revision_sync",
                side_effect=OSError("connection refused"),
            ),
        ):
            status = schema_status()
        assert status.verdict == "unknown"
        assert status.current is None
        assert status.head == "013"
        assert "connection refused" in (status.problem or "")
        assert not status.ok, "unknown must never read as ok"

    def test_unreadable_scripts_are_unknown(self):
        with patch(
            "sysadmin.core.schema_guard.packaged_head",
            side_effect=SchemaRevisionError("cannot read migration scripts"),
        ):
            status = schema_status()
        assert status.verdict == "unknown"
        assert status.head is None

    def test_branched_live_history_is_unknown(self):
        with (
            patch("sysadmin.core.schema_guard.packaged_head", return_value="013"),
            patch(
                "sysadmin.core.schema_guard.live_revision_sync",
                side_effect=SchemaRevisionError("holds 2 rows"),
            ),
        ):
            assert schema_status().verdict == "unknown"

    def test_never_migrated_is_a_mismatch_not_an_unknown(self):
        """`None` from the reader is an answer, not a failure to read."""
        with (
            patch("sysadmin.core.schema_guard.packaged_head", return_value="013"),
            patch("sysadmin.core.schema_guard.live_revision_sync", return_value=None),
        ):
            status = schema_status()
        assert status.verdict == "mismatch"
        assert "never been migrated" in (status.problem or "")


class TestExitStatus:
    def test_every_verdict_has_a_status(self):
        """Derived from the verdicts, never written beside them."""
        from typing import get_args

        from sysadmin.core.schema_guard import SchemaVerdict

        assert set(EXIT_STATUS) == set(get_args(SchemaVerdict))

    def test_the_three_are_distinct(self):
        """2 must not collapse into 1: the hook treats them differently."""
        assert len(set(EXIT_STATUS.values())) == 3
        assert EXIT_STATUS["match"] == 0


class TestMain:
    def _run(self, status: SchemaStatus, argv: list[str] | None = None):
        with patch("sysadmin.core.schema_guard.schema_status", return_value=status):
            return main(argv or [])

    def test_match_exits_zero(self, capsys):
        assert self._run(SchemaStatus("match", "013", "013", None)) == 0
        assert "013" in capsys.readouterr().out

    def test_quiet_silences_only_the_healthy_line(self, capsys):
        assert self._run(SchemaStatus("match", "013", "013", None), ["--quiet"]) == 0
        assert capsys.readouterr().out == ""

    def test_mismatch_exits_one_and_prints_even_when_quiet(self, capsys):
        status = SchemaStatus("mismatch", "013", "012", "behind — run alembic")
        assert self._run(status, ["--quiet"]) == 1
        assert "behind — run alembic" in capsys.readouterr().err

    def test_unknown_exits_two_and_prints_even_when_quiet(self, capsys):
        status = SchemaStatus("unknown", "013", None, "database unreachable")
        assert self._run(status, ["--quiet"]) == 2
        assert "database unreachable" in capsys.readouterr().err

    def test_faults_go_to_stderr(self, capsys):
        """So a shell caller can capture the reason without parsing stdout."""
        status = SchemaStatus("mismatch", "013", "012", "behind")
        self._run(status)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "behind" in captured.err


@pytest.mark.skipif(
    not _db_available(),
    reason="local postgres (projects DB) not reachable — the two readers "
    "can only be compared against a real alembic_version",
)
class TestTheTwoReadersAgree:
    """The guard against the one duplication this design accepts.

    `live_revision` runs on the application's async engine and
    `live_revision_sync` on the sync engine that exists for Alembic,
    because both new callers run outside a running application.  What
    must never diverge is the answer.  Asserting each side separately
    would pin the copy; this drives both against the same live table.
    """

    @pytest.mark.asyncio
    async def test_same_revision_from_both_engines(self):
        from sysadmin.core.database import create_engine_and_session, dispose_engine

        sync_answer = live_revision_sync()
        await create_engine_and_session()
        try:
            async_answer = await live_revision()
        finally:
            await dispose_engine()

        assert async_answer == sync_answer

    def test_the_sync_reader_agrees_with_alembic_itself(self):
        """`alembic current` is the command the guard measures against."""
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        current = live_revision_sync()
        assert current is not None
        assert current in result.stdout


class TestCallersAreWired:
    """Planned and unwired is the failure this family keeps producing.

    A check nothing calls is `SNAG-CFG-001`'s shape — parsed by pydantic
    and read by nothing.  These assert the three shell callers still
    reach the console script, so removing a call is a red test rather
    than a silent loss of the guard.
    """

    WRAPPER = "check-migrations.sh"

    @pytest.mark.parametrize(
        "script",
        ["claude-precommit.sh", "claude-postflight.sh", "notify-unit-failed.sh"],
    )
    def test_script_calls_the_wrapper(self, script):
        text = (REPO_ROOT / "scripts" / script).read_text()
        assert self.WRAPPER in text, f"scripts/{script} no longer checks the schema"

    def test_the_wrapper_is_executable(self):
        assert (REPO_ROOT / "scripts" / self.WRAPPER).stat().st_mode & 0o111

    def test_the_wrapper_names_the_console_script(self):
        text = (REPO_ROOT / "scripts" / self.WRAPPER).read_text()
        assert "sysadmin-check-schema" in text

    def test_the_console_script_is_declared(self):
        """Wired in shell and undeclared in pyproject is a silent exit 2."""
        pyproject = (REPO_ROOT / "pyproject.toml").read_text()
        assert 'sysadmin-check-schema = "sysadmin.core.schema_guard:main"' in pyproject

    def test_the_wrapper_never_applies_a_migration(self):
        """The one option the snag rules out by name.

        Applying unattended is how a bad migration reaches production
        with nobody watching.  This is the only place a future edit
        would put it.
        """
        text = (REPO_ROOT / "scripts" / self.WRAPPER).read_text()
        code = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        )
        assert "upgrade" not in code

    def test_precommit_blocks_on_one_and_not_on_two(self):
        """Exit 2 must warn, not block — otherwise --no-verify becomes habit."""
        text = (REPO_ROOT / "scripts" / "claude-precommit.sh").read_text()
        block = text.split("# Check 2:")[1].split("# Check 3:")[0]
        assert 'SCHEMA_STATUS" -eq 1' in block
        assert "exit 1" in block
        # the else arm (status 2) must not exit
        else_arm = block.split("else")[-1]
        assert "exit" not in else_arm
