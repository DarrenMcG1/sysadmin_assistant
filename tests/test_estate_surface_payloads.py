"""The estate judge's other three surfaces, against payloads the producer built.

Session 52 did this for ``/api/projects/attention`` and ranked the rest
below it on ground that still stands: these three surfaces **do** answer
with live numbers, and the literals in ``tests/test_estate_judgements.py``
were written from real readings rather than invented.  What moved is the
cost of being wrong.  Before Session 53 a mistaken judgement here bought
one toast, once, for ever; ``reminder_hours`` now restates every standing
row every 24 hours, so a row that should not exist nags daily until
somebody closes it by hand.

**What a literal cannot express, and what these fixtures do.**  Every
rule in ``TestTheScan``, ``TestTheAudit``, ``TestTheQueue`` and
``TestAuditFindings`` is exercised one condition at a time, because that
is what a keyword override to ``_scan(...)`` produces.  The producer does
not emit one condition at a time: a failing scan sets ``error`` *and*
leaves ``estate_written`` False, because ``estate.json`` is written near
the end of a run and ``ScanOutcome.estate_written`` starts False.  Those
two rules had never been seen in the same payload, and together they
raised two rows for one fault — one of them saying the scan "completed".
That is the whole argument for a capture over a literal, and it is the
same argument Session 52 made about volume and length.

**How the payloads were made, since the wire cannot supply them.**  The
unhappy states have never occurred: 0 of 7 ``scan_runs`` and 0 of 22
``audit_runs`` carry an error, no ``ports`` finding has ever reached
``breach`` (today's one is ``warn``), and the queue has never had a
waiter.  So the rows are synthetic and everything downstream of them is
the producer's:

    # captured 2026-08-16, box `arch`, estate-manager at ~/projects/estate-manager
    # run in *its* venv, against the live `estate` database, inside
    # transactions that were rolled back — verified afterwards at
    # 7 scan_runs / 22 audit_runs / 92 audit_findings, unchanged.
    scan_invariants(session)        # estate_service.projects.oversight
    audit_invariants(session)       # estate_service.audit.router
    findings(session)               # ditto — including `_streak_starts`
    Arbiter.invariants()            # estate_service.arbiter, on a pinned conn

The ``ports`` breaches are not synthetic at all: real listeners were
bound on 3900–3905, inside the registry's own audited range, and
``estate_service.audit.checks.ports.run_check`` was run against the real
``monitorable-project.md``.  Session 26b-A's method, which is why
``detail['port']`` and ``fingerprint`` below are the producer's spelling
rather than this repository's guess at it.

**This is one notch weaker than Session 52's fixture and says so.**
There, 26 real snapshots and 5 real streaks went through the producer
with two thresholds forced.  Here the *row* is invented; what is
borrowed is the ORM model that would reject a shape the estate cannot
store, the route function, ``_run_payload``, ``_streak_starts`` and
``CheckResult.as_summary``.  A field the producer renames still breaks
these fixtures on re-capture, and the live half below catches it without
one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from sysadmin.estate.judgements import (
    judge_audit_findings,
    judge_audit_invariants,
    judge_projects_invariants,
    judge_queue_invariants,
)
from tests.test_estate_project_contracts import ESTATE_URL, _estate_available

FIXTURES = Path(__file__).parent / "fixtures"

#: The live values of ``agents.estate_judge.*`` in ``config.yaml``.
#: Passed explicitly rather than read from config: a threshold moved in
#: the file should not silently change what these tests assert about a
#: payload recorded against the old one.
SCAN_MAX_AGE_HOURS = 26.0
AUDIT_MAX_AGE_HOURS = 26.0
QUEUE_MAX_DEPTH = 3
QUEUE_MAX_WAIT_SECONDS = 900.0
PORT_BREACH_MAX_ROWS = 5


def scenarios(name: str) -> dict[str, Any]:
    """Every scenario in a fixture, with its provenance block removed.

    The block is not decoration: JSON carries no comment, and these
    files hold synthetic rows.  Stripping it here rather than at write
    time means a re-capture that forgets it fails
    :func:`test_every_fixture_carries_its_provenance` instead of quietly
    passing a hand-edit off as an observation.
    """
    payload = json.loads((FIXTURES / f"estate_{name}.json").read_text())
    return {k: v for k, v in payload.items() if not k.startswith("_provenance")}


def titles(judgements) -> set[str]:
    return {j.title for j in judgements}


@pytest.mark.parametrize(
    "name",
    ["projects_invariants", "audit_invariants", "audit_findings", "queue_invariants"],
)
def test_every_fixture_carries_its_provenance(name: str):
    """Every block says where it came from, and how the live database
    was left alone: rolled back on the connection, or captured against a
    scratch database, or read off the wire with no write at all."""
    doc = json.loads((FIXTURES / f"estate_{name}.json").read_text())
    blocks = [v for k, v in doc.items() if k.startswith("_provenance")]
    assert blocks
    for block in blocks:
        assert block["box"] and block["captured_at"]
        assert any(
            phrase in block["method"]
            for phrase in ("rolled back", "scratch database", "no write")
        ), block["method"]


@pytest.mark.parametrize(
    "name",
    ["projects_invariants", "audit_invariants", "audit_findings", "queue_invariants"],
)
def test_every_scenario_is_claimed_by_exactly_one_provenance_block(name: str):
    """A fixture re-captured in two sittings has two blocks, and the
    thing that goes wrong is a scenario belonging to neither.

    ``estate_queue_invariants.json`` is the live instance: its
    ``live``/``backlog`` pair predates ADR-0077 and its four newer
    scenarios do not, and reading the older pair as though it had been
    captured against today's producer is exactly the mistake the
    fallback path exists to survive. So with more than one block, every
    block names what it covers and the union is total and disjoint."""
    doc = json.loads((FIXTURES / f"estate_{name}.json").read_text())
    blocks = [v for k, v in doc.items() if k.startswith("_provenance")]
    names = {k for k in doc if not k.startswith("_provenance")}
    if len(blocks) == 1 and "applies_to" not in blocks[0]:
        return  # one capture, one sitting: the block covers the file
    claimed = [n for block in blocks for n in block["applies_to"]]
    assert sorted(claimed) == sorted(set(claimed)), "a scenario is claimed twice"
    assert set(claimed) == names


# ── The scan ─────────────────────────────────────────────────────────


class TestTheScanAgainstProducerBuiltPayloads:
    def test_the_live_scan_judges_nothing(self):
        """The estate as it actually is: 26 projects, no parse failures,
        6 hours old.  Worth its own test because every other scenario
        here is synthetic, and a rule that fires on a healthy estate is
        the one defect these fixtures could not otherwise show."""
        assert judge_projects_invariants(scenarios("projects_invariants")["live"],
                                        SCAN_MAX_AGE_HOURS) == []

    def test_a_degraded_scan_names_each_gauge_separately(self):
        """Five independent gauges in one payload, each its own row.
        They are separate faults with separate remedies — a parse failure
        is a document, an unreachable source is a seam — so a roll-up
        here would be Session 46's defect, and the cap that exists for
        ``attention`` is not wanted: the count is fixed at five by the
        producer's schema and cannot run away."""
        out = judge_projects_invariants(
            scenarios("projects_invariants")["degraded"], SCAN_MAX_AGE_HOURS
        )
        assert titles(out) == {
            "Estate scan stale",
            "Estate scan parse failures",
            "Estate scan skipped repositories",
            "Estate scan could not reach sources",
            "Estate scan did not write estate.json",
        }

    def test_a_failed_scan_raises_the_failure_and_not_its_consequence(self):
        """The finding this file was written for.

        ``estate_written`` is False on **every** failing scan, so before
        Session 54 this payload produced two rows for one fault, the
        second of them reading "The last project scan completed without
        rewriting estate.json" — of a scan that did not complete.  With
        ``reminder_hours`` live that is a daily restatement of something
        untrue, which is why a redundancy became worth fixing.
        """
        payload = scenarios("projects_invariants")["failed"]
        assert payload["last_scan"]["error"]
        assert payload["last_scan"]["estate_written"] is False

        out = judge_projects_invariants(payload, SCAN_MAX_AGE_HOURS)
        assert titles(out) == {"Estate scan failed"}

    def test_a_clean_scan_that_did_not_write_still_reports_it(self):
        """The other side of the same guard: the ``estate_written`` rule
        is narrowed, not deleted.  A scan that completed and skipped the
        write is the case its message actually describes."""
        payload = scenarios("projects_invariants")["degraded"]
        assert payload["last_scan"]["error"] is None
        assert "Estate scan did not write estate.json" in titles(
            judge_projects_invariants(payload, SCAN_MAX_AGE_HOURS)
        )

    def test_one_unreachable_source_is_not_reported_as_plural(self):
        """``sources_unreachable`` holds one entry far more often than
        several — it is a list of dead seams, and this estate has one
        seam.  The message reaches a notification body verbatim."""
        payload = scenarios("projects_invariants")["degraded"]
        assert len(payload["last_scan"]["sources_unreachable"]) == 1

        row = next(
            j
            for j in judge_projects_invariants(payload, SCAN_MAX_AGE_HOURS)
            if j.title == "Estate scan could not reach sources"
        )
        assert "1 data source was unreachable" in row.message

    def test_an_empty_scan_runs_table_is_never_ran_not_healthy(self):
        payload = scenarios("projects_invariants")["never_ran"]
        assert payload["scans_total"] == 0
        assert titles(
            judge_projects_invariants(payload, SCAN_MAX_AGE_HOURS)
        ) == {"Estate scan never ran"}


# ── The audit ────────────────────────────────────────────────────────


class TestTheAuditAgainstProducerBuiltPayloads:
    def test_the_live_audit_judges_nothing(self):
        """Three findings and a `warn` on port 3300, all of which this
        surface is supposed to stay quiet about — rule 3."""
        payload = scenarios("audit_invariants")["live"]
        assert payload["last_audit"]["findings_total"] > 0
        assert judge_audit_invariants(payload, AUDIT_MAX_AGE_HOURS) == []

    def test_errored_checks_are_named_from_the_producers_own_summary(self):
        """``check_summary`` is built by ``CheckResult.as_summary()``,
        so this pins the *shape* of an errored check rather than this
        repository's guess at it.  Naming the checks is the point: two
        of seven errored says how much of the audit is unobserved, and
        which two says whether it matters."""
        payload = scenarios("audit_invariants")["errored"]
        summary = payload["last_audit"]["checks"]
        assert set(summary["ports"]) == {"status", "findings", "error"}
        assert summary["ports"]["status"] == "error"

        row = next(
            j
            for j in judge_audit_invariants(payload, AUDIT_MAX_AGE_HOURS)
            if j.title == "Estate audit checks errored"
        )
        assert row.details["errored_checks"] == ["ports", "seams"]
        assert "2 of 7 audit checks errored (ports, seams)" in row.message

    def test_a_stale_errored_run_raises_all_three_without_merging_them(self):
        """Three faults with three remedies — restart the timer, fix the
        broken check, fix the broker credential — so three rows."""
        assert titles(
            judge_audit_invariants(
                scenarios("audit_invariants")["errored"], AUDIT_MAX_AGE_HOURS
            )
        ) == {
            "Estate audit stale",
            "Estate audit checks errored",
            "Estate audit publish failed",
        }

    def test_findings_total_is_carried_but_never_judged(self):
        """Rule 3.  The number is on the age row as evidence, and no
        rule reads it — 8 of today's 10 are the collation family
        :mod:`sysadmin.monitor.collation` already raises here."""
        row = next(
            j
            for j in judge_audit_invariants(
                scenarios("audit_invariants")["errored"], AUDIT_MAX_AGE_HOURS
            )
            if j.title == "Estate audit stale"
        )
        assert "findings_total" in row.details

    def test_an_empty_audit_runs_table_is_never_ran(self):
        assert titles(
            judge_audit_invariants(
                scenarios("audit_invariants")["never_ran"], AUDIT_MAX_AGE_HOURS
            )
        ) == {"Estate audit never ran"}


# ── The audit's port findings ────────────────────────────────────────


class TestAuditFindingsAgainstProducerBuiltPayloads:
    def test_the_live_findings_judge_nothing(self):
        """Today's three findings are two ``docs`` breaches and one
        ``ports`` **warn**, and all three are correctly ignored: docs is
        another repository's conformance, and ``warn`` is availability,
        which ``services.yaml`` owns."""
        payload = scenarios("audit_findings")["live"]
        assert payload["findings"]
        assert judge_audit_findings(payload, PORT_BREACH_MAX_ROWS) == []

    def test_a_real_breach_becomes_one_row_titled_by_its_port(self):
        payload = scenarios("audit_findings")["one_port_breach"]
        finding = payload["findings"][0]
        assert finding["check"] == "ports"
        assert finding["severity"] == "breach"
        assert finding["detail"]["port"] == 3900

        out = judge_audit_findings(payload, PORT_BREACH_MAX_ROWS)
        assert titles(out) == {"Estate port 3900 registry breach"}
        assert out[0].details["port"] == 3900

    def test_the_age_walk_reaches_the_message(self):
        """``standing_days`` and ``age_truncated`` come from
        ``_streak_starts``, which needs several runs to have anything to
        say — the half of this payload a single stored row cannot
        produce, and the reason the fixture holds four."""
        payload = scenarios("audit_findings")["one_port_breach"]
        assert payload["findings"][0]["runs_observed"] == 4
        assert payload["findings"][0]["age_truncated"] is True

        row = judge_audit_findings(payload, PORT_BREACH_MAX_ROWS)[0]
        assert "Standing at least 3 days." in row.message

    def test_six_breaches_collapse_and_still_name_every_port(self):
        """Rule 2: above the cap the count is the news, and nothing is
        lost — the ports move out of the titles into ``details``."""
        payload = scenarios("audit_findings")["six_port_breaches"]
        assert len(payload["findings"]) == 6

        out = judge_audit_findings(payload, PORT_BREACH_MAX_ROWS)
        assert titles(out) == {"Estate port registry breach"}
        assert out[0].details["ports"] == [3900, 3901, 3902, 3903, 3904, 3905]

    def test_the_producers_code_never_reaches_the_wire(self):
        """Pre-staged, and it is the ``PRODUCER_DROPPED_NUDGE_KEYS``
        shape one surface over (``SNAG-ESTATE-006``).

        ``Finding.code`` is a real field on the producer's dataclass —
        ``unclaimed_listener`` here — folded into ``fingerprint`` and
        then dropped: ``AuditFinding`` has no ``code`` column, so the
        route cannot publish one.  ``judge_audit_findings`` reads it
        anyway, which is right and costs nothing while it is absent.

        This asserts the **absence**, so the day estate-manager adds the
        column and the field, the suite says so and the docstring in
        ``judgements.py`` stops being true by itself.
        """
        finding = scenarios("audit_findings")["one_port_breach"]["findings"][0]
        assert "code" not in finding, (
            "estate-manager now publishes `code` on an audit finding — "
            "SNAG-ESTATE-006 is fixed on the producer's side. Drop this "
            "test and the caveat in judge_audit_findings' rule 4; "
            "details['code'] starts carrying a value on its own."
        )
        # Recoverable meanwhile, which is why nothing here parses it.
        assert finding["fingerprint"].endswith(":unclaimed_listener")

        row = judge_audit_findings(
            scenarios("audit_findings")["one_port_breach"], PORT_BREACH_MAX_ROWS
        )[0]
        assert row.details["code"] is None
        assert row.details["fingerprint"] == finding["fingerprint"]


# ── The queue ────────────────────────────────────────────────────────


class TestTheQueueAgainstProducerBuiltPayloads:
    def test_an_idle_queue_judges_nothing(self):
        """``dropped_total: 1`` is live and standing — rule 1's whole
        point.  A ``> 0`` rule on it would have opened a row on this
        payload that no future state could ever clear."""
        payload = scenarios("queue_invariants")["live"]
        assert payload["dropped_total"] == 1
        assert judge_queue_invariants(
            payload, QUEUE_MAX_DEPTH, QUEUE_MAX_WAIT_SECONDS
        ) == []

    def test_a_backlog_and_a_starved_waiter_are_two_rows(self):
        """Both gauges breach in one payload, as they would in life — a
        queue is starved *because* it is backed up.  Two rows because
        they answer different questions: depth says how many are
        blocked, wait says for how long, and a queue can breach either
        alone.

        This payload was captured 2026-08-16 and so predates ADR-0077:
        it is the **legacy producer** specimen, and what it exercises
        now is the fallback. It is deliberately not re-captured — see
        the fixture's ``_provenance.scope``."""
        payload = scenarios("queue_invariants")["backlog"]
        assert payload["depth"] == 5
        assert payload["oldest_waiting_seconds"] == 2880.0
        assert "oldest_unexplained_wait_seconds" not in payload

        out = judge_queue_invariants(payload, QUEUE_MAX_DEPTH, QUEUE_MAX_WAIT_SECONDS)
        assert titles(out) == {"Estate queue backlog", "Estate queue starved"}
        starved = next(j for j in out if j.title == "Estate queue starved")
        assert starved.details["wait_gauge"] == "total"

    def test_the_totals_ride_along_on_both_rows(self):
        """Rule 1's other half: never judged, always reported, so a
        human comparing two runs can see the change this module is
        forbidden to alert on."""
        out = judge_queue_invariants(
            scenarios("queue_invariants")["backlog"],
            QUEUE_MAX_DEPTH,
            QUEUE_MAX_WAIT_SECONDS,
        )
        for row in out:
            assert set(row.details) >= {
                "dropped_total",
                "expired_total",
                "grants_total",
            }

    def test_the_holder_is_carried_as_evidence_for_the_starvation(self):
        """``active_lease`` is the answer to "who is holding it", and it
        is in ``details`` on the starvation row only — the backlog row
        is about the waiters."""
        rows = {
            j.title: j
            for j in judge_queue_invariants(
                scenarios("queue_invariants")["backlog"],
                QUEUE_MAX_DEPTH,
                QUEUE_MAX_WAIT_SECONDS,
            )
        }
        lease = rows["Estate queue starved"].details["active_lease"]
        assert lease["requester"] == "venture-assistant"
        assert "active_lease" not in rows["Estate queue backlog"].details


class TestTheWaitReasonAgainstProducerBuiltPayloads:
    """The three states ADR-0077 introduced, each built by running
    ``Arbiter.submit`` → ``Arbiter.tick`` → ``Arbiter.invariants`` in
    estate-manager's own venv.

    What a literal could not have supplied here is the *pairing*.
    ``waiting_reason`` and ``oldest_unexplained_wait_seconds`` are two
    fields derived from one another by the producer, and a keyword
    override can set them into a combination the arbiter cannot emit —
    which is how a consumer comes to rely on a shape that never
    arrives. Every pairing below is the producer's.
    """

    def _judge(self, name):
        return judge_queue_invariants(
            scenarios("queue_invariants")[name], QUEUE_MAX_DEPTH, QUEUE_MAX_WAIT_SECONDS
        )

    def test_the_live_queue_judges_nothing(self):
        """8400 as it actually answered on 2026-08-30, straight off the
        wire: 27 grants, 3 drops, nothing waiting. The healthy payload
        is the one case a synthetic fixture cannot show, and the case a
        rule most easily fires on by accident."""
        payload = scenarios("queue_invariants")["live_2026_08_30"]
        assert payload["waiting_reason"] is None
        assert payload["dropped_total"] == 3
        assert judge_queue_invariants(
            payload, QUEUE_MAX_DEPTH, QUEUE_MAX_WAIT_SECONDS
        ) == []

    def test_the_monday_wait_judges_nothing(self):
        """The whole reason this changed, in the producer's own numbers.

        1038 s is the top of the 915-1038 s band estate-manager measured
        over five nights, and it is over this repository's threshold.
        The arbiter says a declared holder explains it. Before
        2026-08-30 this payload raised "Estate queue starved" every
        Monday morning and was wrong every time."""
        payload = scenarios("queue_invariants")["behind_holder"]
        assert payload["waiting_reason"] == "behind_holder"
        assert payload["oldest_waiting_seconds"] > QUEUE_MAX_WAIT_SECONDS
        assert payload["oldest_unexplained_wait_seconds"] is None
        assert payload["active_lease"]["requester"] == "venture-drain"
        assert self._judge("behind_holder") == []

    @pytest.mark.parametrize("name", ["holder_overdue", "nothing_granted"])
    def test_the_two_conditions_worth_an_alert_still_reach_one(self, name):
        """The mask must not swallow the thing it was built beside.

        These are the disjunction's two limbs — the message named them
        both before ADR-0077 and still does — and a mask that quietened
        either would be worse than the gauge it replaced."""
        payload = scenarios("queue_invariants")[name]
        assert payload["oldest_unexplained_wait_seconds"] == payload[
            "oldest_waiting_seconds"
        ]
        out = self._judge(name)
        assert titles(out) == {"Estate queue starved"}
        assert out[0].details["wait_gauge"] == "unexplained"
        assert out[0].details["waiting_reason"] == name

    def test_the_holder_is_carried_on_an_overdue_row_and_absent_on_a_starved_one(self):
        """``active_lease`` answers "who is holding it", and the two
        unmasked states differ in whether there is one at all —
        ``nothing_granted`` means no holder exists, which is the
        distinction the old single gauge could not carry either."""
        overdue = self._judge("holder_overdue")[0]
        assert overdue.details["active_lease"]["requester"] == "venture-drain"
        assert self._judge("nothing_granted")[0].details["active_lease"] is None

    def test_a_backlog_behind_a_declared_holder_is_still_a_backlog(self):
        """``depth`` did not change with the wait gauge. A Monday queue
        deep enough to breach is still worth a row — the fix narrowed
        what counts as *starvation*, not what counts as a queue."""
        payload = dict(scenarios("queue_invariants")["behind_holder"])
        payload["depth"] = QUEUE_MAX_DEPTH + 1
        out = judge_queue_invariants(payload, QUEUE_MAX_DEPTH, QUEUE_MAX_WAIT_SECONDS)
        assert titles(out) == {"Estate queue backlog"}


# ── The live half ────────────────────────────────────────────────────


@pytest.mark.skipif(
    not _estate_available(), reason=f"estate-manager ({ESTATE_URL}) unreachable"
)
class TestTheKeysTheJudgeReadsAreStillServed:
    """Producer drift, which no fixture can catch — it is a photograph.

    ``tests/test_estate_project_contracts.py`` makes this argument at
    length for the two project routes; this is the same two-half
    machinery for the three surfaces that file does not cover.  Keys are
    asserted against the **raw payload** rather than through the judge,
    for that file's reason: every rule here is a ``.get()`` with a
    falsey default, so a renamed field does not raise, does not log and
    does not half-work — it produces a clean estate, which is also the
    correct answer most days.
    """

    def _get(self, path: str) -> dict[str, Any]:
        response = httpx.get(f"{ESTATE_URL}{path}", timeout=10.0)
        response.raise_for_status()
        return response.json()

    def _check_ran(self, check: str) -> dict[str, Any]:
        """What the last audit says about one check — a filtered guard's discriminator.

        A guard that filters ``/api/audit/findings`` down to one check
        asserts nothing while that check files nothing, and an empty
        filter cannot be told apart from a check the producer has
        **retired**: both are a loop that runs and executes no body.
        ``last_audit.checks`` is where the estate says which checks ran
        and whether each errored, so it is the one surface that
        separates zero-because-clean from zero-because-blind and from
        zero-because-gone — ``ports_checked``'s rule, asked of another
        repository's audit.

        The membership assertion lives here rather than at each call
        site so the sentence is stated once; the ``error`` reading is
        left to the caller, because what a blind check costs differs per
        family and the message should name it.
        """
        checks = self._get("/api/audit/invariants")["last_audit"]["checks"]
        assert check in checks, (
            f"estate-manager's audit no longer runs a {check!r} check, so every "
            f"guard here that filters /api/audit/findings down to it has been "
            f"silently retired — and judge_audit_findings speaks for it by "
            f"ADR-0006. ran: {sorted(checks)}"
        )
        return checks[check]

    def test_the_scans_gauges_are_all_present(self):
        payload = self._get("/api/projects/invariants")
        assert "scans_total" in payload
        assert set(payload["last_scan"]) >= {
            "run_type",
            "started_at",
            "finished_at",
            "age_seconds",
            "parse_failures",
            "repos_skipped",
            "sources_unreachable",
            "estate_written",
            "error",
        }

    def test_the_audits_gauges_are_all_present(self):
        payload = self._get("/api/audit/invariants")
        assert "audits_total" in payload
        assert set(payload["last_audit"]) >= {
            "run_type",
            "started_at",
            "age_seconds",
            "checks_run",
            "checks_errored",
            "findings_total",
            "checks",
            "publish_error",
            "error",
        }

    def test_every_check_summary_carries_the_error_slot(self):
        """``judge_audit_invariants`` names the errored checks by asking
        each summary for its ``error``.  A producer that moved the error
        into ``status`` alone would leave the row saying "unnamed"."""
        checks = self._get("/api/audit/invariants")["last_audit"]["checks"]
        assert checks
        for name, summary in checks.items():
            assert "error" in summary, name

    def test_every_finding_carries_what_a_breach_would_be_read_by(self):
        payload = self._get("/api/audit/findings")
        assert payload["findings"], "the audit has published no findings to check"
        for finding in payload["findings"]:
            assert set(finding) >= {
                "check",
                "severity",
                "subject",
                "summary",
                "fingerprint",
                "detail",
                "standing_days",
                "runs_observed",
                "age_truncated",
            }

    def test_a_live_ports_breach_still_carries_an_integer_port(self):
        """No longer pre-staged, and the empty branch is what keeps it honest.

        ``_port_of`` refuses a finding whose port will not parse rather
        than titling it from ``subject``, so a producer moving the port
        out of ``detail`` would silence the family rather than break it.

        **The population arrived and this docstring was the last thing
        to know** (2026-09-05).  It read *"the ports check has never
        reached ``breach`` on this box (today's one finding is
        ``warn``), so this asserts nothing until the day it does"* —
        false when measured: the live audit carries one ``breach``,
        ``ports:port 3110:unclaimed_listener``, and coverage over a
        green full suite reports the assertion below as **evaluated**.
        So the guard is live and its own prose said it was not.

        It can go back, which is why the branch is here rather than the
        sentence merely being corrected.  Port 3110 is a transient
        holder — Session 57's dev-server shape — and the finding set
        moved from 6 to 4 inside the sitting that wrote this, so this
        filter oscillates between evaluated and vacuous with nothing but
        an editor's window deciding which.  A guard whose status depends
        on the hour must state its status to the runner, not to the
        reader: see :meth:`_check_ran`.
        """
        breaches = [
            finding
            for finding in self._get("/api/audit/findings")["findings"]
            if finding["check"] == "ports" and finding["severity"] == "breach"
        ]
        if not breaches:
            assert self._check_ran("ports")["error"] is None, (
                "the ports check errored, so its zero breaches are "
                "zero-because-blind rather than a clean estate, and the "
                "assertion below stayed unevaluated for a reason nothing "
                "else on this surface reports"
            )
            return
        for finding in breaches:
            port = finding["detail"]["port"]
            assert isinstance(port, int) and not isinstance(port, bool)

    def test_a_live_wiring_finding_still_separates_its_two_events(self):
        """Pre-staged, and it pins the correction rather than the claim.

        ``judge_audit_wiring``'s stated limit was closed at the producer
        on 2026-09-03 (their ADR-0102, message ``b96a337c``): a
        ``wiring`` fingerprint became ``wiring:<hook>:<code>:<event>``,
        where the event had lived in ``detail`` alone.  That correction
        is written into the docstring from **their source**, because
        ``wiring`` has filed zero findings in the whole history and the
        wire here cannot show it — so this asserts nothing until the
        first one arrives, which is also the first moment it could catch
        anything.

        Both halves, because they can fail apart.  ``detail['event']``
        is what rule 1 builds the identity from, so a producer promoting
        it *out* of ``detail`` and into the fingerprint alone would
        silence this family rather than break it — the ports test's
        argument one check over.  The fourth segment is what the
        docstring now asserts about a format this repository does not
        own; a red there is a conversation with estate-manager, not a
        bug in this module.

        **Falsified against their real dataclass rather than a
        reconstruction of it**, because a pin over an empty population
        is otherwise green whatever it asserts.  Driving
        ``estate_service.audit.finding.Finding.as_payload`` here: the
        shape they ship passes; a rolled-back ``aspect=None`` goes red
        (``wiring:require-handoff.sh:hook_not_wired``); an ``aspect``
        disagreeing with ``detail['event']`` goes red; and the
        whole-file finding gaining one goes red on the colon count.

        **The pre-staging is stated to the runner now, not only to the
        reader** (2026-09-05).  ``wiring`` has filed zero findings in
        the whole history, so for the life of this test the loop has run
        its filter over every finding and executed **none** of its
        assertions — measured rather than reasoned: under coverage
        across a green full suite the three ``assert`` lines below are
        three of the eight statements in ``tests/`` never evaluated.
        A docstring saying "this asserts nothing until the day it does"
        is read by whoever opens the file and by nobody who runs it.

        The premise **reports and never refuses**, which is the opposite
        of the sibling live drive's.  ``test_arbitrated_stops_live.py``
        fails when no lease names ``stopped_units``, because such a lease
        is expected to exist; zero wiring findings is the estate's hooks
        being correctly wired, so a premise that failed here would turn a
        healthy estate into a red suite — the calendar writing a failure,
        which this repository has refused four times over.  What must not
        pass unnoticed is the *other* road to zero, and it is
        :meth:`_check_ran` that separates them.
        """
        findings = [
            finding
            for finding in self._get("/api/audit/findings")["findings"]
            if finding["check"] == "wiring"
        ]
        if not findings:
            assert self._check_ran("wiring")["error"] is None, (
                "the wiring check errored, so its zero findings are "
                "zero-because-blind rather than a correctly wired estate, and "
                "the assertions below stayed unevaluated for a reason nothing "
                "else on this surface reports"
            )
            return
        for finding in findings:
            event = finding["detail"].get("event")
            if event is None:
                # The whole-file finding, which declares no event and
                # takes no aspect.  rule 2's discriminator.
                assert finding["fingerprint"].count(":") == 2, finding["fingerprint"]
                continue
            assert isinstance(event, str) and event
            assert finding["fingerprint"].endswith(f":{event}"), (
                "estate-manager has stopped appending the event to a wiring "
                "fingerprint — the limit judge_audit_wiring records as closed "
                "is open again, and two events from one hook share an age. "
                f"got {finding['fingerprint']!r}"
            )

    def test_the_queues_two_gauges_are_still_gauges(self):
        payload = self._get("/api/queue/invariants")
        assert set(payload) >= {
            "depth",
            "oldest_waiting_seconds",
            "dropped_total",
            "expired_total",
            "grants_total",
            "active_lease",
        }
        assert isinstance(payload["depth"], int)
        assert payload["oldest_waiting_seconds"] is None or isinstance(
            payload["oldest_waiting_seconds"], float
        )

    def test_the_wait_discriminator_is_still_published(self):
        """The one thing the fallback cannot tell us.

        ``_starvation_gauge`` survives this key vanishing — it drops to
        the old gauge and labels the row — so its absence is silent in
        every other test in this repository. This is where it is loud.
        A red here means 8400 stopped publishing the discrimination and
        the Monday false alarm is back, which is a conversation with
        estate-manager rather than a bug in this module."""
        payload = self._get("/api/queue/invariants")
        assert "oldest_unexplained_wait_seconds" in payload
        assert "waiting_reason" in payload
        assert payload["waiting_reason"] in (
            None,
            "behind_holder",
            "holder_overdue",
            "nothing_granted",
        )

    def test_the_masked_gauge_never_exceeds_the_gauge_it_masks(self):
        """The producer's own invariant, asserted from this side.

        ``oldest_unexplained_wait_seconds`` is ``oldest_waiting_seconds``
        with one cause masked to null, so it is that number or nothing —
        never a larger one and never a number of its own. If it ever
        became independently computed, this repository would be
        thresholding something it has not read."""
        payload = self._get("/api/queue/invariants")
        unexplained = payload["oldest_unexplained_wait_seconds"]
        assert unexplained is None or unexplained == payload["oldest_waiting_seconds"]


class TestTheFilteredGuardsReportTheirOwnEmptiness:
    """The discriminator, driven at stubs so it outlives the finding.

    Two guards in :class:`TestTheKeysTheJudgeReadsAreStillServed` filter
    ``/api/audit/findings`` down to one check and assert about the
    members.  While the filtered set is empty they run and assert
    nothing — the shape a green suite cannot report, since an empty
    ``for`` completes.  Measured 2026-09-05 under coverage across a
    green full suite: ``wiring``'s three assertions were three of the
    **eight** statements in ``tests/`` never once evaluated, and they had
    been so since the guard was written.

    This class is deliberately **not** gated on estate availability.  The
    live class can only exercise whichever branch the box happens to be
    in — today that is the empty one for ``wiring`` and the populated one
    for ``ports`` — so the branch it does not take is unasserted exactly
    when it matters.  ``_get`` is stubbed here so both roads to zero are
    driven on every run, on any box, with no audit in the way.

    The rule the four tests pin is that **the premise reports and never
    refuses**.  A clean check filing nothing must stay green — a failing
    premise would make a correctly wired estate a red suite — while a
    check that has been *retired* or has *errored* must go red, because
    those reach zero by roads that silently retire the guard.
    ``ports_checked``'s rule: zero-because-clean is never served as
    zero-because-blind.
    """

    OK = {"error": None, "status": "ok", "findings": 0}
    ERRORED = {"error": "hook directory unreadable", "status": "error", "findings": 0}

    def _driver(self, checks, findings):
        """A live-class instance whose only wire is a dict."""
        instance = TestTheKeysTheJudgeReadsAreStillServed()
        instance._get = lambda path: (  # type: ignore[method-assign]
            {"last_audit": {"checks": checks}}
            if path == "/api/audit/invariants"
            else {"findings": findings}
        )
        return instance

    def test_a_clean_check_filing_nothing_is_not_a_failure(self):
        """The half that must not fire, and the reason the premise is a report.

        Zero ``wiring`` findings is the estate's hooks being correctly
        wired.  ``test_arbitrated_stops_live.py``'s premise fails on an
        empty population because a lease naming ``stopped_units`` is
        expected to exist; here the empty population *is* the good news,
        so refusing it would be the calendar writing a failure.
        """
        driver = self._driver({"wiring": self.OK, "ports": self.OK}, [])
        driver.test_a_live_wiring_finding_still_separates_its_two_events()
        driver.test_a_live_ports_breach_still_carries_an_integer_port()

    def test_a_retired_check_is_a_silently_retired_guard(self):
        """The road to zero no count can see.

        A producer dropping the check empties the filter for ever, and
        the loop goes on completing.  ``judge_audit_findings`` speaks for
        both checks by ADR-0006, so this is a conversation with
        estate-manager rather than a bug here — which is why the message
        names them and lists the checks that did run.
        """
        driver = self._driver({"ports": self.OK}, [])
        with pytest.raises(AssertionError, match="no longer runs a 'wiring' check"):
            driver.test_a_live_wiring_finding_still_separates_its_two_events()

    def test_a_check_that_errored_is_zero_because_blind(self):
        """The second road, and the one that looks most like health.

        An errored check files no findings, so the filter is empty and
        every assertion is skipped — identical output to a clean estate.
        The producer already publishes the difference in
        ``last_audit.checks[...]['error']``; the defect was never a
        missing signal, only an unread one.
        """
        driver = self._driver({"wiring": self.ERRORED, "ports": self.ERRORED}, [])
        with pytest.raises(AssertionError, match="zero-because-blind"):
            driver.test_a_live_wiring_finding_still_separates_its_two_events()
        with pytest.raises(AssertionError, match="zero-because-blind"):
            driver.test_a_live_ports_breach_still_carries_an_integer_port()

    def test_a_populated_filter_still_reaches_the_members(self):
        """The fix must not buy its premise by skipping the work.

        The empty branch returns, so a mistake there — returning
        unconditionally, or filtering on the wrong key — would leave both
        guards green for ever with a premise standing in for the
        assertions.  Driven at a member that is deliberately **wrong** so
        a reached body is observable rather than inferred.
        """
        malformed = [
            {
                "check": "wiring",
                "severity": "warn",
                "detail": {"event": "post_commit"},
                "fingerprint": "wiring:require-handoff.sh:hook_not_wired",
            }
        ]
        driver = self._driver({"wiring": self.OK}, malformed)
        with pytest.raises(AssertionError, match="stopped appending the event"):
            driver.test_a_live_wiring_finding_still_separates_its_two_events()

        bad_port = [
            {
                "check": "ports",
                "severity": "breach",
                "detail": {"port": True},
                "fingerprint": "ports:port 1:unclaimed_listener",
            }
        ]
        driver = self._driver({"ports": self.OK}, bad_port)
        with pytest.raises(AssertionError):
            driver.test_a_live_ports_breach_still_carries_an_integer_port()
