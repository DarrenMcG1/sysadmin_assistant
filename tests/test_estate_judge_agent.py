"""``EstateJudgeAgent``'s lifecycle — dedup, the sweep, and unknown.

Three properties, each of which is a defect this repository has already
paid for once somewhere else:

1. **No flip-flop.** ``monitor/collation.py`` records that dedup and a
   set-based resolve are mutually exclusive — *when the sweep's
   exclusion set is the titles the run raised*.  A deduplicating family
   raises nothing on its second run, so its still-true row is resolved,
   then re-raised, and because the tray fingerprints on
   ``{severity}:{title}`` every flip clears the suppression and notifies
   again: a pile-up that also reads as recovery.  This agent excludes
   the titles the run **judged**, which is a different set, and these
   tests are what pin the difference.

2. **A partial pull resolves nothing outside itself.** Four independent
   surfaces come from one process, so three answering while one 500s is
   a real state.  Sweeping globally would close every health breach and
   idle nudge on the strength of a payload nobody received —
   ``_resolve_recovered``'s "resolving on unknown announces a recovery
   nobody observed", applied per surface instead of per service.

3. **8400 being down is not this agent's alert.**
   ``estate-manager-api`` is an ``http`` entry in ``services.yaml``
   already, and a second owner of one lifecycle is the defect this
   repository has now found at three scales.

Sessions are mocked, so a ``WHERE`` clause has no effect here: the
resolve is asserted on the ids handed to ``session.execute`` and on the
compiled statement, not by round trip.  The same limit
``tests/test_alert_recovery.py`` records.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.estate.agent import SURFACE_DETAIL_KEY, EstateJudgeAgent
from sysadmin.estate.client import SURFACES, SurfaceResult
from sysadmin.estate.judgements import DEFAULT_SEVERITY, TRANSIENT_HOLDER_SEVERITY
from sysadmin.units.ports import attribution_from_blob

HOUR = 3600.0

# A payload set with exactly one fault in it: the scan is 30 hours old.
STALE_SCAN = {
    "scans_total": 12,
    "last_scan": {
        "run_type": "timer",
        "started_at": "2026-08-12T04:30:00+00:00",
        "finished_at": "2026-08-12T04:30:02+00:00",
        "age_seconds": 30 * HOUR,
        "projects_scanned": 26,
        "undeclared": 9,
        "parse_failures": 0,
        "repos_skipped": 0,
        "sources_unreachable": [],
        "estate_written": True,
        "error": None,
    },
}
FRESH_SCAN = {
    **STALE_SCAN,
    "last_scan": {**STALE_SCAN["last_scan"], "age_seconds": 2 * HOUR},
}
CLEAN_AUDIT = {
    "audits_total": 3,
    "last_audit": {
        "run_type": "timer",
        "verdict": "findings",
        "started_at": "2026-08-13T05:03:00+00:00",
        "finished_at": "2026-08-13T05:03:01+00:00",
        "age_seconds": 2 * HOUR,
        "checks_run": 4,
        "checks_errored": 0,
        "findings_total": 10,
        "checks": {},
        "publish_error": None,
        "error": None,
    },
}
#: The audit's findings surface as served on 2026-08-14 — one ``warn``,
#: which this repository does not judge, so the default pull is quiet.
#: A ``breach`` payload is built per-test by ``port_breach``.
NO_FINDINGS = {
    "findings": [
        {
            "check": "ports",
            "severity": "warn",
            "subject": "port 3300",
            "summary": "port 3300 is claimed by venture-assistant but nothing is listening",
            "code": "claimed_but_silent",
            "detail": {"port": 3300},
            "standing_days": 1.3,
        }
    ]
}


def port_breach(port=8888):
    """One unregistered listener, in the shape 8400 serves."""
    return {
        "findings": [
            {
                "check": "ports",
                "severity": "breach",
                "subject": f"port {port}",
                "summary": f"port {port} is listening inside the registry's range",
                "fingerprint": f"ports:port {port}:unclaimed_listener",
                # No `code` key, deliberately: the producer computes one
                # and `AuditFinding` has no column for it, so it never
                # reaches the wire (SNAG-ESTATE-006). A literal that
                # invents a field the producer drops is the thing
                # `tests/test_estate_surface_payloads.py` exists to stop.
                "detail": {"port": port},
                "standing_days": 2.0,
                "runs_observed": 12,
                "age_truncated": False,
            }
        ]
    }


IDLE_QUEUE = {
    "depth": 0,
    "oldest_waiting_seconds": None,
    "dropped_total": 1,
    "expired_total": 0,
    "grants_total": 2,
    "active_lease": None,
}
NO_ATTENTION = {"health": [], "nudges": []}


def results(scan=FRESH_SCAN, attention=NO_ATTENTION, findings=None, unread=()):
    """A full pull, with the named surfaces failed."""
    findings = NO_FINDINGS if findings is None else findings
    payloads = {
        "projects_invariants": scan,
        "projects_attention": attention,
        "audit_invariants": CLEAN_AUDIT,
        "audit_findings": findings,
        "queue_invariants": IDLE_QUEUE,
    }
    return {
        name: (
            SurfaceResult(surface=name, error="ConnectError: refused")
            if name in unread
            else SurfaceResult(surface=name, payload=payloads[name])
        )
        for name in SURFACES
    }


class FakeAlert:
    """Enough of ``Alert`` for the dedup, the sweep and the refresh.

    ``message`` and ``agent`` arrived with ``SNAG-AGENT-009``: a held
    judgement now rewrites the standing row's sentence and its blob, so a
    stand-in without those two fields models a row this loop can no
    longer be handed.

    ``severity`` arrived with ``SNAG-ESTATE-010`` for the same reason and
    is **not** optional: the column is ``NOT NULL`` behind
    ``chk_alert_severity``, so a row with no rung is one the database
    cannot hold, and a stand-in permitting it would let a caller that
    forgot to pass one pass a test the database would refuse.  It
    defaults to the rung an ordinary judgement opens at, which is what
    every standing row in this file is.
    """

    def __init__(self, title, surface, resolved=False, message=None,
                 severity=DEFAULT_SEVERITY):
        self.id = uuid.uuid4()
        self.agent = "estate_judge"
        self.title = title
        self.message = message
        self.severity = severity
        self.details = {SURFACE_DETAIL_KEY: surface} if surface else {}
        self.resolved = resolved


@pytest.fixture
def agent():
    return EstateJudgeAgent()


def _session(open_alerts):
    """A session whose ``_open_alerts`` query returns ``open_alerts``.

    One ``execute`` answers two queries here — the open alerts and
    ``_attribution``'s newest ``unit_audits`` row — so the sweep half
    has to be answered with a state a **database** can produce.
    ``scalar_one_or_none`` returned a bare ``MagicMock`` until
    2026-08-29, which stood for a ``UnitAudit`` whose ``scanned_at``
    was a mock; that was invisible while ``PortAttribution.of()``
    dropped it, and the moment ``details`` began carrying the sweep's
    age unconditionally it reached ``json.dumps`` in ``refresh_alert``
    and raised.  ``None`` — *no sweep has ever run* — is a real state,
    is what these tests mean (none of them is about attribution), and
    is the one a fake cannot get wrong.
    """
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    scalars = MagicMock()
    scalars.all.return_value = open_alerts
    select_result = MagicMock()
    select_result.scalars.return_value = scalars
    select_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=select_result)
    return session


async def _run(agent, session, pull):
    """Drive ``_execute`` with a stubbed pull, bypassing HTTP."""
    import sysadmin.estate.agent as module

    async def fake_pull_all(http, base_url):
        return pull

    original = module.client.pull_all
    module.client.pull_all = fake_pull_all
    try:
        return await agent._execute(session)
    finally:
        module.client.pull_all = original


# ---------------------------------------------------------------------------
# 0. The audit's two surfaces are two surfaces
# ---------------------------------------------------------------------------


class TestTheAuditsTwoSurfaces:
    """``/api/audit/invariants`` and ``/api/audit/findings`` come from one
    check run and must still fail independently.

    Folding them into one surface id would have been the smaller change
    and is the bug: "did the audit complete" and "what did it find" are
    read over two HTTP calls, so one can answer while the other 500s. The
    sweep is scoped per surface, so sharing an id would let a successful
    read of the invariants close every port row raised off a findings
    payload nobody received — ``_resolve_recovered``'s "resolving on
    unknown announces a recovery nobody observed", one level down from
    where this package already applies it.
    """

    async def test_a_port_breach_is_raised_off_its_own_surface(self, agent):
        session = _session([])
        result = await _run(agent, session, results(findings=port_breach(8888)))

        assert result.alerts_raised == 1
        assert result.details["by_surface"]["audit_findings"] == 1
        assert result.details["by_surface"]["audit_invariants"] == 0

    async def test_a_port_row_survives_an_unread_findings_surface(self, agent):
        """The load-bearing one. ``audit_invariants`` answers, so the
        audit looks fine; the port row must not be swept on the strength
        of that."""
        open_row = FakeAlert("Estate port 8888 registry breach", "audit_findings")
        session = _session([open_row])

        result = await _run(agent, session, results(unread=("audit_findings",)))

        assert result.details["resolved"] == 0
        assert "audit_findings" in result.details["unread_surfaces"]

    async def test_a_cleared_port_breach_resolves_once(self, agent):
        open_row = FakeAlert("Estate port 8888 registry breach", "audit_findings")
        session = _session([open_row])

        result = await _run(agent, session, results())

        assert result.details["resolved"] == 1
        assert result.alerts_raised == 0

    async def test_a_standing_port_breach_is_neither_re_raised_nor_swept(self, agent):
        open_row = FakeAlert("Estate port 8888 registry breach", "audit_findings")
        session = _session([open_row])

        result = await _run(agent, session, results(findings=port_breach(8888)))

        assert result.alerts_raised == 0
        assert result.details["resolved"] == 0
        assert result.details["standing"] == 1

    async def test_a_breach_reclassified_transient_quietens_the_standing_row(
        self, agent, monkeypatch
    ):
        """``SNAG-ESTATE-010``, at the family it was filed against.

        The founding case exactly: a breach raised at ``warning`` before
        the sweep's attribution reached this family, judged ``info`` now
        because the port turns out to be held by an editor's dev server.
        Dedup skips the raise — correctly — and until 2026-08-28 skipped
        the reclassification with it, so the two live rows sat at
        ``warning`` for the life of a VS Code window and were restated at
        that rung by ``reminder_hours`` throughout.

        Note what is **not** asserted: no row is raised, none resolved,
        and the count of standing faults does not move.  A quietening
        that showed up in any of those would be the flip-flop
        ``monitor/collation.py`` refuses, wearing this fix's clothes.
        """
        monkeypatch.setattr(
            agent,
            "_attribution",
            AsyncMock(
                return_value=attribution_from_blob(
                    {"transient_ports": {"user:code-oss.scope": [8888]}},
                    "2026-08-28T09:00:00+00:00",
                )
            ),
        )
        open_row = FakeAlert("Estate port 8888 registry breach", "audit_findings")
        assert open_row.severity == DEFAULT_SEVERITY
        session = _session([open_row])

        result = await _run(agent, session, results(findings=port_breach(8888)))

        assert open_row.severity == TRANSIENT_HOLDER_SEVERITY
        assert open_row.details["holder"]["transient"] is True
        assert result.alerts_raised == 0
        assert result.details["resolved"] == 0
        assert result.details["standing"] == 1
        assert result.details["refreshed"] == 1

    async def test_an_ordinary_breach_leaves_the_standing_rung_alone(
        self, agent, monkeypatch
    ):
        """The witness, and it carries the previous test's whole verdict.

        A judge that had stopped computing the quiet rung at all, or an
        attribution that no longer reached this family, would leave the
        row at ``warning`` and look identical.  Same fixture, same
        ``_execute``, one variable moved: the port is not in the
        transient map.
        """
        monkeypatch.setattr(
            agent,
            "_attribution",
            AsyncMock(
                return_value=attribution_from_blob(
                    {"unit_ports": {"system:nginx.service": [8888]}},
                    "2026-08-28T09:00:00+00:00",
                )
            ),
        )
        open_row = FakeAlert("Estate port 8888 registry breach", "audit_findings")
        session = _session([open_row])

        await _run(agent, session, results(findings=port_breach(8888)))

        assert open_row.severity == DEFAULT_SEVERITY

    async def test_an_unread_invariants_surface_does_not_stop_the_findings(self, agent):
        """The other direction, and the reason this is not one surface
        with two payloads: a 500 on the invariants route must not cost
        the estate its port breaches."""
        session = _session([])
        result = await _run(
            agent,
            session,
            results(findings=port_breach(8888), unread=("audit_invariants",)),
        )

        assert result.alerts_raised == 1
        assert result.details["by_surface"]["audit_findings"] == 1
        assert "audit_invariants" not in result.details["by_surface"]


# ---------------------------------------------------------------------------
# 1. Dedup and the sweep, together
# ---------------------------------------------------------------------------


class TestNoFlipFlop:
    async def test_a_new_fault_is_raised(self, agent):
        session = _session([])
        result = await _run(agent, session, results(scan=STALE_SCAN))

        assert result.alerts_raised == 1
        assert result.details["standing"] == 1
        assert session.add.call_count == 1

    async def test_a_standing_fault_is_neither_re_raised_nor_resolved(self, agent):
        """The whole point.

        Run 2 sees the same fault with a row already open. It must raise
        nothing (that is the ``_check_thresholds`` pile-up: at hourly
        polling, 24 rows a day for one stale scan) **and** resolve
        nothing (that is the flip-flop, which would clear the tray's
        fingerprint and re-notify on the next run).
        """
        open_row = FakeAlert("Estate scan stale", "projects_invariants")
        session = _session([open_row])

        result = await _run(agent, session, results(scan=STALE_SCAN))

        assert result.alerts_raised == 0
        assert result.details["resolved"] == 0
        assert result.details["standing"] == 1
        assert session.add.call_count == 0

    async def test_a_cleared_fault_is_resolved_once(self, agent):
        open_row = FakeAlert("Estate scan stale", "projects_invariants")
        session = _session([open_row])

        result = await _run(agent, session, results(scan=FRESH_SCAN))

        assert result.details["resolved"] == 1
        assert result.alerts_raised == 0

    async def test_standing_is_reported_beside_raised(self, agent):
        """``raised`` is 0 on every run after the first, so a run
        reporting only ``raised`` reads as a clean estate. The collation
        family reports ``mismatched`` for the same reason."""
        session = _session([FakeAlert("Estate scan stale", "projects_invariants")])
        result = await _run(agent, session, results(scan=STALE_SCAN))

        assert result.details["raised"] == 0
        assert result.details["standing"] == 1


# ---------------------------------------------------------------------------
# 2. A partial pull
# ---------------------------------------------------------------------------


class TestUnknownIsNotGoodNews:
    async def test_an_unread_surfaces_rows_are_not_resolved(self, agent):
        """attention 500s while the other three answer. Its open rows
        must survive: nothing observed them clearing."""
        open_row = FakeAlert("Project imbabots health breach", "projects_attention")
        session = _session([open_row])

        result = await _run(agent, session, results(unread={"projects_attention"}))

        assert result.details["resolved"] == 0
        assert "projects_attention" in result.details["unread_surfaces"]

    async def test_a_read_surfaces_rows_are_still_resolved(self, agent):
        """The other half: a partial pull must not stop the surfaces
        that *did* answer from being judged and swept."""
        stale_scan_row = FakeAlert("Estate scan stale", "projects_invariants")
        attention_row = FakeAlert("Project a health breach", "projects_attention")
        session = _session([stale_scan_row, attention_row])

        result = await _run(agent, session, results(unread={"projects_attention"}))

        assert result.details["resolved"] == 1

    async def test_nothing_reachable_means_nothing_written(self, agent):
        """8400 down. No judgements, no raises, and — the important
        half — no resolves. Every open row survives."""
        session = _session(
            [
                FakeAlert("Estate scan stale", "projects_invariants"),
                FakeAlert("Estate audit stale", "audit_invariants"),
            ]
        )

        result = await _run(agent, session, results(unread=set(SURFACES)))

        assert result.alerts_raised == 0
        assert result.details["resolved"] == 0
        assert result.details["standing"] == 0
        assert result.details["surfaces_read"] == []

    async def test_an_unreachable_estate_raises_no_alert_of_its_own(self, agent):
        """``estate-manager-api`` is an ``http`` entry in services.yaml,
        polled every 300 s, and both estate timers sit beside it. A
        second owner of that lifecycle closes a row while the first
        still holds it true."""
        session = _session([])

        result = await _run(agent, session, results(unread=set(SURFACES)))

        assert session.add.call_count == 0
        assert result.alerts_raised == 0

    async def test_unread_surfaces_are_named_not_counted(self, agent):
        """Which surface is dark decides whether it matters — the rule
        ``journal.py`` records for ``truncated_sources``."""
        session = _session([])
        result = await _run(agent, session, results(unread={"queue_invariants"}))

        assert list(result.details["unread_surfaces"]) == ["queue_invariants"]


# ---------------------------------------------------------------------------
# 3. The surface key
# ---------------------------------------------------------------------------


class TestTheSurfaceKey:
    async def test_every_raised_row_carries_its_surface(self, agent):
        session = _session([])
        await _run(agent, session, results(scan=STALE_SCAN))

        alert = session.add.call_args[0][0]
        assert alert.details[SURFACE_DETAIL_KEY] == "projects_invariants"

    async def test_a_row_with_no_surface_key_is_never_swept(self, agent):
        """Left open rather than resolved: a stale row is a visible
        fault, a false recovery is an invisible one. Not a live case —
        every row this agent writes carries the key — but the branch is
        the guard against a future edit."""
        session = _session([FakeAlert("Estate scan stale", surface=None)])

        result = await _run(agent, session, results(scan=FRESH_SCAN))

        assert result.details["resolved"] == 0


# ---------------------------------------------------------------------------
# The transaction, and where the HTTP happens
# ---------------------------------------------------------------------------


class TestTheHttpIsOutsideTheTransaction:
    async def test_nothing_touches_the_session_before_the_pull(self, agent):
        """Session 41 gives ``_execute`` a session that has never been
        flushed, so its transaction opens at the first statement. Four
        HTTP round trips against a hung 8400 inside an open transaction
        is SNAG-AGENT-003 again on a host that sets
        ``idle_in_transaction_session_timeout=1min`` — the rule
        ``files/review.py`` learned for inference calls."""
        import sysadmin.estate.agent as module

        session = _session([])
        seen: list[int] = []

        async def watching_pull(http, base_url):
            seen.append(session.execute.call_count + session.add.call_count)
            return results()

        original = module.client.pull_all
        module.client.pull_all = watching_pull
        try:
            await agent._execute(session)
        finally:
            module.client.pull_all = original

        assert seen == [0]


# ---------------------------------------------------------------------------
# 5. One row per title per run
# ---------------------------------------------------------------------------


class TestOneRowPerTitlePerRun:
    """``open_titles`` is a set that the raise loop updates as it goes.

    ``judged`` may legitimately hold two entries with one title, and the
    module that produces them says so: ``judge_audit_findings`` rule 4
    keeps the finding's ``code`` out of the title on purpose, so two
    ``breach`` codes for one port are two findings and one row. Reading
    ``open_titles`` once and never updating it inserted both, then
    deduplicated from the second run onwards — bounded rather than a
    pile-up, and still two unresolved rows for one fault, which is the
    legibility half of ``SNAG-AGENT-006``.

    Unreachable on today's estate, where ``unclaimed_listener`` is the
    only ports breach. Pinned because the *fix* is invisible: a run that
    raises twice looks exactly like a run that raises once until
    somebody counts the rows.
    """

    async def test_two_findings_for_one_port_raise_one_row(self, agent):
        payload = port_breach(8888)
        second = {**payload["findings"][0], "fingerprint": "ports:port 8888:contended"}
        payload = {"findings": [payload["findings"][0], second]}

        session = _session([])
        result = await _run(agent, session, results(findings=payload))

        assert result.details["standing"] == 2
        assert result.alerts_raised == 1
        assert session.add.call_count == 1

    async def test_two_distinct_ports_still_raise_two_rows(self, agent):
        """The guard must not collapse what the family exists to name —
        rule 1's one-row-per-port, which a title-keyed set could break in
        the other direction."""
        payload = {
            "findings": [
                port_breach(8888)["findings"][0],
                port_breach(8889)["findings"][0],
            ]
        }
        session = _session([])
        result = await _run(agent, session, results(findings=payload))

        assert result.alerts_raised == 2
        assert session.add.call_count == 2
