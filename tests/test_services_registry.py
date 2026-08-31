"""Tests for services.yaml — schema, kind-based check selection, id resolution."""

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
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_SERVICES_YAML = REPO_ROOT / "services.yaml"


def entry(**overrides) -> ServiceEntry:
    base = {"name": "thing", "kind": "systemd", "systemd": {"unit": "thing.service"}}
    return ServiceEntry.model_validate(base | overrides)



def _journal_message_shapes(unit: str, *, user: bool) -> tuple[int, int] | None:
    """(records read, of which JSON-shaped), or ``None`` if unreadable.

    Deliberately a raw ``journalctl`` read: the point is the shape of
    ``MESSAGE`` as journald holds it, which is exactly what the ``json``
    declaration is a statement about.
    """
    import json as _json
    import subprocess

    command = ["journalctl", "-u", unit, "--since", "7 days ago",
               "-n", "500", "-a", "-o", "json", "--no-pager"]
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
    for line in result.stdout.splitlines():
        try:
            message = _json.loads(line).get("MESSAGE")
        except ValueError:
            continue
        if not isinstance(message, str):
            continue
        total += 1
        json_shaped += message.lstrip().startswith("{")
    return total, json_shaped

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
        assert declared == {"sysadmin-service", "estate-manager-api"}

    @pytest.mark.parametrize("declared_name", ["sysadmin-service",
                                               "estate-manager-api"])
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
        """
        services = load_services(LIVE_SERVICES_YAML)
        entries = [e for e in services.services if e.name == declared_name]
        assert len(entries) == 1, declared_name
        source = entries[0]
        assert source.log is not None and source.log.format == "json"

        found = _journal_message_shapes(source.log_unit,
                                        user=source.scope == "user")
        if found is None:
            pytest.skip(f"journalctl cannot read {source.log_unit}")
        total, json_shaped = found
        assert total > 0, (
            f"premise failed: no records read for {source.log_unit}, so "
            "this test witnessed nothing"
        )
        assert json_shaped > 0, (
            f"{declared_name} declares format: json but none of {total} "
            f"recent records in {source.log_unit} is a JSON document — "
            "the declaration has gone stale"
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
