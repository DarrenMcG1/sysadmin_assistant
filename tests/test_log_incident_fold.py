"""SNAG-LOG-015 — one GPU reset occupied twelve alert rows.

A full-card amdgpu MODE1 reset writes eleven distinct signatures in the
same six seconds and :class:`~sysadmin.monitor.log_aggregator.LogAggregatorAgent`
opened a row for each.  Measured on the live table: the 2026-09-04 reset
raised **ten** ``warning`` rows at one instant (``created_at``
10:36:31.494, a single poll) and the three 2026-09-03 resets eleven
apiece.  The twelfth — the declared ``GPU was reset`` row, the only one
that names the fault — was the news, and it arrived beside eleven
fragments of its own wreckage, each with its own tray fingerprint.

**The entry's hardest question dissolves rather than gets answered.**  It
asks what resolves a swallowed member *"since each is a separate open row
with its own dedup lifecycle and ``monitor/collation.py``'s flip-flop is
what a careless answer rebuilds"*.  The fold runs over the ``faults``
dict **before** ``_open_alerts``, so a swallowed member is never a row:
there is nothing to resolve, and a flip-flop needs two owners of one row
where there is exactly one.  ``SNAG-AGENT-005`` reached the same shape
for the same reason — a log line cannot un-write itself, so this family's
fixes are raise rules.

**What these tests can and cannot show.**  The fold is decided in Python
before any row is built, so it needs no database — the same property that
made ``SNAG-AGENT-005``'s dedup testable.  What they cannot show is that
the window still clears a real reset; that is
:func:`test_the_shipped_window_clears_every_observed_reset`, which pins
the measurement rather than a fixture, and the live half is in
``tests/test_critical_signature_live.py``.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sysadmin.core.escalation import is_louder_than
from sysadmin.monitor.log_actions import (
    INCIDENT_WINDOW_SECONDS,
    correlate,
    group_incidents,
)
from sysadmin.monitor.log_aggregator import (
    ALERT_INCIDENT_WINDOW_SECONDS,
    CRITICAL_SIGNATURES,
    DECLARED_FLOOR_SEVERITY,
    NOISE_SEVERITY,
    CriticalSignature,
    LogAggregatorAgent,
    _fault_message,
    _merge_members,
    fold_declared_incidents,
)
from sysadmin.monitor.log_signature import alert_title, signature

#: The 2026-09-04 reset, in the order and at the offsets the journal
#: recorded them, seconds after the first error line.  Read off
#: ``log_entries`` rather than typed from the entry: the offsets are what
#: the window is measured against, so a hand-rounded copy would make
#: every window test agree with itself.
RESET_CHAIN: tuple[tuple[float, str], ...] = (
    (0.000000, "amdgpu 0000:03:00.0: ring gfx_0.0.0 timeout, signaled seq=141849676, "
               "emitted seq=141849680"),
    (0.000075, "amdgpu 0000:03:00.0:  Process GameThread pid 348941 thread vkd3d_queue pid 349051"),
    (0.000137, "amdgpu 0000:03:00.0: Starting gfx_0.0.0 ring reset"),
    (0.000202, "[drm:gfx_v11_0_bad_op_irq [amdgpu]] *ERROR* Illegal opcode in command stream"),
    (2.000374, "amdgpu 0000:03:00.0: MES failed to respond to msg=RESET"),
    (2.000654, "amdgpu 0000:03:00.0: failed to reset legacy queue"),
    (2.000862, "amdgpu 0000:03:00.0: Ring gfx_0.0.0 reset failed"),
    (4.198385, "amdgpu 0000:03:00.0: MES failed to respond to msg=REMOVE_QUEUE"),
    (4.205278, "amdgpu 0000:03:00.0: failed to unmap legacy queue"),
    (4.427374, "[drm:gfx_v11_0_hw_fini [amdgpu]] *ERROR* failed to halt cp gfx"),
)

#: The declared line, and its offset from the anchor.
VRAM_LOST = "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!"
VRAM_LOST_OFFSET = 4.967547

#: The widest anchor-to-declaration span any reset on this box has
#: produced, across all five in the journal (2026-08-29 → 2026-09-04,
#: both installed kernel branches): 4.9579, 4.9597, 4.9599, 4.9614 and
#: **4.9675** s.  It is amdgpu's fixed reset timeout schedule rather than
#: anything about load, which is why the five agree to ten milliseconds.
OBSERVED_RESET_SPAN_SECONDS = 4.9675

#: The nearest separation between two kernel error lines on this box that
#: are genuinely **two** incidents: ``virt/tdx: TDX not supported by the
#: host platform`` at boot, followed by a USB enumeration failure.
#: Measured over all 81,509 kernel lines at ``PRIORITY<=3`` in the
#: journal, which hold **zero** consecutive gaps between 4.9 and 5.1 s.
OBSERVED_TWO_INCIDENT_SECONDS = 7.04

T0 = datetime(2026, 9, 4, 9, 35, 32, 819860, tzinfo=UTC)


def _fault(
    message: str,
    offset: float,
    *,
    source: str = "kernel",
    severity: str = "warning",
    declared: CriticalSignature | None = None,
    count: int = 1,
    noise_reason: str | None = None,
    covered_by: str | None = None,
) -> dict:
    """One entry of the ``faults`` dict ``_execute`` builds.

    Built by hand rather than driven through ``_execute`` because the
    fold's input *is* this dict — driving the agent would test the
    ingest loop as well and make a red ambiguous about which half moved.
    ``tests/test_log_alert_dedup.py`` drives the loop.
    """
    sig = signature(message)
    title = declared.title if declared is not None else alert_title(
        "error", source, message
    )
    return {
        "title": title,
        "first_logged_at": T0 + timedelta(seconds=offset),
        "members": [],
        "severity": (
            NOISE_SEVERITY
            if noise_reason or covered_by
            else DECLARED_FLOOR_SEVERITY
            if declared is not None
            else severity
        ),
        "declared": declared,
        "source": source,
        "message": message,
        "count": count,
        "signature": sig,
        "noise_reason": noise_reason,
        "covered_by": covered_by,
    }


def _declaration() -> CriticalSignature:
    """The shipped declaration, read rather than rebuilt.

    A locally-constructed :class:`CriticalSignature` would let these
    tests keep passing on a day the real one has been reworded or
    removed — asserting a *value* where the fold's behaviour depends on
    *provenance*, which is the shape two of Session 59's guards were.
    """
    return CRITICAL_SIGNATURES[("kernel", signature(VRAM_LOST))]


def _reset_faults(*, declared: bool = True) -> dict[str, dict]:
    faults = {}
    for offset, message in RESET_CHAIN:
        fault = _fault(message, offset)
        faults[fault["title"]] = fault
    if declared:
        fault = _fault(VRAM_LOST, VRAM_LOST_OFFSET, declared=_declaration())
        faults[fault["title"]] = fault
    return faults


# --- The fold -----------------------------------------------------------


def test_the_reset_becomes_one_row():
    """Eleven signatures, one declared row.  The whole entry."""
    folded = fold_declared_incidents(_reset_faults())

    assert len(folded) == 1
    (row,) = folded.values()
    assert row["title"] == _declaration().title
    assert row["declared"] is not None


def test_every_swallowed_signature_is_named():
    """``SNAG-ESTATE-001``: a roll-up that drops a member names nothing.

    Asserted as a set equality rather than as a count, because a count
    is exactly the thing that entry is about.
    """
    (row,) = fold_declared_incidents(_reset_faults()).values()

    assert {m["signature"] for m in row["members"]} == {
        signature(message) for _, message in RESET_CHAIN
    }
    # And the identity a reader carries from ``GET /api/logs/trends`` or
    # from a fragment row raised before this fix.
    assert {m["alert_title"] for m in row["members"]} == {
        alert_title("error", "kernel", message) for _, message in RESET_CHAIN
    }


def test_the_swallowed_signatures_are_stored_whole():
    """Un-capped, deliberately — ``SNAG-LOG-013`` is what a cap rebuilds.

    ``details`` is JSONB read by an API client, not a rendered string
    with a reader's attention as its budget, and 9 of 55 signatures on
    this box share their first 120 characters.  Capping a machine
    readable field would name several members identically, which is the
    roll-up promising to name what it swallows and naming none of it.
    """
    long_line = "amdgpu 0000:03:00.0: " + "diagnostic detail " * 20
    faults = _reset_faults()
    extra = _fault(long_line, 1.0)
    faults[extra["title"]] = extra

    (row,) = fold_declared_incidents(faults).values()
    stored = next(
        m for m in row["members"]
        if m["signature"].startswith("amdgpu N:N:N.N: diagnostic")
    )
    assert stored["signature"] == signature(long_line)
    assert len(stored["signature"]) > 120


def test_occurrences_are_not_summed_onto_the_anchor():
    """The row's own count is compared across incidents of one fault.

    ``_incident_recommendation`` rule 1 sums, because there the total is
    a sort key across advice rows and every member shares one currency.
    Here summing would make the count of ``VRAM is lost`` — which a reset
    writes exactly once — depend on how many fragments fell inside the
    window.
    """
    faults = _reset_faults()
    for fault in faults.values():
        if fault["declared"] is None:
            fault["count"] = 9

    (row,) = fold_declared_incidents(faults).values()
    assert row["count"] == 1
    assert sum(m["occurrences"] for m in row["members"]) == 9 * len(RESET_CHAIN)


# --- What is refused ----------------------------------------------------


def test_a_group_with_no_declaration_is_left_alone():
    """Only a declaration may name a folded row.

    The advice surface titles its roll-up after the **anchor**, which is
    free there because the row is recomputed live and persists nothing.
    Here the title is the dedup identity, the tray fingerprint and the
    resolve key, and an anchor-derived title forks all three the moment
    two incidents begin with different lines.
    """
    folded = fold_declared_incidents(_reset_faults(declared=False))
    assert len(folded) == len(RESET_CHAIN)
    assert all(not row["members"] for row in folded.values())


def test_a_group_with_two_declarations_is_left_alone():
    """Two names is no name, and picking one is the arbitrary choice the
    declaration exists to remove.

    Empty population today — there is one declaration, and both of its
    kernel spellings share one :class:`CriticalSignature` and therefore
    one title, so the two branches cannot produce two names for one
    reset.  Written because the population is empty *by coincidence of
    how many declarations exist*, not by construction.
    """
    other = CriticalSignature(
        title="A different declared fault", reason="...", arrives_at="info"
    )
    faults = _reset_faults()
    second = _fault("amdgpu 0000:03:00.0: something else declared", 1.0, declared=other)
    faults[second["title"]] = second

    folded = fold_declared_incidents(faults)
    assert len(folded) == len(faults)
    assert all(not row["members"] for row in folded.values())


def test_a_louder_sibling_is_not_swallowed():
    """The fold may never quieten anything.

    ``judge_attention``'s roll-up takes the loudest rung it swallows;
    applying that verbatim here would let a fold *override a
    quietening*.  Refusing to swallow the louder member gets the same
    guarantee with no ordering question.  Reachable rather than
    theoretical: ``RDSEED32 is broken`` arrives from this kernel at
    ``PRIORITY=2`` and raises ``critical``.
    """
    faults = _reset_faults()
    loud = _fault(
        "RDSEED32 is broken. Disabling the corresponding CPUID bit.",
        1.0,
        severity="critical",
    )
    faults[loud["title"]] = loud

    folded = fold_declared_incidents(faults)
    assert loud["title"] in folded
    assert not folded[loud["title"]]["members"]
    # ...and the rest of the chain still folds around it.
    assert len(folded) == 2


def test_a_quietened_declaration_silences_only_itself():
    """An operator quietening the reset has not quietened the kernel.

    ``known_noise`` rule 1 keys on ``(source, signature)`` precisely so
    that one judgement does not reach another signature, and this is
    that rule holding through the fold: with the declared row at
    :data:`NOISE_SEVERITY` every ``warning`` fragment is louder, so
    nothing is swallowed and nothing is made quiet.
    """
    faults = _reset_faults()
    declared_title = _declaration().title
    faults[declared_title] = _fault(
        VRAM_LOST, VRAM_LOST_OFFSET, declared=_declaration(),
        noise_reason="the owner judged this harmless",
    )

    folded = fold_declared_incidents(faults)
    assert len(folded) == len(faults)
    assert folded[declared_title]["severity"] == NOISE_SEVERITY
    assert all(not row["members"] for row in folded.values())


def test_a_fault_from_an_unrelated_source_is_not_swallowed():
    """Rule 1 of ``correlate``: the graph is the filter, not the clock."""
    faults = _reset_faults()
    stranger = _fault("connection refused", 1.0, source="alfred-backend.service")
    faults[stranger["title"]] = stranger

    folded = fold_declared_incidents(faults)
    assert stranger["title"] in folded
    assert len(folded) == 2


def test_a_declared_relation_is_honoured():
    """...and a source systemd declares a relation with *is* swallowed.

    Empty population for the one declaration that exists — ``kernel`` is
    not a systemd unit, so ``unit_relations()`` has no entry for it — and
    wired anyway, because the day a unit-source line is declared this is
    the half that decides correctness.  Driven at the *graph*, which is
    the thing that would silently stop being passed.
    """
    faults = _reset_faults()
    neighbour = _fault("connection refused", 1.0, source="alfred-backend.service")
    faults[neighbour["title"]] = neighbour

    folded = fold_declared_incidents(
        faults, {"kernel": frozenset({"alfred-backend.service"})}
    )
    assert len(folded) == 1


# --- The window ---------------------------------------------------------


def test_a_fault_outside_the_window_is_not_swallowed():
    faults = _reset_faults()
    late = _fault("amdgpu 0000:03:00.0: unrelated later fault", 30.0)
    faults[late["title"]] = late

    folded = fold_declared_incidents(faults)
    assert late["title"] in folded
    assert len(folded) == 2


def test_the_shipped_window_clears_every_observed_reset():
    """The guard the entry needs, because its failure mode is silent.

    A window that no longer reaches the declared line leaves the
    declaration standing alone and the ten fragments back — no
    exception, no red, just the entry quietly reopening.  So the
    measurement is asserted rather than remembered:
    :data:`ALERT_INCIDENT_WINDOW_SECONDS` must clear the widest span any
    reset on this box has produced, and clear it by more than the
    rounding on that measurement.

    **The shared constant would pass a naive version of this test**,
    which is the point.  ``INCIDENT_WINDOW_SECONDS`` is 5.0 against an
    observed 4.9675 — it clears, by **32 ms, 0.6 % of its own value** —
    so the assertion is on the *margin* and not on the inequality.  The
    knife edge is exact and was driven live: at 4.9674 s the 2026-09-04
    reset produces eleven rows and at 4.9676 s it produces one.
    """
    assert ALERT_INCIDENT_WINDOW_SECONDS > OBSERVED_RESET_SPAN_SECONDS
    # A tenth of a second is not a policy, it is bigger than the spread
    # of the five measurements (10 ms) by an order of magnitude.
    assert ALERT_INCIDENT_WINDOW_SECONDS - OBSERVED_RESET_SPAN_SECONDS > 0.1
    # ...and below the nearest thing it must not merge.
    assert ALERT_INCIDENT_WINDOW_SECONDS < OBSERVED_TWO_INCIDENT_SECONDS
    # The shared constant is what this exists to be distinct from.
    assert INCIDENT_WINDOW_SECONDS - OBSERVED_RESET_SPAN_SECONDS < 0.05


def test_the_window_is_load_bearing_at_the_measured_edge():
    """Driven at the edge rather than asserted about the constant."""
    faults = _reset_faults()
    assert len(fold_declared_incidents(faults, None, VRAM_LOST_OFFSET - 0.001)) == 11
    assert len(
        fold_declared_incidents(_reset_faults(), None, VRAM_LOST_OFFSET + 0.001)
    ) == 1


# --- The message and the merge -----------------------------------------


def test_an_unfolded_row_says_nothing_extra():
    fault = _fault(VRAM_LOST, 0.0, declared=_declaration())
    assert _fault_message(fault) == VRAM_LOST


def test_a_folded_row_says_it_stands_for_more_than_itself():
    """The toast is ``title`` + ``message`` and nothing else.

    ``details['members']`` names them, which is the shape
    ``judge_audit_findings`` rule 3 uses; the message is what tells a
    reader of the toast that the field is worth opening.
    """
    (row,) = fold_declared_incidents(_reset_faults()).values()
    message = _fault_message(row)

    assert VRAM_LOST in message
    assert "10 further signature(s)" in message
    assert "details['members']" in message


def test_members_accumulate_across_incidents():
    """A member named on the first incident is not dropped by the second.

    Deliberately the *opposite* treatment from ``noise_reason`` and
    ``covered_by``, which are set-or-popped because each states the
    row's present classification.
    """
    first = [{"source": "kernel", "signature": "a", "alert_title": "A", "occurrences": 2}]
    second = [
        {"source": "kernel", "signature": "a", "alert_title": "A", "occurrences": 3},
        {"source": "kernel", "signature": "b", "alert_title": "B", "occurrences": 1},
    ]
    merged = _merge_members(first, second)

    by_sig = {m["signature"]: m for m in merged}
    assert set(by_sig) == {"a", "b"}
    assert by_sig["a"]["occurrences"] == 5
    assert by_sig["b"]["occurrences"] == 1


def test_a_malformed_stored_member_is_dropped_not_repaired():
    """``details`` is evidence; a guess about a broken member is worse
    than its absence, and neither may make an agent run raise."""
    merged = _merge_members(
        ["not a dict", None, {"source": "kernel", "signature": "a"}],
        [{"source": "kernel", "signature": "a", "occurrences": 4}],
    )
    assert len(merged) == 1
    assert merged[0]["occurrences"] == 4


def test_a_row_written_before_this_fix_has_no_members_key():
    assert _merge_members(None, [{"source": "s", "signature": "x", "occurrences": 1}]) == [
        {"source": "s", "signature": "x", "occurrences": 1}
    ]


# --- The extraction -----------------------------------------------------


def test_correlate_orders_its_own_input():
    """Rule 4 lives in ``correlate``, not at each caller.

    **The obvious version of this test passes against an unsorted
    implementation**, which is why it is written this way.  Reversing the
    reset chain puts the declared line first; every other member is then
    *earlier*, so every gap is negative, nothing exceeds the window and
    the whole chain folds anyway — the right answer for the wrong reason.

    What an unsorted run actually gets wrong is *which fault is the
    anchor*, and the window is measured from the anchor alone (rule 3).
    So the discriminator is a third fault that is inside the window of a
    later member and outside the window of the earliest one: sorted it is
    its own group, unsorted it is swallowed into an incident it is eleven
    seconds away from.
    """
    early = _fault("amdgpu 0000:03:00.0: something failed first", 0.0)
    declared = _fault(VRAM_LOST, 5.5, declared=_declaration())
    late = _fault("amdgpu 0000:03:00.0: something failed much later", 11.0)
    # Presented anchor-last, which is the order a dict can hand over.
    faults = {
        declared["title"]: declared,
        late["title"]: late,
        early["title"]: early,
    }

    folded = fold_declared_incidents(faults)
    # The declared row swallows what is within 5.9s of the *earliest*
    # fault, and ``late`` is 11s from it.
    assert late["title"] in folded
    assert {m["signature"] for m in folded[declared["title"]]["members"]} == {
        early["signature"]
    }


def test_group_incidents_still_filters_first_sightings():
    """The regression the extraction could have introduced.

    ``correlate`` knows nothing about :class:`ChangeKind`; the filter is
    the advice caller's and must stay there, or every active surge lands
    in one "incident" because they all last fired moments ago.
    """
    from sysadmin.monitor.log_trends import ChangeKind, SignatureTrend

    def trend(sig: str, change: ChangeKind) -> SignatureTrend:
        return SignatureTrend(
            signature=sig, alert_title=sig, source="kernel", severity="error",
            sample=sig, current=1, previous=0, total=1,
            first_seen=T0, last_seen=T0, change=change,
        )

    groups = group_incidents(
        [trend("a", ChangeKind.NEW), trend("b", ChangeKind.SURGED)]
    )
    assert [t.signature for group in groups for t in group] == ["a"]


def test_is_louder_than_orders_the_alert_rungs():
    """``critical`` > ``warning`` > ``info``, and not alphabetically."""
    assert is_louder_than("critical", "warning")
    assert is_louder_than("warning", "info")
    assert not is_louder_than("warning", "critical")
    assert not is_louder_than("info", "info")
    # An unknown rung reads as the floor, as it does throughout the module.
    assert not is_louder_than("nonsense", "info")


@pytest.mark.parametrize(
    "window", [ALERT_INCIDENT_WINDOW_SECONDS, INCIDENT_WINDOW_SECONDS]
)
def test_a_lone_fault_is_returned_untouched(window):
    """``correlate`` returns groups of one so a caller can see that a
    signature was considered and left alone."""
    fault = _fault(VRAM_LOST, 0.0, declared=_declaration())
    folded = fold_declared_incidents({fault["title"]: fault}, None, window)
    assert folded == {fault["title"]: fault}
    assert not correlate([])


# --- End to end, through the agent -------------------------------------


def _journal_entry(message: str, offset: float, severity: str = "error") -> dict:
    """One line as ``read_journal`` returns it.

    A third copy of a shape two test modules already build, and it earns
    itself: both of theirs stamp ``datetime.now(UTC)``, so every entry in
    a run shares one moment and no window can be exercised through them.
    The offsets are the whole subject here.
    """
    return {
        "source": "kernel",
        "severity": severity,
        "message": message,
        "logged_at": T0 + timedelta(seconds=offset),
        "raw_line": message,
        "metadata": {},
    }


def _chain_entries() -> list[dict]:
    return [
        *(_journal_entry(message, offset) for offset, message in RESET_CHAIN),
        _journal_entry(VRAM_LOST, VRAM_LOST_OFFSET, severity="info"),
    ]


@pytest.mark.asyncio
async def test_the_agent_raises_one_row_for_the_whole_chain():
    """The wiring, and the proof that the fold runs *before* the read.

    Every other test in this file drives ``fold_declared_incidents``
    directly, which says nothing about whether ``_execute`` calls it, or
    calls it early enough.  This one asserts the property the entry
    turns on: a swallowed member never becomes an :class:`Alert`, so
    there is no row for anything to resolve.
    """
    from tests.test_critical_signatures import _CountingSession, _run

    agent = LogAggregatorAgent()
    session = _CountingSession()
    entries = _chain_entries()
    result = await _run(agent, session, entries)

    assert result.alerts_raised == 1
    assert [a.title for a in session.alerts] == [_declaration().title]
    # Every line is still stored — the fold moves which alert row counts
    # a line, never whether ``log_entries`` holds it.
    assert result.findings_count == len(entries)
    assert len(session.alerts[0].details["members"]) == len(RESET_CHAIN)


@pytest.mark.asyncio
async def test_a_recurrence_keeps_the_folded_message():
    """``alert.message`` is composed in one place, or the first
    recurrence silently rewrites it back to the un-folded form.

    ``_record_recurrence`` and the raise both write that column, and two
    sites composing one sentence is ``SNAG-DB-003``'s shape at the size
    of a string.
    """
    from sysadmin.core.models.alert import Alert as AlertRow
    from tests.test_critical_signatures import _CountingSession, _run

    open_row = AlertRow(
        agent="log_aggregator",
        severity=DECLARED_FLOOR_SEVERITY,
        title=_declaration().title,
        message=VRAM_LOST,
        details={"source": "kernel", "occurrences": 1},
    )
    session = _CountingSession(open_alerts=[open_row])
    result = await _run(LogAggregatorAgent(), session, _chain_entries())

    assert result.alerts_raised == 0
    assert session.alerts == []
    assert "further signature(s)" in open_row.message
    assert len(open_row.details["members"]) == len(RESET_CHAIN)


@pytest.mark.asyncio
async def test_a_recurrence_does_not_drop_the_members_it_already_named():
    """The accumulation, driven at ``_record_recurrence`` rather than at
    the helper.

    ``test_members_accumulate_across_incidents`` pins ``_merge_members``
    and says nothing about whether the recurrence path calls it — a
    stubbed collaborator widening a check, one file over.  Driven: a row
    that already names a member the second incident did not produce must
    still name it.
    """
    from sysadmin.core.models.alert import Alert as AlertRow
    from tests.test_critical_signatures import _CountingSession, _run

    remembered = {
        "source": "kernel",
        "signature": "a signature only the first incident produced",
        "alert_title": "Log error: kernel — an earlier fragment",
        "occurrences": 3,
    }
    open_row = AlertRow(
        agent="log_aggregator",
        severity=DECLARED_FLOOR_SEVERITY,
        title=_declaration().title,
        message=VRAM_LOST,
        details={"source": "kernel", "occurrences": 1, "members": [remembered]},
    )
    session = _CountingSession(open_alerts=[open_row])
    await _run(LogAggregatorAgent(), session, _chain_entries())

    assert remembered in open_row.details["members"]
    assert len(open_row.details["members"]) == len(RESET_CHAIN) + 1


@pytest.mark.asyncio
async def test_the_agent_hands_the_fold_the_declared_graph():
    """``_execute`` passes ``_relations()``, or rule 6 ships inert.

    Without this the graph could stop being read and every test above
    would stay green, because they hand ``correlate`` a graph directly.
    Its population is empty on this box — ``kernel`` is not a systemd
    unit — so the graph is stubbed rather than read, which is what makes
    the assertion about the *wiring* and not about the estate.
    """
    from unittest.mock import patch

    from tests.test_critical_signatures import _CountingSession, _run

    session = _CountingSession()
    entries = [
        *_chain_entries(),
        {**_journal_entry("connection refused", 1.0), "source": "alfred-backend.service"},
    ]
    with patch.object(
        LogAggregatorAgent,
        "_relations",
        staticmethod(lambda: {"kernel": frozenset({"alfred-backend.service"})}),
    ):
        result = await _run(LogAggregatorAgent(), session, entries)

    assert result.alerts_raised == 1
    assert len(session.alerts[0].details["members"]) == len(RESET_CHAIN) + 1


@pytest.mark.asyncio
async def test_an_unreadable_unit_directory_does_not_take_the_run_down():
    """The enrichment may never become a dependency of the alert.

    ``estate/judgements.py`` states the rule this borrows, and
    ``SNAG-LOG-004`` is what this module costs when one source's
    exception kills the ingest of every other.  An unreadable directory
    buys same-source folding only, which is what the chain needs anyway.
    """
    from unittest.mock import patch

    from tests.test_critical_signatures import _CountingSession, _run

    session = _CountingSession()
    with patch(
        "sysadmin.monitor.log_aggregator.unit_relations",
        side_effect=PermissionError("/etc/systemd/system"),
    ):
        result = await _run(LogAggregatorAgent(), session, _chain_entries())

    assert result.alerts_raised == 1
    assert len(session.alerts[0].details["members"]) == len(RESET_CHAIN)
