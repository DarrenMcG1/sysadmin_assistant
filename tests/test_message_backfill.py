"""``SNAG-LOG-008`` — repairing rows a late ``format: json`` declaration froze.

The pure half.  The database half is
``tests/test_message_backfill_live.py``, driven against real rows in a
rolled-back transaction, because this module's central claim is about
what a *stored* row holds and a fake answers that from whatever the test
put in it.

Rule 1 of :mod:`sysadmin.monitor.message_backfill` is a **provenance**
claim and is asserted as one.  Once rule 2's witness has passed, the
record's ``MESSAGE`` and the stored ``message`` are byte-equal by
definition, so a derivation from ``raw_line`` and one from ``message``
produce the identical string and no behavioural test can separate them.
Asserting a value where the claim is about provenance is the shape this
repository has now shipped four times (``SERVICES_SKIPPED is SKIPPED``,
the two Session 59 guards, ``EXPIRY_FORMAT``), so it is an ``ast`` sweep.
"""

import ast
import inspect
from pathlib import Path
from uuid import uuid4

import pytest

from sysadmin.core.config import LogSource
from sysadmin.monitor import message_backfill
from sysadmin.monitor.message_backfill import (
    BACKFILL_FORMAT,
    BackfillReport,
    FrozenRow,
    json_declared_sources,
    never_unwrapped,
    record_message,
    render,
)

MODULE_PATH = Path(message_backfill.__file__)


def journal_record(message: str, **extra: str) -> str:
    """One journalctl ``-o json`` record, as ``raw_line`` stores it."""
    import json

    return json.dumps({
        "__CURSOR": "s=abc;i=1",
        "__REALTIME_TIMESTAMP": "1787418616000000",
        "PRIORITY": "4",
        "_PID": "2511314",
        "MESSAGE": message,
        **extra,
    })


ENVELOPE = '{"timestamp": "2026-08-17 14:12:04,508", "level": "WARNING", ' \
           '"logger": "sysadmin.core.agent", "message": "alert_raised"}'


class _Config:
    """The one attribute :func:`json_declared_sources` reads."""

    def __init__(self, *sources: LogSource) -> None:
        self.sources = list(sources)


class TestTheWitness:
    """Rule 2 — ``raw_line`` says whether anything ever unwrapped the row."""

    def test_a_row_read_under_text_is_witnessed_as_never_unwrapped(self):
        assert never_unwrapped(ENVELOPE, journal_record(ENVELOPE)) is True

    def test_a_row_read_under_json_is_witnessed_as_already_unwrapped(self):
        """The fragment is not the whole, so the row is left alone."""
        assert never_unwrapped("alert_raised", journal_record(ENVELOPE)) is False

    def test_an_unparseable_raw_line_is_cannot_tell_and_not_no(self):
        """``None`` rather than ``False``.

        The two have opposite remedies — one is "leave it alone, it is
        correct", the other is "this could not be measured" — and a
        predicate that collapsed them would serve zero-because-blind as
        zero-because-clean.  A ``raw_line`` cut at 2000 characters is the
        reachable case and lands here.
        """
        assert never_unwrapped(ENVELOPE, journal_record(ENVELOPE)[:2000][:120]) is None
        assert never_unwrapped(ENVELOPE, None) is None
        assert never_unwrapped(ENVELOPE, "") is None

    def test_a_raw_line_that_is_not_an_object_is_cannot_tell(self):
        assert record_message('["not", "an", "object"]') is None
        assert record_message("null") is None

    def test_a_non_utf8_message_is_read_the_way_the_reader_reads_it(self):
        """``message_text``'s list branch, borrowed rather than restated.

        ``-a`` renders a non-UTF-8 field as an array of byte values, and
        the witness must resolve it the same way ``read_journal`` did or
        a correctly-stored row reads as never-unwrapped.
        """
        import json

        raw = json.dumps({"MESSAGE": list(b"alert_raised")})
        assert record_message(raw) == "alert_raised"


class TestThePopulationIsTheDeclaration:
    """Rule 3 — a declaration is honoured; an application is not recognised."""

    def test_only_a_source_declaring_the_format_is_scanned(self):
        config = _Config(
            LogSource(name="a", type="journalctl", unit="a.service", format="json"),
            LogSource(name="b", type="journalctl", unit="b.service", format="text"),
        )
        assert json_declared_sources(config) == ("a.service",)

    def test_a_source_is_named_by_its_unit_and_not_by_its_name(self):
        """``log_entries.source`` holds the unit.

        ``log_source_scopes`` records this trap from the other side:
        keying on ``name`` where the column holds the unit yields an
        empty map that reads as "every source is a system unit" — a
        wrong answer wearing the shape of a right one.  Here it would
        yield a scan of zero rows that reads as "nothing is frozen".
        """
        config = _Config(
            LogSource(name="sysadmin-service", type="journalctl",
                      unit="sysadmin.service", format="json"),
        )
        assert json_declared_sources(config) == ("sysadmin.service",)

    def test_a_source_that_can_produce_no_rows_is_dropped(self):
        """Neither a unit nor a path — ``stored_source_name`` returns
        ``None`` and it must not be unioned into the scan as a name."""
        config = _Config(LogSource(name="ghost", type="journalctl", format="json"))
        assert json_declared_sources(config) == ()

    def test_a_file_source_is_named_by_its_name(self):
        config = _Config(
            LogSource(name="app-log", type="file", path="/var/log/app.log",
                      format="json"),
        )
        assert json_declared_sources(config) == ("app-log",)

    def test_the_default_format_is_not_the_backfill_format(self):
        """The declaration has to be *made*.

        If ``LogFormat``'s default were ``json`` this repair would scan
        every source on the box, which is rule 3 inverted.
        """
        assert LogSource(name="x", type="journalctl", unit="x.service").format != (
            BACKFILL_FORMAT
        )


class TestTheReportKeepsItsThreeAnswersApart:
    """Rule 6 — not-knowing is never success."""

    def test_an_empty_report_is_not_blind(self):
        assert BackfillReport(sources=("a.service",), scanned=3).blind is False

    def test_a_refused_row_makes_the_report_blind(self):
        report = BackfillReport(sources=("a.service",), scanned=3,
                                unwitnessed=(uuid4(),))
        assert report.blind is True

    def test_an_unrecoverable_row_makes_the_report_blind(self):
        report = BackfillReport(sources=("a.service",), scanned=3,
                                unrecoverable=(uuid4(),))
        assert report.blind is True

    def test_the_two_ways_of_not_knowing_are_named_separately(self):
        """One field holding both would be ``UnitFinding.enabled``'s trap.

        A row nothing can witness and a row whose envelope will not parse
        have different remedies: the first is left alone for ever, the
        second is a message cut at its stored cap and is genuinely lost.
        """
        text = render(BackfillReport(
            sources=("a.service",), scanned=3,
            unwitnessed=(uuid4(),), unrecoverable=(uuid4(),),
        ))
        assert "refused" in text
        assert "unrecoverable" in text

    def test_the_dry_run_says_it_has_written_nothing(self):
        row = FrozenRow(uuid4(), "a.service", ENVELOPE, "alert_raised", {})
        assert "would be rewritten" in render(
            BackfillReport(sources=("a.service",), scanned=1, frozen=(row,))
        )
        assert "would be rewritten" not in render(
            BackfillReport(sources=("a.service",), scanned=1, frozen=(row,),
                           applied=True)
        )


class TestProvenance:
    """Rules 1, 3 and 5, which are claims about the source and not the output."""

    @staticmethod
    def _function(name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
        tree = ast.parse(MODULE_PATH.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name == name:
                    return node
        raise AssertionError(f"{name} is not defined in {MODULE_PATH.name}")

    def test_the_new_message_is_unwrapped_from_the_message_column(self):
        """Rule 1, asserted where it lives.

        Behaviourally the two derivations are indistinguishable once the
        witness has passed, which is exactly why this is a source check
        and not a value one.
        """
        plan = self._function("plan_backfill")
        calls = [
            node for node in ast.walk(plan)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "unwrap_json_message"
        ]
        assert calls, "plan_backfill no longer calls unwrap_json_message"
        for call in calls:
            arg = call.args[0]
            assert isinstance(arg, ast.Attribute) and arg.attr == "message", (
                "the new message must be unwrapped from the stored message column, "
                "never re-derived from raw_line — that is a second statement of "
                "read_journal's own parse and free to drift from it"
            )

    def test_the_source_set_is_borrowed_and_never_rebuilt(self):
        """Rule 3.  Both statements have owners already.

        A local re-read of ``services.yaml``, or a hand-written map from
        source to unit, is a second statement of a fact
        ``composed_log_sources`` and ``stored_source_name`` each own.
        """
        body = ast.unparse(self._function("json_declared_sources"))
        assert "composed_log_sources" in body
        assert "stored_source_name" in body

    def test_raw_line_is_never_written(self):
        """It is the record verbatim and the witness the next run needs.

        Rewriting it would make this repair self-erasing: run twice and
        the second pass could no longer tell a frozen row from a
        repaired one.
        """
        source = MODULE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        assert target.attr != "raw_line", (
                            "raw_line is the witness; rewriting it disarms rule 2"
                        )

    def test_metadata_is_reassigned_and_never_mutated_in_place(self):
        """SQLAlchemy does not track mutation inside a plain JSONB dict.

        ``SNAG-AGENT-005``'s rule 3: an in-place bump looks like it
        worked and writes nothing.  So the envelope must arrive by
        assignment of a fresh dict, and never by ``.update()``.
        """
        apply_fn = self._function("apply_backfill")
        body = ast.unparse(apply_fn)
        assert "metadata_ =" in body
        for node in ast.walk(apply_fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert not (
                    node.func.attr == "update"
                    and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "metadata_"
                ), "an in-place update of a JSONB column writes nothing"


class TestNothingSchedulesIt:
    """Rule 5 — a repair that rewrites stored history is run by a human.

    ``check-migrations.sh`` is asserted never to contain the word
    ``upgrade`` for the same reason: applying unattended is how a bad
    rewrite reaches production with nobody watching.  The check is over
    the *sources* rather than over a running scheduler, because a plan
    built in a test is not the plan the daemon builds.
    """

    def test_no_job_plan_or_agent_reaches_the_backfill(self):
        roots = [Path("sysadmin/core/jobs.py"), Path("sysadmin/main.py")]
        roots += sorted(Path("sysadmin").rglob("*agent*.py"))
        offenders = [
            path for path in roots
            if path.exists() and "message_backfill" in path.read_text()
        ]
        assert offenders == [], (
            f"{[str(p) for p in offenders]} reaches the backfill — it must be "
            "run by hand, never scheduled"
        )

    def test_it_is_wired_as_a_console_script(self):
        """The half that must exist, so the previous test cannot pass by
        the module being unreachable altogether."""
        assert (
            'sysadmin-backfill-messages = "sysadmin.monitor.message_backfill:main"'
            in Path("pyproject.toml").read_text()
        )


class TestTheExitStatusesAreDistinct:
    """``ports_checked``'s rule at the size of a return code."""

    def test_the_three_statuses_differ(self):
        assert len({
            message_backfill.EXIT_CLEAN,
            message_backfill.EXIT_WORK_PENDING,
            message_backfill.EXIT_UNKNOWN,
        }) == 3

    def test_clean_is_zero_so_a_shell_caller_reads_it_as_success(self):
        assert message_backfill.EXIT_CLEAN == 0

    @pytest.mark.parametrize(
        "report,expected",
        [
            (BackfillReport(sources=("a",), scanned=1), "EXIT_CLEAN"),
            (
                BackfillReport(
                    sources=("a",), scanned=1,
                    frozen=(FrozenRow(uuid4(), "a", ENVELOPE, "alert_raised", {}),),
                ),
                "EXIT_WORK_PENDING",
            ),
            (
                BackfillReport(
                    sources=("a",), scanned=1,
                    frozen=(FrozenRow(uuid4(), "a", ENVELOPE, "alert_raised", {}),),
                    applied=True,
                ),
                "EXIT_CLEAN",
            ),
            (
                BackfillReport(sources=("a",), scanned=1, unwitnessed=(uuid4(),)),
                "EXIT_UNKNOWN",
            ),
        ],
    )
    def test_main_maps_a_report_to_its_status(self, report, expected, monkeypatch):
        async def _run(confirm: bool):
            return report

        monkeypatch.setattr(message_backfill, "run", _run)
        assert message_backfill.main([]) == getattr(message_backfill, expected)

    def test_blindness_outranks_pending_work(self, monkeypatch):
        """A run that found work *and* could not measure everything is
        reported as unknown, not as work pending — the caller must not
        read a partial scan as a complete one."""
        report = BackfillReport(
            sources=("a",), scanned=2,
            frozen=(FrozenRow(uuid4(), "a", ENVELOPE, "alert_raised", {}),),
            unwitnessed=(uuid4(),),
        )

        async def _run(confirm: bool):
            return report

        monkeypatch.setattr(message_backfill, "run", _run)
        assert message_backfill.main([]) == message_backfill.EXIT_UNKNOWN

    def test_a_failure_to_look_is_unknown_and_not_a_traceback(self, monkeypatch):
        async def _run(confirm: bool):
            raise RuntimeError("postgres is not answering")

        monkeypatch.setattr(message_backfill, "run", _run)
        assert message_backfill.main([]) == message_backfill.EXIT_UNKNOWN


class TestTheDryRunIsTheDefault:
    """``files/actions.py``'s contract, one domain over."""

    def test_confirm_is_off_unless_asked_for(self, monkeypatch):
        seen: list[bool] = []

        async def _run(confirm: bool):
            seen.append(confirm)
            return BackfillReport(sources=("a",), scanned=0)

        monkeypatch.setattr(message_backfill, "run", _run)
        message_backfill.main([])
        message_backfill.main(["--confirm"])
        assert seen == [False, True]

    def test_run_writes_nothing_without_confirm(self):
        """The gate is in :func:`run`, not only in argument parsing."""
        body = inspect.getsource(message_backfill.run)
        assert "if confirm" in body
        assert "apply_backfill" in body
