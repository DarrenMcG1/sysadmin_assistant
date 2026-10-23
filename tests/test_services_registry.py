"""Tests for services.yaml — schema, kind-based check selection, id resolution."""

import time
from pathlib import Path

import pytest
import yaml
from estate.registry import UnknownProjectError, load_registry
from pydantic import ValidationError

from sysadmin.core.config import get_config
from sysadmin.core.unit_failure import OWN_UNIT
from sysadmin.monitor.services import (
    SKIPPED,
    CheckPlan,
    ServiceEntry,
    ServicesError,
    ServicesFile,
    check_plan,
    load_services,
    log_sources,
    parse_services,
    stored_source_name,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_SERVICES_YAML = REPO_ROOT / "services.yaml"

#: Every source whose ``log.format`` is not ``text``, **hand-written so
#: that adding one costs a measurement**.  The set test below pins
#: membership against the shipped file and the live witness derives its
#: parametrisation from this constant, so the two cannot part: a
#: declaration added without a name here turns the set test red, and a
#: name here without a declaration turns it red from the other side,
#: while the witness reaches every member by construction rather than by
#: a second list somebody has to remember to extend.
#:
#: ``estate-manager-api`` joined 2026-08-31 (their ADR-0079, announced
#: as message ``76e0438b``).  The three timer sources joined 2026-09-13
#: on the measurement recorded in ``services.yaml`` beside them: all
#: four estate entry points call one ``configure_logging`` whose
#: ``resolve_format`` picks the prefixing formatter by a tty test, 378
#: JSON records carry that formatter's exact key order, no text record
#: follows the first JSON one, and no record begins with a literal
#: ``<N>`` — which excludes ``SyslogLevelPrefix=no``.  The membership
#: check joined 2026-09-26 (their ADR-0205, message ``6d3dbf47``): a
#: flag on the scan's own entry point, so the same formatter by
#: construction, and 551 JSON records of 551 when declared.  ``searxng``
#: — the estate's shim on 8600 — joined 2026-10-01 (their ADR-0231,
#: message ``e6782a8a``), witnessed on the live unit's current run: the
#: four uvicorn lifecycle records it opened with at 12:13 BST are JSON.
DECLARED_JSON_SOURCES = {
    "sysadmin-service",
    "estate-manager-api",
    "estate-manager-scan-timer",
    "estate-manager-audit-timer",
    "estate-manager-review-timer",
    "estate-manager-scan-check-timer",
    "searxng",
}

#: The members of :data:`DECLARED_JSON_SOURCES` whose cadence is a
#: **schedule** rather than a process, so the live witness reads them
#: without a time window and asks a different question of them.  See
#: :func:`_journal_message_shapes` for why a window is wrong here, and
#: ``TestLiveServicesYaml.test_a_declared_source_really_writes_json``
#: for what replaces it.
SCHEDULED_JSON_SOURCES = {
    "estate-manager-scan-timer",
    "estate-manager-audit-timer",
    "estate-manager-review-timer",
    "estate-manager-scan-check-timer",
}

#: The members of :data:`DECLARED_JSON_SOURCES` whose JSON is written
#: **at startup** and then drowned, so the live witness reads the
#: opening records of the unit's current run rather than its newest.
#:
#: The shim's only steady-state record is ``uvicorn.access``, plain text
#: and outside the estate's ``configure_logging`` by their choice — about
#: 800 a day, 22,774 of 23,778 in thirty days being this repository's own
#: health polls.  Its JSON is the four lifecycle lines a start writes,
#: plus a warning whose population is zero.  So the newest-500 read the
#: daemons take held 4 JSON records of 494 half an hour after the
#: 2026-10-01 restart and would hold none about fifteen hours later —
#: green on the day of the commit and red the next morning with nothing
#: having changed, which is the witness reading traffic rather than the
#: declaration.
STARTUP_JSON_SOURCES = {"searxng"}

#: How long after ``ActiveEnterTimestamp`` the opening read looks.
#: uvicorn's four lifecycle lines landed within one second of it on
#: 2026-10-01; the margin is for a slow start, not a measured tail.
_STARTUP_WINDOW_SECONDS = 60


def _active_enter_epoch(unit: str, *, user: bool) -> int | None:
    """The unit's current run's start, whole seconds, or ``None``.

    ``None`` for an inactive unit, whose ``ActiveEnterTimestamp`` is
    empty, and for any failure to ask.  Whole seconds is
    ``--timestamp=unix``'s own granularity, and it errs toward reading
    *more*: a stop and start inside one second put the previous run's
    shutdown lines into the window (measured: four plain-text ones on
    2026-10-01).  That cannot hide a JSON record, so it cannot turn the
    witness green falsely.
    """
    return _unit_epoch(unit, "ActiveEnterTimestamp", user=user)


def _unit_epoch(unit: str, prop: str, *, user: bool) -> int | None:
    """A timestamp property of ``unit`` in whole seconds, or ``None``."""
    import subprocess

    command = ["systemctl", "show", "--timestamp=unix", "-p", prop,
               "--value", unit]
    if user:
        command.insert(1, "--user")
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    if result.returncode != 0 or not value.startswith("@"):
        return None
    try:
        return int(value[1:])
    except ValueError:
        return None


def entry(**overrides) -> ServiceEntry:
    base = {"name": "thing", "kind": "systemd", "systemd": {"unit": "thing.service"}}
    return ServiceEntry.model_validate(base | overrides)



#: What ``SYSLOG_IDENTIFIER`` reads for a record systemd wrote about a
#: unit rather than one the unit wrote itself.  ``format:`` is a
#: statement about what the **application** emits, so systemd's own
#: lines are outside it by construction — ``Starting …``, ``Finished …``
#: and the ``Consumed … CPU time`` accounting are plain text whatever
#: the application does, and counting them makes a journal look mixed
#: when the declaration is perfectly true.  Session 224 measured the
#: cost of not excluding them: across the three estate oneshots'
#: journals they are 141, 114 and 12 records, and for the review they
#: are the **newest** record on every run.
_SYSTEMD_OWN = "systemd"


def _journal_message_shapes(
    unit: str, *, user: bool, since: str | None = "7 days ago",
    until: str | None = None,
) -> tuple[int, int, bool] | None:
    """(application records, of which JSON-shaped, newest is JSON), or ``None``.

    Deliberately a raw ``journalctl`` read: the point is the shape of
    ``MESSAGE`` as journald holds it, which is exactly what the ``json``
    declaration is a statement about.

    ``since`` is ``None`` for a source whose cadence is a **schedule**
    rather than a process.  A window is right for a daemon, which logs
    continuously, and wrong for a weekly oneshot: the window and the
    period are then the same length, so the read straddles a firing and
    the guard reddens on the hour it happens to run — a harness reading
    a clock it did not supply.  Worse, an empty window would make this
    guard speak for *"did the unit run"*, which the ``kind: timer``
    entry beside it already owns; two owners of one lifecycle is the
    defect this repository has now found at six scales.
    """
    import json as _json
    import subprocess

    command = ["journalctl", "-u", unit, "-n", "500", "-a", "-o", "json",
               "--no-pager"]
    if since is not None:
        # After the unit, never before it: ``-u`` takes the next token as
        # its argument, so inserting at index 2 hands it ``--since`` and
        # journalctl exits non-zero — which this helper reports as
        # "cannot read" and the caller turns into a skip.  Measured while
        # writing it: all five sources skipped green, including the one
        # that had passed for weeks.
        command[3:3] = ["--since", since]
    if until is not None:
        command[3:3] = ["--until", until]
    if user:
        command.insert(1, "--user")
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    total = json_shaped = 0
    newest_is_json = False
    for line in result.stdout.splitlines():
        try:
            record = _json.loads(line)
        except ValueError:
            continue
        if record.get("SYSLOG_IDENTIFIER") == _SYSTEMD_OWN:
            continue
        message = record.get("MESSAGE")
        if not isinstance(message, str):
            continue
        total += 1
        shaped = message.lstrip().startswith("{")
        json_shaped += shaped
        newest_is_json = bool(shaped)
    return total, json_shaped, newest_is_json


def _newest_plain_record_usec(unit: str, *, user: bool) -> int | None:
    """``__REALTIME_TIMESTAMP`` of the newest plain-text application record.

    A raw read of its own, so the instant the live negative is pinned at
    is not chosen by the helper under test.  Microseconds because a
    whole-second ``--until`` would let a JSON line written in the same
    second as the request it answers become the newest record again.
    """
    import json as _json
    import subprocess

    command = ["journalctl", "-u", unit, "-n", "500", "-a", "-o", "json",
               "--no-pager"]
    if user:
        command.insert(1, "--user")
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    newest = None
    for line in result.stdout.splitlines():
        try:
            record = _json.loads(line)
        except ValueError:
            continue
        message = record.get("MESSAGE")
        if (record.get("SYSLOG_IDENTIFIER") != _SYSTEMD_OWN
                and isinstance(message, str)
                and not message.lstrip().startswith("{")):
            newest = int(record["__REALTIME_TIMESTAMP"])
    return newest


def _journal_head_epoch(*, user: bool) -> int | None:
    """When the oldest record journald still holds was written, or ``None``.

    The retention horizon, which an empty read has to be checked against
    before it counts as evidence.  The user journal is size-capped and
    shared with every process in the session, so its horizon moves with
    their traffic rather than with the calendar: measured 2026-10-23 it
    reached back three days, llama-server and Steam writing about a
    quarter of a million lines a day between them.  A record written
    before the horizon is gone, and a read that finds nothing then says
    nothing about the producer.
    """
    import json as _json
    import subprocess

    # The stream runs oldest first, so its first line is the head; it is
    # read and the process closed, never the whole journal buffered.
    command = ["journalctl", "-o", "json", "--output-fields=__REALTIME_TIMESTAMP",
               "--no-pager", "-q"]
    if user:
        command.insert(1, "--user")
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True) as proc:
            assert proc.stdout is not None
            first = proc.stdout.readline()
            proc.kill()
    except OSError:
        return None
    try:
        return int(_json.loads(first)["__REALTIME_TIMESTAMP"]) // 1_000_000
    except (ValueError, KeyError, TypeError):
        return None


def _skip_if_rotated_out(unit: str, written: int | None, *, user: bool) -> None:
    """Skip when the records a read wanted were written before the horizon.

    Called only once a read has come back empty, so a non-empty read is
    asserted on whatever the horizon is.  ``written`` is when the wanted
    records were made — a run's start, a timer's last firing — and
    ``None`` leaves the empty read to its caller's assertion, which is
    where it was before the horizon was looked at.
    """
    head = _journal_head_epoch(user=user)
    if written is not None and head is not None and written < head:
        pytest.skip(
            f"{unit}'s records from @{written} predate the journal's oldest "
            f"retained record at @{head}; retention, not the producer, "
            "emptied the read"
        )

def make_registry(tmp_path: Path, *ids: str):
    for project_id in ids:
        path = tmp_path / project_id
        path.mkdir(parents=True, exist_ok=True)
        (path / ".git").mkdir(exist_ok=True)
        (path / ".project.yaml").write_text(
            yaml.safe_dump({"schema": 1, "id": project_id, "name": project_id}),
            encoding="utf-8",
        )
    return load_registry(tmp_path)


# ── schema ───────────────────────────────────────────────────────


class TestServiceEntry:
    def test_scope_defaults_to_user(self):
        assert entry().scope == "user"

    def test_scope_can_be_system(self):
        assert entry(systemd={"unit": "x.service", "scope": "system"}).scope == "system"

    def test_unknown_scope_rejected(self):
        with pytest.raises(ValueError):
            entry(systemd={"unit": "x.service", "scope": "session"})

    def test_http_requires_a_url(self):
        with pytest.raises(ValueError, match="kind http requires a url"):
            ServiceEntry.model_validate({"name": "x", "kind": "http"})

    def test_http_needs_no_unit(self):
        probe = ServiceEntry.model_validate(
            {"name": "internet", "kind": "http", "url": "https://1.1.1.1"}
        )
        assert probe.unit is None

    def test_tcp_requires_host_and_port(self):
        with pytest.raises(ValueError, match="requires host and port"):
            ServiceEntry.model_validate({"name": "x", "kind": "tcp", "host": "h"})

    @pytest.mark.parametrize("kind", ["systemd", "timer", "oneshot", "static"])
    def test_unit_kinds_require_a_unit(self, kind):
        with pytest.raises(ValueError, match="requires a systemd unit"):
            ServiceEntry.model_validate({"name": "x", "kind": kind})

    def test_timer_must_name_a_timer_unit(self):
        with pytest.raises(ValueError, match="must name a .timer unit"):
            entry(kind="timer", systemd={"unit": "thing.service"})

    def test_monitor_false_requires_a_reason(self):
        with pytest.raises(ValueError, match="requires a reason"):
            entry(kind="static", monitor=False)

    def test_monitor_false_with_a_reason_is_accepted(self):
        assert entry(kind="static", monitor=False, reason="on demand").monitor is False

    def test_typo_field_rejected_not_ignored(self):
        with pytest.raises(ValueError):
            entry(systemdd={"unit": "x.service"})

    def test_log_unit_inherits_the_systemd_unit(self):
        svc = entry(log={"type": "journalctl"})
        assert svc.log_unit == "thing.service"

    def test_log_unit_can_be_overridden(self):
        svc = entry(log={"type": "journalctl", "unit": "other.service"})
        assert svc.log_unit == "other.service"

    def test_log_format_defaults_to_text(self):
        """Fourteen of fifteen sources emit plain lines, so the reader
        keeps reading them exactly as it did before the field existed."""
        assert entry(log={"type": "journalctl"}).log.format == "text"

    def test_log_format_can_be_declared_json(self):
        assert entry(log={"type": "journalctl", "format": "json"}).log.format == "json"

    def test_unknown_log_format_rejected(self):
        """A typo fails at load — the property services.yaml was built
        around, and the reason this is a ``Literal`` rather than a string.
        A silently-ignored ``format: jsn`` leaves SNAG-LOG-003 standing
        with a line in the file saying it does not."""
        with pytest.raises(ValidationError):
            entry(log={"type": "journalctl", "format": "jsn"})

    def test_the_declaration_reaches_the_reader(self):
        """``LogRef.format`` is useless unless ``log_sources`` carries it:
        the field would be validated, documented and read by nothing,
        which is ``SNAG-CFG-001``'s shape exactly."""
        parsed = parse_services(
            {
                "schema": 1,
                "services": [
                    {
                        "name": "structured",
                        "kind": "systemd",
                        "systemd": {"unit": "structured.service"},
                        "log": {"type": "journalctl", "format": "json"},
                    },
                    {
                        "name": "plain",
                        "kind": "systemd",
                        "systemd": {"unit": "plain.service"},
                        "log": {"type": "journalctl"},
                    },
                ],
            }
        )
        assert {s.name: s.format for s in log_sources(parsed)} == {
            "structured": "json",
            "plain": "text",
        }

    def test_no_log_means_no_log_unit(self):
        assert entry().log_unit is None


class TestServicesFile:
    def test_unknown_schema_rejected(self):
        with pytest.raises(ValueError, match="unsupported schema"):
            parse_services({"schema": 2, "services": []})

    def test_duplicate_names_rejected(self):
        raw = {
            "schema": 1,
            "services": [
                {"name": "dupe", "kind": "systemd", "systemd": {"unit": "a.service"}},
                {"name": "dupe", "kind": "systemd", "systemd": {"unit": "b.service"}},
            ],
        }
        with pytest.raises(ValueError, match="unique"):
            parse_services(raw)

    def test_not_a_mapping_rejected(self):
        with pytest.raises(ValueError, match="mapping"):
            parse_services([1, 2, 3])

    def test_project_ids_deduplicated_in_order(self):
        raw = {
            "schema": 1,
            "services": [
                {"name": "a", "kind": "systemd", "project": "beta",
                 "systemd": {"unit": "a.service"}},
                {"name": "b", "kind": "systemd", "project": "alpha",
                 "systemd": {"unit": "b.service"}},
                {"name": "c", "kind": "systemd", "project": "beta",
                 "systemd": {"unit": "c.service"}},
                {"name": "d", "kind": "systemd", "systemd": {"unit": "d.service"}},
            ],
        }
        parsed = parse_services(raw)
        assert parsed.project_ids == ["beta", "alpha"]
        assert [s.name for s in parsed.host_services] == ["d"]
        assert [s.name for s in parsed.for_project("beta")] == ["a", "c"]

    def test_a_project_may_have_many_services(self):
        raw = {
            "schema": 1,
            "services": [
                {"name": f"s{i}", "kind": "systemd", "project": "one",
                 "systemd": {"unit": f"s{i}.service"}}
                for i in range(5)
            ],
        }
        assert len(parse_services(raw).for_project("one")) == 5


# ── kind decides the check ───────────────────────────────────────


class TestCheckPlan:
    def test_http_polls_the_url_and_asserts_the_unit(self):
        plan = check_plan(entry(kind="http", url="http://x/health"))
        assert plan == CheckPlan(poll_url=True, assert_active=True)

    def test_http_without_a_unit_only_polls(self):
        probe = ServiceEntry.model_validate(
            {"name": "internet", "kind": "http", "url": "https://1.1.1.1"}
        )
        assert check_plan(probe) == CheckPlan(poll_url=True, assert_active=False)

    def test_systemd_asserts_active(self):
        assert check_plan(entry()) == CheckPlan(assert_active=True)

    def test_tcp_connects_only(self):
        svc = ServiceEntry.model_validate(
            {"name": "x", "kind": "tcp", "host": "h", "port": 1}
        )
        assert check_plan(svc) == CheckPlan(connect=True)

    def test_timer_asserts_the_timer_and_inspects_the_last_run(self):
        plan = check_plan(entry(kind="timer", systemd={"unit": "x.timer"}))
        assert plan == CheckPlan(assert_active=True, inspect_timer=True)

    @pytest.mark.parametrize("kind", ["oneshot", "static"])
    def test_quiet_kinds_check_nothing(self, kind):
        assert check_plan(entry(kind=kind)).checks_nothing

    def test_monitor_false_overrides_the_kind(self):
        svc = entry(kind="http", url="http://x", monitor=False, reason="deliberate")
        assert check_plan(svc).checks_nothing

    def test_a_checking_plan_is_not_quiet(self):
        assert not check_plan(entry()).checks_nothing


# ── id resolution ────────────────────────────────────────────────


class TestIdResolution:
    def _write(self, tmp_path: Path, *projects: str | None) -> Path:
        path = tmp_path / "services.yaml"
        path.write_text(
            yaml.safe_dump({
                "schema": 1,
                "services": [
                    {"name": f"svc{i}", "kind": "systemd",
                     "systemd": {"unit": f"svc{i}.service"},
                     **({"project": p} if p else {})}
                    for i, p in enumerate(projects)
                ],
            }),
            encoding="utf-8",
        )
        return path

    def test_known_ids_load(self, tmp_path):
        registry = make_registry(tmp_path / "estate", "alfred")
        path = self._write(tmp_path, "alfred", None)
        assert len(load_services(path, registry).services) == 2

    def test_unknown_id_raises_at_load(self, tmp_path):
        registry = make_registry(tmp_path / "estate", "alfred")
        path = self._write(tmp_path, "alfrd")
        with pytest.raises(UnknownProjectError) as excinfo:
            load_services(path, registry)
        assert excinfo.value.unknown == ["alfrd"]

    def test_every_unknown_id_reported_at_once(self, tmp_path):
        registry = make_registry(tmp_path / "estate", "alfred")
        path = self._write(tmp_path, "alfred", "nope", "also-nope")
        with pytest.raises(UnknownProjectError) as excinfo:
            load_services(path, registry)
        assert excinfo.value.unknown == ["also-nope", "nope"]

    def test_the_error_names_the_file(self, tmp_path):
        registry = make_registry(tmp_path / "estate", "alfred")
        path = self._write(tmp_path, "nope")
        with pytest.raises(UnknownProjectError, match="services.yaml"):
            load_services(path, registry)

    def test_an_unmigrated_estate_skips_the_id_check(self, tmp_path, caplog):
        """Zero manifests means not-yet-migrated, not every id wrong."""
        estate = tmp_path / "estate"
        (estate / "repo" / ".git").mkdir(parents=True)
        registry = load_registry(estate)
        assert registry.ids == ()

        path = self._write(tmp_path, "anything")
        assert len(load_services(path, registry).services) == 1
        assert "services_project_ids_unchecked" in caplog.text

    def test_one_manifest_makes_it_strict(self, tmp_path):
        registry = make_registry(tmp_path / "estate", "alfred")
        path = self._write(tmp_path, "anything")
        with pytest.raises(UnknownProjectError):
            load_services(path, registry)

    def test_a_partial_load_that_refused_everything_is_still_strict(self, tmp_path):
        """``SNAG-SVC-007``. Every manifest refused also declares nothing,
        and reading that as an un-migrated estate would switch the id
        check off — with a migration hint — at the moment every
        reference is genuinely unresolvable."""
        estate = tmp_path / "estate"
        (estate / "alfred" / ".git").mkdir(parents=True)
        (estate / "alfred" / ".project.yaml").write_text("schema: 1\nid: [\n")
        registry = load_registry(estate, partial=True)
        assert registry.ids == () and len(registry.refused) == 1

        path = self._write(tmp_path, "alfred")
        with pytest.raises(UnknownProjectError):
            load_services(path, registry)

    def test_no_registry_means_no_id_check(self, tmp_path):
        path = self._write(tmp_path, "whatever")
        assert len(load_services(path).services) == 1

    def test_missing_file_raises_services_error(self, tmp_path):
        with pytest.raises(ServicesError, match="unreadable"):
            load_services(tmp_path / "absent.yaml")

    def test_malformed_yaml_raises_services_error(self, tmp_path):
        path = tmp_path / "services.yaml"
        path.write_text("services: [unclosed\n", encoding="utf-8")
        with pytest.raises(ServicesError, match="unreadable"):
            load_services(path)

    def test_invalid_entry_raises_services_error(self, tmp_path):
        path = tmp_path / "services.yaml"
        path.write_text(
            yaml.safe_dump({"schema": 1, "services": [{"name": "x", "kind": "http"}]}),
            encoding="utf-8",
        )
        with pytest.raises(ServicesError, match="invalid"):
            load_services(path)


# ── the file this repository actually ships ──────────────────────


class TestLiveServicesYaml:
    @pytest.fixture(scope="class")
    def services(self):
        return load_services(LIVE_SERVICES_YAML)

    def test_it_parses(self, services: ServicesFile):
        assert len(services.services) >= 17

    def test_this_daemons_own_entry_declares_the_format_it_writes_in(self):
        """The two statements of one fact, pinned rather than restated.

        ``service.log_format`` in config.yaml decides what this process
        emits; ``log.format`` in services.yaml decides how the reader
        parses it. They are set in different files by different hands and
        nothing connected them, so a switch to text logging would leave a
        ``format: json`` declaration reading a format that no longer
        exists — and removing the declaration would let ``SNAG-LOG-003``
        back with a line in the file claiming otherwise.

        Keyed on :data:`~sysadmin.core.unit_failure.OWN_UNIT` rather than
        on the service ``name``, because the unit is what the journal is
        read by and ``name`` is a historical label
        (``sysadmin-service``) that services.yaml's own header warns
        against treating as identity.
        """
        services = load_services(LIVE_SERVICES_YAML)
        own = [e for e in services.services if e.log and e.log_unit == OWN_UNIT]
        assert len(own) == 1, f"expected exactly one log source for {OWN_UNIT}"
        assert own[0].log.format == get_config().service.log_format

    def test_only_measured_sources_declare_a_format(self):
        """The set is measured, and the claim it used to make is dead.

        Until 2026-08-31 this asserted ``{"sysadmin-service"}`` and read
        *"this daemon is the only JSON-writing journal source on this
        box, which is the whole reason the fix went to a per-source
        declaration rather than into the reader"*.  The estate's four
        entry points began emitting one JSON document per record that day
        (their ADR-0079, announced here as message ``76e0438b``), so the
        founding observation is false.

        **Its falsification is the design's vindication, not its
        refutation.**  A reader that had sniffed a leading ``{`` would
        now be carrying a special case keyed on *two* applications' log
        formats; the per-source declaration absorbed the second producer
        in one line of services.yaml and no code at all.  That is the
        property this test still guards: a third name appearing here
        without a measurement behind it turns it red.

        The two declarations are **not** equally well supported, and the
        asymmetry is the reason the live witness below exists.  This
        daemon's is pinned against ``service.log_format`` by the test
        above — a fact this repository owns.  The estate's cannot be:
        a repository may not import another's config, so nothing in this
        checkout can state what estate code emits.
        """
        services = load_services(LIVE_SERVICES_YAML)
        declared = {
            e.name for e in services.services if e.log and e.log.format != "text"
        }
        assert declared == DECLARED_JSON_SOURCES

    @pytest.mark.parametrize("declared_name", sorted(DECLARED_JSON_SOURCES))
    @pytest.mark.box
    def test_a_declared_source_really_writes_json(self, declared_name):
        """The witness for a statement this repository cannot pin.

        ``unwrap_json_message`` **fails open at every step**, and that is
        what makes a wrong declaration silent: were the estate to revert
        to plain text, every record would pass through untouched, every
        test would stay green, and services.yaml would carry a false
        statement about another repository indefinitely.  This repository
        has already settled that shape once — the queue wait-gauge fix
        made the producer's new field loud *only* in its live half,
        because "a graceful degradation with no separate alarm degrades
        unnoticed".  Same argument, a journal instead of a payload.

        It reads the raw ``MESSAGE`` rather than going through
        ``read_journal``, which would already have unwrapped it and so
        could only agree with itself.

        Every way of not-knowing is a **skip** with its own reason, never
        a pass; and the premise — that the read returned records at all —
        is asserted separately, because an empty read satisfies "no
        non-JSON records" vacuously.

        **A scheduled source is asked a different question, and the
        asymmetry is the producer's rather than a convenience** (Session
        224).  For the three estate oneshots the read takes no window,
        for :func:`_journal_message_shapes`' reason, and the newest
        application record must *itself* be JSON — which is the precise
        statement "the most recent run wrote JSON", needs no clock, and
        catches a revert on the very next firing instead of waiting for
        the last JSON record to age out.  It cannot be asked of
        ``estate-manager-api``: the estate leaves ``uvicorn.access``
        outside ``configure_logging`` deliberately, *"this service has no
        such middleware, so disabling would delete the access log rather
        than de-duplicate it"*, so its newest application record is
        normally a plain-text access line.  Measured 2026-09-13 — the
        three oneshots answer ``True`` and the api answers ``False`` with
        ``INFO:     127.0.0.1 - "GET /api/health HTTP/1.1" 200 OK``.

        **A startup source is asked about the opening of its current run**
        (2026-10-01, :data:`STARTUP_JSON_SOURCES`).  Its JSON is written
        once per start and buried under access lines within hours, so
        the daemon read would go red with no change to the producer.
        The opening records are there for as long as the run is, and a
        revert shows on the next restart — the only moment the producer's
        logging configuration can change at all.
        """
        services = load_services(LIVE_SERVICES_YAML)
        entries = [e for e in services.services if e.name == declared_name]
        assert len(entries) == 1, declared_name
        source = entries[0]
        assert source.log is not None and source.log.format == "json"

        scheduled = declared_name in SCHEDULED_JSON_SOURCES
        user = source.scope == "user"
        if declared_name in STARTUP_JSON_SOURCES:
            started = _active_enter_epoch(source.log_unit, user=user)
            if started is None:
                pytest.skip(f"{source.log_unit} has no current run to read")
            found = _journal_message_shapes(
                source.log_unit, user=user, since=f"@{started}",
                until=f"@{started + _STARTUP_WINDOW_SECONDS}",
            )
        else:
            found = _journal_message_shapes(
                source.log_unit, user=user,
                since=None if scheduled else "7 days ago",
            )
        if found is None:
            pytest.skip(f"journalctl cannot read {source.log_unit}")
        total, json_shaped, newest_is_json = found
        if total == 0:
            # A daemon logs all week, so an empty window is the producer's
            # however short retention is; the other two read one moment.
            if declared_name in STARTUP_JSON_SOURCES:
                written = started
            elif scheduled:
                written = _unit_epoch(source.unit, "LastTriggerUSec", user=user)
            else:
                written = None
            _skip_if_rotated_out(source.log_unit, written, user=user)
        assert total > 0, (
            f"premise failed: no application records read for "
            f"{source.log_unit}, so this test witnessed nothing"
        )
        assert json_shaped > 0, (
            f"{declared_name} declares format: json but none of {total} "
            f"recent application records in {source.log_unit} is a JSON "
            "document — the declaration has gone stale"
        )
        if scheduled:
            assert newest_is_json, (
                f"{declared_name} declares format: json and the newest "
                f"application record in {source.log_unit} is not a JSON "
                "document, so the most recent run wrote something else — "
                "the declaration has gone stale since that run"
            )

    def test_it_contains_no_paths(self):
        """The property that makes a dead-path entry impossible."""
        raw = yaml.safe_load(LIVE_SERVICES_YAML.read_text(encoding="utf-8"))
        rendered = yaml.safe_dump(raw)
        assert "/home/" not in rendered
        assert "path" not in {
            key for service in raw["services"] for key in service
        }

    def test_every_service_that_names_a_project_resolves(self, services):
        registry = load_registry("~/projects")
        if not registry.ids:
            pytest.skip("estate not migrated on this machine")
        registry.assert_known(services.project_ids, str(LIVE_SERVICES_YAML))

    def test_system_scoped_units_are_declared_explicitly(self, services):
        """The four units the user-by-default would have broken."""
        system = {s.name for s in services.services if s.scope == "system"}
        assert {"postgresql", "networkmanager", "pgbackrest-backup-timer",
                "sysadmin-service"} <= system

    def test_oneshot_schedules_are_watched_through_their_timers(self, services):
        timers = {s.name for s in services.services if s.kind == "timer"}
        assert "alfred-evaluate-timer" in timers
        assert "sportsanalyser-pipeline-timer" in timers
        assert "venture-enrich-nightly-timer" in timers

    def test_every_unmonitored_service_says_why(self, services):
        for service in services.services:
            if not service.monitor:
                assert service.reason, service.name

    def test_skipped_is_an_allowed_health_status(self):
        from sysadmin.monitor.models.service_health import ServiceHealth

        constraint = next(
            c for c in ServiceHealth.__table__.constraints
            if getattr(c, "name", None) == "chk_health_status"
        )
        assert SKIPPED in str(constraint.sqltext)


class TestTheEstateTimersAreReadAtTheirService:
    """The estate oneshots' journals: three added 2026-09-13 (Session 224),
    the membership check 2026-09-26 (their ADR-0205).

    The entries are ``kind: timer`` and their ``systemd.unit`` is the
    **timer**, because the sweep reports a oneshot under the half
    carrying ``[Install]``.  The output is written by the other half, so
    each ``log:`` block names its ``.service`` explicitly through the
    optional ``LogRef.unit``.  The two conventions do not collide; what
    would collide is inheriting the unit, and that failure is **silent**
    — a timer's journal parses, reads clean and yields nothing, which is
    the "reads zero rows and looks exactly like a working one" trap the
    idea this closes spent three sittings avoiding.
    """

    TIMER_SOURCES = {
        "estate-manager-scan-timer": "estate-manager-scan.service",
        "estate-manager-audit-timer": "estate-manager-audit.service",
        "estate-manager-review-timer": "estate-manager-review.service",
        "estate-manager-scan-check-timer": "estate-manager-scan-check.service",
    }

    @pytest.fixture(scope="class")
    def by_name(self):
        sources = log_sources(load_services(LIVE_SERVICES_YAML))
        return {s.name: s for s in sources}

    def test_all_of_them_are_ingested(self, by_name):
        """The premise: without this the assertions below pass vacuously."""
        missing = sorted(set(self.TIMER_SOURCES) - set(by_name))
        assert not missing, (
            f"{missing} declare no log: block, so this repository reads "
            "none of the estate's timer journals"
        )

    @pytest.mark.parametrize("name", sorted(TIMER_SOURCES))
    def test_it_reads_the_service_and_not_the_timer(self, name, by_name):
        """The override, which is the whole point of the entry.

        Keyed on the ``.service``/``.timer`` suffix rather than on the
        literal unit strings alone, because the failure this guards is
        *inheritance* — a deleted ``unit:`` leaves ``log_unit`` reading
        ``systemd.unit``, which is the timer, and a suffix test names
        that directly.
        """
        source = by_name[name]
        assert source.unit == self.TIMER_SOURCES[name]
        assert source.unit.endswith(".service"), (
            f"{name} reads {source.unit}: a timer's journal holds only "
            "systemd's start lines, so the source would ingest nothing "
            "and report clean"
        )

    @pytest.mark.parametrize("name", sorted(TIMER_SOURCES))
    def test_it_is_read_from_the_user_journal(self, name, by_name):
        """``scope:`` still decides this, and it decides it correctly.

        The override moves the *unit* and not the scope, so a reader
        might reasonably wonder whether the service is where the timer
        is.  Both are user units here, so the inherited answer is right
        — asserted rather than assumed, because ``journalctl`` without
        ``--user`` on a user unit returns success and no records, which
        is this class's silent failure a second time.
        """
        assert by_name[name].user is True

    @pytest.mark.parametrize("name", sorted(TIMER_SOURCES))
    def test_rows_are_keyed_on_the_service_unit(self, name, by_name):
        """What ``log_entries.source`` will hold for these rows.

        A journal source is stamped with its **unit**, so these rows are
        keyed on the ``.service`` while the declaration is keyed on the
        entry ``name`` — the split ``stored_source_name`` exists to make
        explicit and the one ``log_source_scopes`` records as a trap.
        """
        assert stored_source_name(by_name[name]) == self.TIMER_SOURCES[name]

    @pytest.mark.parametrize("name", sorted(TIMER_SOURCES))
    def test_they_declare_the_format_the_estate_writes(self, name, by_name):
        """Paired with :data:`DECLARED_JSON_SOURCES`, which pins the set."""
        source = by_name[name]
        assert source.format == "json"
        assert source.severity_filter == "warning"

    @pytest.mark.parametrize("name", sorted(TIMER_SOURCES))
    def test_the_timers_own_journal_would_have_ingested_nothing(self, name):
        """The measurement that makes the override necessary rather than tidy.

        Driven at the **timer**, which is what a deleted ``unit:`` would
        read.  Measured 2026-09-13: 16 records each and **zero** of them
        written by anything but systemd.  This is the live half of the
        suffix test above — that one catches the edit, this one says why
        the edit matters, and a reader who trusted inheritance would get
        a source that parses, reads clean and stores nothing.
        """
        entries = [e for e in load_services(LIVE_SERVICES_YAML).services
                   if e.name == name]
        assert len(entries) == 1, name
        timer_unit = entries[0].unit
        assert timer_unit.endswith(".timer"), timer_unit
        found = _journal_message_shapes(timer_unit, user=True, since=None)
        if found is None:
            pytest.skip(f"journalctl cannot read {timer_unit}")
        total, _, _ = found
        assert total == 0, (
            f"{timer_unit} now carries {total} application record(s), so "
            "the premise behind naming the service explicitly has moved "
            "and this entry should be re-measured"
        )


@pytest.mark.box
class TestTheJournalHelperCanAnswerBothWays:
    """The detector driven where it must say *no*, so its *yes* means something.

    Every source in :data:`SCHEDULED_JSON_SOURCES` answers
    ``newest_is_json=True`` today, so a helper that returned ``True``
    unconditionally would redden nothing and the assertion built on it
    would be inert — a no-op mutation is not a control.  These drive it
    at the two shapes that must differ.
    """

    def test_it_says_no_where_the_newest_record_is_plain_text(self):
        """``estate-manager-api`` is the live negative, and not by accident.

        The estate leaves ``uvicorn.access`` outside ``configure_logging``
        deliberately — *"this service has no such middleware, so
        disabling would delete the access log rather than de-duplicate
        it"* — so its journal interleaves plain-text access lines with
        JSON ones even though the declaration is perfectly true.  That
        is exactly why the newest-record assertion is asked only of the
        scheduled sources.

        **The read is pinned at an instant whose newest application
        record is plain text, chosen by a raw read of its own** (Session
        325).  It used to read up to *now*, and *now* is the arbiter's
        as much as the access log's: while a lease waits,
        ``estate_service.arbiter`` writes a JSON ``lease … waits`` line
        every few seconds.  Measured 2026-10-02: the newest record was
        JSON for 0–0.3 % of each of the seven days before, and for 34 %
        of 10:33–10:42 that morning, the window in which this failed
        three runs of four.  It was recorded as the ``json_shaped``
        premise failing; it was the third assertion — the newest record
        *was* JSON — read through a ``grep | tail -3`` that keeps that
        assertion's source line and not its ``E`` line.  Pinned, the
        instant is a fact about the journal rather than about the
        traffic, so a red here means the helper cannot say *no*.
        """
        unit = "estate-manager-api.service"
        pin = _newest_plain_record_usec(unit, user=True)
        if pin is None:
            pytest.skip(f"no plain-text application record to pin in {unit}")
        seconds, micros = divmod(pin, 1_000_000)
        found = _journal_message_shapes(unit, user=True, since=None,
                                        until=f"@{seconds}.{micros:06d}")
        if found is None:
            pytest.skip(f"journalctl cannot read {unit}")
        total, json_shaped, newest_is_json = found
        assert total > 0, "premise failed: no application records read"
        assert json_shaped > 0, (
            "premise failed: the pinned read holds no JSON at all, so this "
            "witnesses nothing about the newest record specifically"
        )
        assert newest_is_json is False, (
            f"the helper called the newest record JSON at {pin}, whose "
            "newest application record is plain text by a raw read — the "
            "detector cannot say no, so the scheduled sources' yes is inert"
        )

    def test_the_startup_read_is_bounded_by_its_window(self):
        """The ``--until`` arm, shown to cut rather than merely parse.

        A misplaced flag makes journalctl exit non-zero, which the helper
        reports as ``None`` and the witness turns into a skip — green and
        witnessing nothing, the way all five sources once skipped.  So
        the bounded read must answer, and must answer with fewer records
        than the same read left open, or ``until`` is doing nothing.
        """
        unit = "estate-manager-searxng-shim.service"
        started = _active_enter_epoch(unit, user=True)
        if started is None:
            pytest.skip(f"{unit} has no current run to read")
        if time.time() < started + 2 * _STARTUP_WINDOW_SECONDS:
            pytest.skip(f"{unit} started too recently to outgrow its window")
        bounded = _journal_message_shapes(
            unit, user=True, since=f"@{started}",
            until=f"@{started + _STARTUP_WINDOW_SECONDS}",
        )
        assert bounded is not None, "journalctl refused the bounded read"
        opened = _journal_message_shapes(unit, user=True, since=f"@{started}")
        assert opened is not None
        assert bounded[0] < opened[0], (
            f"the bounded read saw {bounded[0]} records and the open one "
            f"{opened[0]}, so --until is not cutting"
        )

    def test_it_excludes_systemd_and_would_otherwise_have_counted(self):
        """The exclusion, shown to be load-bearing rather than tidy.

        Driven at a timer, whose journal is **only** systemd's lines: the
        helper reports zero application records, while the same read
        without the exclusion sees sixteen.  Without this the filter
        could be deleted and every assertion above would stay green.
        """
        import json as _json
        import subprocess

        unit = "estate-manager-scan.timer"
        found = _journal_message_shapes(unit, user=True, since=None)
        if found is None:
            pytest.skip(f"journalctl cannot read {unit}")
        assert found[0] == 0

        raw = subprocess.run(
            ["journalctl", "--user", "-u", unit, "-n", "500", "-a",
             "-o", "json", "--no-pager"],
            capture_output=True, text=True, timeout=30,
        )
        unfiltered = sum(
            1 for line in raw.stdout.splitlines()
            if isinstance(_json.loads(line).get("MESSAGE"), str)
        )
        if unfiltered == 0:
            # A timer writes its lines when it starts, not when it fires.
            _skip_if_rotated_out(unit, _active_enter_epoch(unit, user=True),
                                 user=True)
        assert unfiltered > 0, (
            f"premise failed: {unit} carries no records at all, so the "
            "exclusion is untested rather than shown to matter"
        )

    def test_the_windowed_read_is_not_silently_unusable(self):
        """The windowed form refuses rather than skips, and here is why.

        ``since`` was added 2026-09-13 and its first draft inserted the
        flag at index 2 — **between** ``-u`` and the unit — so
        ``journalctl`` took ``--since`` as the unit name and exited
        non-zero.  :func:`_journal_message_shapes` reports that as
        "cannot read" and every caller turns it into a skip, so the whole
        live witness went green while measuring nothing: five sources
        skipped, including the one that had passed for weeks.

        A skip is not health, so the windowed form is pinned at a source
        that cannot legitimately be empty — this daemon's own unit, which
        logs continuously — and the assertion is a **refusal**.  Driven
        as a falsification: restoring the index-2 insertion turns this
        red where it leaves every other test in the file green.
        """
        found = _journal_message_shapes(OWN_UNIT, user=False,
                                        since="7 days ago")
        assert found is not None, (
            f"the windowed read of {OWN_UNIT} failed, which every caller "
            "reports as a skip — check the journalctl argument order "
            "before trusting any other result in this file"
        )
        total, _, _ = found
        assert total > 0, (
            f"premise failed: no application records for {OWN_UNIT} in "
            "seven days, so the windowed form witnessed nothing"
        )


# ── SNAG-SVC-007: a malformed manifest elsewhere does not stop the boot ──


def _broken(estate: Path, tree: str) -> Path:
    path = estate / tree
    (path / ".git").mkdir(parents=True)
    # 2026-09-24's specimen: `change:` indented under a `- date:`.
    (path / ".project.yaml").write_text(
        "schema: 1\nid: x\nname: x\ndecisions:\n  - date: 2026-09-24\n"
        "     change: y\n",
        encoding="utf-8",
    )
    return path


class TestAPartialRegistryLoad:
    """What ``partial=True`` buys the lifespan, and what it must not."""

    def _services(self, tmp_path: Path, *projects: str) -> Path:
        return TestIdResolution()._write(tmp_path, *projects)

    def test_an_unreferenced_broken_manifest_no_longer_fails_the_load(self, tmp_path):
        """The founding case: a repository ``services.yaml`` never names."""
        estate = tmp_path / "estate"
        make_registry(estate, "alfred")
        _broken(estate, "archive/bsl-translator")
        with pytest.raises(Exception):
            load_registry(estate)  # the strict contract, unchanged
        registry = load_registry(estate, partial=True)
        assert len(load_services(self._services(tmp_path, "alfred"), registry).services) == 1

    def test_a_referenced_broken_manifest_still_fails_and_the_journal_says_why(
        self, tmp_path, caplog
    ):
        """Session 255's intent, kept: a tree ``services.yaml`` references
        still fails the boot, through the unknown-id check — which can
        name the id and never the reason, because the id is inside the
        file that would not parse.

        **The reason is the library's own WARNING, and this pins it.**
        ``estate.registry`` logs ``registry_manifest_refused`` inside
        ``load_registry``, so it lands before the id check by
        construction, and this repository does not restate it. If the
        estate stops writing it, this goes red: add a line in the
        lifespan and the reload before the id check, at WARNING."""
        estate = tmp_path / "estate"
        make_registry(estate, "sysadmin-assistant")
        _broken(estate, "alfred")
        caplog.set_level("WARNING")

        registry = load_registry(estate, partial=True)
        with pytest.raises(UnknownProjectError) as excinfo:
            load_services(self._services(tmp_path, "alfred"), registry)
        # The id it can name is the reference, never the broken file's own.
        assert excinfo.value.unknown == ["alfred"]

        refusals = [r for r in caplog.records if r.getMessage() == "registry_manifest_refused"]
        assert len(refusals) == 1
        [record] = refusals
        assert record.levelname == "WARNING"
        assert record.path == str(estate / "alfred")
        assert record.cause == "invalid"
        assert "unreadable YAML" in record.reason


class TestEveryProductionLoadIsPartial:
    """The owner's ruling covers every call site, not the lifespan alone.

    An AST sweep rather than a grep, so a call spelled across lines or
    through an alias is still found and a mention in a docstring is not.
    A seventh call added strict is the defect coming back by another door:
    the routes answer 500, the unit sweep fails its run.
    """

    def _calls(self):
        import ast

        found = []
        for path in sorted((REPO_ROOT / "sysadmin").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "load_registry"
                ):
                    partial = next(
                        (k.value for k in node.keywords if k.arg == "partial"), None
                    )
                    # ``depth`` is the second positional parameter; a
                    # keyword spelling is accepted too, so a caller that
                    # names it is not reported as having dropped it.
                    depth = next(
                        (k.value for k in node.keywords if k.arg == "depth"),
                        node.args[1] if len(node.args) > 1 else None,
                    )
                    found.append(
                        (path.relative_to(REPO_ROOT), node.lineno, partial, depth)
                    )
        return found

    def test_the_sweep_finds_the_known_calls(self):
        """The premise: a sweep that finds nothing passes the next test.
        A floor rather than an equality — six on 2026-09-25, in five
        files — because a seventh call that *is* partial keeps the claim,
        and an equality would go red on it."""
        assert len(self._calls()) >= 6

    def test_every_call_passes_partial_true(self):
        import ast

        strict = [
            f"{path}:{line}"
            for path, line, partial, _depth in self._calls()
            if not (isinstance(partial, ast.Constant) and partial.value is True)
        ]
        assert strict == []

    def test_every_call_passes_the_configured_depth(self):
        """Every call hands ``<config>.discovery_depth`` as the depth.

        Until 2026-10-01 one caller of five passed it and four took the
        library's default. Both read 2, so nothing differed on the box,
        but setting the key to 1 would have given the unit sweep a
        different project set from the registry ``services.yaml`` is
        checked against — the drift ``load_registry`` exists to remove.
        The test asks for the *attribute*, not for any value: a literal
        ``2`` at a call site is the defect in a different costume, since
        it stops agreeing with the key the moment the key is set.
        """
        import ast

        defaulted = [
            f"{path}:{line}"
            for path, line, _partial, depth in self._calls()
            if not (
                isinstance(depth, ast.Attribute) and depth.attr == "discovery_depth"
            )
        ]
        assert defaulted == []
