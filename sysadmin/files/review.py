"""Weekly LLM-narrated disk review (file-organiser Tier 3).

Pipeline: gather structured facts (disk occupancy delta, audit deltas,
per-kind reclaim from Tier 2) → build a bounded prompt → ask
llama-server for a short narrative → store a :class:`DiskReview` row and
raise an ``info`` alert so the tray notices.

The facts come from **two tables on purpose**.  ``filesystem_audits``
measures junk accumulation; only ``resource_snapshots`` measures disk
occupancy, and occupancy is what answers "is this disk actually filling
up".  A week where reclaimable junk grew 3 GB while occupancy fell is a
different story from one where both rose, and a review built on either
table alone cannot tell them apart.

The LLM is optional at every step: when llama-server is unavailable the
review is still generated from :func:`build_fallback_narrative` — a
deterministic digest of the same facts — with ``llm_used=False``.  The
structured inputs are stored alongside the narrative (``stats``) so the
prose stays auditable against the data it was written from.

llama-server calls go through :class:`LLMClient`, which is constructed
per run (never shared across scheduler event loops — SNAG-AGENT-003).
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.database import get_scheduler_session
from sysadmin.core.models.alert import Alert
from sysadmin.files import forecast
from sysadmin.files import recommendations as file_recommendations
from sysadmin.files.models.disk_review import DiskReview
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot

logger = logging.getLogger(__name__)

DEFAULT_MOUNT = "/"

# The count columns worth trending, mapped to the findings key the
# recommendations use, so the two halves of ``stats`` line up.
TRENDED_COUNTS = {
    "duplicate_groups": "duplicate_groups_count",
    "old_downloads": "old_downloads_count",
    "misplaced_files": "misplaced_files_count",
    "large_files": "large_files_count",
    "empty_dirs": "empty_dirs_count",
    "similar_folders": "similar_folders_count",
    "stale_project_dirs": "stale_project_dirs_count",
}

REVIEW_SYSTEM_PROMPT = (
    "You are a pragmatic systems administrator reviewing one Linux "
    "workstation's disk. Write in UK English. Be concrete and reference "
    "directories by name. Do not invent facts not present in the data."
)

# The numeric sections are deliberately NOT the model's job, and the
# enforcement is structural rather than instructional.  Verified live
# 2026-08-06 (dria-agent-a-3b): given a prompt that listed sizes and
# told it not to restate them, it restated them anyway *and* invented a
# derived figure — "50 rebuildable dependency directories, each
# consuming 5GB", a quotient it computed from a 25 GB total the prompt
# had supplied.  Session 23 hit the same class of failure with scores.
#
# So the prompt below contains no figures at all: sizes become bands
# ("very large"), categories become named phrases, and occupancy becomes
# a direction.  A model with no numbers in its context cannot restate or
# derive one.  All real figures live in build_facts_section.
REVIEW_INSTRUCTIONS = (
    "Write three brief plain-text sections: 1) Where the mess is coming "
    "from: which categories explain the growth, judging from the listed "
    "items; 2) Clear first: at most three of the listed items, named by "
    "their category; 3) Watch: anything trending the wrong way that is "
    "not yet urgent, or 'nothing' if there is none. Figures are reported "
    "separately, so do not state any number, size, count, percentage or "
    "date — describe magnitude in words. Hard limit 150 words. Plain "
    "prose only: no markdown, no headings, no numbered or bulleted lists."
)

# Number-free names for each recommendation kind.  The Tier 2 titles
# carry counts ("Clear 11400 stale downloads") and so cannot go in the
# prompt; these say the same thing without a figure to regurgitate.
KIND_PHRASES = {
    "risk": "a projected disk threshold crossing",
    "duplicates": "groups of duplicate files",
    "downloads": "stale downloads in ~/Downloads",
    "stale_caches": "stale build caches (__pycache__ and similar)",
    "rebuildable_dirs": "rebuildable dependency directories (node_modules, .venv)",
    "large_files": "individually large files",
    "misplaced": "files sitting outside their category folders",
    "empty_dirs": "empty directories",
    "similar_folders": "similarly named folder pairs",
}

# Megabyte thresholds for the qualitative size bands.
SIZE_BANDS = ((10240, "very large"), (1024, "large"), (0.1, "moderate"))


async def gather_review_data(
    session: AsyncSession,
    period_days: int = 7,
    mount: str = DEFAULT_MOUNT,
) -> dict[str, Any]:
    """Structured facts for the review: current state plus deltas.

    Baselines are the *oldest row inside the window* — the closest thing
    to "where this stood a week ago" without assuming any particular
    scan cadence.  With nothing to compare against, deltas are ``None``
    rather than 0: "unchanged" and "unknown" are different answers and
    the narrative must not conflate them.

    Returns ``{}`` when there is no audit at all, which the caller
    treats as "nothing to review".
    """
    cutoff = datetime.now(UTC) - timedelta(days=period_days)

    latest = (
        await session.execute(
            select(FilesystemAudit)
            .order_by(desc(FilesystemAudit.scanned_at))
            .limit(1)
        )
    ).scalars().first()
    if latest is None:
        return {}

    baseline = (
        await session.execute(
            select(FilesystemAudit)
            .where(FilesystemAudit.scanned_at >= cutoff)
            .order_by(asc(FilesystemAudit.scanned_at))
            .limit(1)
        )
    ).scalars().first()
    # A lone audit inside the window is its own baseline — comparing a
    # row with itself would report a spurious "no change".
    if baseline is not None and baseline.id == latest.id:
        baseline = None

    agent_config = get_config().agents.file_organiser
    disk = await _gather_disk(session, cutoff, mount)
    projection = forecast.most_urgent_projection(
        disk.pop("_projections"),
        horizon_days=file_recommendations.RISK_HORIZON_DAYS,
    )
    disk["projection"] = projection._asdict() if projection else None

    return {
        "period_days": period_days,
        "disk": disk,
        "audit": _audit_facts(latest, baseline),
        "actions": _action_facts(latest, baseline, agent_config, projection),
    }


async def _gather_disk(
    session: AsyncSession, cutoff: datetime, mount: str
) -> dict[str, Any]:
    """Occupancy now, a week ago, and the fitted threshold crossings."""
    rows = (
        await session.execute(
            select(ResourceSnapshot.recorded_at, ResourceSnapshot.disk_usage)
            .where(ResourceSnapshot.recorded_at >= cutoff)
            .order_by(ResourceSnapshot.recorded_at)
        )
    ).all()
    series = forecast.disk_series_from(
        ((row.recorded_at, row.disk_usage) for row in rows), mount
    )

    if not series:
        return {
            "mount": mount,
            "current_percent": None,
            "baseline_percent": None,
            "delta_pp": None,
            "_projections": [],
        }

    current = series[-1][1]
    baseline = series[0][1]
    return {
        "mount": mount,
        "current_percent": round(current, 1),
        "baseline_percent": round(baseline, 1),
        # Percentage *points*, not percent — the difference of two
        # percentages is not itself a percentage.
        "delta_pp": round(current - baseline, 1) if len(series) > 1 else None,
        "samples": len(series),
        "_projections": forecast.project_disk_thresholds(series),
    }


def _audit_facts(
    latest: FilesystemAudit, baseline: FilesystemAudit | None
) -> dict[str, Any]:
    """Reclaimable total and per-finding counts, with week-on-week deltas."""
    counts: dict[str, Any] = {}
    for label, column in TRENDED_COUNTS.items():
        now = getattr(latest, column, 0) or 0
        was = getattr(baseline, column, None) if baseline is not None else None
        counts[label] = {
            "now": now,
            "delta": (now - was) if isinstance(was, int) else None,
        }

    reclaimable = latest.total_reclaimable_mb or 0
    baseline_reclaimable = (
        baseline.total_reclaimable_mb or 0 if baseline is not None else None
    )
    return {
        "scanned_at": latest.scanned_at.isoformat() if latest.scanned_at else None,
        "baseline_scanned_at": (
            baseline.scanned_at.isoformat()
            if baseline is not None and baseline.scanned_at
            else None
        ),
        # ``total_reclaimable_mb`` counts stale project directories only —
        # it is the audit's own long-running series, kept as-is so the
        # trend stays comparable with historical rows, and is *not* the
        # same number as the actions total below.
        "stale_dirs_mb": reclaimable,
        "stale_dirs_delta_mb": (
            reclaimable - baseline_reclaimable
            if baseline_reclaimable is not None
            else None
        ),
        "counts": counts,
    }


def _true_counts(audit: FilesystemAudit) -> dict[str, int]:
    """The audit row's untruncated counts, keyed by findings key."""
    return {
        "duplicates": audit.duplicate_groups_count or 0,
        "old_downloads": audit.old_downloads_count or 0,
        "misplaced_files": audit.misplaced_files_count or 0,
        "large_files": audit.large_files_count or 0,
        "empty_dirs": audit.empty_dirs_count or 0,
        "similar_folders": audit.similar_folders_count or 0,
        "stale_project_dirs": audit.stale_project_dirs_count or 0,
    }


def _action_facts(
    latest: FilesystemAudit,
    baseline: FilesystemAudit | None,
    agent_config: Any,
    projection: forecast.ThresholdProjection | None,
) -> dict[str, Any]:
    """Tier 2 advice for the latest audit, diffed per kind against a week ago."""
    recs = file_recommendations.recommendations_for_audit(
        latest.findings or {}, agent_config, projection, _true_counts(latest)
    )
    was_by_kind: dict[str, float] = {}
    if baseline is not None:
        # No projection for the baseline: the risk item carries 0 MB, so
        # including it would add a kind to the diff that never moves.
        was_by_kind = {
            r.kind: r.reclaimable_mb
            for r in file_recommendations.recommendations_for_audit(
                baseline.findings or {},
                agent_config,
                None,
                _true_counts(baseline),
            )
        }

    by_kind = {}
    for rec in recs:
        was = was_by_kind.get(rec.kind)
        by_kind[rec.kind] = {
            "now_mb": rec.reclaimable_mb,
            "delta_mb": (
                round(rec.reclaimable_mb - was, 1) if was is not None else None
            ),
        }

    return {
        "top": [
            {
                "kind": r.kind,
                "title": r.title,
                "severity": r.severity,
                "reclaimable_mb": r.reclaimable_mb,
                "action": r.action,
            }
            for r in recs[:5]
        ],
        "by_kind": by_kind,
        "total_reclaimable_mb": file_recommendations.total_reclaimable_mb(recs),
        "risk_count": sum(1 for r in recs if r.severity == "risk"),
        "action_count": len(recs),
    }


def build_facts_section(data: dict[str, Any]) -> str:
    """Deterministic 'what moved' block — numbers never come from the LLM."""
    disk = data["disk"]
    audit = data["audit"]
    actions = data["actions"]
    lines: list[str] = []

    if disk["current_percent"] is None:
        lines.append(f"Disk {disk['mount']}: no occupancy samples this period.")
    else:
        line = f"Disk {disk['mount']}: {disk['current_percent']}% used"
        if disk["delta_pp"] is not None:
            line += f" ({disk['delta_pp']:+.1f} pp over the period)"
        projection = disk.get("projection")
        if projection and projection["state"] == "projected":
            line += (
                f"; crosses {projection['percent']:.0f}% around "
                f"{projection['date']}"
            )
        elif projection and projection["state"] == "exceeded":
            line += f"; already past {projection['percent']:.0f}%"
        else:
            line += "; not on course to cross a threshold"
        lines.append(line + ".")

    lines.append(
        f"Reclaimable now: {forecast.format_mb(actions['total_reclaimable_mb'])} "
        f"across {actions['action_count']} actions."
    )

    movers = [
        (kind, block["delta_mb"])
        for kind, block in actions["by_kind"].items()
        if block["delta_mb"]
    ]
    if movers:
        movers.sort(key=lambda kv: -abs(kv[1]))
        lines.append(
            "Moved: "
            + ", ".join(
                f"{kind} {'+' if mb > 0 else ''}{forecast.format_mb(mb)}"
                for kind, mb in movers
            )
            + "."
        )

    count_movers = [
        (label, block["delta"])
        for label, block in audit["counts"].items()
        if block["delta"]
    ]
    if count_movers:
        count_movers.sort(key=lambda kv: -abs(kv[1]))
        lines.append(
            "Counts: "
            + ", ".join(f"{label} {delta:+d}" for label, delta in count_movers[:5])
            + "."
        )
    elif audit["baseline_scanned_at"] is None:
        lines.append("No earlier scan in this period — deltas unavailable.")

    return "\n".join(lines)


def size_band(mb: float) -> str:
    """Qualitative magnitude — the only size the prompt is allowed to see."""
    for threshold, label in SIZE_BANDS:
        if mb >= threshold:
            return label
    return "frees no space"


def _kind_phrase(kind: str) -> str:
    return KIND_PHRASES.get(kind, kind.replace("_", " "))


def occupancy_phrase(disk: dict[str, Any]) -> str:
    """Describe occupancy and its trend without stating a figure."""
    if disk["current_percent"] is None:
        return "Disk occupancy is unknown — no samples were recorded."

    level = (
        "nearly full" if disk["current_percent"] >= 90
        else "filling up" if disk["current_percent"] >= 75
        else "comfortable"
    )
    delta = disk.get("delta_pp")
    if delta is None:
        trend = "with no earlier reading to compare against"
    elif delta > 1:
        trend = "and rising noticeably"
    elif delta > 0:
        trend = "and creeping up"
    elif delta < -1:
        trend = "and falling"
    else:
        trend = "and holding steady"

    projection = disk.get("projection")
    if projection and projection["state"] == "exceeded":
        horizon = "A usage threshold has already been passed."
    elif projection and projection["state"] == "projected":
        days = projection["days_from_now"] or 0
        horizon = (
            "A threshold crossing is expected soon." if days <= 30
            else "A threshold crossing is expected within months."
            if days <= 365
            else "No threshold crossing is expected for years."
        )
    else:
        horizon = "It is not on course to cross a threshold."

    return f"Disk occupancy is {level} {trend}. {horizon}"


def build_review_prompt(data: dict[str, Any]) -> str:
    """Deterministic, figure-free prompt from the gathered facts.

    Contains no numbers by construction — see the note above
    :data:`REVIEW_INSTRUCTIONS` for the live failure that motivated it.
    """
    actions = data["actions"]
    lines = [
        "Weekly disk report for one Linux workstation.",
        occupancy_phrase(data["disk"]),
        "",
        "Outstanding items, most significant first:",
    ]
    for item in actions["top"]:
        marker = " [RISK]" if item["severity"] == "risk" else ""
        lines.append(
            f"- {_kind_phrase(item['kind'])}{marker} — "
            f"{size_band(item['reclaimable_mb'])} — {item['action']}"
        )

    movers = [
        (kind, block["delta_mb"])
        for kind, block in actions["by_kind"].items()
        if block["delta_mb"]
    ]
    if movers:
        lines += ["", "Categories that changed over the period:"]
        lines += [
            f"- {_kind_phrase(kind)}: {'grew' if mb > 0 else 'shrank'}"
            for kind, mb in sorted(movers, key=lambda kv: -abs(kv[1]))
        ]

    lines += ["", REVIEW_INSTRUCTIONS]
    return "\n".join(lines)


def strip_markdown(text: str) -> str:
    """Remove heading, list and emphasis markers the model was told not to emit.

    Instructions are a request, not a constraint. Verified live
    2026-08-06: under an explicit "no markdown, no headings, no numbered
    or bulleted lists" instruction, dria-agent-a-3b produced
    ``### Where the Mess is Coming From``, then ``1. **Node_modules
    directories**:`` on the next attempt. Stripping is deterministic, so
    the stored narrative matches the plain-text format the briefing and
    tray expect whatever the model does.

    Markers are only recognised at the start of a line, so prose keeps
    its hyphens and any inline asterisks.
    """
    cleaned = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        elif stripped.startswith(("- ", "* ", "+ ")):
            stripped = stripped[2:].strip()
        else:
            # "1. ", "2) " — an ordered list the model was asked not to use
            stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        cleaned.append(stripped.replace("**", ""))
    return "\n".join(cleaned).strip()


def build_fallback_narrative(data: dict[str, Any]) -> str:
    """Deterministic digest used when llama-server is unavailable."""
    actions = data["actions"]
    lines = [
        f"Weekly disk review ({data['period_days']} days) — "
        "generated without LLM narration.",
        build_facts_section(data),
    ]
    if actions["risk_count"]:
        lines.append("A disk threshold crossing is projected — see the risk action.")
    for item in actions["top"][:3]:
        lines.append(f"Clear first: {item['title']} — {item['action']}")
    return "\n".join(lines)


async def generate_review(
    session: AsyncSession,
    llm_client=None,
    period_days: int = 7,
    mount: str = DEFAULT_MOUNT,
) -> DiskReview | None:
    """Generate, store and return a review; None when there is no data.

    ``llm_client`` is injectable for tests; by default a fresh
    :class:`LLMClient` is built for this run and shut down afterwards.
    """
    from sysadmin.core.llm_client import LLMClient

    data = await gather_review_data(session, period_days, mount)
    if not data:
        logger.info("disk_review_skipped_no_data")
        return None

    # Inference can take minutes and Postgres may enforce
    # idle_in_transaction_session_timeout (1min on this host, which
    # killed the connection mid-generation when found live) — end the
    # read transaction now; the INSERT below begins a fresh one.
    await session.commit()

    config = get_config()
    narrative: str | None = None

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
        # Numbers first, deterministically; the model's prose follows,
        # with any markdown it emitted against instructions removed
        narrative = f"{build_facts_section(data)}\n\n{strip_markdown(narrative)}"
    else:
        narrative = build_fallback_narrative(data)
        logger.warning("disk_review_llm_unavailable_used_fallback")

    review = DiskReview(
        period_days=period_days,
        narrative=narrative,
        llm_used=llm_used,
        model_used=config.llm.model if llm_used else None,
        stats=data,
    )
    session.add(review)
    await session.flush()
    return review


async def run_weekly_review() -> None:
    """Scheduler entry point — generate, store, and notify via an alert."""
    async with get_scheduler_session() as session:
        review = await generate_review(session)
        if review is None:
            return

        first_line = review.narrative.splitlines()[0] if review.narrative else ""
        session.add(Alert(
            agent="file_organiser",
            severity="info",
            title="Weekly disk review ready",
            message=first_line[:255],
            details={
                "review_id": str(review.id),
                "llm_used": review.llm_used,
                "endpoint": "/api/files/review",
            },
        ))
    logger.info("weekly_disk_review_generated")
