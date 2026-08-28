"""Weekly LLM-narrated system health review — Session 25, Tier 3.

The last unbuilt tier of the service-reliability area, and the fourth
Tier 3 in this repository.  Tier 1
(:mod:`sysadmin.monitor.reliability`) scores each service; Tier 2
(:mod:`sysadmin.monitor.service_recommendations`) says what to do about
the scores.  This narrates the week the box has had, weekly, in the
shape Sessions 23, 24 and 27 proved: deterministic facts, a bounded
figure-free prompt, the model writing only the qualitative sections, a
digest fallback when llama-server is unavailable, and the structured
inputs stored beside the prose so it stays auditable against its data.

**It does not reuse the ``project_reviews`` table its written design
names.**  Session 25's plan said this tier "reuses the
``project_reviews`` table design".  That table left with the projects
domain on 2026-08-13 (ADR-0005) and was dropped by migration 014 on
2026-08-24, so the sentence describes a table that no longer exists.
What the plan actually meant — deterministic facts in ``stats``, hybrid
narrative in ``narrative`` — survives in ``disk_reviews`` and
``log_reviews``, and this mirrors those.

Four inputs, from the roadmap entry: the flappiest services, the alert
volume delta, an anomaly summary and the resource trend direction.

Two rules any Tier 3 here follows, both bought with a live debugging
session in Session 23 and re-verified in Sessions 24 and 69:

1. **Commit the read transaction before calling the LLM.**  This host
   sets ``idle_in_transaction_session_timeout=1min`` and inference takes
   longer.
2. **Give the model no numbers — do not merely instruct it not to use
   them.**  Handed figures and told not to restate them,
   dria-agent-a-3b restated them *and* published a quotient it derived.

And three this tier adds, each settled against the live tables rather
than by argument:

3. **The alert delta counts distinct titles, never rows.**  This
   repository has written down four times that its ``alerts`` table
   holds one row *per failed check* rather than one per incident —
   ``reliability.py``'s "123 rows for one internet outage",
   ``SNAG-AGENT-002``, ``SNAG-AGENT-005``'s 598,091 rows, and
   ``judgements.py`` rule 1's cumulative-total refusal — and had never
   applied it to a *count of alerts* because nothing counted them.
   Measured on this box 2026-08-25 across the two comparison windows:
   **24 rows against 59,650**, a 2,485x fall, of which **59,200 share a
   single title** and fell on one day.  The same two windows hold
   **17 distinct titles against 39**, a 2.3x fall, which is the shape a
   reader would recognise.  Rows are still carried in ``stats`` as
   evidence — dropping them would make the two numbers indistinguishable
   for a future reader — but no sentence is ever written from them.

4. **A fall is refused when the monitor's own coverage fell**, which is
   :func:`sysadmin.monitor.log_review.direction_phrase`'s asymmetry
   applied to a different mechanism.  There it was read truncation; here
   it is agent-run coverage, and the logic is identical because the
   one-directionality is: a window the monitor missed can hide alerts it
   never recorded and can never invent one, so a **rise** is trustworthy
   however gappy the window and a **fall** is not.  This is not
   hypothetical here — the two live windows were observed at **16.5 %**
   and **96.8 %** of expected runs, so an unqualified reading of the
   headline figure is a sentence sending the reader away from a box that
   was simply switched off.  Both windows' coverage is measured, because
   comparing one window's completeness against nothing is the mistake
   the comparison itself makes.

5. **Disk occupancy is deferred to the disk review by name, not
   re-narrated.**  ``GET /api/files/review`` already writes a weekly
   paragraph about occupancy, its direction and its projected threshold
   crossings, and both narratives land in the *same* 06:00 briefing.  A
   second speaker for one fact is the defect this repository has now
   found at six scales, and the cheapest place to not build it is here.
   So the resource half narrates CPU, RAM, swap and load — which nothing
   else on this box narrates at all — and ``stats`` still records the
   disk figures as evidence so the review remains auditable.  The
   fallback digest names the disk review rather than staying silent,
   because an omission a reader has to infer is one they will not infer.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.database import get_scheduler_session
from sysadmin.core.models.agent_run import AgentRun
from sysadmin.core.models.alert import Alert
from sysadmin.core.text import strip_markdown
from sysadmin.monitor.models.health_review import HealthReview
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.reliability import LOW_COVERAGE_FRACTION, ReliabilityScore
from sysadmin.monitor.reliability_history import (
    compute_reliability,
    fetch_timer_series,
)
from sysadmin.monitor.service_recommendations import recommend, total_recoverable_points

logger = logging.getLogger(__name__)

#: The agent whose runs measure coverage.  ``sysadmin`` is the only agent
#: that writes ``service_health``, ``resource_snapshots`` *and* the
#: threshold and anomaly alerts, so its run count is the one number that
#: says how much of a window this review can see at all.  Named rather
#: than passed, because a caller free to choose would be free to choose
#: an agent whose cadence has nothing to do with the data being counted.
COVERAGE_AGENT = "sysadmin"

#: How many advice rows reach the prompt.  Tier 2 serves 4 today and the
#: model is asked for 150 words; a list longer than this cannot be
#: discussed inside that budget, and the ranking already put the ones
#: worth discussing at the top.  :data:`TOP_ACTIONS`'s value and reason
#: are ``log_review``'s.
TOP_ACTIONS = 5

#: How many services the flappiest list names.  Bounded for the reason
#: every roll-up here is: a list that names nothing is a count, and a
#: count is not news (``SNAG-ESTATE-001``).  Five is the width at which
#: it still names them.
TOP_FLAPPING = 5

#: How many anomalies the facts section lists individually before it
#: stops.  Live population over fourteen days is **four**, so this does
#: not bind today and is here for the week a sensor starts oscillating.
TOP_ANOMALIES = 5

#: Metrics the resource half narrates, and their labels.
#:
#: **Disk is deliberately absent** — rule 5.  It is not an oversight and
#: the omission is stated in the fallback digest rather than left for a
#: reader to notice, because ``GET /api/files/review`` narrates occupancy
#: weekly into the same briefing and two narratives about one mount is
#: the second-owner defect.
NARRATED_METRICS: tuple[tuple[str, str], ...] = (
    ("cpu_percent", "CPU"),
    ("ram_percent", "RAM"),
    ("swap_percent", "swap"),
    ("load_avg_15m", "load"),
)

#: Movement below this fraction of the previous mean is "steady".
#:
#: **Invented, and it says so** — ``NOISE_MIN_OCCURRENCES``' and
#: ``flap_min_episodes``' status, stated the same way.  Nothing on this
#: box measures where a reader stops calling a CPU average unchanged,
#: and the honest derivation would need a labelled set of "this mattered"
#: against "this did not".  A tenth is picked to be defensible rather
#: than derived from anything.  Note what makes it cheap to be wrong
#: about: it decides a *word* in a figure-free prompt, and every real
#: figure it describes is in ``stats`` and in the facts section
#: regardless.
STEADY_FRACTION = 0.10

REVIEW_SYSTEM_PROMPT = (
    "You are a pragmatic systems administrator reviewing one Linux "
    "workstation's week. Write in UK English. Refer to services by the "
    "names given. Do not invent facts not present in the data."
)

REVIEW_INSTRUCTIONS = (
    "Write three brief plain-text sections: 1) The week: how the "
    "machine held up, judging from SERVICE RELIABILITY and ALERT "
    "ACTIVITY; 2) Look at first: at most three entries taken from "
    "SERVICE RELIABILITY only, named exactly as spelt above, or "
    "'nothing' if that list is empty; 3) Watch: anything in RESOURCE "
    "TREND or ANOMALIES moving the wrong way that is not yet urgent, or "
    "'nothing' if there is none. Do not discuss disk space; a separate "
    "review covers it. Figures are reported separately, so do not state "
    "any number, count, multiple, percentage or date — describe "
    "magnitude in words. Hard limit 150 words. Plain prose only: no "
    "markdown, no headings, no numbered or bulleted lists. Begin "
    "directly with the first section: do not introduce, acknowledge or "
    "restate the request."
)


# ---------------------------------------------------------------------------
# Phrasing — everything the prompt is allowed to see
# ---------------------------------------------------------------------------


def coverage_confidence(fraction: float) -> str:
    """``high``/``low`` from an observed-run fraction.

    :data:`~sysadmin.monitor.reliability.LOW_COVERAGE_FRACTION` is
    imported rather than restated: the scorer already owns the line below
    which a window is too gappy to trust, and a second copy of it here
    would let a review call a window trustworthy while every score inside
    it says the opposite.
    """
    return "low" if fraction < LOW_COVERAGE_FRACTION else "high"


def confidence_phrase(confidence: str, comparable: bool) -> str:
    """Say what the two windows are worth, in words, with no fraction in it.

    Two separate claims, because they fail separately.  ``confidence`` is
    about *this* window — whether the review can describe the week at
    all.  ``comparable`` is about the pair — whether the week-on-week
    figures mean anything, which is a different question and the one that
    is false on this box today.
    """
    if confidence == "low":
        # The subject is spelt out because the model got it wrong.
        # Handed "The monitor was down for much of this period", the live
        # 2026-08-25 generation opened with "The machine was down for
        # much of the week" — the exact inversion this rule exists to
        # prevent, and the worst one available: it reads as an outage
        # report about a box that was merely unwatched, on a review whose
        # other sections describe genuine service outages.  Naming the
        # monitoring service and then denying the inference in the next
        # clause is what stopped it.
        this_week = (
            "The monitoring service itself was not running for much of this "
            "period, so this record is incomplete. That says nothing about how "
            "the machine behaved — only about how much of it was seen. "
            "Everything below is a floor and nothing here should be read as quiet."
        )
    else:
        this_week = (
            "The monitoring service ran for essentially the whole period, so "
            "the record is complete."
        )

    if comparable:
        return this_week
    return (
        f"{this_week} The two periods were not watched equally closely, so "
        "any change between them describes the watching as much as the machine."
    )


def direction_phrase(delta: int, comparable: bool) -> str:
    """Describe a week-on-week movement, refusing to call a fall a fall when blind.

    **Asymmetric, and that is the whole rule** — the second outing of
    :func:`sysadmin.monitor.log_review.direction_phrase`'s argument
    against a different mechanism.  There the one-directional thing was
    read truncation; here it is monitor downtime, and it is
    one-directional in exactly the same way: a period the monitor did not
    watch can hide alerts that were never recorded and can never invent
    one.  So a **rise** is trustworthy however unequal the two periods
    were — the missing runs could only have made it larger — and a
    **fall** is not, because a quiet week and an unwatched week produce
    the same smaller number.

    On this box the second case is not hypothetical.  The comparison
    windows were observed at 16.5 % and 96.8 % of expected runs, and an
    unqualified "far fewer alerts than last week" is the one sentence in
    a health review that can send somebody away from a machine that was
    merely switched off.
    """
    if delta > 0:
        return "raised more distinct faults"
    if delta == 0:
        return "raised the same number of distinct faults"
    if comparable:
        return "raised fewer distinct faults"
    return "recorded fewer distinct faults, which may be the watching rather than the machine"


def movement_phrase(current: float | None, previous: float | None) -> str:
    """A resource metric's direction, in words, with no figure in it."""
    if current is None:
        return "was not sampled"
    if previous is None:
        return "has no earlier period to compare against"
    if previous == 0:
        return "rose from nothing" if current > 0 else "stayed at nothing"
    change = (current - previous) / abs(previous)
    if change > STEADY_FRACTION:
        return "ran higher than last period"
    if change < -STEADY_FRACTION:
        return "ran lower than last period"
    return "held steady"


def grade_phrase(summary: dict[str, int]) -> str:
    """Estate-level reliability, in words.

    ``failing`` before ``unreliable`` before ``degraded``: the loudest
    band present is what the sentence is about, which is
    ``judge_attention``'s "a roll-up takes the loudest rung it swallows"
    read as prose rather than as a severity.
    """
    if summary.get("failing"):
        return "at least one service failed outright"
    if summary.get("unreliable"):
        return "at least one service was unreliable"
    if summary.get("degraded"):
        return "some services were degraded"
    return "every service held up"


# ---------------------------------------------------------------------------
# Gathering
# ---------------------------------------------------------------------------


async def gather_review_data(
    session: AsyncSession,
    period_days: int | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Structured facts for one review.  ``None`` when nothing was observed.

    The reliability half comes from the **same** two calls
    ``GET /api/services/reliability`` and ``GET /api/services/actions``
    make, so a narrative cannot call a service unreliable while the
    endpoint calls it fine.

    ``None`` is reserved for a period in which the monitor recorded no
    runs at all, which means nothing was *observed* rather than that
    nothing happened.  A quiet week is a result and is narrated — "the
    box had a good week" is a useful thing for this review to say, and a
    review that only appears when something broke teaches its reader that
    its absence means health, which it does not.
    """
    config = get_config()
    window = period_days or config.agents.sysadmin.reliability.window_days
    now = now or datetime.now(UTC)
    window_start = now - timedelta(days=window)
    previous_start = window_start - timedelta(days=window)

    coverage = await _gather_coverage(
        session,
        window_start,
        previous_start,
        now,
        window,
        config.agents.sysadmin.health_check_interval_seconds,
    )
    if not coverage["runs_observed"] and not coverage["previous_runs_observed"]:
        return None

    scores = await compute_reliability(session, config, now=now)
    timers = await fetch_timer_series(session, config, now=now)
    advice = recommend(
        scores,
        config.agents.sysadmin.service_actions,
        timers=timers,
        check_interval_seconds=config.agents.sysadmin.health_check_interval_seconds,
        now=now,
    )

    confidence = coverage_confidence(coverage["fraction"])

    return {
        "period_days": window,
        "generated_at": now.isoformat(),
        "window_start": window_start.isoformat(),
        "previous_start": previous_start.isoformat(),
        "confidence": confidence,
        "comparable": coverage["comparable"],
        "coverage": coverage,
        "services": _service_facts(scores, advice),
        "alerts": await _gather_alerts(session, window_start, previous_start, now),
        "anomalies": await _gather_anomalies(
            session, window_start, previous_start, now
        ),
        "resources": await _gather_resources(
            session, window_start, previous_start, now
        ),
    }


async def _gather_coverage(
    session: AsyncSession,
    window_start: datetime,
    previous_start: datetime,
    now: datetime,
    window_days: int,
    interval_seconds: int,
) -> dict[str, Any]:
    """How much of each period the monitor actually watched.

    Both periods, not just this one.  A review that measured its own
    window's completeness and compared the result against a period it
    never examined would be making exactly the mistake the comparison
    makes — and it is the *previous* window that is complete on this box,
    so a one-sided check would report "coverage is poor" and still let
    every delta through unqualified.

    ``runs_expected`` is arithmetic off the configured interval rather
    than a second count, which makes it exact and makes it wrong in a
    known direction: a period containing a config change to the interval
    is measured against the current one.  That is the same approximation
    ``reliability.py`` already makes for ``checks_expected``, and sharing
    it means the two cannot disagree about how complete a week was.
    """
    rows = (
        await session.execute(
            select(
                func.count()
                .filter(AgentRun.started_at >= window_start)
                .label("current"),
                func.count()
                .filter(
                    AgentRun.started_at >= previous_start,
                    AgentRun.started_at < window_start,
                )
                .label("previous"),
            ).where(
                AgentRun.agent == COVERAGE_AGENT,
                AgentRun.started_at >= previous_start,
                AgentRun.started_at < now,
            )
        )
    ).one()

    expected = max(1, int(window_days * 86400 / max(1, interval_seconds)))
    current = rows.current or 0
    previous = rows.previous or 0
    fraction = current / expected
    previous_fraction = previous / expected

    return {
        "agent": COVERAGE_AGENT,
        "runs_observed": current,
        "previous_runs_observed": previous,
        "runs_expected": expected,
        "fraction": round(fraction, 4),
        "previous_fraction": round(previous_fraction, 4),
        "percent": round(fraction * 100, 2),
        "previous_percent": round(previous_fraction * 100, 2),
        # Both periods must clear the scorer's own bar before a
        # week-on-week claim is worth making.  Not a *third* threshold:
        # it is `LOW_COVERAGE_FRACTION` applied twice, which is what
        # makes "comparable" mean the same thing as "confident", twice.
        "comparable": (
            coverage_confidence(fraction) == "high"
            and coverage_confidence(previous_fraction) == "high"
        ),
    }


def _service_facts(scores: list[ReliabilityScore], advice: Any) -> dict[str, Any]:
    """Tier 1's scores and Tier 2's advice, projected to what a narrative needs.

    The flappiest list is ordered by **episodes**, not by score.  They
    disagree and the disagreement is the entry's whole reason for naming
    flappiness separately: ``internet`` lost 7.5 % of its checks across
    three incidents while ``venture-assistant`` lost 27 % in one, and the
    first is the more interesting row because retry logic survives one
    long outage and dies on three short ones.  Ordering this list by
    score would put the second on top and answer a question Tier 1
    already answers.
    """
    summary = {
        "services_scored": len(scores),
        "reliable": sum(1 for s in scores if s.grade == "reliable"),
        "degraded": sum(1 for s in scores if s.grade == "degraded"),
        "unreliable": sum(1 for s in scores if s.grade == "unreliable"),
        "failing": sum(1 for s in scores if s.grade == "failing"),
        "muted": sum(1 for s in scores if s.muted),
        "low_confidence": sum(1 for s in scores if s.confidence == "low"),
        "mean_score": (
            round(sum(s.score for s in scores) / len(scores), 1) if scores else 100.0
        ),
    }

    flapping = sorted(
        (s for s in scores if not s.muted and s.outage_episodes > 0),
        key=lambda s: (-s.outage_episodes, s.score, s.service),
    )[:TOP_FLAPPING]

    return {
        "summary": summary,
        "flappiest": [
            {
                "service": s.service,
                "episodes": s.outage_episodes,
                "score": s.score,
                "grade": s.grade,
                "uptime_percent": s.uptime_percent,
                "longest_outage_minutes": s.longest_outage_minutes,
                "confidence": s.confidence,
            }
            for s in flapping
        ],
        "recommendations_total": len(advice.recommendations),
        "recoverable_points": total_recoverable_points(advice.recommendations),
        "suppressed_by_confidence": advice.suppressed_by_confidence,
        "muted_skipped": advice.muted_skipped,
        "top": [
            {
                "kind": r.kind,
                "severity": r.severity,
                "service": r.service,
                "title": r.title,
                "action": r.action,
                "recoverable_points": r.recoverable_points,
                "grade": r.grade,
                "confidence": r.confidence,
                "evidence": r.evidence,
            }
            for r in advice.recommendations[:TOP_ACTIONS]
        ],
    }


async def _gather_alerts(
    session: AsyncSession,
    window_start: datetime,
    previous_start: datetime,
    now: datetime,
) -> dict[str, Any]:
    """Distinct alert titles this period against last, with rows as evidence.

    Rule 3.  ``count(DISTINCT title)`` is the figure every sentence is
    written from; ``count(*)`` is carried beside it and never phrased.
    Keeping the row count is not hedging — it is what lets a future
    reader tell a week with more faults from a week with one loud one,
    which is precisely the distinction the naive version destroys.

    ``new_titles`` is the finer half, and it is the half that holds still
    through a swap: a period in which one fault resolved as another
    opened has an unchanged distinct count and an entirely different
    list.  ``check_open_titles``' argument, one domain over.
    """
    counts = (
        await session.execute(
            select(
                func.count().filter(Alert.created_at >= window_start).label("rows"),
                func.count()
                .filter(
                    Alert.created_at >= previous_start,
                    Alert.created_at < window_start,
                )
                .label("previous_rows"),
                func.count(func.distinct(Alert.title))
                .filter(Alert.created_at >= window_start)
                .label("titles"),
                func.count(func.distinct(Alert.title))
                .filter(
                    Alert.created_at >= previous_start,
                    Alert.created_at < window_start,
                )
                .label("previous_titles"),
            ).where(
                Alert.created_at >= previous_start,
                Alert.created_at < now,
            )
        )
    ).one()

    current_titles = {
        row[0]
        for row in (
            await session.execute(
                select(Alert.title)
                .where(Alert.created_at >= window_start, Alert.created_at < now)
                .distinct()
            )
        ).all()
    }
    previous_titles = {
        row[0]
        for row in (
            await session.execute(
                select(Alert.title)
                .where(
                    Alert.created_at >= previous_start,
                    Alert.created_at < window_start,
                )
                .distinct()
            )
        ).all()
    }

    by_severity = {
        severity: count
        for severity, count in (
            await session.execute(
                select(Alert.severity, func.count(func.distinct(Alert.title)))
                .where(Alert.created_at >= window_start, Alert.created_at < now)
                .group_by(Alert.severity)
            )
        ).all()
    }

    titles = counts.titles or 0
    previous = counts.previous_titles or 0
    return {
        "distinct_titles": titles,
        "previous_distinct_titles": previous,
        "title_delta": titles - previous,
        # Evidence only.  Never phrased — see rule 3.
        "rows": counts.rows or 0,
        "previous_rows": counts.previous_rows or 0,
        "by_severity": by_severity,
        "new_titles": sorted(current_titles - previous_titles),
        "cleared_titles": sorted(previous_titles - current_titles),
    }


async def _gather_anomalies(
    session: AsyncSession,
    window_start: datetime,
    previous_start: datetime,
    now: datetime,
) -> dict[str, Any]:
    """Z-score outliers raised this period, from the rows the detector wrote.

    Read back from ``alerts`` rather than recomputed.  Recomputing would
    be a second implementation of
    :func:`sysadmin.monitor.anomaly.detect_anomalies` reading the same
    snapshots through a different window, and the two would disagree the
    first time ``anomaly.window_days`` was edited — the shape
    ``max_priority_for`` and ``syslog_priority`` both exist to avoid.
    The detector's own ``as_details`` payload is the record, and it
    carries the dedup key on purpose.
    """
    rows = (
        await session.execute(
            select(Alert.title, Alert.details, Alert.created_at)
            .where(
                Alert.created_at >= window_start,
                Alert.created_at < now,
                Alert.details["anomaly"].astext == "true",
            )
            .order_by(Alert.created_at.desc())
        )
    ).all()

    previous_count = (
        await session.execute(
            select(func.count()).where(
                Alert.created_at >= previous_start,
                Alert.created_at < window_start,
                Alert.details["anomaly"].astext == "true",
            )
        )
    ).scalar() or 0

    items = []
    for title, details, created_at in rows[:TOP_ANOMALIES]:
        details = details or {}
        items.append(
            {
                "title": title,
                "resource": details.get("resource"),
                "direction": details.get("direction"),
                "z_score": details.get("z_score"),
                "value": details.get("value"),
                "mean": details.get("mean"),
                "at": created_at.isoformat() if created_at else None,
            }
        )

    return {
        "count": len(rows),
        "previous_count": previous_count,
        "listed": len(items),
        "items": items,
    }


async def _gather_resources(
    session: AsyncSession,
    window_start: datetime,
    previous_start: datetime,
    now: datetime,
) -> dict[str, Any]:
    """Per-metric means for both periods — CPU, RAM, swap and load.

    **Disk is absent by rule 5**, and its figures are still recorded
    under ``disk_evidence`` so the review is auditable against the same
    snapshots the disk review read.  What is refused is a *sentence*
    about them, not the data.

    Swap is derived here rather than stored: ``resource_snapshots`` keeps
    ``swap_used_mb``/``swap_total_mb`` and no percentage, so computing it
    at read time is the only option that does not add a column stating a
    quotient of two columns beside it.
    """
    rows = (
        await session.execute(
            select(
                ResourceSnapshot.recorded_at,
                ResourceSnapshot.cpu_percent,
                ResourceSnapshot.ram_percent,
                ResourceSnapshot.swap_used_mb,
                ResourceSnapshot.swap_total_mb,
                ResourceSnapshot.load_avg_15m,
                ResourceSnapshot.disk_usage,
            ).where(
                ResourceSnapshot.recorded_at >= previous_start,
                ResourceSnapshot.recorded_at < now,
            )
        )
    ).all()

    current: dict[str, list[float]] = {key: [] for key, _ in NARRATED_METRICS}
    previous: dict[str, list[float]] = {key: [] for key, _ in NARRATED_METRICS}
    disk_current: list[tuple[datetime, float]] = []

    for row in rows:
        bucket = current if row.recorded_at >= window_start else previous
        _append(bucket, "cpu_percent", row.cpu_percent)
        _append(bucket, "ram_percent", row.ram_percent)
        _append(bucket, "swap_percent", _swap_percent(row))
        _append(bucket, "load_avg_15m", row.load_avg_15m)
        if row.recorded_at >= window_start:
            occupancy = _root_percent(row.disk_usage)
            if occupancy is not None:
                disk_current.append((row.recorded_at, occupancy))

    metrics = []
    for key, label in NARRATED_METRICS:
        now_mean = _mean(current[key])
        was_mean = _mean(previous[key])
        metrics.append(
            {
                "metric": key,
                "label": label,
                "current_mean": now_mean,
                "previous_mean": was_mean,
                "samples": len(current[key]),
                "previous_samples": len(previous[key]),
            }
        )

    disk_current.sort()
    return {
        "metrics": metrics,
        "samples": len(rows),
        # Evidence, never narrated — rule 5.  The disk review owns the
        # sentence; this exists so a reader auditing the stats blob can
        # see the same mount this review deliberately did not discuss.
        "disk_evidence": {
            "mount": "/",
            "current_percent": round(disk_current[-1][1], 1) if disk_current else None,
            "baseline_percent": round(disk_current[0][1], 1) if disk_current else None,
            "samples": len(disk_current),
            "narrated_by": "GET /api/files/review",
        },
    }


def _append(bucket: dict[str, list[float]], key: str, value: Any) -> None:
    if key in bucket and value is not None:
        bucket[key].append(float(value))


def _swap_percent(row: Any) -> float | None:
    total = row.swap_total_mb or 0
    if not total:
        return None
    return 100.0 * (row.swap_used_mb or 0) / total


def _root_percent(disk_usage: Any) -> float | None:
    """Occupancy of ``/`` out of the snapshot's per-mount blob."""
    if not isinstance(disk_usage, dict):
        return None
    entry = disk_usage.get("/")
    if not isinstance(entry, dict):
        return None
    percent = entry.get("percent")
    return float(percent) if isinstance(percent, int | float) else None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def build_facts_section(data: dict[str, Any]) -> str:
    """Deterministic 'what happened' block — numbers never come from the LLM."""
    services = data["services"]
    summary = services["summary"]
    alerts = data["alerts"]
    anomalies = data["anomalies"]
    coverage = data["coverage"]

    lines = [
        f"Window: {data['period_days']} days, "
        f"{summary['services_scored']} services scored, "
        f"mean reliability {summary['mean_score']}."
    ]

    lines.append(
        f"Grades: {summary['reliable']} reliable, {summary['degraded']} degraded, "
        f"{summary['unreliable']} unreliable, {summary['failing']} failing."
    )

    if services["flappiest"]:
        lines.append(
            "Most outage episodes: "
            + ", ".join(
                f"{row['service']} {row['episodes']}"
                for row in services["flappiest"]
            )
            + "."
        )
    else:
        lines.append("Most outage episodes: no service dropped out this period.")

    # Rule 3: the distinct-title figure is what the sentence is written
    # from; the row count is named as the raw total so a reader can see
    # both without either being mistaken for the other.
    lines.append(
        f"Distinct faults alerted: {alerts['distinct_titles']} this period "
        f"against {alerts['previous_distinct_titles']} last "
        f"({alerts['rows']} and {alerts['previous_rows']} raw alert rows)."
    )
    if alerts["new_titles"]:
        lines.append(f"New this period: {len(alerts['new_titles'])} fault titles.")

    lines.append(
        f"Resource anomalies: {anomalies['count']} this period "
        f"against {anomalies['previous_count']} last."
    )

    movers = [
        f"{row['label']} {row['previous_mean']}→{row['current_mean']}"
        for row in data["resources"]["metrics"]
        if row["current_mean"] is not None and row["previous_mean"] is not None
    ]
    lines.append(
        ("Means: " + ", ".join(movers) + ".")
        if movers
        else "Means: not enough samples to compare periods."
    )

    if services["recommendations_total"]:
        lines.append(
            f"Outstanding: {services['recommendations_total']} recommendations "
            f"worth {services['recoverable_points']} recoverable points."
        )
    else:
        lines.append("Outstanding: nothing recommended — no service met a threshold.")

    # ports_checked's rule: a qualifier the reader has to infer is one
    # they will not infer.  Both of these change what every figure above
    # is worth, so both are stated rather than left in `stats`.
    lines.append(
        f"Monitor coverage: {coverage['percent']}% of expected runs this period, "
        f"{coverage['previous_percent']}% last."
    )
    lines.append(confidence_phrase(data["confidence"], data["comparable"]))
    return "\n".join(lines)


def build_review_prompt(data: dict[str, Any]) -> str:
    """Deterministic, figure-free prompt from the gathered facts.

    **No digit reaches this prompt from the data**, which is the precise
    form of rule 2.  It is narrower than what the two sibling modules'
    docstrings claimed until 2026-08-25 — both said "contains no digit
    by construction" while their prompts carried ``1``, ``2``, ``3`` and
    ``150``, the section numbers and word limit in their own
    ``REVIEW_INSTRUCTIONS`` (``SNAG-DOCS-004``, fixed).  The claim was
    always about the *data* half, so the two halves are asserted apart
    and the rule is stated once in :mod:`tests.review_prompts`; each of
    the three modules drives its own prompt against it.

    Every count above becomes a band, a direction or a grade name.  The
    one field carrying free text is a **service name**, which is
    deliberately not filtered through a digit gate the way
    ``log_review`` filters a signature: a name is not a measurement, and
    a service called ``postgres15`` would be dropped from the review
    entirely by a gate that cannot tell the two apart — the review
    losing a service is a worse outcome than the model reading a digit
    that means nothing about the week.  Empty population on this box
    today: 0 of 30 configured service names contain a digit.
    """
    services = data["services"]
    alerts = data["alerts"]
    comparable = data["comparable"]
    lines = [
        "Weekly system health report for one Linux workstation.",
        confidence_phrase(data["confidence"], comparable),
        "",
        "SERVICE RELIABILITY:",
        f"- Overall: {grade_phrase(services['summary'])}.",
    ]

    # Every service that dropped out is named, and the *grade* does the
    # ranking rather than a filter here.  The first draft listed only
    # ``unreliable``/``failing`` services and fell back to the whole list
    # when there were none — driven against the live table it dropped
    # ``searxng`` and ``alfred-frontend``, both degraded with real
    # outages, at the exact moment ``venture-chat`` went unreliable.  A
    # rule that hides two faults the instant a third appears is worse
    # than no rule, and the instruction block already caps the model at
    # three, so the filter bought nothing and cost two names.
    if services["flappiest"]:
        for row in services["flappiest"]:
            repeat = (
                "dropped out repeatedly"
                if row["episodes"] > 1
                else "dropped out once"
            )
            lines.append(f"- {row['service']}: {repeat}, graded {row['grade']}.")
    else:
        lines.append("- No service dropped out this period.")

    lines += [
        "",
        "ALERT ACTIVITY:",
        f"- The machine {direction_phrase(alerts['title_delta'], comparable)}.",
    ]
    if alerts["new_titles"]:
        lines.append("- Some faults appeared for the first time this period.")

    anomalies = data["anomalies"]
    lines += ["", "ANOMALIES:"]
    if anomalies["items"]:
        for item in anomalies["items"]:
            resource = item.get("resource") or "a resource"
            direction = item.get("direction") or "away from"
            lines.append(f"- {resource} ran unusually {direction} its recent average.")
    else:
        lines.append("- No resource strayed from its recent average.")

    lines += ["", "RESOURCE TREND (disk is covered by a separate review):"]
    for row in data["resources"]["metrics"]:
        lines.append(
            f"- {row['label']}: "
            f"{movement_phrase(row['current_mean'], row['previous_mean'])}."
        )

    lines += ["", REVIEW_INSTRUCTIONS]
    return "\n".join(lines)


def build_fallback_narrative(data: dict[str, Any]) -> str:
    """Deterministic digest used when llama-server is unavailable."""
    services = data["services"]
    lines = [
        f"Weekly system health review ({data['period_days']} days) — "
        "generated without LLM narration.",
        build_facts_section(data),
    ]

    risky = [row for row in services["top"] if row["severity"] == "risk"]
    if risky:
        lines.append(
            f"{len(risky)} of these are ranked risk — look at those first."
        )
    for row in services["top"][:3]:
        lines.append(f"Look at first: {row['title']} — {row['action']}")
    if not services["recommendations_total"]:
        lines.append("No service needed attention this period.")

    # Rule 5, stated rather than left to be noticed.  A reader who knows
    # a disk review exists can go and read it; one who does not would
    # otherwise conclude this review looked at the disk and found
    # nothing worth saying.
    lines.append(
        "Disk occupancy is not covered here — see the weekly disk review "
        "at GET /api/files/review."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


async def generate_review(
    session: AsyncSession,
    llm_client=None,
    period_days: int | None = None,
) -> HealthReview | None:
    """Generate, store and return a review; ``None`` when nothing was observed.

    ``llm_client`` is injectable for tests; by default a fresh
    :class:`~sysadmin.core.llm_client.LLMClient` is built for this run and
    shut down afterwards — never shared across scheduler event loops
    (``SNAG-AGENT-003``).
    """
    from sysadmin.core.llm_client import LLMClient

    data = await gather_review_data(session, period_days)
    if data is None:
        logger.info("health_review_skipped_no_data")
        return None

    # Rule 1: inference outlives this host's
    # idle_in_transaction_session_timeout (1min), so the read transaction
    # ends here and the INSERT below opens a fresh one.
    await session.commit()

    config = get_config()
    owns_client = llm_client is None
    client = llm_client or LLMClient()
    if owns_client:
        await client.startup()
    try:
        narrative = await client.generate(
            build_review_prompt(data), system=REVIEW_SYSTEM_PROMPT
        )
    finally:
        if owns_client:
            await client.shutdown()

    llm_used = narrative is not None
    if narrative is not None:
        # Numbers first and deterministically; the model's prose after,
        # with the markdown it emits against instructions removed.
        narrative = f"{build_facts_section(data)}\n\n{strip_markdown(narrative)}"
    else:
        narrative = build_fallback_narrative(data)
        logger.warning("health_review_llm_unavailable_used_fallback")

    review = HealthReview(
        period_days=data["period_days"],
        narrative=narrative,
        llm_used=llm_used,
        model_used=config.llm.model if llm_used else None,
        confidence=data["confidence"],
        stats=data,
    )
    session.add(review)
    await session.flush()
    return review


async def run_weekly_review() -> None:
    """Scheduler entry point — generate and store the review.

    **It announces nothing** — the ruling in ``SNAG-AGENT-010``, argued
    once in :func:`sysadmin.files.review.run_weekly_review` and cited
    here rather than restated.

    This writer is the one that made the reason legible, because the
    contamination is self-referential: :func:`_gather_alerts` above
    counts distinct ``alerts`` titles with **no severity filter**, and
    :func:`build_review_prompt` phrases that figure as "Distinct faults
    alerted".  An ``info`` row announcing *this* review therefore
    arrived in the next review's ``new_titles`` as a fault — a review
    counting its own announcement.  Deleting the write is what keeps the
    numerator honest; filtering the query instead would leave three
    immortal rows on the box and teach the count to ignore a severity
    that other families legitimately use (``known_noise``'s quietening,
    ``COVERED_SIGNATURES``).

    ``agent="sysadmin"`` is gone with the row.  Nothing here writes to
    ``alerts`` now, so the ``chk_alert_agent`` check that mattered before
    adding an alert-writing surface does not apply to this module.
    """
    async with get_scheduler_session() as session:
        review = await generate_review(session)
        if review is None:
            return

    logger.info("weekly_health_review_generated")
