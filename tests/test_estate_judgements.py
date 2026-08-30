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

import json
import re
from pathlib import Path

import pytest

from sysadmin.core.text import TRUNCATION_MARKER
from sysadmin.estate.judgements import (
    DEFAULT_SEVERITY,
    HEALTH_ROLLUP_TITLE,
    JUDGED_AUDIT_CHECKS,
    JUDGED_AUDIT_SEVERITY,
    NEXT_ACTION_CHARS,
    NUDGE_ROLLUP_TITLE,
    PORTS_CHECK,
    SURFACE_TITLE_PATTERNS,
    TRANSIENT_HOLDER_SEVERITY,
    WIRING_CHECK,
    WIRING_FILE_TITLE,
    judge_attention,
    judge_audit_findings,
    judge_audit_invariants,
    judge_audit_wiring,
    judge_projects_invariants,
    judge_queue_invariants,
)

HOUR = 3600.0

#: The live default for ``agents.estate_judge.attention_max_rows``.  Most
#: rules below are about one row's wording and do not care, so they take
#: it through :func:`attention`; the tests that *are* about the cap pass
#: their own and say so.
MAX_ROWS = 5


def attention(payload, max_rows: int = MAX_ROWS):
    return judge_attention(payload, max_rows)


def _recorded_attention():
    """The populated payload, produced by the producer's own dataclass.

    Provenance and the two forced thresholds are documented on
    ``tests/test_estate_project_contracts.py::TestRecordedAttention``,
    which owns the recording; this file consumes it.
    """
    path = Path(__file__).parent / "fixtures" / "estate_projects_attention.json"
    return json.loads(path.read_text())


def _nudges(count: int, *, severity: str = "info", days: int = 9):
    return [
        {
            "project_name": f"project-{n}",
            "days": days,
            "threshold": 7,
            "severity": severity,
            "next_action": "x",
            "at_window_edge": False,
        }
        for n in range(count)
    ]


def _breaches(count: int):
    return [
        {"project": f"project-{n}", "score": 10, "threshold": 60, "status": "active"}
        for n in range(count)
    ]



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
    """The shape 8400 serves **today** — ADR-0077, estate message
    ``d1939cf7``.  ``waiting_reason`` and
    ``oldest_unexplained_wait_seconds`` are present and ``None``, which
    is what an idle queue looks like: nothing waiting, so nothing to
    explain."""
    payload = {
        "depth": 0,
        "oldest_waiting_seconds": None,
        "dropped_total": 1,
        "expired_total": 0,
        "grants_total": 2,
        "waiting_reason": None,
        "oldest_unexplained_wait_seconds": None,
        "active_lease": None,
    }
    payload.update(overrides)
    return payload


def _legacy_queue(**overrides):
    """The shape 8400 served before 2026-08-30, and the reason the
    fallback exists at all.

    The two discriminating keys are **absent**, not ``None``.  Every
    test that uses this is about a producer that cannot answer "was this
    wait explained", which is a different fact from one that answered
    "no"."""
    payload = _queue(**overrides)
    del payload["waiting_reason"]
    del payload["oldest_unexplained_wait_seconds"]
    return payload


def _starving(seconds=1200.0, reason="nothing_granted", **overrides):
    """A wait the producer says nothing explains."""
    return _queue(
        **{
            "depth": 1,
            "oldest_waiting_seconds": seconds,
            "oldest_unexplained_wait_seconds": seconds,
            "waiting_reason": reason,
            **overrides,
        }
    )


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
        assert attention({"health": [], "nudges": []}) == []

    def test_a_health_breach_is_one_warning_row(self):
        out = attention(
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
        out = attention(
            {"health": [{"project": "x", "score": 0, "threshold": 100}], "nudges": []}
        )
        assert out[0].severity != "critical"

    @pytest.mark.parametrize("severity", ["info", "warning", "critical"])
    def test_a_nudge_severity_is_taken_verbatim(self, severity):
        """The estate computed it on the ladder that was ported there
        with the domain. Re-deriving it here would be two
        implementations of one ladder in two repositories — the
        copy-drift the estate manager exists to remove."""
        out = attention(
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
        out = attention(
            {
                "health": [],
                "nudges": [{"project_name": "a", "days": 9, "threshold": 7, "severity": "loud"}],
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
        assert "at least 10 days" in attention(payload)[0].message

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
        message = attention(payload)[0].message
        assert "at least" not in message
        assert "10 days" in message

    def test_an_entry_with_no_project_name_is_dropped(self):
        """The producer's contract, not ours. A row titled
        ``Project None health breach`` deduplicates against every other
        malformed entry and names nothing."""
        out = attention({"health": [{"score": 1, "threshold": 2}], "nudges": [{"days": 1}]})
        assert out == []


class TestAttentionAgainstAPopulatedPayload:
    """The first exercise of these rules against real data (Session 52).

    ``SNAG-ESTATE-002``'s closing paragraph: every rule in ``TestAttention``
    above is pinned against a dict literal written by the same hand that
    wrote the consumer, because ``/api/projects/attention`` has answered
    ``{"health": [], "nudges": []}`` on all four occasions anyone has
    looked.  A literal cannot express volume or length, and both turned
    out to be wrong.
    """

    def test_the_recording_lands_on_both_sides_of_the_cap(self):
        """31 rows and 31 tray fingerprints from one hourly poll, before
        the cap existed — and the recording splits them without being
        made to.  26 breaches is the estate's whole scored population
        arriving at once, which is the arithmetic being wrong; 5 nudges
        is its whole *eligible* population, which is a fortnight away
        from the box.  One collapses and the other does not, in the same
        payload, which is the independence rule as data rather than as
        an argument."""
        payload = _recorded_attention()
        assert len(payload["health"]) == 26
        assert len(payload["nudges"]) == 5

        out = attention(payload)
        assert len(out) == 1 + 5
        assert HEALTH_ROLLUP_TITLE in titles(out)
        assert NUDGE_ROLLUP_TITLE not in titles(out)
        assert "Project sysadmin_assistant next action idle" in titles(out)

    def test_every_project_is_still_named_in_details(self):
        """A roll-up is only defensible because nothing is lost — it
        moves the names out of the titles, it does not drop them."""
        rows = {j.title: j for j in attention(_recorded_attention())}
        rollup = rows[HEALTH_ROLLUP_TITLE]
        assert len(rollup.details["projects"]) == 26
        assert "sysadmin_assistant" in rollup.details["projects"]
        # Scalars per project, so two runs can be diffed — the block is
        # evidence for the count, not a copy of the rows it replaced.
        assert rollup.details["scores"]["PersonalAssistant-auto"] == 50

    def test_no_recorded_message_runs_past_a_notification(self):
        """Measured before the cut: the live actions on this estate reach
        469 characters, and ``sysadmin_tray.notifications`` appends
        ``alert.message`` to a notification body verbatim."""
        out = attention(_recorded_attention(), max_rows=99)
        longest = max(len(j.message) for j in out)
        assert longest < 250, longest

    def test_a_cut_action_is_marked_and_kept_whole_in_details(self):
        """``SNAG-BRIEF-002``'s rule, which this family was not applying:
        a cut nothing marks is indistinguishable from a sentence that
        happened to end there."""
        payload = _recorded_attention()
        action = payload["nudges"][2]["next_action"]
        assert len(action) > NEXT_ACTION_CHARS

        row = next(j for j in attention(payload, max_rows=99) if "idle" in j.title)
        assert TRUNCATION_MARKER in row.message
        assert row.details["next_action"] in {n["next_action"] for n in payload["nudges"]}
        assert len(row.details["next_action"]) > NEXT_ACTION_CHARS

    def test_a_short_action_is_not_marked(self):
        row = attention({"health": [], "nudges": _nudges(1)})[0]
        assert TRUNCATION_MARKER not in row.message
        assert row.message.endswith(": x")


class TestTheAttentionCap:
    """A shape guard, not a tolerance — ``judge_audit_findings`` rule 2
    one surface over.  Twenty-six repositories do not go bad between two
    hourly polls; a threshold moved in the estate's config.yaml does
    exactly that to all of them at once."""

    def test_at_the_cap_every_project_keeps_its_own_row(self):
        """A roll-up cannot name anything (Session 46), so the individual
        rows survive for as long as there are few enough of them."""
        out = attention({"health": _breaches(MAX_ROWS), "nudges": []})
        assert len(out) == MAX_ROWS
        assert HEALTH_ROLLUP_TITLE not in titles(out)

    def test_one_past_the_cap_collapses(self):
        out = attention({"health": _breaches(MAX_ROWS + 1), "nudges": []})
        assert titles(out) == {HEALTH_ROLLUP_TITLE}
        assert out[0].details["breach_count"] == MAX_ROWS + 1
        assert out[0].details["max_rows"] == MAX_ROWS

    def test_the_two_families_collapse_independently(self):
        """Separate producers inside the estate — a score against a
        threshold, and a streak against a schedule.  They fail
        separately, and collapsing the working half because the other
        one broke would hide the half that still names its projects."""
        out = attention({"health": _breaches(MAX_ROWS + 1), "nudges": _nudges(2)})
        assert titles(out) == {
            HEALTH_ROLLUP_TITLE,
            "Project project-0 next action idle",
            "Project project-1 next action idle",
        }

    def test_a_rollup_takes_the_loudest_rung_it_swallows(self):
        """Collapsing rows must not also quieten them.  ``info`` is below
        ``tray.notify_min_severity`` on this box, so an escalated nudge
        folded into an ``info`` row would make the fix for noise the
        reason the one entry that earned a toast never got one."""
        nudges = _nudges(MAX_ROWS, severity="info") + _nudges(1, severity="warning")
        out = attention({"health": [], "nudges": nudges})
        assert titles(out) == {NUDGE_ROLLUP_TITLE}
        assert out[0].severity == "warning"

    def test_a_rollup_of_quiet_nudges_stays_quiet(self):
        """The other half of the same rule: loudest-it-swallows, not
        loud-because-there-are-many.  Volume is not severity."""
        out = attention({"health": [], "nudges": _nudges(MAX_ROWS + 1, severity="info")})
        assert out[0].severity == "info"

    def test_the_health_rollup_is_one_rung_like_the_rows_it_replaces(self):
        out = attention({"health": _breaches(MAX_ROWS + 1), "nudges": []})
        assert out[0].severity == DEFAULT_SEVERITY != "critical"

    def test_a_malformed_entry_is_dropped_before_the_count(self):
        """Otherwise the producer serving one broken row is what tips a
        family into collapsing — the count would be measuring the
        payload's length rather than the number of faults."""
        health = _breaches(MAX_ROWS) + [{"score": 1, "threshold": 2}]
        out = attention({"health": health, "nudges": []})
        assert len(out) == MAX_ROWS
        assert HEALTH_ROLLUP_TITLE not in titles(out)


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

    @pytest.mark.parametrize("field", ["dropped_total", "expired_total", "grants_total"])
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

    def test_the_oldest_unexplained_wait_is_judged(self):
        out = judge_queue_invariants(_starving(1200.0), 3, 900.0)
        assert titles(out) == {"Estate queue starved"}
        assert out[0].details["wait_gauge"] == "unexplained"

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


class TestTheWaitThatIsExplained:
    """Estate message ``d1939cf7`` / their ADR-0076 and ADR-0077.

    Their weekly review now takes a GPU lease instead of sampling a
    counter, so it queues behind ``venture-enrich-nightly`` every Monday
    05:30 and waits 915-1038 s — over this repository's 900 s threshold
    every time, for a cause the "Estate queue starved" message does not
    name and cannot: the queue working exactly as designed.
    """

    def test_the_monday_wait_is_not_starvation(self):
        """The founding case, at the top of the measured band.

        ``oldest_waiting_seconds`` is 1038 and over threshold; the
        producer says a declared holder explains it, and this judges
        nothing. Before 2026-08-30 it judged a row every Monday."""
        payload = _queue(
            depth=1,
            oldest_waiting_seconds=1038.0,
            oldest_unexplained_wait_seconds=None,
            waiting_reason="behind_holder",
        )
        assert payload["oldest_waiting_seconds"] > 900.0
        assert judge_queue_invariants(payload, 3, 900.0) == []

    def test_the_threshold_did_not_move(self):
        """Raising 900 was the other candidate and is refused in the
        docstring: at a bigger number the gauge still cannot tell a
        normal Monday from a stuck queue. So the same 900 that swallows
        the Monday must still catch an unexplained wait one second over
        it."""
        assert judge_queue_invariants(_starving(900.5), 3, 900.0)
        assert judge_queue_invariants(_starving(900.0), 3, 900.0) == []

    def test_the_mask_is_read_and_never_recomputed(self):
        """``waiting_reason == "behind_holder"`` plus the raw gauge
        reconstructs the masked number, and reconstructing it here would
        be a second implementation of the producer's derivation —
        ``SNAG-DB-003``'s shape.

        So an inconsistent payload is judged on the **field**, not on
        the reason: this one says ``behind_holder`` and still publishes
        an unexplained wait, and the row is raised. The estate owns that
        derivation; disagreeing with it silently is how two statements
        of one fact drift."""
        payload = _queue(
            depth=1,
            oldest_waiting_seconds=1200.0,
            oldest_unexplained_wait_seconds=1200.0,
            waiting_reason="behind_holder",
        )
        assert titles(judge_queue_invariants(payload, 3, 900.0)) == {
            "Estate queue starved"
        }

    def test_a_masked_wait_and_an_unpublished_one_are_not_the_same_fact(self):
        """``ports_checked``'s rule, and the whole of the fallback.

        Two payloads carrying the *same* ``oldest_waiting_seconds``.
        One has the discriminator and says the wait is explained; the
        other has no discriminator at all. ``payload.get(...)`` answers
        ``None`` for both. Masked means looked-at-and-explained; absent
        means not asked, and answering it with silence retires this
        family the day the estate rolls back."""
        masked = _queue(
            depth=1,
            oldest_waiting_seconds=1038.0,
            oldest_unexplained_wait_seconds=None,
            waiting_reason="behind_holder",
        )
        absent = _legacy_queue(depth=1, oldest_waiting_seconds=1038.0)
        assert masked["oldest_waiting_seconds"] == absent["oldest_waiting_seconds"]
        assert masked.get("oldest_unexplained_wait_seconds") is None
        assert absent.get("oldest_unexplained_wait_seconds") is None

        assert judge_queue_invariants(masked, 3, 900.0) == []
        out = judge_queue_invariants(absent, 3, 900.0)
        assert titles(out) == {"Estate queue starved"}

    def test_the_fallback_row_says_which_gauge_it_read(self):
        """A row that fell back must not claim a discrimination the
        producer did not supply — in ``details`` for a machine and in
        the message for the human the toast reaches."""
        out = judge_queue_invariants(
            _legacy_queue(depth=1, oldest_waiting_seconds=1038.0), 3, 900.0
        )
        assert out[0].details["wait_gauge"] == "total"
        assert "oldest_unexplained_wait_seconds" in out[0].message
        assert "cannot be ruled out" in out[0].message

    @pytest.mark.parametrize(
        "reason,phrase",
        [
            ("holder_overdue", "past its hold deadline"),
            ("nothing_granted", "Nothing holds a lease"),
        ],
    )
    def test_the_reason_is_named_because_the_producer_names_it(self, reason, phrase):
        """The old message posed a disjunction. ``waiting_reason``
        answers it, and leaving it unread is ``SNAG-UNITS-004``'s defect
        — under-reading a field the producer had already filled in.

        These two are exactly the disjunction's two limbs, which is why
        the sentence stays true: they are the only reasons that can
        still reach a row."""
        out = judge_queue_invariants(_starving(1200.0, reason=reason), 3, 900.0)
        assert phrase in out[0].message
        assert "Either a holder never released" not in out[0].message
        assert out[0].details["waiting_reason"] == reason

    def test_an_unrecognised_reason_is_not_rendered(self):
        """The vocabulary is the estate's. A fourth value means the
        producer has moved, and naming it from a guess is the
        ``subject`` fallback ``_port_of`` refuses. It falls back to the
        disjunction, which is true of anything."""
        out = judge_queue_invariants(_starving(1200.0, reason="quota_exhausted"), 3, 900.0)
        assert "Either a holder never released" in out[0].message
        assert out[0].details["waiting_reason"] == "quota_exhausted"
        assert out[0].details["wait_gauge"] == "unexplained"

    def test_both_wait_numbers_are_carried_as_evidence(self):
        """The raw gauge is no longer judged and is still reported: it
        is how long the request had actually been queued, which is the
        figure a human takes to the arbiter."""
        details = judge_queue_invariants(_starving(1200.0), 3, 900.0)[0].details
        assert details["oldest_waiting_seconds"] == 1200.0
        assert details["oldest_unexplained_wait_seconds"] == 1200.0

    def test_the_title_did_not_move(self):
        """Rule 2 of the module docstring. The title is the identity key
        — dedup, the resolve and the tray's ``{severity}:{title}``
        fingerprint all read it — so changing the gauge behind it must
        not change it. A standing row raised before this sitting stays
        the same row."""
        out = judge_queue_invariants(_starving(1200.0), 3, 900.0)
        assert out[0].title == "Estate queue starved"

    def test_the_backlog_gauge_is_untouched(self):
        """``depth`` was not part of the change and must not have moved
        with it: a Monday wait behind a declared holder still backs the
        queue up, and that is still worth a row."""
        payload = _queue(
            depth=9,
            oldest_waiting_seconds=1038.0,
            oldest_unexplained_wait_seconds=None,
            waiting_reason="behind_holder",
        )
        assert titles(judge_queue_invariants(payload, 3, 900.0)) == {
            "Estate queue backlog"
        }


# ---------------------------------------------------------------------------
def _breach(port=8888, **overrides):
    """One ``breach`` finding in the shape 8400 actually serves.

    Field-for-field from a live capture on 2026-08-14, which matters
    because two of the keys this module reads (``standing_days``,
    ``age_truncated``) are not in estate-manager's ``Finding`` dataclass
    — its router computes them per response — so a payload built from
    the dataclass would silently omit them.
    """
    finding = {
        "check": "ports",
        "severity": "breach",
        "subject": f"port {port}",
        "summary": (
            f"port {port} is listening inside the registry's range but no row "
            "claims it; the next project to pick a port cannot see that this "
            "one is taken"
        ),
        "fingerprint": f"ports:port {port}:unclaimed_listener",
        "code": "unclaimed_listener",
        "detail": {"port": port},
        "observed_at": "2026-08-14T11:26:09.810417+00:00",
        "first_seen_at": "2026-08-12T14:18:12.245695+00:00",
        "standing_days": 2.0,
        "runs_observed": 12,
        "age_truncated": False,
    }
    finding.update(overrides)
    return finding


#: The live payload on 2026-08-14: one ``warn``, no breach.
_LIVE_WARN = {
    "check": "ports",
    "severity": "warn",
    "subject": "port 3300",
    "summary": (
        "port 3300 is claimed by venture-assistant but nothing is listening; "
        "the service is stopped, or the row should say dormant"
    ),
    "fingerprint": "ports:port 3300:claimed_but_silent",
    "code": "claimed_but_silent",
    "detail": {"port": 3300, "project": "venture-assistant", "role": "frontend"},
    "standing_days": 1.3,
    "runs_observed": 8,
    "age_truncated": True,
}


class TestAuditFindings:
    """Rule 3's one exception: the ``ports`` check, judged per finding."""

    def test_the_live_payload_judges_nothing(self):
        """The payload as served on 2026-08-14 — one ``warn`` — is silent.

        Pinned deliberately rather than left implicit. This family ships
        with **zero live rows**, which is the same starting position
        ``SNAG-ESTATE-002`` files against ``judge_attention``, and a test
        that only ever ran against a synthesised breach would hide the
        fact that the quiet case is the observed one.
        """
        assert judge_audit_findings({"findings": [_LIVE_WARN]}, 5) == []

    def test_a_breach_is_one_row_naming_the_port(self):
        [judgement] = judge_audit_findings({"findings": [_breach(port=8888)]}, 5)
        assert judgement.surface == "audit_findings"
        assert judgement.title == "Estate port 8888 registry breach"
        assert judgement.severity == DEFAULT_SEVERITY
        assert judgement.details["port"] == 8888
        assert judgement.details["code"] == "unclaimed_listener"

    def test_two_breaches_are_two_rows(self):
        """Session 46's rule. A shared title means one fault masks the
        next behind the tray's ``{severity}:{title}`` fingerprint, which
        is how ``Unmonitored systemd units: 17 findings`` stayed open,
        accurate and unread for eight days."""
        judged = judge_audit_findings({"findings": [_breach(port=8888), _breach(port=9999)]}, 5)
        assert [j.title for j in judged] == [
            "Estate port 8888 registry breach",
            "Estate port 9999 registry breach",
        ]

    def test_rows_are_ordered_by_port(self):
        """Not for tidiness: the sweep keys on title, so a stable order
        keeps two runs of the same estate comparable in ``agent_runs``."""
        judged = judge_audit_findings({"findings": [_breach(port=9999), _breach(port=8888)]}, 5)
        assert [j.details["port"] for j in judged] == [8888, 9999]

    def test_above_the_cap_it_collapses_to_one_row(self):
        judged = judge_audit_findings({"findings": [_breach(port=8880 + n) for n in range(6)]}, 5)
        assert len(judged) == 1
        assert judged[0].title == "Estate port registry breach"
        assert judged[0].details["breach_count"] == 6

    def test_the_roll_up_names_the_ports_it_did_not_title(self):
        """The roll-up is allowed only because it still names them.
        ``ALERT_TITLE``'s failure was a count with nothing behind it."""
        judged = judge_audit_findings({"findings": [_breach(port=8880 + n) for n in range(6)]}, 5)
        assert judged[0].details["ports"] == [8880, 8881, 8882, 8883, 8884, 8885]

    def test_exactly_at_the_cap_is_still_per_port(self):
        judged = judge_audit_findings({"findings": [_breach(port=8880 + n) for n in range(5)]}, 5)
        assert len(judged) == 5

    # ── Session 57: the holder decides how loud, never who ───────────

    def test_a_dev_servers_breach_is_quietened_and_still_recorded(self):
        """The first two live rows this family ever produced.

        3110 and 8110 on 2026-08-16, both Alfred dev servers inside
        ``app-code-oss-26348.scope``. The estate's finding is literally
        correct — no registry row claims either port — and its remedy is
        the half that does not apply. Dropping the row was the obvious
        implementation and rebuilds this family's founding defect: a
        ports breach detected, correct, machine-readable and never said
        out loud.
        """
        [judgement] = judge_audit_findings(
            {"findings": [_breach(port=3110)]}, 5, _attribution(3110, transient=True)
        )
        assert judgement.severity == TRANSIENT_HOLDER_SEVERITY
        assert judgement.title == "Estate port 3110 registry breach"
        assert judgement.details["holder"]["unit"] == "app-code-oss-26348.scope"

    def test_the_quiet_rung_changes_nothing_a_reader_keys_on(self):
        """Severity moves; identity does not.

        The scope number changes on every login, which is why
        ``Listener.transient`` exists at all, so nothing derived from the
        holder may reach the title or the message.
        """
        [quiet] = judge_audit_findings(
            {"findings": [_breach(port=3110)]}, 5, _attribution(3110, transient=True)
        )
        [loud] = judge_audit_findings({"findings": [_breach(port=3110)]}, 5)
        assert quiet.title == loud.title
        assert quiet.message == loud.message
        assert "code-oss" not in quiet.title
        assert "code-oss" not in quiet.message

    def test_a_real_unit_holding_the_port_still_speaks(self):
        """A holder that is a service is not a reason to be quiet — the
        annotation only ever changes the rung for a *transient* one."""
        [judgement] = judge_audit_findings(
            {"findings": [_breach(port=8888)]}, 5, _attribution(8888, transient=False)
        )
        assert judgement.severity == DEFAULT_SEVERITY

    def test_an_unattributed_breach_is_unchanged(self):
        """The six-hourly sweep against this agent's hourly poll: a dev
        server started inside a sweep window has no attribution, reads as
        an ordinary breach, and is raised at ``warning``. Accepted and
        named rather than fixed by a second ``ss`` call — SNAG-ESTATE-009.
        """
        [judgement] = judge_audit_findings({"findings": [_breach(port=3110)]}, 5)
        assert judgement.severity == DEFAULT_SEVERITY
        assert judgement.details["holder"] is None

    # -- what the sweep knew, beside who it named (SNAG-ESTATE-009) ------

    def test_every_row_says_what_the_sweep_knew(self):
        """The annotation is on **every** breach, not only the odd one.

        A key present only sometimes is ``ports_checked``'s collapse one
        level down — absent-because-clean served as absent-because-blind
        — so the reading is uniform and its *value* carries the news.
        """
        attribution = _MixedAttribution(transient={3110}, real={8100}, seen={5432})
        judged = judge_audit_findings(
            {"findings": [_breach(port=p) for p in (3110, 5432, 8100, 8110)]}, 5, attribution
        )
        assert {j.details["port"]: j.details["attribution"]["reading"] for j in judged} == {
            3110: "transient",
            5432: "unattributed",
            8100: "held",
            8110: "unswept",
        }

    def test_the_two_rows_holder_cannot_separate_are_separated(self):
        """The entry's claim is indistinguishability, and this is it.

        A port the sweep *looked straight at* and a port it ran before
        both carry ``holder: None`` and the same rung.  Until
        2026-08-29 nothing else on the row told them apart.
        """
        attribution = _MixedAttribution(transient=set(), real=set(), seen={5432})
        seen, unswept = judge_audit_findings(
            {"findings": [_breach(port=5432), _breach(port=8110)]}, 5, attribution
        )
        assert seen.details["holder"] is None and unswept.details["holder"] is None
        assert seen.severity == unswept.severity == DEFAULT_SEVERITY
        assert seen.details["attribution"] != unswept.details["attribution"]

    def test_the_annotation_moves_no_rung(self):
        """Deliberately not a fix for the loud rung — refused on
        correctness, not cost. ``_attribution`` fails **open** in
        writing, so quietening on absent evidence would drop the whole
        family below the tray's threshold the day ``ss`` fails."""
        attribution = _MixedAttribution(transient=set(), real=set(), seen=set())
        [judgement] = judge_audit_findings({"findings": [_breach(port=8110)]}, 5, attribution)
        assert judgement.details["attribution"]["reading"] == "unswept"
        assert judgement.severity == DEFAULT_SEVERITY

    def test_the_roll_up_carries_a_reading_for_every_port(self):
        """Unlike ``holders``, which is filtered to the ones it named.

        Filtering a reading would be the collapse it exists to remove,
        one branch over: an absent entry would mean both "no holder" and
        "no evidence".
        """
        findings = [_breach(port=8880 + n) for n in range(6)]
        attribution = _MixedAttribution(transient={8880}, real=set(), seen={8881})
        [judgement] = judge_audit_findings({"findings": findings}, 5, attribution)
        assert set(judgement.details["attribution"]) == {str(8880 + n) for n in range(6)}
        assert set(judgement.details["holders"]) == {"8880"}
        assert judgement.details["attribution"]["8881"]["reading"] == "unattributed"
        assert judgement.details["attribution"]["8882"]["reading"] == "unswept"

    def test_no_attribution_at_all_is_unknown_not_unswept(self):
        """The duck-typed fallback, answered by an empty attribution
        rather than by a string spelled a second time here."""
        [judgement] = judge_audit_findings({"findings": [_breach(port=8110)]}, 5)
        assert judgement.details["attribution"] == {"reading": "unknown", "observed_at": None}

    def test_the_roll_up_takes_the_loudest_rung_it_swallows(self):
        """Session 52's rule. Six dev servers and one genuine unclaimed
        listener is one row that still has to be heard; collapsing rows
        must not also quieten them."""
        findings = [_breach(port=8880 + n) for n in range(6)]
        attribution = _MixedAttribution(
            transient={8880, 8881, 8882, 8883, 8884}, real={8885}
        )
        [judgement] = judge_audit_findings({"findings": findings}, 5, attribution)
        assert judgement.severity == DEFAULT_SEVERITY

    def test_a_roll_up_of_only_dev_servers_stays_quiet(self):
        """Volume is not severity in the other direction either."""
        findings = [_breach(port=8880 + n) for n in range(6)]
        attribution = _MixedAttribution(transient=set(range(8880, 8886)), real=set())
        [judgement] = judge_audit_findings({"findings": findings}, 5, attribution)
        assert judgement.severity == TRANSIENT_HOLDER_SEVERITY
        assert set(judgement.details["holders"]) == {
            str(port) for port in range(8880, 8886)
        }

    def test_the_quiet_rung_is_derived_from_the_trays_threshold(self):
        """Not picked. The requirement is "stays in
        ``GET /api/sysadmin/alerts``, leaves the notification path", and
        ``tray.notify_min_severity`` is the only thing on this box that
        decides the second half. A number chosen independently of it
        would be a threshold nothing obeys — ``SNAG-CFG-001``'s shape.
        """
        import yaml

        from sysadmin.core.escalation import SEVERITY_ORDER

        live = yaml.safe_load(Path("config.yaml").read_text())
        # Top-level ``tray:``, not ``notifications.tray:`` — the latter is
        # ``mute_services`` and nothing else. Read from the live file so
        # the day the owner raises the threshold this test says so.
        threshold = live["tray"]["notify_min_severity"]
        assert SEVERITY_ORDER[TRANSIENT_HOLDER_SEVERITY] < SEVERITY_ORDER[threshold]

    @pytest.mark.parametrize("check", ["collation", "pointers", "seams"])
    def test_other_checks_are_never_judged_even_at_breach(self, check):
        """The reason ``JUDGED_AUDIT_CHECK`` is a check name and not a
        severity: **all four** checks emit ``breach``. Collation is the
        family ``sysadmin.monitor.collation`` already raises here, so
        judging it double-counts this service's own alerts through a
        second producer; pointers and seams are other repositories'
        conformance."""
        assert judge_audit_findings({"findings": [_breach(check=check)]}, 5) == []

    @pytest.mark.parametrize("severity", ["warn", "info"])
    def test_only_breaches_are_judged(self, severity):
        """``warn`` is ``claimed_but_silent`` — availability, which
        ``services.yaml`` plus the sysadmin agent's ``% unreachable``
        family already owns. A second owner closes a row while the first
        still holds it true."""
        assert judge_audit_findings({"findings": [_breach(severity=severity)]}, 5) == []

    def test_a_finding_with_no_usable_port_is_skipped(self):
        """Rule 3: the port comes from ``detail['port']``, never from
        ``subject``. Falling back to the sentence is what would produce a
        title that forks when the producer rewords it."""
        assert judge_audit_findings({"findings": [_breach(detail={})]}, 5) == []
        assert judge_audit_findings({"findings": [_breach(detail=None)]}, 5) == []
        assert judge_audit_findings({"findings": [_breach(detail={"port": "eight"})]}, 5) == []

    def test_a_digit_string_port_is_accepted(self):
        [judgement] = judge_audit_findings({"findings": [_breach(detail={"port": "8888"})]}, 5)
        assert judgement.details["port"] == 8888

    def test_a_bool_is_not_a_port(self):
        """``isinstance(True, int)`` is ``True`` in Python, so this is a
        real hole rather than a hypothetical one."""
        assert judge_audit_findings({"findings": [_breach(detail={"port": True})]}, 5) == []

    def test_the_title_carries_no_code(self):
        """``unclaimed_listener`` is the only ports breach today. A title
        built from the code forks the row the day a second one lands for
        the same port — the producer owns that vocabulary, not us."""
        [judgement] = judge_audit_findings({"findings": [_breach(code="some_future_code")]}, 5)
        assert judgement.title == "Estate port 8888 registry breach"
        assert judgement.details["code"] == "some_future_code"

    def test_the_message_is_the_producers_summary(self):
        [judgement] = judge_audit_findings({"findings": [_breach()]}, 5)
        assert judgement.message.startswith("port 8888 is listening inside")
        assert "Standing 2 days." in judgement.message

    def test_a_truncated_age_is_reported_as_a_lower_bound(self):
        """``at_window_edge``'s rule on ``/api/projects/next``: a
        first-seen at the retention edge makes the standing time a lower
        bound, and rendering it as exact invents precision."""
        [judgement] = judge_audit_findings({"findings": [_breach(age_truncated=True)]}, 5)
        assert "Standing at least 2 days." in judgement.message

    def test_a_first_sighting_drops_the_clause(self):
        """Caught by the live run, not by design. The estate stamps a
        brand-new finding ``standing_days: 0.0``, and "Standing 0 days"
        reads as a rounding artefact rather than a fact — the row's own
        ``created_at`` already says when it appeared."""
        [judgement] = judge_audit_findings({"findings": [_breach(standing_days=0.0)]}, 5)
        assert judgement.message.endswith("this one is taken")
        assert "Standing" not in judgement.message

    def test_a_missing_standing_time_drops_the_clause(self):
        [judgement] = judge_audit_findings({"findings": [_breach(standing_days=None)]}, 5)
        assert "Standing" not in judgement.message

    @pytest.mark.parametrize("payload", [{}, {"findings": None}, {"findings": []}])
    def test_a_malformed_or_empty_payload_judges_nothing(self, payload):
        """Defensive for ``core/contracts.py``'s reason: the producer is
        another repository on its own release cycle."""
        assert judge_audit_findings(payload, 5) == []

    def test_non_dict_entries_are_ignored(self):
        assert judge_audit_findings({"findings": ["nonsense", 7, None]}, 5) == []


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
    out += attention(
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
    out += judge_queue_invariants(_starving(9999.0, depth=9), 3, 900.0)
    # Both shapes of the ports family: one row per port, and the roll-up
    # that replaces them above `port_breach_max_rows`. The roll-up has a
    # title of its own and would otherwise never reach the partition
    # guard, which is exactly how a stray pattern gets shipped.
    # Both shapes of the attention families too, for the same reason:
    # the two roll-up titles are fixed strings that no `Project % …`
    # pattern matches, so a missing pattern would go unnoticed until a
    # roll-up row sat unresolvable in the table.
    out += attention(
        {"health": _breaches(MAX_ROWS + 1), "nudges": _nudges(MAX_ROWS + 1)}
    )
    out += judge_audit_findings({"findings": [_breach(port=8888)]}, 5)
    out += judge_audit_findings({"findings": [_breach(port=8880 + n) for n in range(6)]}, 5)
    # Both shapes of the wiring family, which shares the ports family's
    # surface: the per-hook row and the fixed-title file-level one. The
    # second has no `%` anywhere in it, so a missing pattern would leave
    # a row about *every hook on the box being down* sitting in the table
    # with nothing able to resolve it.
    out += judge_audit_wiring({"findings": _recorded_wiring("misplaced")})
    out += judge_audit_wiring({"findings": _recorded_wiring("truncated")})
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


class _MixedAttribution:
    """Stands in for ``PortAttribution`` where a run holds both kinds.

    Deliberately not the real class: the roll-up rule is about what
    ``judge_audit_findings`` does with a mixture, and building the
    mixture out of a stored blob would test ``attribution_from_blob``
    again — which ``tests/test_unit_ports.py`` already drives end to end
    from real ``ss`` output.
    """

    def __init__(self, transient: set[int], real: set[int], seen: set[int] | None = None):
        self._transient = transient
        self._real = real
        self._seen = seen

    def of(self, port: int):
        if port in self._transient:
            return _holder("app-code-oss-26348.scope", transient=True)
        if port in self._real:
            return _holder("alfred-backend.service", transient=False)
        return None

    def reading(self, port: int):
        """Delegated to the real value rather than re-implemented here.

        The mixture stays hand-built, which is what this stand-in is
        for; the *vocabulary* is the producer's, because a second
        spelling of ``unswept`` in a test file is ``SNAG-DB-003``'s
        shape and would agree with this module while disagreeing with
        the box.
        """
        from sysadmin.units.ports import PortAttribution

        return PortAttribution(
            holders={p: "user:alfred-backend.service" for p in self._real},
            transient_holders={p: "user:app-code-oss-26348.scope" for p in self._transient},
            observed_at=OBSERVED_AT,
            unattributed=None if self._seen is None else frozenset(self._seen),
        ).reading(port)


#: The sweep's own stamp, stated once so ``_holder`` and ``reading``
#: cannot disagree about the age of one observation.
OBSERVED_AT = "2026-08-17T06:07:11+01:00"


def _holder(unit: str, *, transient: bool):
    return {
        "unit": unit,
        "scope": "user",
        "transient": transient,
        "observed_at": OBSERVED_AT,
    }


def _attribution(port: int, *, transient: bool, seen: set[int] | None = None):
    return _MixedAttribution(
        transient={port} if transient else set(),
        real=set() if transient else {port},
        seen=seen,
    )


# ---------------------------------------------------------------------------
# The wiring family — the audit's second judged check (ADR-0006)
# ---------------------------------------------------------------------------


def _recorded_wiring(specimen: str) -> list[dict]:
    """Findings from a real run of estate-manager's ``wiring`` check.

    **Recorded, not written.**  ``tests/fixtures/estate_audit_wiring.json``
    was produced on 2026-08-30 by driving their
    ``estate_service.audit.checks.wiring.run_check`` in their own venv
    (repository at commit ``003f3bc``, clean tree) against four
    specimens built from this box's live ``~/.claude/settings.json``:

    - ``clean`` — the live file, unmutated.  **Zero findings**, which is
      the family's live population and the reason the other three exist.
    - ``misplaced`` — the 2026-08-25 paste's first shape: a well-formed
      hooks block at the **top level**.  It parses, wires nothing, and
      files **one finding per declared hook** — four.
    - ``truncated`` — that paste's other shape, a missing ``]``.  The
      producer short-circuits to **one** ``settings_unparseable``
      finding rather than one per hook, which is why this family needs
      no roll-up of its own.
    - ``one_unwired`` — ``SessionStart`` removed, the single-row case
      and the exact failure estate-manager's ADR-0068 §4 asks about.

    Only **public** symbols were driven (``run_check``, ``WiringConfig``,
    ``Finding.as_payload``): a private helper's name is what their next
    fix renames.  The projection models the **HTTP** wire rather than
    the MQTT one — ``code`` is dropped, because ``AuditFinding`` has no
    column for it (``SNAG-ESTATE-006``, re-verified against the live
    endpoint the same day) — so a judge that came to depend on ``code``
    would fail here rather than in production.
    """
    path = Path(__file__).parent / "fixtures" / "estate_audit_wiring.json"
    return json.loads(path.read_text())[specimen]["findings"]


def _wiring(**overrides) -> dict:
    """One recorded ``hook_not_wired`` finding, with fields overridden."""
    finding = dict(_recorded_wiring("one_unwired")[0])
    detail = overrides.pop("detail", ...)
    finding.update(overrides)
    if detail is not ...:
        finding["detail"] = detail
    return finding


class TestTheWiringFamilyIsAdmitted:
    """``wiring`` joins ``ports`` — ADR-0006, answering estate-manager's
    message ``8462bcc5`` and their ADR-0068 §4.

    The subject is ``~/.claude/settings.json``: in no repository at all,
    estate-wide by construction, repairable only by the owner (their
    ADR-0024), and measured on 2026-08-29 to have no consumer anywhere.
    Every clause of :data:`JUDGED_AUDIT_CHECKS`' ownership test
    transfers, so the alternative to judging it here is that nobody ever
    says it.
    """

    def test_the_live_specimen_judges_nothing(self):
        """The family ships with an empty population, like ``ports``
        before it. Recorded from the real file rather than asserted, so
        the day the box's wiring breaks this fixture stops being clean
        and says so."""
        assert judge_audit_wiring({"findings": _recorded_wiring("clean")}) == []

    def test_the_2026_08_25_paste_gives_one_row_per_hook(self):
        """The uncollapsed shape, and the reason rule 4 needs no
        threshold: four declared hooks, four rows, each naming a hook a
        human can act on."""
        judged = judge_audit_wiring({"findings": _recorded_wiring("misplaced")})
        assert [j.title for j in judged] == [
            "Estate hook foreign-repo-write-notice.sh not wired for PreToolUse",
            "Estate hook inbox-notice.sh not wired for SessionStart",
            "Estate hook require-handoff.sh not wired for Stop",
            "Estate hook session-notice-observe.sh not wired for Notification",
        ]

    def test_the_failure_the_estate_asked_about_is_spoken(self):
        """Their ADR-0068 §4's whole condition: a dead ``SessionStart``
        entry raises a judgement at the owner. Before this it was
        detected, correct, machine-readable and said to nobody."""
        [judged] = judge_audit_wiring({"findings": _recorded_wiring("one_unwired")})
        assert judged.title == "Estate hook inbox-notice.sh not wired for SessionStart"
        assert judged.surface == "audit_findings"
        assert judged.details["event"] == "SessionStart"
        assert judged.details["subject"] == "inbox-notice.sh"

    def test_an_unparseable_settings_file_is_one_row_with_a_fixed_title(self):
        """Rule 4's other half. The producer already collapses this case
        to a single finding, and the title carries no path: ``subject``
        is a *configured* path here, so an f-string title would fork the
        row the day the estate re-spells its own config."""
        [judged] = judge_audit_wiring({"findings": _recorded_wiring("truncated")})
        assert judged.title == WIRING_FILE_TITLE
        assert judged.details["event"] is None

    def test_the_subject_key_names_the_producers_field_not_a_hook(self):
        """Found by the live drive rather than by reading. The key was
        written as ``hook`` and is right on three specimens; on this one
        the producer's subject is the config file's path, so the name
        would have promised a hook and delivered a file —
        ``UnitFinding.enabled``'s trap, one dict key wide."""
        [judged] = judge_audit_wiring({"findings": _recorded_wiring("truncated")})
        assert judged.details["subject"].endswith("settings-truncated.json")

    def test_every_row_carries_an_event_key(self):
        """Present on both shapes, ``None`` on the file-level one, never
        omitted. A key that appears only sometimes makes "the estate did
        not say" and "this row is not about one hook" one observation —
        ``ports_checked``'s rule at the size of a dict key."""
        for specimen in ("misplaced", "truncated", "one_unwired"):
            for judged in judge_audit_wiring({"findings": _recorded_wiring(specimen)}):
                assert "event" in judged.details

    def test_the_wire_carries_no_code_at_all(self):
        """The premise of rule 2, measured rather than assumed. ``code``
        is computed by the producer and folded into ``fingerprint``, and
        ``AuditFinding`` has no column for it (``SNAG-ESTATE-006``) — so
        a judge that discriminated on it would read ``None`` on every
        row the estate can serve and put every finding on one branch."""
        for specimen in ("misplaced", "truncated", "one_unwired"):
            for finding in _recorded_wiring(specimen):
                assert "code" not in finding

    @pytest.mark.parametrize(
        ("code", "detail", "expected_event"),
        [
            # The witness: `code` and the shape of `detail` disagree, so
            # the two implementations part company. Without a specimen
            # like this the test is a constant observation — the recorded
            # findings carry no `code`, so a code-reading judge agrees
            # with a detail-reading one by accident and the mutation
            # survives. It did, on the first drive.
            ("settings_unparseable", {"event": "Stop"}, "Stop"),
            ("hook_not_wired", {"error": "Expecting ','", "line": 657}, None),
        ],
    )
    def test_the_kind_is_read_from_detail_and_never_from_code(
        self, code, detail, expected_event
    ):
        """Rule 2. ``detail``'s shape is a fact this module can read on
        the live wire; ``code`` is a field it would have to invent a
        source for."""
        [judged] = judge_audit_wiring({"findings": [_wiring(code=code, detail=detail)]})
        assert judged.details["event"] == expected_event
        assert (judged.title == WIRING_FILE_TITLE) is (expected_event is None)


class TestTheWiringFamilyIsNarrow:
    """What the admission deliberately does not reach."""

    def test_nothing_is_judged_at_info(self):
        """``hook_wired_undeclared`` is the check's one ``info`` code,
        and the estate says in writing that "an extra event is the
        owner's prerogative over their own config, and the estate
        records it rather than judging it". A consumer that judged it
        would be a second opinion on a policy the producer declined to
        hold — ``claimed_tool_default``'s treatment one check over.

        Constructed rather than recorded: the estate's own check notes
        that no live instance exists."""
        undeclared = _wiring(
            severity="info",
            summary="inbox-notice.sh is wired behind Stop, which it does not declare",
            detail={"event": "Stop", "declares": ["SessionStart"]},
        )
        assert judge_audit_wiring({"findings": [undeclared]}) == []

    def test_a_wiring_finding_at_breach_is_not_judged(self):
        """The mapping is a filter in both directions. ``wiring`` emits
        no ``breach`` at any code — their ADR-0067 §4 refuses one — so a
        breach arriving here means the producer's contract moved, and
        the honest response is silence plus a suite that says so."""
        assert judge_audit_wiring({"findings": [_wiring(severity="breach")]}) == []

    def test_a_ports_finding_at_warn_is_still_not_judged(self):
        """**The reason the constant had to become a mapping.** Widening
        a single severity to admit ``wiring``'s ``warn`` would have
        re-imported ``ports``' ``claimed_but_silent``, which is
        availability — owned here by ``services.yaml`` plus the sysadmin
        agent's ``% unreachable`` family. A second owner closes a row
        while the first still holds it true."""
        assert judge_audit_findings({"findings": [_breach(severity="warn")]}, 5) == []

    def test_neither_family_reads_the_others_findings(self):
        """One payload, one surface, two families. Each filters on its
        own check name, so a wiring payload cannot produce a port row and
        the reverse."""
        wiring_payload = {"findings": _recorded_wiring("misplaced")}
        assert judge_audit_findings(wiring_payload, 5) == []
        assert judge_audit_wiring({"findings": [_breach()]}) == []

    def test_a_finding_with_no_usable_subject_is_skipped(self):
        """Rule 1 makes ``subject`` half the identity, so an unusable one
        is skipped rather than titled from the summary — the forkable
        title ``_port_of`` refuses one field over."""
        for subject in (None, "", "   ", 42, ["inbox-notice.sh"]):
            assert judge_audit_wiring({"findings": [_wiring(subject=subject)]}) == []

    @pytest.mark.parametrize("event", [None, "", "   ", 5, ["Stop"], {"a": 1}, True])
    def test_an_unusable_event_falls_back_to_the_file_level_row(self, event):
        """Never formatted into a title. ``detail`` arrives through JSONB,
        so an ``event`` that came back as a number or a list would
        otherwise become ``Estate hook x not wired for ['Stop']`` — a
        title that forks on the producer's serialisation."""
        [judged] = judge_audit_wiring({"findings": [_wiring(detail={"event": event})]})
        assert judged.title == WIRING_FILE_TITLE

    def test_a_finding_with_no_detail_at_all_is_still_a_row(self):
        """Fails *open*, like the ports family's attribution: missing
        evidence costs the qualifier, never the alert."""
        [judged] = judge_audit_wiring({"findings": [_wiring(detail=None)]})
        assert judged.title == WIRING_FILE_TITLE

    def test_there_is_no_rollup(self):
        """Rule 4. The population is bounded by the estate's own
        ``hooks/`` directory rather than by what is listening on the box,
        so many-at-once is not a different fault — and a threshold here
        would be invented against a population that has never exceeded
        four."""
        many = [
            _wiring(subject=f"hook-{n}.sh", detail={"event": f"Event{n}"})
            for n in range(20)
        ]
        assert len(judge_audit_wiring({"findings": many})) == 20

    def test_nothing_reaches_critical(self):
        """Rule 5. An unparseable ``settings.json`` does take the
        blocking ``Stop`` hook down — the one genuine this-box fault on
        these surfaces — and still gets ``warning``: ``critical`` breaks
        the DND windows and is what the tray leaves on screen, reserved
        for a fault costing something *now*, and a dead hook costs the
        *next* session. The estate refused ``breach`` for this check on
        the same shape of argument."""
        for specimen in ("misplaced", "truncated", "one_unwired"):
            for judged in judge_audit_wiring({"findings": _recorded_wiring(specimen)}):
                assert judged.severity == DEFAULT_SEVERITY

    def test_a_bad_payload_judges_nothing(self):
        for payload in ({}, {"findings": None}, {"findings": "x"}, {"findings": [None, 7]}):
            assert judge_audit_wiring(payload) == []


class TestWiringStandingDays:
    """``standing_days`` is carried as evidence, never as identity."""

    def test_a_first_sighting_says_nothing_about_standing(self):
        """The recorded specimens are all first sightings, stamped
        ``0.0``. "Standing 0 days" is true, reads as a rounding artefact,
        and says nothing ``created_at`` does not."""
        [judged] = judge_audit_wiring({"findings": _recorded_wiring("one_unwired")})
        assert "Standing" not in judged.message

    def test_a_standing_fault_says_how_long(self):
        [judged] = judge_audit_wiring({"findings": [_wiring(standing_days=3.0)]})
        assert judged.message.endswith("Standing 3 days.")

    def test_a_truncated_age_is_marked_a_lower_bound(self):
        [judged] = judge_audit_wiring(
            {"findings": [_wiring(standing_days=3.0, age_truncated=True)]}
        )
        assert judged.message.endswith("Standing at least 3 days.")

    def test_the_producers_sentence_is_taken_verbatim(self):
        """The estate owns the ``wiring`` contract and its wording
        explains the fault better than a paraphrase kept in step with
        it."""
        finding = _recorded_wiring("one_unwired")[0]
        [judged] = judge_audit_wiring({"findings": [finding]})
        assert judged.message == finding["summary"]


class TestTheJudgedCheckMapping:
    """:data:`JUDGED_AUDIT_CHECKS` — what admits a check, and its shape."""

    def test_exactly_two_checks_are_judged(self):
        """Ten of the audit's twelve checks are still excluded, and each
        admission needed an ADR. A third arriving without one is the
        widening rule 3 exists to prevent."""
        assert JUDGED_AUDIT_CHECKS == {PORTS_CHECK: "breach", WIRING_CHECK: "warn"}

    def test_the_ports_severity_is_derived_rather_than_retyped(self):
        """**Provenance, not value.** ``JUDGED_AUDIT_SEVERITY == "breach"``
        is true whether the constant is derived from the mapping or
        written beside it, and CPython interns the string either way — so
        the only instrument that can tell them apart is the source.
        ``max_priority_for`` against ``PRIORITY_MAP``'s rule, pinned the
        way that rule has to be pinned."""
        import ast

        source = Path("sysadmin/estate/judgements.py").read_text()
        assigned = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "JUDGED_AUDIT_SEVERITY"
                for t in node.targets
            )
        ]
        assert len(assigned) == 1, "one statement, or this test is measuring the wrong one"
        value = assigned[0].value
        assert isinstance(value, ast.Subscript), ast.dump(value)
        assert isinstance(value.value, ast.Name)
        assert value.value.id == "JUDGED_AUDIT_CHECKS"
        # And the derivation still yields the rung the ports paragraph
        # argues for, which the AST alone cannot say.
        assert JUDGED_AUDIT_SEVERITY == "breach"

    def test_every_recorded_finding_carries_the_rung_the_mapping_admits(self):
        """The producer's own evidence rather than a pin against their
        source: every finding a real run of their check produced is at
        the rung this repository speaks for."""
        recorded = [
            finding
            for specimen in ("misplaced", "truncated", "one_unwired")
            for finding in _recorded_wiring(specimen)
        ]
        assert recorded
        assert {f["severity"] for f in recorded} == {JUDGED_AUDIT_CHECKS[WIRING_CHECK]}
        assert {f["check"] for f in recorded} == {WIRING_CHECK}


class TestEveryJudgeFunctionReachesThePartitionGuard:
    """``_every_title`` is hand-maintained, and that is how a stray
    pattern ships.

    The wiring family passed all four partition tests before it was
    added here — because nothing produced its titles, so ``Estate hook %``
    could have been missing from :data:`SURFACE_TITLE_PATTERNS` and the
    suite would have stayed green while a row about every hook on the box
    being down sat unresolvable in ``alerts``. Enumerating the rule
    functions is what makes the omission an error rather than a silence.
    """

    def test_every_public_judge_function_is_driven(self):
        import ast

        from sysadmin.estate import judgements

        rules = {
            name
            for name in dir(judgements)
            if name.startswith("judge_") and callable(getattr(judgements, name))
        }
        source = Path(__file__).read_text()
        driver = next(
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == "_every_title"
        )
        called = {
            node.func.id
            for node in ast.walk(driver)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        # One alias exists and is named rather than resolved: `attention`
        # wraps `judge_attention` to supply the live `max_rows`. A second
        # alias would leave its rule uncovered and fail here, which is
        # the behaviour wanted — an alias is a way to hide a call.
        aliases = {"attention": "judge_attention"}
        covered = called | {aliases[name] for name in called & set(aliases)}
        assert rules - covered == set(), f"not driven by _every_title: {rules - covered}"
