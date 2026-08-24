"""Ranked, executable advice off the log trend (Session 27, Tier 2).

Sibling of :mod:`sysadmin.monitor.log_trends` the way
``units/recommendations.py`` is a sibling of ``units/scan.py``: that
module measures, this one says what to do about it, and keeping them
apart is what stops a threshold moving in one place and a
recommendation's wording disagreeing with it in another.

Pure module.  Takes a :class:`~sysadmin.monitor.log_trends.LogTrendReport`
and the declared noise list, returns :class:`LogRecommendation` rows.

**Advice has to be executable, and this session is the first in this
repository to build the mechanism a recommendation names rather than
naming one that exists.**  Session 48 is the precedent and the warning:
it found ``sysadmin-failed.service`` shipping a row that said "paste the
snippet below" with no snippet, an item no execution sitting can close,
so it returns on every sweep for ever.  Tier 2's scoped example —
*"this warning appeared 400x — add to known-noise or fix it"* — named a
known-noise list that did not exist, and there were exactly two honest
ways out: build it, or stop making the recommendation.  It is built
(``agents.log_aggregator.known_noise``, quietening rather than
suppressing per Session 57), so every row below names a step that can
actually be taken today.

Four rules, three of them the opposite of the obvious implementation:

1. **Kind ranks before volume, and no number is invented to merge
   them.**  A signature seen four times for the first time outranks one
   seen 39,919 times for the fifth week — the ordering
   ``FileRecommendationInfo`` uses when a projected disk-threshold
   crossing outranks every byte total, and for the same reason: novelty
   is the only thing here a reader cannot get by looking at today's
   alerts.  Within a kind, ``occurrences`` orders honestly because it is
   measured.  Unlike ``UnitRecommendationInfo``, which has no score
   field at all, this one has a real currency and says what it is.

2. **A signature already declared as noise earns no recommendation.**
   The obvious implementation keeps it and marks it handled, which turns
   a list of things to do into a list of things done.  What it *does*
   get is a row in the trend, at ``info``, carrying the operator's own
   ``reason`` — visible to anyone who looks, absent from the queue of
   work.

3. **Nothing is recommended as noise on volume alone.**  Volume is what
   makes a fault worth looking at; it is not evidence that it is
   harmless.  A ``NOISE`` row additionally requires the signature to be
   **old and flat** — first seen before the current window and neither
   surging nor new — because a fault that has been shouting the same
   thing at the same rate for a fortnight is the shape an operator can
   actually judge.  Get this wrong and the endpoint recommends silencing
   an outage on its second day.

4. **A low-confidence report recommends nothing about volume.**  Every
   ``NOISE`` row is an argument from a count, and
   :class:`~sysadmin.monitor.log_trends.Confidence` ``LOW`` means the
   count is missing an unknown amount of data.  ``NEW`` rows survive,
   because a first sighting is still a first sighting when the series is
   gappy — a gap can hide a fault, never invent one.  That asymmetry is
   the whole reason confidence is carried rather than being folded into
   the numbers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sysadmin.core.text import truncate_at_word
from sysadmin.monitor.journal import since_timestamp
from sysadmin.monitor.log_trends import (
    ChangeKind,
    Confidence,
    LogTrendReport,
    SignatureTrend,
)

__all__ = [
    "INCIDENT_WINDOW_SECONDS",
    "NOISE_MIN_OCCURRENCES",
    "LogRecommendation",
    "SAMPLE_DETAIL_CHARS",
    "SIGNATURE_DETAIL_CHARS",
    "capped_signature",
    "group_incidents",
    "journal_command",
    "quoted_signature",
    "RecommendationKind",
    "recommend",
]

#: Occurrences in the current window before a flat, long-standing
#: signature is worth offering as noise.
#:
#: **Invented, and it says so** — the terms ``queue_max_depth`` is
#: declared on in config.yaml.  Tier 2's scoped example said "appeared
#: 400x", which is a number in a sentence rather than a measurement; 100
#: is the round number below it that still clears everything on this box
#: that is plainly not noise.  Measured 2026-08-17, the live population
#: either side of it is unambiguous: the two Bluetooth firmware
#: signatures sit at 39,919 apiece and the next loudest thing on the box
#: is 52.
NOISE_MIN_OCCURRENCES = 100

#: How long after the first line of an incident a related unit's first
#: line may still belong to it.
#:
#: **Measured, and what was measured is the gap rather than the
#: number.**  Across the 21 first-sighting signatures the live trend
#: holds (2026-08-18, on the purged table), the separations are
#: bimodal with nothing whatever in between:
#:
#: * every pair that is genuinely one incident lands inside **349 ms**
#:   — mosquitto's four lines span 33 ms and the provisioner's two
#:   arrive 315-349 ms after them;
#: * the nearest pair that is genuinely **two** incidents is **64.4 s**
#:   apart (``sysadmin.service``'s startup ``api.auth_token is not set``
#:   warning, then the log aggregator's alert burst a minute later).
#:
#: So every value between 0.35 s and 64 s produces identical output on
#: this box, and the constant is not a threshold anything currently sits
#: near.  5 s is the geometric midpoint of the two measurements, which is
#: the honest way to sit as far from both as the data allows rather than
#: to pick a round number and defend it afterwards.  Unlike
#: :data:`NOISE_MIN_OCCURRENCES`, which is invented and says so, this one
#: is derived — but from a property of *this* data, so a box whose
#: services retry on a five-second timer would have to re-measure it.
#:
#: Note which half of the rule this is doing.  Time alone would be a bad
#: rule and the same live window proves it: ``alfred-backend.service``
#: failed **1.2 s** after mosquitto, well inside any usable window, for
#: an entirely unrelated reason (PostgreSQL was still starting up).  What
#: excludes it is the declared graph, not the clock.
INCIDENT_WINDOW_SECONDS = 5.0

#: How much of each swallowed signature the incident row quotes.
#:
#: A roll-up must **name** what it swallows — ``SNAG-ESTATE-001``'s rule,
#: the one this whole family exists to honour — so every member is listed
#: and none is dropped.  What is bounded is each member's *length*, not
#: their number: ``sysadmin.service``'s own rows are ~250 characters of
#: raw JSON apiece (``SNAG-LOG-008``), and seven of those quoted in full
#: is a detail string no reader gets to the end of.  Truncating a
#: signature still names it; omitting one does not.
SIGNATURE_DETAIL_CHARS = 120

#: How much of the latest verbatim line a ``detail`` quotes.
#:
#: A second constant rather than a reuse of
#: :data:`SIGNATURE_DETAIL_CHARS`, because the two bound different
#: things: a signature is an *identity* a reader may carry to another
#: surface and match against it, and a sample is one example line
#: offered as colour.  The value is unchanged — it was written twice as
#: a bare ``[:200]`` slice until it was named here.
SAMPLE_DETAIL_CHARS = 200


def capped_signature(signature: str) -> str:
    """A signature bounded at :data:`SIGNATURE_DETAIL_CHARS`, cut marked.

    ``truncate_at_word`` rather than a slice, and that is a fix rather
    than a tidying.
    :func:`~sysadmin.monitor.log_review._quoted_signature` already says
    in writing that an unmarked cut is ``SNAG-BRIEF-002``, and that it
    is *worse* on a signature than in a briefing because a reader may
    try to match the signature against ``GET /api/logs/actions`` — and
    this module, which is the surface that route serves and the one that
    lent ``log_review`` the constant, was slicing.  Measured on the
    2026-08-12 window before the change: **12 member signatures cut
    mid-word at exactly 120 characters**, one ending ``"message":
    "alert_raised", "service"`` with nothing to say it had been cut.
    """
    return truncate_at_word(signature, SIGNATURE_DETAIL_CHARS)


def quoted_signature(signature: str) -> str:
    """The signature as a *title* carries it (``SNAG-LOG-010``).

    **A row's identity is the fault, not the source** — ``SNAG-AGENT-005``'s
    rule, unapplied one module over until now.  That entry moved the
    signature into ``alert_title`` precisely because four open rows all
    reading ``Log error: kernel`` are indistinguishable to whoever is
    looking at them.  Every title here was built from ``source`` and a
    number, and sibling rows share both.

    The entry filed this against ``noise`` alone and ranked it last on a
    population of zero.  Driven through the real :func:`recommend`
    against the live table, **the family it names is the smallest of the
    three affected**: at the 2026-08-12 anchor 14 of 21 rows collided in
    five groups — ``New incident on sysadmin.service`` four times, ``New
    incident on kernel`` three, ``New fault from sysadmin.service``
    three, ``New fault from sportsanalyser-frontend.service`` twice, and
    the entry's own ``kernel: 39885 occurrences, unchanged`` twice.  At
    the 2026-08-24 anchor the ``noise`` population really is zero and
    **7 of 9 rows still collide**.  So the rule goes to every builder
    rather than to the one that was noticed.

    The cost is stated rather than hidden: ``sysadmin.service``'s
    signatures are whole JSON records (``SNAG-LOG-008``), so those
    titles now open with ``{"timestamp": "N-N-N …``.  It is the trade
    ``alert_title`` already made and ``SNAG-LOG-003`` already paid for —
    an ugly title a reader can tell apart beats a tidy one they cannot.

    The format lives here rather than at each call site so a title and a
    review line naming one signature read the same way.
    ``log_review._quoted_signature`` keeps only its ``figure_free``
    gate, which is about what may reach a *model* and applies nowhere
    else.
    """
    return f' — "{capped_signature(signature)}"'


class RecommendationKind(StrEnum):
    """Ranked in declaration order — see rule 1."""

    #: First seen inside the current window.  Go and look.
    NEW = "new_signature"
    #: Established, and at least :data:`~sysadmin.monitor.log_trends.SURGE_RATIO`
    #: times its previous volume.
    SURGE = "surge"
    #: Loud, old and flat.  Fix it or declare it.
    NOISE = "noise"


_ORDER = {kind: index for index, kind in enumerate(RecommendationKind)}


@dataclass(frozen=True)
class IncidentMember:
    """One signature swallowed by an incident row.

    Carried so the roll-up can **name** what it collapsed rather than
    count it — ``SNAG-ESTATE-001``'s rule, which cost a session to learn
    when ``Unmonitored systemd units: 17 findings`` sat open, accurate
    and unread for eight days while two of the seventeen restart-looped
    52,178 times.
    """

    source: str
    signature: str
    alert_title: str
    occurrences: int


@dataclass(frozen=True)
class LogRecommendation:
    """One thing to do, with the step that does it."""

    kind: RecommendationKind
    severity: str
    title: str
    detail: str
    #: The step, in words the operator can act on without translating.
    action: str
    source: str
    signature: str
    alert_title: str
    occurrences: int
    #: The exact YAML to paste, for the one kind that has a config edit
    #: as its remedy.  ``None`` everywhere else, and rows that have none
    #: never tell the reader to paste anything — Session 48's rule, which
    #: exists because a row promising an absent snippet can never be
    #: closed.
    snippet: str | None = None
    #: Every signature this row stands for, when it is an incident
    #: roll-up; empty for the ordinary one-signature rows, which are the
    #: overwhelming majority.  ``source``/``signature``/``alert_title``
    #: above stay the **anchor's** rather than becoming a list, so a
    #: reader who ignores this field entirely still gets a correct row
    #: about the fault that happened first.
    members: tuple[IncidentMember, ...] = ()

    @property
    def is_incident(self) -> bool:
        """Whether this row stands for more than one signature."""
        return len(self.members) > 1

    @property
    def units(self) -> tuple[str, ...]:
        """The distinct sources this row covers, anchor first."""
        seen = [self.source]
        seen.extend(m.source for m in self.members if m.source not in seen)
        return tuple(seen)


def group_incidents(
    trends: Sequence[SignatureTrend],
    related: Mapping[str, frozenset[str]] | None = None,
    window_seconds: float = INCIDENT_WINDOW_SECONDS,
) -> list[list[SignatureTrend]]:
    """Collapse first sightings that are one incident into one group.

    ``related`` maps a source to the sources systemd declares it has a
    relation with, already resolved to the source's own scope by the
    caller — :func:`journal_command`'s ``scopes`` argument's posture, and
    for its reason: this module stays pure and the router owns the read.
    Every group is returned, including groups of one, so the caller can
    see that a signature was considered and left alone.

    **This is the rule ``SNAG-LOG-001`` asked for, and it is not the rule
    that entry proposed.**  The entry's shape was "same unit, same
    window, one of them a ``Failed to start`` line systemd emits about
    another".  Driven against the live specimen — the 2026-08-12
    mosquitto core dump, the cleanest one this box has produced — that
    rule collapses mosquitto's four lines and leaves
    ``estate-broker-provision.service``'s two standing as an unrelated
    second fault, which is *more* misleading than the six rows it
    replaces: the reader is told a dependency failed and, separately,
    that a broker crashed.

    Five rules, four of them the opposite of the obvious implementation:

    1. **Membership needs the declared graph, not a longer window.**
       ``estate-broker-provision.service`` declares
       ``After=mosquitto.service``; nothing anywhere declares that
       ``alfred-backend.service`` has anything to do with mosquitto, and
       alfred-backend failed **1.2 s** after the crash — inside any
       window that could hold the 349 ms this incident actually spans.
       Its real cause was PostgreSQL still starting up, which is visible
       in its journal and in no rule a clock could express.  The graph is
       the filter; the window only bounds it.

    2. **One hop, never transitive closure.**  ``.target`` units are hubs
       — six user units on this box declare
       ``After=network-online.target`` — so a second hop relates every
       network-using service to every other and the rule degenerates into
       "same window", which rule 1 has just refused.  A relation must
       hold **directly** between the two sources.

    3. **Every member is measured against the anchor, never against the
       group.**  Single-linkage — admitting a signature because it is
       close to something already admitted — lets a chain walk
       arbitrarily far from where it started, so a restart loop retrying
       every 5 s would grow one incident across a whole outage.  The
       anchor is the earliest first sighting and the window is measured
       from it alone, which is also what an incident *is*: something
       failed at a moment, and consequences landed shortly after.

    4. **First sightings only.**  ``first_seen`` is the moment the fault
       happened only for a signature seen for the first time.  A
       ``SURGED`` signature's ``first_seen`` is weeks old and says
       nothing about when it surged, and grouping surges on ``last_seen``
       instead would put every currently-active surge in one "incident",
       since they all last fired moments ago.  So a surge is never a
       member and never an anchor — which also means every member of a
       group shares one kind, and the rung arithmetic a roll-up normally
       needs (``judge_attention``'s "take the loudest rung you swallow")
       has nothing to decide here.  It is absent because it is vacuous,
       not because it was forgotten.

    5. **Ties are broken on the signature, so the anchor is
       deterministic.**  Seven of ``sysadmin.service``'s rows share a
       timestamp to the millisecond; without a total order the anchor —
       and therefore the row's title — would depend on dict ordering
       upstream.

    Fails **open**: with no graph, or a graph that reaches neither
    source, the rule still groups by source and otherwise leaves rows
    exactly as they are today.  ``collation.py``'s posture rather than
    ``schema_guard``'s, and here the two coincide — not knowing means not
    collapsing, so the failure mode is the status quo rather than a false
    merge.
    """
    edges = related or {}
    firsts = sorted(
        (t for t in trends if t.change is ChangeKind.NEW),
        key=lambda t: (t.first_seen, t.source, t.signature),
    )

    groups: list[list[SignatureTrend]] = []
    claimed: set[int] = set()

    for index, anchor in enumerate(firsts):
        if index in claimed:
            continue
        claimed.add(index)
        group = [anchor]
        neighbours = edges.get(anchor.source, frozenset())
        for other_index in range(index + 1, len(firsts)):
            if other_index in claimed:
                continue
            other = firsts[other_index]
            gap = (other.first_seen - anchor.first_seen).total_seconds()
            if gap > window_seconds:
                # Rule 3: measured from the anchor, and ``firsts`` is
                # sorted, so nothing later can qualify either.
                break
            if other.source == anchor.source or other.source in neighbours:
                claimed.add(other_index)
                group.append(other)
        groups.append(group)

    return groups


def _noise_snippet(trend: SignatureTrend) -> str:
    """The config.yaml block that quietens this signature.

    Emitted with a placeholder ``reason`` rather than a generated one:
    the field exists to record *the operator's* judgement, and a sentence
    this module wrote would read back as though someone had made a
    decision nobody made.
    """
    return (
        "agents:\n"
        "  log_aggregator:\n"
        "    known_noise:\n"
        f"      - source: {trend.source}\n"
        f"        signature: {trend.signature!r}\n"
        "        reason: \"<why this is safe to quieten>\"\n"
    )


def recommend(
    report: LogTrendReport,
    declared_noise: set[tuple[str, str]] | None = None,
    scopes: dict[str, bool] | None = None,
    related: Mapping[str, frozenset[str]] | None = None,
) -> list[LogRecommendation]:
    """Turn a trend report into ranked, executable advice.

    ``declared_noise`` is the set of ``(source, signature)`` pairs already
    in ``agents.log_aggregator.known_noise``, ``scopes`` maps each
    declared source to whether it is a user unit, and ``related`` is the
    declared systemd dependency graph — see :func:`group_incidents`.  All
    three are passed in rather than read from config here so this module
    stays pure and the caller owns the reads — ``reliability.py``'s
    division of labour.

    The declared-noise filter runs **before** grouping, not inside it: a
    signature the operator has already judged is not work, so it must not
    reappear as a member of somebody else's incident row either.
    """
    declared = declared_noise or set()
    undeclared = [
        trend
        for trend in report.signatures
        # Rule 2: already judged.  It is still in the trend, still
        # counted, and still carries the operator's reason on its alert
        # row; it is simply not work.
        if (trend.source, trend.signature) not in declared
    ]

    out: list[LogRecommendation] = []

    for group in group_incidents(undeclared, related):
        if len(group) == 1:
            out.append(_new_recommendation(group[0], scopes))
        else:
            out.append(_incident_recommendation(group, scopes))

    for trend in undeclared:
        if trend.change is ChangeKind.NEW:
            continue  # Grouped above, whether or not it joined anything.
        if trend.change is ChangeKind.SURGED:
            out.append(
                _surge_recommendation(trend, report.previous_start, scopes)
            )
        elif _is_noise_candidate(trend, report.confidence):
            out.append(_noise_recommendation(trend))

    out.sort(key=lambda r: (_ORDER[r.kind], -r.occurrences, r.signature))
    return out


def _is_noise_candidate(trend: SignatureTrend, confidence: Confidence) -> bool:
    """Loud, old and flat — rules 3 and 4.

    ``RETURNED`` counts as flat: it was here before the window and is
    here now, which is the same standing fault seen through a gap.
    ``FALLING`` does too — something on its way out is exactly what an
    operator may want to stop hearing about.  ``NEW`` and ``SURGED`` are
    excluded by construction, since they are their own kinds above.
    """
    if confidence is Confidence.LOW:
        return False
    if trend.current < NOISE_MIN_OCCURRENCES:
        return False
    return trend.change in (
        ChangeKind.STEADY,
        ChangeKind.RISING,
        ChangeKind.FALLING,
        ChangeKind.RETURNED,
    )


def journal_command(
    source: str,
    since: datetime,
    scopes: dict[str, bool] | None = None,
    others: Sequence[str] = (),
) -> str:
    """The journalctl invocation that actually reads ``source``.

    **Written after the first live run emitted three commands that do not
    work**, which is the whole reason this repository drives a new
    surface against real data before believing it.  The draft emitted
    ``journalctl -u <source> --since …`` for everything, and:

    * ``kernel`` is not a unit.  It needs ``-k``, which
      :func:`~sysadmin.monitor.journal.read_journal` has always known and
      this module did not — the same fact, stated twice, one of them
      wrong.
    * **Seven of the fourteen declared log sources are user units**
      (``alfred-backend``, ``sportsanalyser-*``, ``venture-assistant``,
      ``estate-manager-api``, …), and ``journalctl -u`` without
      ``--user`` reads the system journal, where they are not.

    ``scopes`` maps unit name to "is a user unit", built by the caller
    from ``services.yaml`` so this module stays pure.  A source missing
    from it is treated as a **system** unit: that is journalctl's own
    default, and being wrong that way returns "no entries" immediately,
    where the reverse would quietly read a different journal.  It is
    ``SNAG-UNITS-003``'s trade — a command that fails loudly beats one
    that misleads silently.

    ``others`` names further units to read in the same invocation, for an
    incident spanning more than one.  They are safe to fold into one
    command because a declared relation cannot cross scopes — systemd
    does not order across managers — so every unit in a group shares the
    anchor's journal.  ``kernel`` takes ``-k`` and can never have
    company: it has no unit file, so it declares no relation and groups
    only with itself.

    **``since`` is a ``datetime``, not a rendered string, and that is the
    fix rather than a tidying** (``SNAG-LOG-009``).  Three callers each
    formatted ``f"{first_seen:%Y-%m-%d %H:%M}"`` and journalctl reads a
    bare datetime as **local** while every timestamp here is UTC, so all
    nine live rows pointed an hour early on this box — and *late* west of
    Greenwich, where the sign flips and the command misses the incident
    it exists to explain.  It works in BST, which is the trap: the error
    widens the window here and narrows it there, so the box that would
    notice is the one that never runs the command.

    Taking the ``datetime`` is what stops a fourth caller re-deriving it:
    the rendering is
    :func:`~sysadmin.monitor.journal.since_timestamp`'s alone, and it has
    said why since the module was written — the same fact stated twice
    with one of them wrong, which is what the ``-k`` bullet above is
    already about.  ``@<epoch>`` carries no zone at all, so it is
    unambiguous rather than merely correct here.
    """
    stamp = since_timestamp(since)
    if source == "kernel":
        return f"journalctl -k --since '{stamp}'"
    scope = "--user " if (scopes or {}).get(source) else ""
    units = " ".join(f"-u {unit}" for unit in (source, *others))
    return f"journalctl {scope}{units} --since '{stamp}'"


def _new_recommendation(
    trend: SignatureTrend, scopes: dict[str, bool] | None = None
) -> LogRecommendation:
    return LogRecommendation(
        kind=RecommendationKind.NEW,
        severity="risk",
        title=(
            f"New fault from {trend.source}"
            f"{quoted_signature(trend.signature)}"
        ),
        detail=(
            f"First seen {trend.first_seen:%Y-%m-%d %H:%M} UTC, "
            f"{trend.current} occurrence(s) since. "
            f"Latest line: {truncate_at_word(trend.sample, SAMPLE_DETAIL_CHARS)}"
        ),
        action="Read the source: " + journal_command(
            trend.source, trend.first_seen, scopes
        ),
        source=trend.source,
        signature=trend.signature,
        alert_title=trend.alert_title,
        occurrences=trend.current,
    )


def _incident_recommendation(
    group: Sequence[SignatureTrend], scopes: dict[str, bool] | None = None
) -> LogRecommendation:
    """One row for signatures that are one incident (``SNAG-LOG-001``).

    ``group`` arrives ordered by ``first_seen``, so ``group[0]`` is the
    anchor — the fault that happened first, which for the live specimen
    is the mosquitto core dump rather than the provisioner failure it
    caused.  Naming the anchor in the title is what makes this row better
    than the six it replaces and not merely shorter: it says which of the
    six things went wrong first.

    Three rules:

    1. **Occurrences are summed.**  It is the sort key within a kind, and
       an incident that produced six lines across two units genuinely is
       more interesting than a single first sighting that produced one.
       Summing is honest here in a way it would not be across *kinds* —
       the objection ``FileRecommendationInfo`` raises to one ``points``
       field meaning three units — because every member shares this one.

    2. **The action reads every unit at once.**  Six rows previously
       carried six ``journalctl`` invocations that had to be run and
       mentally interleaved to see the ordering that is the whole point.
       One command with the units in ``first_seen`` order shows the
       causality directly.

    3. **The detail names every member and truncates none of them
       away.**  What is bounded is each signature's length
       (:data:`SIGNATURE_DETAIL_CHARS`), never the count — a roll-up that
       drops a member is the count-that-cannot-name-anything this
       repository spent ``SNAG-ESTATE-001`` removing.
    """
    anchor = group[0]
    units: list[str] = []
    for trend in group:
        if trend.source not in units:
            units.append(trend.source)
    others = tuple(units[1:])
    span = (group[-1].first_seen - anchor.first_seen).total_seconds()
    occurrences = sum(trend.current for trend in group)

    if len(units) == 1:
        title = f"New incident on {anchor.source}"
    elif len(units) == 2:
        title = f"New incident: {anchor.source} then {others[0]}"
    else:
        title = (
            f"New incident: {anchor.source} then "
            f"{len(others)} related units"
        )
    # Rule 4: the anchor's signature, for ``quoted_signature``'s reason.
    # The unit names above are shared — ``sysadmin.service`` anchored
    # four separate incidents in the 2026-08-12 window and produced four
    # identical titles — and the anchor's signature is what the row is
    # already *about*: rule 3 says naming the anchor is what makes this
    # row better than the six it replaces, and until now it named only
    # the anchor's unit.
    title += quoted_signature(anchor.signature)

    lines = [
        f"{len(group)} new signature(s) across {len(units)} unit(s) within "
        f"{span:.3f}s of {anchor.first_seen:%Y-%m-%d %H:%M:%S} UTC, "
        f"{occurrences} occurrence(s) in total. "
        f"Grouped because they share a unit or a declared systemd "
        f"dependency; {anchor.source} failed first."
    ]
    lines.extend(
        f"  - {trend.source}: {capped_signature(trend.signature)}"
        for trend in group
    )

    return LogRecommendation(
        kind=RecommendationKind.NEW,
        severity="risk",
        title=title,
        detail="\n".join(lines),
        action="Read the whole incident: " + journal_command(
            anchor.source,
            anchor.first_seen,
            scopes,
            others,
        ),
        source=anchor.source,
        signature=anchor.signature,
        alert_title=anchor.alert_title,
        occurrences=occurrences,
        members=tuple(
            IncidentMember(
                source=trend.source,
                signature=trend.signature,
                alert_title=trend.alert_title,
                occurrences=trend.current,
            )
            for trend in group
        ),
    )


def _surge_recommendation(
    trend: SignatureTrend,
    previous_start: datetime,
    scopes: dict[str, bool] | None = None,
) -> LogRecommendation:
    ratio = f"{trend.ratio:.1f}x" if trend.ratio is not None else "sharply"
    return LogRecommendation(
        kind=RecommendationKind.SURGE,
        severity="risk",
        title=(
            f"{trend.source} fault up {ratio}"
            f"{quoted_signature(trend.signature)}"
        ),
        detail=(
            f"{trend.previous} occurrence(s) last window, {trend.current} this one. "
            f"Latest line: {truncate_at_word(trend.sample, SAMPLE_DETAIL_CHARS)}"
        ),
        # No ``--grep``: the draft grepped on the *normalised* signature,
        # whose ``N`` placeholders match no real line, and its first token
        # is usually the unit's own name — which matches every line in its
        # own journal. The window plus the sample in ``detail`` is what a
        # reader actually needs.
        action="Compare the two windows: " + journal_command(
            trend.source, previous_start, scopes
        ),
        source=trend.source,
        signature=trend.signature,
        alert_title=trend.alert_title,
        occurrences=trend.current,
    )


def _noise_recommendation(trend: SignatureTrend) -> LogRecommendation:
    """Loud, old and flat — and the title no longer claims the last of those.

    ``unchanged`` was asserted for every change kind
    :func:`_is_noise_candidate` admits, and it admits four:
    ``STEADY``, ``RISING``, ``FALLING`` and ``RETURNED``.  Measured at
    the 2026-08-12 anchor, both live rows are ``FALLING`` — **39,885
    this window against 77,496 last** — so the title asserted flatness
    about a signature that had halved, while the row's own ``detail``
    printed the two numbers contradicting it.

    The count stays, because Tier 2's question is literally "this
    warning appeared 400x — add to known-noise or fix it" and the volume
    is the reason to act.  The direction goes, because ``detail`` states
    it, ``change`` decides it, and a title is not the place to restate a
    fact a row already carries — twice, in this case, and wrongly.
    """
    return LogRecommendation(
        kind=RecommendationKind.NOISE,
        severity="advice",
        title=(
            f"{trend.source}: {trend.current} occurrences"
            f"{quoted_signature(trend.signature)}"
        ),
        detail=(
            f"{trend.current} this window against {trend.previous} last, "
            f"{trend.total} in all retained history since "
            f"{trend.first_seen:%Y-%m-%d}. Fix it, or declare it noise and "
            f"it drops to info — it keeps being counted either way."
        ),
        action=(
            "Add the block below to config.yaml, then reload without a "
            "restart: POST /api/sysadmin/reload"
        ),
        source=trend.source,
        signature=trend.signature,
        alert_title=trend.alert_title,
        occurrences=trend.current,
        snippet=_noise_snippet(trend),
    )
