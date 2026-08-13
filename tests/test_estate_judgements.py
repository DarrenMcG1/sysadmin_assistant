"""The judging swap's rules, exercised against literals.

The estate manager publishes and never acts (its ADR-0003, ADR-0004 §6);
this repository judges.  These tests cover
:mod:`sysadmin.estate.judgements`, which is pure by construction — no
database, no HTTP, no clock — precisely so the rules can be pinned
without 8400 running.

**That is not a convenience here, it is the only option for half of
them.**  ``GET /api/projects/attention`` has answered ``{"health": [],
"nudges": []}`` every time anyone has looked, and the estate's own suite
asserts exactly that (``test_nudges_are_published_not_stored``).  The
populated shape has never been observed on either side of the seam, so
the payloads below are built from the producer's dataclass fields
(``estate_service/projects/nudges.py``) rather than from a capture — and
the ``asdict``-drops-properties finding is what makes that distinction
worth stating: ``Nudge.title`` and ``Nudge.message`` are properties and
never reach the wire.

Live values used below, read from 8400 on 2026-08-13:

- ``/api/projects/invariants`` — 1 scan, manual, 10.2 h old,
  ``sources_unreachable: ["services endpoint unreachable: HTTPStatusError"]``
- ``/api/audit/invariants`` — 3 audits, 10 findings (2 ports, 8 collation),
  0 checks errored
- ``/api/queue/invariants`` — depth 0, ``dropped_total`` 1, ``grants_total`` 2
"""

import re

import pytest

from sysadmin.estate.judgements import (
    DEFAULT_SEVERITY,
    SURFACE_TITLE_PATTERNS,
    judge_attention,
    judge_audit_invariants,
    judge_projects_invariants,
    judge_queue_invariants,
)

HOUR = 3600.0


def _like(pattern: str, value: str) -> bool:
    """SQL ``LIKE`` for the ``%``-only patterns used here."""
    return re.fullmatch(re.escape(pattern).replace("%", ".*"), value) is not None


def _scan(**overrides):
    """A healthy scan payload, shaped like the live one."""
    last = {
        "run_type": "timer",
        "started_at": "2026-08-13T04:30:00+00:00",
        "finished_at": "2026-08-13T04:30:02+00:00",
        "age_seconds": 2 * HOUR,
        "projects_scanned": 26,
        "undeclared": 9,
        "parse_failures": 0,
        "repos_skipped": 0,
        "sources_unreachable": [],
        "estate_written": True,
        "error": None,
    }
    last.update(overrides)
    return {"scans_total": 12, "last_scan": last}


def _audit(**overrides):
    last = {
        "run_type": "timer",
        "verdict": "findings",
        "started_at": "2026-08-13T05:03:00+00:00",
        "finished_at": "2026-08-13T05:03:01+00:00",
        "age_seconds": 2 * HOUR,
        "checks_run": 4,
        "checks_errored": 0,
        "findings_total": 10,
        "checks": {
            "ports": {"error": None, "status": "findings", "findings": 2},
            "seams": {"error": None, "status": "ok", "findings": 0},
            "pointers": {"error": None, "status": "ok", "findings": 0},
            "collation": {"error": None, "status": "findings", "findings": 8},
        },
        "publish_error": None,
        "error": None,
    }
    last.update(overrides)
    return {"audits_total": 3, "last_audit": last}


def _queue(**overrides):
    payload = {
        "depth": 0,
        "oldest_waiting_seconds": None,
        "dropped_total": 1,
        "expired_total": 0,
        "grants_total": 2,
        "active_lease": None,
    }
    payload.update(overrides)
    return payload


def titles(judgements):
    return {j.title for j in judgements}


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------


class TestTheScan:
    def test_a_healthy_scan_judges_nothing(self):
        assert judge_projects_invariants(_scan(), 26.0) == []

    def test_no_scan_on_record_is_its_own_judgement(self):
        out = judge_projects_invariants({"scans_total": 0, "last_scan": None}, 26.0)
        assert titles(out) == {"Estate scan never ran"}

    def test_no_scan_on_record_judges_only_that(self):
        """Every other rule reads ``last_scan``; without one they would
        all fire at once off missing keys, so the empty case returns
        early. Nine alerts for one fault is the pile-up in miniature."""
        out = judge_projects_invariants({"scans_total": 0, "last_scan": None}, 26.0)
        assert len(out) == 1

    def test_age_is_judged_against_the_configured_window(self):
        assert judge_projects_invariants(_scan(age_seconds=25 * HOUR), 26.0) == []
        out = judge_projects_invariants(_scan(age_seconds=27 * HOUR), 26.0)
        assert "Estate scan stale" in titles(out)

    def test_undeclared_is_never_judged(self):
        """9 of 26 repositories carry no .project.yaml and the estate
        scores them exactly like ``active``. It is a standing description
        of the estate, not a breach — a rule on it opens a row that stays
        open until somebody declares nine repositories they have chosen
        not to declare."""
        out = judge_projects_invariants(_scan(undeclared=26), 26.0)
        assert out == []

    def test_a_skipped_repository_is_judged(self):
        """``repos_skipped`` counts repositories whose analysis *threw*.
        A skipped repository writes no snapshot, so it vanishes from
        every project surface without being reported as gone."""
        out = judge_projects_invariants(_scan(repos_skipped=2), 26.0)
        assert "Estate scan skipped repositories" in titles(out)

    def test_parse_failures_are_judged(self):
        out = judge_projects_invariants(_scan(parse_failures=1), 26.0)
        assert "Estate scan parse failures" in titles(out)

    def test_unreachable_sources_make_one_row_and_name_themselves(self):
        """Rule 2: variable text never enters a title.

        ``sources_unreachable`` is free text ending in an exception class
        name, so a per-source title would open a second row for the same
        dead seam the day it fails with ``ConnectError`` instead of
        ``HTTPStatusError`` — a family that never deduplicates. One row;
        ``details['sources']`` names them, the rule ``journal.py``
        already applies to ``truncated_sources``."""
        live = "services endpoint unreachable: HTTPStatusError"
        variant = "services endpoint unreachable: ConnectError"

        first = judge_projects_invariants(_scan(sources_unreachable=[live]), 26.0)
        second = judge_projects_invariants(_scan(sources_unreachable=[variant]), 26.0)

        assert titles(first) == titles(second) == {"Estate scan could not reach sources"}
        assert first[0].details["sources"] == [live]
        assert second[0].details["sources"] == [variant]

    def test_two_unreachable_sources_still_make_one_row(self):
        out = judge_projects_invariants(
            _scan(sources_unreachable=["a unreachable", "b unreachable"]), 26.0
        )
        assert len(out) == 1
        assert out[0].details["count"] == 2

    def test_a_scan_that_wrote_no_estate_json_is_judged(self):
        out = judge_projects_invariants(_scan(estate_written=False), 26.0)
        assert "Estate scan did not write estate.json" in titles(out)

    def test_a_recorded_error_is_judged(self):
        out = judge_projects_invariants(_scan(error="boom"), 26.0)
        assert "Estate scan failed" in titles(out)
        assert "boom" in [j for j in out if j.title == "Estate scan failed"][0].message

    def test_a_scan_with_no_finish_is_judged(self):
        out = judge_projects_invariants(_scan(finished_at=None), 26.0)
        assert "Estate scan did not finish" in titles(out)

    def test_everything_is_warning(self):
        out = judge_projects_invariants(
            _scan(age_seconds=99 * HOUR, parse_failures=3, error="x"), 26.0
        )
        assert out
        assert {j.severity for j in out} == {DEFAULT_SEVERITY} == {"warning"}


# ---------------------------------------------------------------------------
# Attention — the half where this repository is a delivery path
# ---------------------------------------------------------------------------


class TestAttention:
    def test_an_empty_payload_judges_nothing(self):
        """The live answer today, and the only one anyone has seen."""
        assert judge_attention({"health": [], "nudges": []}) == []

    def test_a_health_breach_is_one_warning_row(self):
        out = judge_attention(
            {
                "health": [
                    {
                        "project": "imbabots",
                        "score": 30,
                        "threshold": 40,
                        "status": "active",
                    }
                ],
                "nudges": [],
            }
        )
        assert titles(out) == {"Project imbabots health breach"}
        assert out[0].severity == "warning"
        assert out[0].details["score"] == 30

    def test_a_health_breach_never_reaches_critical(self):
        """``critical`` breaks through the DND windows by configuration
        and is the only severity the tray renders non-transient. A
        repository scoring low is a standing condition that can persist
        for weeks; it does not earn that."""
        out = judge_attention(
            {"health": [{"project": "x", "score": 0, "threshold": 100}], "nudges": []}
        )
        assert out[0].severity != "critical"

    @pytest.mark.parametrize("severity", ["info", "warning", "critical"])
    def test_a_nudge_severity_is_taken_verbatim(self, severity):
        """The estate computed it on the ladder that was ported there
        with the domain. Re-deriving it here would be two
        implementations of one ladder in two repositories — the
        copy-drift the estate manager exists to remove."""
        out = judge_attention(
            {
                "health": [],
                "nudges": [
                    {
                        "project_name": "alfred",
                        "days": 9,
                        "threshold": 7,
                        "severity": severity,
                        "next_action": "Wire the thing",
                        "at_window_edge": False,
                    }
                ],
            }
        )
        assert out[0].severity == severity
        assert out[0].details["severity_source"] == "estate"

    def test_an_unknown_severity_falls_back_rather_than_writing_it(self):
        """``alerts`` has a CHECK constraint on severity. A producer
        typo would otherwise be a CheckViolationError that takes the
        whole run's transaction with it."""
        out = judge_attention(
            {
                "health": [],
                "nudges": [
                    {"project_name": "a", "days": 9, "threshold": 7, "severity": "loud"}
                ],
            }
        )
        assert out[0].severity == DEFAULT_SEVERITY

    def test_the_window_edge_hedge_is_kept(self):
        """A streak reaching the edge of the retention window has an
        unknown true length. Restating it as exact is the small
        dishonesty the producer's own docstring refuses to commit."""
        payload = {
            "health": [],
            "nudges": [
                {
                    "project_name": "a",
                    "days": 10,
                    "threshold": 7,
                    "severity": "info",
                    "at_window_edge": True,
                    "next_action": "x",
                }
            ],
        }
        assert "at least 10 days" in judge_attention(payload)[0].message

    def test_a_nudge_without_the_hedge_states_the_figure(self):
        payload = {
            "health": [],
            "nudges": [
                {
                    "project_name": "a",
                    "days": 10,
                    "threshold": 7,
                    "severity": "info",
                    "at_window_edge": False,
                    "next_action": "x",
                }
            ],
        }
        message = judge_attention(payload)[0].message
        assert "at least" not in message
        assert "10 days" in message

    def test_an_entry_with_no_project_name_is_dropped(self):
        """The producer's contract, not ours. A row titled
        ``Project None health breach`` deduplicates against every other
        malformed entry and names nothing."""
        out = judge_attention(
            {"health": [{"score": 1, "threshold": 2}], "nudges": [{"days": 1}]}
        )
        assert out == []


# ---------------------------------------------------------------------------
# The audit — its invariants, never its findings
# ---------------------------------------------------------------------------


class TestTheAudit:
    def test_a_healthy_audit_judges_nothing(self):
        assert judge_audit_invariants(_audit(), 26.0) == []

    def test_findings_are_never_judged(self):
        """Rule 3, and the concrete reason: 8 of today's 10 findings are
        stale collation versions, which ``monitor/collation.py`` already
        holds eight open rows for. A rule on the total would announce
        this service's own alerts a second time through another
        producer — and the rest are conformance breaches in other
        repositories, which the estate rules send to those repositories'
        own ADR processes."""
        assert judge_audit_invariants(_audit(findings_total=500), 26.0) == []

    def test_a_stale_audit_reports_findings_without_alerting_on_them(self):
        out = judge_audit_invariants(_audit(age_seconds=30 * HOUR), 26.0)
        assert titles(out) == {"Estate audit stale"}
        assert out[0].details["findings_total"] == 10

    def test_an_errored_check_is_judged_and_named(self):
        """A check that errored produced no finding, so the audit's
        clean-looking result for that dimension means nothing looked
        rather than nothing was wrong — ``_resolve_recovered``'s
        ``error``-versus-``skipped`` distinction."""
        checks = _audit()["last_audit"]["checks"]
        checks["ports"] = {"error": "boom", "status": "error", "findings": 0}
        out = judge_audit_invariants(
            _audit(checks_errored=1, checks=checks, findings_total=8), 26.0
        )
        assert titles(out) == {"Estate audit checks errored"}
        assert out[0].details["errored_checks"] == ["ports"]

    def test_a_publish_failure_is_judged_separately_from_a_run_failure(self):
        """Findings computed but not published is a different fault from
        an audit that did not run: the findings are still served at
        /api/audit/findings, so the remedy differs."""
        out = judge_audit_invariants(_audit(publish_error="mqtt down"), 26.0)
        assert titles(out) == {"Estate audit publish failed"}

    def test_no_audit_on_record_is_its_own_judgement(self):
        out = judge_audit_invariants({"audits_total": 0, "last_audit": None}, 26.0)
        assert titles(out) == {"Estate audit never ran"}
        assert len(out) == 1


# ---------------------------------------------------------------------------
# The queue — gauges only
# ---------------------------------------------------------------------------


class TestTheQueue:
    def test_an_idle_queue_judges_nothing(self):
        """The live payload today: depth 0, one historical drop."""
        assert judge_queue_invariants(_queue(), 3, 900.0) == []

    @pytest.mark.parametrize(
        "field", ["dropped_total", "expired_total", "grants_total"]
    )
    def test_a_cumulative_total_is_never_judged(self, field):
        """Rule 1, and the most important test in this file.

        These are ``count(*)`` over the whole ``gpu_leases`` table —
        lifetime values that only ever rise. A ``> 0`` rule raises a row
        no future state can clear, which is ``redis unreachable``'s
        6,283 rows, ``Critical disk usage on /``'s 13,971 and the
        Bluetooth storm's 598,091 arriving by a fourth route.
        ``dropped_total`` is already 1 on the live queue, so the naive
        rule would have raised an immortal row on its first run."""
        assert judge_queue_invariants(_queue(**{field: 10_000}), 3, 900.0) == []

    def test_depth_is_judged(self):
        out = judge_queue_invariants(_queue(depth=5), 3, 900.0)
        assert titles(out) == {"Estate queue backlog"}

    def test_depth_at_the_threshold_is_not_a_breach(self):
        assert judge_queue_invariants(_queue(depth=3), 3, 900.0) == []

    def test_the_oldest_wait_is_judged(self):
        out = judge_queue_invariants(_queue(oldest_waiting_seconds=1200.0), 3, 900.0)
        assert titles(out) == {"Estate queue starved"}

    def test_a_null_wait_is_not_a_breach(self):
        """``NULL`` is what the producer's ``min(...) FILTER`` returns
        when nothing is waiting — an empty queue, not an unknown one."""
        assert judge_queue_invariants(_queue(oldest_waiting_seconds=None), 3, 0.0) == []

    def test_the_totals_are_carried_as_evidence(self):
        """Not judged, but not discarded either: a human comparing two
        runs can see a change this module cannot."""
        out = judge_queue_invariants(_queue(depth=9), 3, 900.0)
        assert out[0].details["dropped_total"] == 1
        assert out[0].details["grants_total"] == 2


# ---------------------------------------------------------------------------
# The partition the resolve depends on
# ---------------------------------------------------------------------------


def _every_title():
    """Every title these rules can produce, from maximally-broken input."""
    out = []
    out += judge_projects_invariants(
        _scan(
            age_seconds=99 * HOUR,
            finished_at=None,
            parse_failures=3,
            repos_skipped=2,
            sources_unreachable=["x unreachable"],
            estate_written=False,
            error="boom",
        ),
        26.0,
    )
    out += judge_projects_invariants({"scans_total": 0, "last_scan": None}, 26.0)
    out += judge_attention(
        {
            "health": [{"project": "some-project", "score": 1, "threshold": 40}],
            "nudges": [
                {
                    "project_name": "another_project",
                    "days": 9,
                    "threshold": 7,
                    "severity": "info",
                    "next_action": "x",
                }
            ],
        }
    )
    out += judge_audit_invariants(
        _audit(
            age_seconds=99 * HOUR,
            checks_errored=1,
            publish_error="mqtt down",
            error="boom",
        ),
        26.0,
    )
    out += judge_audit_invariants({"audits_total": 0, "last_audit": None}, 26.0)
    out += judge_queue_invariants(
        _queue(depth=9, oldest_waiting_seconds=9999.0), 3, 900.0
    )
    return out


class TestTheSurfacePartition:
    """The sweep is scoped to the surfaces a run read.

    If one surface's patterns matched another's titles, a successful
    pull of one surface could close rows belonging to one that failed —
    announcing a recovery from a payload nobody received. That is
    ``_resolve_recovered``'s "resolving on unknown" rule, and here it
    depends on the titles partitioning cleanly.
    """

    def test_every_title_matches_its_own_surface(self):
        for judgement in _every_title():
            patterns = SURFACE_TITLE_PATTERNS[judgement.surface]
            assert any(_like(p, judgement.title) for p in patterns), judgement.title

    def test_no_title_matches_another_surface(self):
        for judgement in _every_title():
            for surface, patterns in SURFACE_TITLE_PATTERNS.items():
                if surface == judgement.surface:
                    continue
                assert not any(_like(p, judgement.title) for p in patterns), (
                    f"{judgement.title!r} ({judgement.surface}) also matches {surface}"
                )

    def test_every_surface_is_covered(self):
        assert {j.surface for j in _every_title()} == set(SURFACE_TITLE_PATTERNS)

    def test_no_title_collides_with_the_sysadmin_agents_sweep(self):
        """Belt and braces. ``_resolve_recovered`` scopes on
        ``Alert.agent == self.name``, so ``estate_judge`` rows are
        already unreachable from it — but a title that *looks* like a
        service alert is a trap for whoever reads the table next."""
        from sysadmin.monitor.agent import RESOLVABLE_TITLE_PATTERNS

        for judgement in _every_title():
            for pattern in RESOLVABLE_TITLE_PATTERNS:
                assert not _like(pattern, judgement.title), judgement.title
