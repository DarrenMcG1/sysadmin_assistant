"""Consumer-driven contract test for the estate's project routes (SNAG-TRAY-006).

The tray fetches ``GET /api/projects/overview`` and ``GET
/api/projects/{name}`` from **estate-manager on port 8400**
(``sysadmin_tray/client.py``) and parses them with *this* repository's
``ProjectOverviewResponse`` / ``ProjectDetailResponse`` /
``ProjectHistoryPoint``.  Nothing joined the two sides up: the fetch
paths swallow every failure to ``logger.debug``, so a producer that
renamed a field would empty the projects tab in silence.

**Two models, not one, deliberately.**  The obvious fix is a shared
class imported by both repositories, and it is the wrong one — the two
sides are doing different jobs.  This side is a *tolerant parse*
(``extra="ignore"``, every field defaulted, ``ValidationError`` meaning
"connection lost" to the tray by design); the estate's is a *producer's
guarantee* (``response_model=``).  Collapsing them makes the tray's
defensiveness the producer's problem and makes the producer's
strictness a way for the tray to crash on a field it was never going to
read — the exact defect ``extra="ignore"`` exists to prevent.  So the
seam is tested rather than deleted.

**Two halves, because neither alone is the test.**

* The **recorded** half parses committed fixtures.  Deterministic,
  offline, runs in CI, and catches *consumer*-side drift — someone
  editing ``sysadmin/core/contracts.py``.  It cannot catch producer
  drift: the fixture is a photograph.
* The **live** half runs the same assertions against 8400 and is what
  actually catches producer drift.  It is skipped when the estate is
  unreachable rather than failed, because a red gate on a box where
  estate-manager happens not to be running reports a fault in a
  repository that has none.  The reachability-skip shape is borrowed
  from ``tests/test_schema_drift.py`` rather than a custom marker or an
  environment variable, so there is one way to say "this needs a live
  dependency" here.

The assertions are factored into ``_assert_*`` helpers called by both
halves, so the two cannot drift apart — a live-only assertion would be
one nobody runs in CI, and a recorded-only one would be one the
producer is never held to.

**Why "it parses" is not the assertion.**  ``Contract.from_dict({})``
*succeeds*: unknown fields are ignored and every field has a default.  A
bare no-``ValidationError`` test therefore goes green against a producer
that stopped serving the route's content entirely.  Each helper first
asserts the keys the consumer reads are **present in the raw payload**,
then asserts the parsed values are usable — the first catches a dropped
field that defaulting would hide, the second catches a field that
arrived with the wrong shape.

**The fixtures are recorded data, not scaffolding.**  This is the first
JSON fixture in ``tests/`` — every other payload here is an inline dict,
and that remains right for a payload the test author invented.  These
two were produced by another repository's code against the live estate
database, and inlining them as Python dicts would let a hand-edit pass
for an observation.  Provenance, since JSON cannot carry a comment:

    # captured 2026-08-13, box `arch`, estate-manager on :8400
    curl -s localhost:8400/api/projects/overview      # 26 projects
    curl -s 'localhost:8400/api/projects/sysadmin_assistant?limit=5'

Both are the response bodies reformatted by ``python -m json.tool
--indent 2`` and otherwise unedited.  Re-record with the same two
commands when the producer legitimately changes shape.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from sysadmin.core.contracts import ProjectDetailResponse, ProjectOverviewResponse

FIXTURES = Path(__file__).parent / "fixtures"

#: Hard-coded rather than derived from ``services.yaml`` or the estate
#: judge's ``base_url``, for the reason that config duplicates it in the
#: first place: a derived URL follows a rename silently and the test
#: goes on passing against nothing.  The fixtures were recorded from
#: this address; if it moves, this line should fail to resolve and be
#: changed by hand.
ESTATE_URL = "http://localhost:8400"

#: The tray's own call (``client.fetch_project_detail``) passes 30.  The
#: fixture was recorded at 5 — the shape assertions are independent of
#: the window, which is the point of asserting shape rather than length.
TRAY_DETAIL_LIMIT = 30

#: Every key ``ProjectOverviewEntry`` declares.  Absence is invisible to
#: the parse (all defaulted), so it is checked against the raw payload.
OVERVIEW_ENTRY_KEYS = frozenset({
    "name",
    "health_score",
    "grade",
    "last_commit_at",
    "branch_count",
    "stale_branch_count",
    "todo_count",
    "has_readme",
    "has_claude_md",
    "total_size_mb",
    "scanned_at",
})

#: ``ProjectDetailResponse.current`` is ``dict[str, Any]`` — nothing
#: validates it, so only the key the tray's contract test already reads
#: back (``current["health_score"]``) is required here.  The rest of the
#: block is the scanner's business and the tray must not pin it.
DETAIL_CURRENT_KEYS = frozenset({"health_score", "scanned_at"})

#: Every key ``ProjectHistoryPoint`` declares.
HISTORY_POINT_KEYS = frozenset({
    "health_score",
    "scanned_at",
    "next_action",
    "next_action_source",
    "next_action_changed",
})


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def _estate_available() -> bool:
    """True when 8400 answers its health route inside 2 s.

    Mirrors ``tests/test_schema_drift.py::_db_available``: a bare
    ``except`` because every way of not reaching the estate — refused,
    timed out, DNS, a proxy in the way — has the same consequence for
    this test, and distinguishing them here would only produce a
    skip reason nobody reads.
    """
    try:
        return httpx.get(f"{ESTATE_URL}/api/health", timeout=2.0).status_code == 200
    except Exception:
        return False


# ── Shared assertions ────────────────────────────────────────────────


def _assert_iso(value: str, field: str) -> datetime:
    """Parse an ISO-8601 stamp, failing with the field that broke.

    Not cosmetic: ``ProjectCard.update_from_overview`` renders the date
    as ``last_commit_at.split("T")[0]``, so a producer switching to
    epoch seconds or ``%d/%m/%Y`` would put the whole string on the card
    rather than raise anything.
    """
    assert isinstance(value, str), f"{field} is {type(value).__name__}, not a string"
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # re-raised as a failure that names the field
        raise AssertionError(f"{field} is not ISO-8601: {value!r} ({exc})") from exc


def _assert_overview_usable(payload: dict[str, Any]) -> ProjectOverviewResponse:
    """The overview as the projects tab consumes it."""
    assert isinstance(payload.get("projects"), list), "no `projects` list in the payload"
    assert payload["projects"], "the estate reported no projects at all"

    for raw in payload["projects"]:
        missing = OVERVIEW_ENTRY_KEYS - set(raw)
        assert not missing, f"overview entry {raw.get('name')!r} is missing {sorted(missing)}"

    parsed = ProjectOverviewResponse.from_dict(payload)

    #: The tab's status label renders ``count`` while the cards come
    #: from ``projects`` — a disagreement is a visible lie, not a
    #: parse failure.
    assert parsed.count == len(parsed.projects)

    for entry in parsed.projects:
        assert entry.name, "an overview entry arrived with no name"
        # `grade` is title-cased straight onto the card; empty renders "Grade: ".
        # Membership of the four bands is deliberately *not* asserted — the
        # bands come from the estate's own `grade_bands` config and a fifth
        # one is the producer's business, which the tray renders unharmed.
        assert entry.grade, f"{entry.name} arrived with no grade"
        # QProgressBar.setRange(0, 100) clamps silently, so an out-of-range
        # score mis-renders rather than raising.
        assert 0 <= entry.health_score <= 100, f"{entry.name}: score {entry.health_score}"
        assert entry.branch_count >= 0
        assert entry.todo_count >= 0
        if entry.last_commit_at is not None:
            _assert_iso(entry.last_commit_at, f"{entry.name}.last_commit_at")
        if entry.scanned_at is not None:
            _assert_iso(entry.scanned_at, f"{entry.name}.scanned_at")

    return parsed


def _assert_detail_usable(payload: dict[str, Any], *, name: str) -> ProjectDetailResponse:
    """The detail route as the trend chart consumes it."""
    assert set(payload) >= {"name", "current", "history"}, f"detail keys: {sorted(payload)}"

    missing_current = DETAIL_CURRENT_KEYS - set(payload["current"])
    assert not missing_current, f"`current` is missing {sorted(missing_current)}"

    assert payload["history"], f"{name} has no history points"
    for i, raw in enumerate(payload["history"]):
        missing = HISTORY_POINT_KEYS - set(raw)
        assert not missing, f"history[{i}] is missing {sorted(missing)}"

    parsed = ProjectDetailResponse.from_dict(payload)
    assert parsed.name == name

    # `current` is dict[str, Any] — nothing coerces it, so the type on
    # the wire is the type the consumer gets.
    score = parsed.current["health_score"]
    assert isinstance(score, int), f"current.health_score is {type(score).__name__}"
    assert 0 <= score <= 100

    points = parsed.history
    # The tab filters on `if p.scanned_at` before plotting, so a history
    # of null stamps renders "No snapshots recorded" — indistinguishable
    # from a project that was never scanned.
    assert all(p.scanned_at for p in points), f"{name} has history points with no scanned_at"
    stamps = [_assert_iso(p.scanned_at or "", f"history[{i}].scanned_at")
              for i, p in enumerate(points)]

    # `ProjectDetailResponse`'s docstring promises newest-first and the
    # tab `reversed()`s on that promise alone. Ascending order would
    # plot the trend backwards without erroring anywhere.
    assert stamps == sorted(stamps, reverse=True), f"{name}: history is not newest-first"

    _assert_tri_state(points, name=name)
    _assert_size_is_numeric(parsed.current, name=name)
    return parsed


def _assert_tri_state(points: list[Any], *, name: str) -> None:
    """``next_action_changed`` is ``None`` on the oldest point, bool above it.

    The three-valued field is the whole reason ``build_narrative_history``
    exists on the producer side, and ``None`` there means "not knowable
    from this response", never "unchanged" — a consumer that reads the
    oldest point as ``False`` reports a streak whose length moves with
    ``limit`` while the data does not.  A producer that started sending
    ``False`` there would collapse the distinction with no parse error
    (``bool | None`` accepts both), which is why it is asserted rather
    than trusted.
    """
    assert points[-1].next_action_changed is None, (
        f"{name}: the oldest history point claims to know whether it changed"
    )
    for i, point in enumerate(points[:-1]):
        assert isinstance(point.next_action_changed, bool), (
            f"{name}: history[{i}].next_action_changed is "
            f"{point.next_action_changed!r}, not a bool"
        )


def _assert_size_is_numeric(current: dict[str, Any], *, name: str) -> None:
    """``current["total_size_mb"]` is a number, and that is all it is.

    The live payload carries an ``int`` here (``2`` for this repository)
    while every overview entry carries a ``float`` — same column, same
    scanner.  The difference is the routes: the overview has
    ``response_model=ProjectOverviewResponse``, which coerces the
    ``Integer`` column to its declared ``float``, and the detail route
    has no ``response_model=`` at all, so the raw value reaches the wire.

    Asserting ``float`` here — the tempting symmetry with
    ``ProjectOverviewEntry`` — would be pinning an accident of the
    producer's serialisation, and would fail the day a project's size
    is fractional.  What the consumer may actually rely on is that it
    is a number, because ``current`` is ``dict[str, Any]`` and nothing
    on this side will coerce it.
    """
    size = current.get("total_size_mb")
    if size is not None:
        assert isinstance(size, (int, float)), (
            f"{name}: total_size_mb is {type(size).__name__} — `current` is "
            "unvalidated on both sides, so this reaches the tray verbatim"
        )


# ── Recorded half — always runs ──────────────────────────────────────


class TestRecordedOverview:
    def test_recorded_payload_is_usable(self):
        parsed = _assert_overview_usable(_load("estate_projects_overview.json"))
        assert parsed.count == 26

    def test_empty_payload_would_also_parse(self):
        """The reason every test above asserts on populated fields.

        This is not a guard against a regression — it pins the property
        that makes a naive version of this module worthless, so anyone
        tempted to reduce it to ``from_dict(payload)`` can see what that
        would prove.
        """
        assert ProjectOverviewResponse.from_dict({}).projects == []
        assert ProjectDetailResponse.from_dict({}).history == []


class TestRecordedDetail:
    def test_recorded_payload_is_usable(self):
        parsed = _assert_detail_usable(
            _load("estate_project_detail.json"), name="sysadmin_assistant"
        )
        assert len(parsed.history) == 5

    def test_recorded_history_carries_a_run_of_unchanged(self):
        """A ``False`` point, which the tri-state assertion alone cannot force.

        Every recorded point could be ``True`` and the shape assertions
        would still pass, leaving the "a run of False measures how long
        one action stayed open" half of the contract unexercised by any
        committed data.  The recording holds one, so it is pinned here.
        """
        parsed = ProjectDetailResponse.from_dict(_load("estate_project_detail.json"))
        flags = [p.next_action_changed for p in parsed.history]
        assert flags == [True, True, True, False, None]
        assert parsed.history[3].next_action == parsed.history[4].next_action


# ── Live half — skipped when the estate is not running ───────────────


@pytest.mark.skipif(not _estate_available(), reason=f"estate-manager ({ESTATE_URL}) unreachable")
class TestLiveEstate:
    """The same assertions against the running producer.

    This is the half that catches producer drift; the recorded half
    cannot, and would keep passing for as long as the fixture sits in
    git.  It is also the half that must never turn the gate red on its
    own — a box without estate-manager running has no fault to report.
    """

    def test_live_overview_is_usable(self):
        resp = httpx.get(f"{ESTATE_URL}/api/projects/overview", timeout=10.0)
        assert resp.status_code == 200
        _assert_overview_usable(resp.json())

    def test_live_detail_is_usable(self):
        """The project name comes from the live overview, never a constant.

        The tray only ever asks for a project it has just been handed a
        card for, so a hard-coded name would be able to fail with a 404
        for a reason the tray cannot reach — a project retired from the
        estate is not a contract breach.
        """
        overview = _assert_overview_usable(
            httpx.get(f"{ESTATE_URL}/api/projects/overview", timeout=10.0).json()
        )
        name = overview.projects[0].name

        resp = httpx.get(
            f"{ESTATE_URL}/api/projects/{name}",
            params={"limit": TRAY_DETAIL_LIMIT},
            timeout=10.0,
        )
        assert resp.status_code == 200
        _assert_detail_usable(resp.json(), name=name)
