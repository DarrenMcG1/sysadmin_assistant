"""Weekly LLM-narrated log review — Session 27, Tier 3.

The last unbuilt tier in the log-aggregator area, and the one that had to
wait.  Tier 1 (:mod:`sysadmin.monitor.log_trends`) says what changed;
Tier 2 (:mod:`sysadmin.monitor.log_actions`) says what to do about it.
This narrates the second over the first, weekly, in the shape Sessions 23
and 24 proved: deterministic facts, a bounded figure-free prompt, the
model writing only the qualitative sections, a digest fallback when
llama-server is unavailable, and the structured inputs stored beside the
prose so it stays auditable against its data.

**Why it is built on the recommendations rather than the trend.**
Session 23 narrated "each project's top three recommendations" and this
follows it, but the reason is sharper here: until 2026-08-17 the same
mosquitto core dump appeared as *six* recommendations, because systemd
narrates one crash in six lines that are six genuine signatures.  A
narrative written then would have described one crash six times and read
as six faults.  ``group_incidents`` collapsed them (``SNAG-LOG-001``) and
the endpoint went 24 rows to 11; this module consumes the 11.  Three
sittings deferred this tier on the stated grounds that the stack beneath
it had not been observed, and that is what they were waiting for.

**What replaced what.**  ``LogAggregatorAgent.summarise()`` claimed this
ground and never ran: it had no caller in production, in the scheduler or
in a test, and ``agents.log_aggregator.summarise_with_llm`` was parsed by
pydantic and read only by the uncalled method — the ``SNAG-CFG-001``
shape.  Its one stored row, 2026-07-24, is the argument against extending
it rather than replacing it.  It covered **29 seconds** (13:16:47 →
13:17:16), because its window was the newest 100 rows and the box was
mid-Bluetooth-storm; it reported ``entry_count = error_count = 100``,
both the query's ``LIMIT``; and having been handed a hundred raw
timestamped lines it answered with "1. Repeated failures 2. Pattern of
failures 3. Potential firmware loading issues" and the invented rate
"every 1-2 seconds".  There is no edit that makes that a Tier 3, because
the direction of flow *is* the design: raw rows into a model is the
opposite of facts out of one.

Two rules any Tier 3 here follows, both bought with a live debugging
session in Session 23 and both re-verified in Session 24:

1. **Commit the read transaction before calling the LLM.**  This host
   sets ``idle_in_transaction_session_timeout=1min`` and inference takes
   longer.
2. **Give the model no numbers — do not merely instruct it not to use
   them.**  Handed figures and told not to restate them,
   dria-agent-a-3b restated them *and* published a quotient it derived.

And one this tier adds, which the other two could not have found:

3. **The normalised signature may go into the prompt verbatim, because
   normalisation is the operation that makes it figure-free.**
   ``signature()`` maps every digit run to ``N``, so the identity Tier 1
   already keys on carries no figure to regurgitate — measured
   2026-08-18, **0 of 46 live signatures contain a digit**.  The disk
   review had to invent ``KIND_PHRASES`` to keep numbers away from the
   model; here the safe form already existed and is the same string the
   reader will match against ``GET /api/logs/actions``.  It is still
   filtered through :func:`figure_free`, because ``_HEX`` produces
   ``0xN`` and that ``0`` is a digit by construction — an empty
   population on this box today, reachable the moment a driver logs an
   address.
"""

import logging
import re
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.database import get_scheduler_session
from sysadmin.core.gpu_lease import (
    acquire_review_lease,
    release_review_lease,
)
from sysadmin.core.text import strip_markdown
from sysadmin.monitor.log_actions import (
    NOISE_MIN_OCCURRENCES,
    LogRecommendation,
    RecommendationKind,
    quoted_signature,
    recommend,
)
from sysadmin.monitor.log_query import (
    build_trend_report,
    log_source_scopes,
    unit_relations,
)
from sysadmin.monitor.log_trends import (
    RATIO_MIN_COUNT,
    Confidence,
    LogTrendReport,
)
from sysadmin.monitor.models.log_review import LogReview

logger = logging.getLogger(__name__)

#: How many recommendations reach the prompt.  The endpoint serves 11
#: today and the model is asked for 150 words; a list longer than this
#: cannot be discussed inside that budget, and the ranking already put
#: the ones worth discussing at the top.
TOP_ACTIONS = 5

#: How many sources the facts section names before it stops.  Nine are
#: declared here and all nine appear in the trend, so this binds; the
#: ordering is by absolute error movement, so what it drops is the
#: sources that did not move.
TOP_SOURCES = 5

#: Occurrence bands — the only volume the prompt is allowed to see.
#:
#: **Two of the three edges are borrowed rather than picked**, which is
#: the point.  :data:`~sysadmin.monitor.log_trends.RATIO_MIN_COUNT` is
#: already the count below which Tier 1 refuses to compute a ratio, and
#: :data:`~sysadmin.monitor.log_actions.NOISE_MIN_OCCURRENCES` is already
#: the count above which Tier 2 will consider a signature loud enough to
#: be worth silencing.  Reusing them means the narrative's sense of
#: "loud" and the ranking's sense of it cannot drift apart — the rule
#: ``max_priority_for`` follows against ``PRIORITY_MAP``.
#:
#: :data:`STORM_OCCURRENCES` is the exception and **is invented**.  It
#: exists because "loud" for both a hundred-occurrence warning and a
#: kernel storm would tell the model they rank together, and they do not.
#: Live on this box the occurrence counts are ``1, 1, 2, 4, 6, 7, 11, 16,
#: 26, 39885, 39885`` — bimodal, with a 1,534x gap and nothing inside it,
#: so every value between 27 and 39,884 produces identical output today.
#: That makes the choice safe rather than derived, and unlike
#: ``INCIDENT_WINDOW_SECONDS`` there is one specimen rather than
#: twenty-one, so it is not dressed up as a measurement.
STORM_OCCURRENCES = 10_000

OCCURRENCE_BANDS: tuple[tuple[int, str], ...] = (
    (STORM_OCCURRENCES, "storming"),
    (NOISE_MIN_OCCURRENCES, "loud"),
    (RATIO_MIN_COUNT, "repeated"),
)

#: Number-free names for the three recommendation kinds.  Tier 2's own
#: titles carry figures — a surge's ratio, an incident's unit count, a
#: noise row's occurrences — and so cannot go in the prompt; these say
#: the same thing without one.  (The example this comment used to give,
#: ``"kernel: 39885 occurrences, unchanged"``, stopped being a real
#: title with ``SNAG-LOG-010``; the leak path it names did not.)
KIND_PHRASES = {
    RecommendationKind.NEW.value: "a fault seen for the first time",
    RecommendationKind.SURGE.value: "an established fault getting louder",
    RecommendationKind.NOISE.value: "a long-standing fault nobody has silenced",
}

REVIEW_SYSTEM_PROMPT = (
    "You are a pragmatic systems administrator reviewing one Linux "
    "workstation's logs. Write in UK English. Refer to services and "
    "faults by the names given. Do not invent facts not present in the "
    "data."
)

REVIEW_INSTRUCTIONS = (
    "Write three brief plain-text sections: 1) What broke: which "
    "services and faults account for this week, judging from the "
    "OUTSTANDING FAULTS list; 2) Look at first: at most three entries "
    "taken from the OUTSTANDING FAULTS list only, never from VOLUME "
    "CHANGES, named by their service exactly as spelt above; 3) Watch: "
    "anything in VOLUME CHANGES moving the wrong way that is not yet "
    "urgent, or 'nothing' if there is none. Figures are reported "
    "separately, so do not state any number, count, multiple, "
    "percentage or date — describe magnitude in words. Hard limit 150 "
    "words. Plain prose only: no markdown, no headings, no numbered or "
    "bulleted lists."
)

_DIGIT = re.compile(r"\d")


def figure_free(text: str) -> bool:
    """True when ``text`` carries no digit for the model to restate.

    The gate rule 3 rests on.  Applied to every signature before it
    reaches the prompt rather than trusted from the measurement, because
    the measurement is a property of this box's log lines while the gate
    should be a property of the text.

    **The exception it named is unreachable, and it was never a property
    of this box** (measured 2026-09-03).  This said ``_HEX`` rewrites a
    hex literal to ``0xN``, *"which is digit-free in intent and not in
    fact"* — but :func:`~sysadmin.monitor.log_signature.signature`
    applies ``_NUM`` **after** ``_HEX``, over its result, so the ``0``
    is eaten too and ``0x1f`` arrives as ``NxN``.  Every digit run in a
    message becomes ``N``, so a signature is digit-free by construction
    and this gate has an empty population: **79 of 79** retained
    signatures on the live table pass it.

    It stays, and not out of caution.  The gate's input is *typed* as a
    signature and nothing enforces that it is one — the one caller
    reads ``item["signature"]`` out of a JSON facts blob — so it is the
    last thing standing between a mis-projected field and a prompt whose
    whole contract is that it carries no figure.  What it must **not**
    become is a gate on the *rendered* line: see
    :func:`_quoted_signature`.
    """
    return not _DIGIT.search(text)


def _quoted_signature(signature: str) -> str:
    """The signature as the prompt may see it, or nothing at all.

    Two gates, and they refuse for different reasons.

    :func:`figure_free` is about correctness — rule 3's one structural
    exception.  The length cap is about the prompt being *readable*:
    ``sysadmin.service`` logs whole JSON records on one line, so
    ``SNAG-LOG-008``'s signatures are ~250 characters apiece, and two of
    the five rows the live report served on 2026-08-24 were exactly
    that.  Quoted in full, one of them is most of a bounded prompt — the
    model is asked for 150 words and handed a paragraph of serialised
    logger metadata to write them about.

    The cap and the marked cut are
    :func:`~sysadmin.monitor.log_actions.quoted_signature`'s, borrowed
    whole rather than restated: it was chosen against these same rows
    for this same reason one module over, and since ``SNAG-LOG-010``
    that function writes the titles of the very rows this line
    describes.  A review naming a signature one way and
    ``GET /api/logs/actions`` naming it another is the disagreement
    ``log_query``'s docstring exists to prevent, in the one form a
    reader cannot check.

    What stays here is the ``figure_free`` gate alone, because it is
    about what may reach a *model* and applies to no other caller.

    **And ``discriminate=False``, which is the one property this render
    gives up and the reason it may** (``SNAG-LOG-013``, closed
    2026-09-03).  A cut signature now carries eight hex characters of
    its own digest so that two faults agreeing past the cap stop
    rendering as one; those characters are digits, and this prompt
    carries none from the data by construction.  The identity they
    restore is for a reader who carries it to another surface and
    matches it, and **nothing matches a review line against anything** —
    the line is colour in a narrative, and its own ``member_count``
    clause already says "one incident covering several related faults"
    without naming which.

    The alternative was to gate on the *rendered* text rather than on
    the input, which is the shape that looks tidier and is measurably
    worse: **8 of 79** retained signatures are cut at
    :data:`~sysadmin.monitor.log_actions.SIGNATURE_DETAIL_CHARS` and
    **8 of 8** are figure-free, so it would have deleted every cut
    signature from the prompt outright.  A line reading
    ``sysadmin.service: a new fault appeared`` with the fault's text
    removed is the surface with nothing else to say what happened.

    So the two renders differ, and they differ in exactly one direction
    and by exactly one token.  That is a narrower divergence than the
    one this gate already permits, which is to emit nothing at all.
    """
    if not figure_free(signature):
        return ""
    return quoted_signature(signature, discriminate=False)


def occurrence_band(count: int) -> str:
    """Qualitative volume — the only count the prompt is allowed to see."""
    for threshold, label in OCCURRENCE_BANDS:
        if count >= threshold:
            return label
    return "a handful"


def confidence_phrase(confidence: str) -> str:
    """Say what the window is worth, in words, with no fraction in it."""
    if confidence == Confidence.LOW.value:
        return (
            "Parts of this period went unread, so every count below is a "
            "floor and nothing here should be read as quiet."
        )
    if confidence == Confidence.MEDIUM.value:
        return "A small part of this period went unread, so counts are floors."
    return "The whole period was read."


def direction_phrase(delta: int, confidence: str) -> str:
    """Describe an error movement, refusing to call a fall a fall when blind.

    **Asymmetric, and that is the whole rule.**  Truncation is
    one-directional — a read that hits its ceiling drops entries, so it
    can only ever make a count too low.  A rise is therefore trustworthy
    however incomplete the window was: the missing entries could only
    have made it larger.  A *fall* is not, because a source that went
    quiet and a source whose reads were truncated produce the same
    smaller number, and the second is the state this window is in.

    This is :data:`~sysadmin.monitor.log_trends.TRUNCATION_LOW_FRACTION`'s
    argument one layer up.  Session 63 used one-directionality to justify
    a threshold on the *input*; here it decides what the narrative is
    allowed to claim on the way out.  Saying "quieter than last week" off
    a window that was not fully read is the one sentence in a log review
    that can send somebody away from a live fault.
    """
    if delta > 0:
        return "got louder"
    if delta == 0:
        return "held steady"
    if confidence == Confidence.HIGH.value:
        return "got quieter"
    return "reported less, which may be the reading rather than the fault"


async def gather_review_data(
    session: AsyncSession, period_days: int | None = None
) -> dict[str, Any] | None:
    """Structured facts for one review.  ``None`` when nothing was observed.

    The report and the advice come from the **same** call the two
    endpoints use (:func:`sysadmin.monitor.log_query.build_trend_report`),
    so a narrative cannot call a signature new while
    ``GET /api/logs/actions`` calls it established.

    A week with recommendations and a week without are both results and
    both narrated — "nothing new broke" is the most useful thing this
    review can ever say.  ``None`` is reserved for a report with no
    signatures at all, which means nothing was *observed*, not that
    nothing happened.
    """
    config = get_config().agents.log_aggregator
    window = period_days or config.trend_window_days

    report = await build_trend_report(session, window)
    if not report.signatures:
        return None

    declared = {(n.source, n.signature) for n in config.known_noise}
    recs = recommend(report, declared, log_source_scopes(), unit_relations())

    return {
        "period_days": report.window_days,
        "generated_at": report.generated_at.isoformat(),
        "window_start": report.window_start.isoformat(),
        "confidence": str(report.confidence),
        "truncated": report.truncated,
        "declared_noise": len(declared),
        "actions": _action_facts(recs),
        "signatures": _signature_facts(report),
        "sources": _source_facts(report),
        "coverage": {
            "runs_observed": report.coverage.runs_observed,
            "runs_expected": report.coverage.runs_expected,
            "runs_truncated": report.coverage.runs_truncated,
            "runs_instrumented": report.coverage.runs_instrumented,
        },
    }


def _action_facts(recs: list[LogRecommendation]) -> dict[str, Any]:
    """Tier 2's output, projected to what the narrative and its audit need.

    ``members`` is carried as a **count and a list of names**, not
    dropped to a count — ``SNAG-ESTATE-001``'s rule.  A roll-up that says
    "6 signatures" and cannot say which is the ``Unmonitored systemd
    units: 17 findings`` row that sat open and unread for eight days.
    """
    by_kind: dict[str, int] = {}
    for rec in recs:
        by_kind[str(rec.kind)] = by_kind.get(str(rec.kind), 0) + 1

    return {
        "total": len(recs),
        "by_kind": by_kind,
        "risk_count": sum(1 for r in recs if r.severity == "risk"),
        "top": [
            {
                "kind": str(rec.kind),
                "severity": rec.severity,
                "title": rec.title,
                "action": rec.action,
                "source": rec.source,
                "signature": rec.signature,
                "alert_title": rec.alert_title,
                "occurrences": rec.occurrences,
                "member_count": len(rec.members),
                "members": [m.signature for m in rec.members],
            }
            for rec in recs[:TOP_ACTIONS]
        ],
    }


def _signature_facts(report: LogTrendReport) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for trend in report.signatures:
        counts[str(trend.change)] = counts.get(str(trend.change), 0) + 1
    return {
        "distinct": len(report.signatures),
        "by_change": counts,
        "new": len(report.new_signatures),
        "groups_read": report.groups_read,
    }


def _source_facts(report: LogTrendReport) -> list[dict[str, Any]]:
    """Per-source movement, loudest mover first.

    Errors and warnings stay separate because
    :class:`~sysadmin.monitor.log_trends.SourceTrend` keeps them
    separate, and for its reason: a source whose warnings doubled while
    its errors vanished has not "got 50 % worse", and one number cannot
    say so.
    """
    rows: list[dict[str, Any]] = [
        {
            "source": s.source,
            "current_errors": s.current_errors,
            "previous_errors": s.previous_errors,
            "error_delta": s.error_delta,
            "current_warnings": s.current_warnings,
            "previous_warnings": s.previous_warnings,
            "warning_delta": s.current_warnings - s.previous_warnings,
            "new_signatures": s.new_signatures,
        }
        for s in report.sources
    ]
    rows.sort(key=lambda r: (-abs(r["error_delta"]), -abs(r["warning_delta"])))
    return rows


def build_facts_section(data: dict[str, Any]) -> str:
    """Deterministic 'what happened' block — numbers never come from the LLM."""
    actions = data["actions"]
    sigs = data["signatures"]
    lines = [
        f"Window: {data['period_days']} days, "
        f"{sigs['distinct']} distinct fault signatures, "
        f"{sigs['new']} of them first seen this period."
    ]

    if actions["total"]:
        by_kind = ", ".join(
            f"{count} {kind}" for kind, count in sorted(actions["by_kind"].items())
        )
        lines.append(f"Outstanding: {actions['total']} recommendations ({by_kind}).")
    else:
        lines.append("Outstanding: nothing recommended — no fault met a threshold.")

    movers = [row for row in data["sources"] if row["error_delta"]][:TOP_SOURCES]
    if movers:
        lines.append(
            "Errors by source: "
            + ", ".join(
                f"{row['source']} {row['previous_errors']}→{row['current_errors']}"
                for row in movers
            )
            + "."
        )
    else:
        lines.append("Errors by source: no source changed its error count.")

    for item in actions["top"][:3]:
        line = f"- {item['title']} ({item['occurrences']} occurrences)"
        if item["member_count"]:
            line += f", covering {item['member_count']} signatures"
        lines.append(line)

    # ports_checked's rule: a qualifier the reader has to infer is one
    # they will not infer.  Both of these change what the numbers above
    # are worth, so both are stated rather than left in `stats`.
    lines.append(confidence_phrase(data["confidence"]))
    if data["truncated"]:
        lines.append(
            "The grouped read hit its cap, so these rankings are over a subset."
        )

    return "\n".join(lines)


def build_review_prompt(data: dict[str, Any]) -> str:
    """Deterministic, figure-free prompt from the gathered facts.

    **No digit reaches this prompt from the data** — see rules 2 and 3
    in the module docstring, and :func:`figure_free` for the one shape
    that has to be filtered rather than trusted.

    This said "contains no digit by construction" until 2026-08-25 and
    was false in a half rule 2 never covered (``SNAG-DOCS-004``):
    :data:`REVIEW_INSTRUCTIONS` numbers its sections and caps the model
    at 150 words, and those digits are instructions *to* the model
    rather than measurements *about* the box.  Both halves are asserted,
    apart, in :mod:`tests.review_prompts`, which owns the distinction
    for all three Tier 3 reviews.
    """
    actions = data["actions"]
    lines = [
        "Weekly log report for one Linux workstation.",
        confidence_phrase(data["confidence"]),
        "",
    ]

    if actions["top"]:
        lines.append("OUTSTANDING FAULTS, most significant first:")
        for item in actions["top"]:
            marker = " [RISK]" if item["severity"] == "risk" else ""
            entry = (
                f"- {item['source']}: {KIND_PHRASES.get(item['kind'], item['kind'])}"
                f"{marker} — {occurrence_band(item['occurrences'])}"
            )
            entry += _quoted_signature(item["signature"])
            if item["member_count"]:
                entry += " — one incident covering several related faults"
            lines.append(entry)
    else:
        lines.append("No fault met a threshold this period.")

    movers = [row for row in data["sources"] if row["error_delta"]][:TOP_SOURCES]
    if movers:
        lines += ["", "VOLUME CHANGES (context only, not a list of faults):"]
        lines += [
            f"- {row['source']}: "
            f"{direction_phrase(row['error_delta'], data['confidence'])}"
            for row in movers
        ]

    lines += ["", REVIEW_INSTRUCTIONS]
    return "\n".join(lines)


def build_fallback_narrative(data: dict[str, Any]) -> str:
    """Deterministic digest used when llama-server is unavailable."""
    actions = data["actions"]
    lines = [
        f"Weekly log review ({data['period_days']} days) — "
        "generated without LLM narration.",
        build_facts_section(data),
    ]
    if actions["risk_count"]:
        lines.append(
            f"{actions['risk_count']} of these are ranked risk — look at those first."
        )
    for item in actions["top"][:3]:
        lines.append(f"Look at first: {item['title']} — {item['action']}")
    if not actions["total"]:
        lines.append("Nothing new broke this period.")
    return "\n".join(lines)


async def generate_review(
    session: AsyncSession,
    llm_client=None,
    period_days: int | None = None,
    *,
    gpu_lease_held: bool = False,
) -> LogReview | None:
    """Generate, store and return a review; ``None`` when nothing was observed.

    ``llm_client`` is injectable for tests; by default a fresh
    :class:`~sysadmin.core.llm_client.LLMClient` is built for this run and
    shut down afterwards — never shared across scheduler event loops
    (``SNAG-AGENT-003``).
    """
    from sysadmin.core.llm_client import LLMClient

    data = await gather_review_data(session, period_days)
    if data is None:
        logger.info("log_review_skipped_no_data")
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
            build_review_prompt(data),
            system=REVIEW_SYSTEM_PROMPT,
            gpu_lease_held=gpu_lease_held,
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
        logger.warning("log_review_llm_unavailable_used_fallback")

    review = LogReview(
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
    here rather than restated.  This wrote an ``info`` alert row that
    nothing could resolve and retention could never purge.

    The docstring this replaces reasoned that the row was safe *because*
    "a second speaker for one fault is the defect ``SNAG-LOG-005``
    closed" — and it was right about the principle while the row it
    defended became a counted fault anyway:
    :func:`sysadmin.monitor.health_review._gather_alerts` takes no
    severity filter, so a notice is narrated under "Distinct faults
    alerted".  The announcement was never reachable by a speaker either;
    ``info`` sits below both severity gates on this box.  What already
    announces this review is ``briefing/data.py``, which reads
    ``log_reviews`` directly and expires a stale one, which the alert
    never did.

    **It takes a GPU lease and waits for the grant** (``SNAG-SCHED-003``,
    2026-08-31).  It used to dispatch straight into
    :func:`generate_review`, whose ``ensure_gpu_idle`` read the card once
    and gave up; on a Monday inside ``venture-enrich-nightly``'s hold
    that is a deterministic digest published into the 06:00 briefing,
    with nothing on the stored row able to say whether the card was busy
    or llama-server was down.  The argument is
    :mod:`sysadmin.core.gpu_lease`'s and is not restated here.

    Three orderings below are load-bearing:

    * **The lease is taken before the scheduler session is opened.**  The
      wait is minutes and this host enforces
      ``idle_in_transaction_session_timeout`` at 1 min, which has already
      killed a connection mid-generation once (rule 1 in
      :func:`generate_review`).  Waiting inside the session would trade a
      gate that gives up for a lease that arrives to a dead connection.
    * **``gpu_lease_held`` is exactly "we hold one".**  With the lease in
      hand the counter has already been read, by the arbiter, as a retry
      rather than a refusal; reading it again here would put the give-up
      back while holding the card.  Without one, every refusal degrades
      to the gate that was there before.
    * **The release is in a ``finally`` and is best-effort.**  A release
      that raised would turn a stored review into a failed unit, and the
      arbiter's hold deadline restores the baseline regardless.
    """
    async with httpx.AsyncClient() as queue_client:
        lease_id = await acquire_review_lease(queue_client, "log_review")
        try:
            async with get_scheduler_session() as session:
                review = await generate_review(
                    session, gpu_lease_held=lease_id is not None
                )
        finally:
            if lease_id is not None:
                await release_review_lease(queue_client, lease_id, "log_review")

    if review is None:
        return

    logger.info("weekly_log_review_generated")
