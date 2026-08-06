"""Turn a filesystem audit into ranked, actionable disk advice.

The file-organiser equivalent of :mod:`sysadmin.services.recommendations`,
with one deliberate difference: there is no health score here, so the
currency is **reclaimable megabytes** rather than recoverable points.
That is a more honest unit — it is directly measurable — but it only
applies to the findings that actually free space.

Three finding types free space when acted on: duplicate groups, old
downloads and stale caches.  The rest are *tidiness*: moving a misplaced
file, removing an empty directory or merging similar folders reclaims
nothing.  Those carry ``reclaimable_mb = 0.0`` and are ranked by
``item_count`` beneath anything with real megabytes behind it, rather
than being given an invented currency to compete on.

Large files are a fourth case — measurable but not reclaimable, because
whether a 4 GB video is junk is a judgement only the user can make.
They are surfaced for review at 0.0 MB with the total in ``detail``.

Ranking is risk-first, exactly like the project recommendations.  The one
risk is a projected disk-threshold crossing inside
:data:`RISK_HORIZON_DAYS`: it reclaims nothing by itself, but "this disk
fills up in three weeks" outranks any byte total, the way ``no_remote``
outranks score arithmetic in Session 22.

Pure module: no DB access, no FastAPI — give it a findings dict, get a
list.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from sysadmin.contracts import FileRecommendationInfo
from sysadmin.services.forecast import ThresholdProjection, format_mb

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sysadmin.config import FileOrganiserConfig

# A crossing further out than this is a trend, not a risk.
RISK_HORIZON_DAYS = 30.0

# Stale project directories the stale-cache cleaner will actually remove.
# Defined here rather than in the agent so the advice and the executor
# cannot drift apart; ``FileOrganiserAgent`` imports this constant.
CACHE_DIR_TYPES = ("__pycache__", ".pytest_cache", ".tox")

# Stale project directories that are *not* caches.  Big, safely
# regenerable, but no endpoint deletes them — the advice names the
# manual step, the convention Session 22 established for findings with
# no executor.
REBUILDABLE_DIR_TYPES = ("node_modules", ".venv", "venv", "target", "build", "dist")


def recommendations_for_audit(
    findings: dict[str, Any],
    agent_config: FileOrganiserConfig,
    disk_projection: ThresholdProjection | None = None,
    true_counts: Mapping[str, int] | None = None,
) -> list[FileRecommendationInfo]:
    """Ranked disk advice for one filesystem audit's findings.

    ``findings`` is the stored ``FilesystemAudit.findings`` blob.  It is
    read tolerantly: entries written before sizes were recorded simply
    price at 0.0 MB and fall to the tidiness tier rather than raising.

    ``true_counts`` maps a findings key to the *pre-truncation* count
    from the audit row's own columns.  This matters: findings lists are
    capped at 50–100 entries before storage, and on a real scan the caps
    bite hard — 11,877 misplaced files stored as 200.  Without the true
    counts every recommendation understates itself by up to sixty-fold,
    and the sizes summed from a truncated list become a lower bound,
    which the detail text then has to say out loud.

    ``disk_projection`` is the soonest threshold crossing from
    :func:`sysadmin.services.forecast.project_disk_thresholds`, or
    ``None`` when there is too little resource history to fit a line.

    Ordering: ``risk`` first, then reclaimable megabytes descending,
    then item count descending, then title for stability.
    """
    counts: Mapping[str, int] = true_counts or {}
    recs: list[FileRecommendationInfo] = []

    risk = _disk_risk(disk_projection)
    if risk is not None:
        recs.append(risk)

    recs.extend(_space_recommendations(findings, agent_config, counts))
    recs.extend(_tidiness_recommendations(findings, agent_config, counts))

    recs.sort(
        key=lambda r: (r.severity != "risk", -r.reclaimable_mb, -r.item_count, r.title)
    )
    return recs


def total_reclaimable_mb(recs: list[FileRecommendationInfo]) -> float:
    """Megabytes freed if every recommendation were acted on.

    Sums only what is genuinely reclaimable, so this is smaller than
    "everything the audit found" and larger than
    ``FilesystemAudit.total_reclaimable_mb``, which counts stale project
    directories alone.
    """
    return round(sum(r.reclaimable_mb for r in recs), 1)


def _disk_risk(
    projection: ThresholdProjection | None,
) -> FileRecommendationInfo | None:
    """The threshold-crossing risk item, if the horizon is close enough.

    ``not_growing`` never produces a risk — a disk that is not filling
    has no crossing to warn about, whatever the current reading.
    """
    if projection is None or projection.state == "not_growing":
        return None

    if projection.state == "exceeded":
        detail = (
            f"Disk usage is already at or past {projection.percent:.0f}%. "
            "Reclaiming space is no longer optional."
        )
    elif projection.state == "projected":
        days = projection.days_from_now
        if days is None or days > RISK_HORIZON_DAYS:
            return None
        detail = (
            f"Disk usage is projected to cross {projection.percent:.0f}% "
            f"on {projection.date} — about {days:.0f} days away, on the "
            "current growth trend."
        )
    else:  # unknown state — say nothing rather than guess
        return None

    return FileRecommendationInfo(
        kind="risk",
        severity="risk",
        title=f"Disk crosses {projection.percent:.0f}% soon",
        detail=detail,
        reclaimable_mb=0.0,
        item_count=0,
        action="Act on the reclaim items below, or move data to another volume",
    )


def _space_recommendations(
    findings: dict[str, Any],
    agent_config: FileOrganiserConfig,
    counts: Mapping[str, int],
) -> list[FileRecommendationInfo]:
    """Findings that genuinely free space when acted on."""
    recs: list[FileRecommendationInfo] = []

    duplicates = _as_list(findings.get("duplicates"))
    if duplicates:
        reclaim = sum(_number(d.get("reclaimable_mb")) for d in duplicates)
        extra_copies = sum(
            max(_int(d.get("count")) - 1, 0) for d in duplicates
        )
        # Counted in *groups*, matching ``duplicate_groups_count`` — the
        # only duplicate figure the audit row stores untruncated.  Extra
        # copies can only be summed from the stored list, so they belong
        # in the detail, not the count.
        groups = _true_count(counts, "duplicates", len(duplicates))
        missing = _sizes_missing(duplicates, "reclaimable_mb")
        recs.append(FileRecommendationInfo(
            kind="duplicates",
            title=f"Deduplicate {groups} groups of identical files",
            detail=(
                f"Deleting all but one copy of each frees "
                f"{_size_phrase(reclaim, groups, len(duplicates), missing)}; "
                f"{extra_copies} redundant copies across the "
                f"{len(duplicates)} groups measured."
                # An audit that recorded no sizes cannot have sorted by
                # them either, so its stored slice is not "the largest".
                + _truncation_note(
                    groups, len(duplicates), "groups", sorted_by_size=not missing
                )
                + _sizing_caveat(missing)
            ),
            reclaimable_mb=round(reclaim, 1),
            item_count=groups,
            action=(
                "POST /api/files/clean/duplicates "
                "(dry run; add confirm: true to execute)"
            ),
        ))

    downloads = _as_list(findings.get("old_downloads"))
    if downloads:
        reclaim = sum(_number(d.get("size_mb")) for d in downloads)
        total = _true_count(counts, "old_downloads", len(downloads))
        missing = _sizes_missing(downloads, "size_mb")
        recs.append(FileRecommendationInfo(
            kind="downloads",
            title=f"Clear {total} stale downloads",
            detail=(
                f"Untouched for over {agent_config.downloads_stale_days} days, "
                f"holding {_size_phrase(reclaim, total, len(downloads), missing)}."
                + _truncation_note(
                    total, len(downloads), "downloads", sorted_by_size=not missing
                )
                + _sizing_caveat(missing)
            ),
            reclaimable_mb=round(reclaim, 1),
            item_count=total,
            action=(
                "POST /api/files/clean/downloads "
                "(dry run; add confirm: true to execute)"
            ),
        ))

    # Stale project directories are split between two recommendations but
    # the audit stores one combined count, so neither half can claim a
    # true count of its own — the note goes on the combined shortfall.
    stale_dirs = _as_list(findings.get("stale_project_dirs"))
    stale_note = _truncation_note(
        _true_count(counts, "stale_project_dirs", len(stale_dirs)),
        len(stale_dirs),
        noun="stale directories",
    )

    caches = [d for d in stale_dirs if d.get("type") in CACHE_DIR_TYPES]
    if caches:
        reclaim = sum(_number(d.get("size_mb")) for d in caches)
        recs.append(FileRecommendationInfo(
            kind="stale_caches",
            title=f"Delete {len(caches)} stale cache directories",
            detail=(
                f"{', '.join(sorted({str(d.get('type')) for d in caches}))} — "
                f"{format_mb(reclaim)}, regenerated automatically on next run."
                + stale_note
            ),
            reclaimable_mb=round(reclaim, 1),
            item_count=len(caches),
            action="POST /api/files/clean/stale-caches",
        ))

    rebuildable = [d for d in stale_dirs if d.get("type") in REBUILDABLE_DIR_TYPES]
    if rebuildable:
        reclaim = sum(_number(d.get("size_mb")) for d in rebuildable)
        biggest = max(rebuildable, key=lambda d: _number(d.get("size_mb")))
        recs.append(FileRecommendationInfo(
            kind="rebuildable_dirs",
            title=f"Delete {len(rebuildable)} rebuildable dependency directories",
            detail=(
                f"{format_mb(reclaim)} across "
                f"{', '.join(sorted({str(d.get('type')) for d in rebuildable}))}; "
                f"largest is {biggest.get('path')} at "
                f"{format_mb(_number(biggest.get('size_mb')))}. "
                "No endpoint removes these — reinstall on next build."
                + stale_note
            ),
            reclaimable_mb=round(reclaim, 1),
            item_count=len(rebuildable),
            action="Delete by hand; each is regenerated by its package manager",
        ))

    return recs


def _tidiness_recommendations(
    findings: dict[str, Any],
    agent_config: FileOrganiserConfig,
    counts: Mapping[str, int],
) -> list[FileRecommendationInfo]:
    """Findings worth acting on that free no space."""
    recs: list[FileRecommendationInfo] = []

    large = _as_list(findings.get("large_files"))
    if large:
        size_total = sum(_number(f.get("size_mb")) for f in large)
        biggest = max(large, key=lambda f: _number(f.get("size_mb")))
        large_count = _true_count(counts, "large_files", len(large))
        recs.append(FileRecommendationInfo(
            kind="large_files",
            title=f"Review {large_count} large files",
            detail=(
                f"Each over {agent_config.large_file_mb} MB, "
                f"{_size_phrase(size_total, large_count, len(large), False)} "
                f"in total; largest is {biggest.get('path')} at "
                f"{format_mb(_number(biggest.get('size_mb')))}. "
                "Not counted as reclaimable — only you know which are junk."
                + _truncation_note(large_count, len(large), "large files")
            ),
            reclaimable_mb=0.0,
            item_count=large_count,
            action="Inspect GET /api/files/large and delete or archive by hand",
        ))

    misplaced = findings.get("misplaced_files")
    if isinstance(misplaced, dict) and misplaced:
        by_category: dict[str, int] = {
            str(cat): len(paths)
            for cat, paths in misplaced.items()
            if isinstance(paths, list) and paths
        }
        listed: int = sum(by_category.values())
        misplaced_count = _true_count(counts, "misplaced_files", listed)
        if misplaced_count:
            breakdown = ", ".join(
                f"{count} {cat}"
                for cat, count in sorted(by_category.items(), key=lambda kv: -kv[1])
            )
            recs.append(FileRecommendationInfo(
                kind="misplaced",
                title=(
                    f"File {misplaced_count} misplaced files into their categories"
                ),
                detail=(
                    f"{breakdown}. Moving files frees no space."
                    + _truncation_note(
                        misplaced_count, listed, "files", sorted_by_size=False
                    )
                ),
                reclaimable_mb=0.0,
                item_count=misplaced_count,
                action=(
                    "POST /api/files/organise "
                    "(dry run; add confirm: true to execute)"
                ),
            ))

    empty_dirs = _as_list(findings.get("empty_dirs"), allow_scalars=True)
    if empty_dirs:
        empty_count = _true_count(counts, "empty_dirs", len(empty_dirs))
        recs.append(FileRecommendationInfo(
            kind="empty_dirs",
            title=f"Remove {empty_count} empty directories",
            detail=(
                "Cleared by the stale-cache endpoint, which removes empty "
                "directories in the same pass."
                + _truncation_note(
                    empty_count, len(empty_dirs), "directories",
                    sorted_by_size=False,
                )
            ),
            reclaimable_mb=0.0,
            item_count=empty_count,
            action="POST /api/files/clean/stale-caches",
        ))

    similar = _as_list(findings.get("similar_folders"), allow_scalars=True)
    if similar:
        similar_count = _true_count(counts, "similar_folders", len(similar))
        recs.append(FileRecommendationInfo(
            kind="similar_folders",
            title=f"Merge {similar_count} similarly named folder groups",
            detail=(
                "Names within "
                f"{agent_config.similarity_threshold:.0%} similarity — likely "
                "the same thing kept twice. No executor: merging needs a "
                "judgement about which copy is current."
                + _truncation_note(
                    similar_count, len(similar), "groups", sorted_by_size=False
                )
            ),
            reclaimable_mb=0.0,
            item_count=similar_count,
            action="Inspect GET /api/files/report and merge by hand",
        ))

    return recs


def _true_count(counts: Mapping[str, int], key: str, listed: int) -> int:
    """The audit row's untruncated count, or the listed length.

    Never returns less than ``listed``: a stored count smaller than the
    stored list would mean the two disagree, and the list is the thing
    we can actually see.
    """
    stored = counts.get(key)
    if not isinstance(stored, int) or isinstance(stored, bool) or stored < 0:
        return listed
    return max(stored, listed)


def _truncation_note(
    total: int,
    listed: int,
    noun: str = "items",
    sorted_by_size: bool = True,
) -> str:
    """Say when the detail was computed from a truncated sample.

    ``sorted_by_size`` distinguishes the lists the agent sorts before
    truncating (duplicates, downloads, large files, stale directories —
    so the stored sample really is the largest) from the ones it does
    not (misplaced files, empty directories, similar folders, which are
    stored in walk order).  Calling an arbitrary slice "the largest"
    would be a small lie in the same class as the ones this note exists
    to prevent.
    """
    if total <= listed:
        return ""
    which = "largest" if sorted_by_size else "first"
    return (
        f" Detail covers the {which} {listed} of {total} {noun} — "
        "findings are truncated before storage."
    )


def _sizes_missing(items: list[dict], key: str) -> bool:
    """True when no item records a size — an audit predating the field."""
    return bool(items) and not any(key in item for item in items)


def _size_phrase(mb: float, total: int, listed: int, missing: bool) -> str:
    """Describe a size total at the confidence the data supports.

    Three states, and conflating them is how "frees 0 MB" ends up on a
    finding holding gigabytes: sizes were never recorded (unknown), the
    list was truncated (a floor), or the figure is exact.
    """
    if missing:
        return "an unrecorded amount"
    if total > listed:
        return f"at least {format_mb(mb)}"
    return format_mb(mb)


def _sizing_caveat(missing: bool) -> str:
    """The remedy for an audit that predates size recording."""
    if not missing:
        return ""
    return " Sizes were not recorded by this scan — rescan to price it."


def _as_list(value: Any, allow_scalars: bool = False) -> list:
    """Coerce a findings entry to a list of dicts (or of anything).

    Findings come from JSONB and are hand-editable in the database, so a
    malformed entry must degrade to "no recommendation" rather than
    raising inside an API request.
    """
    if not isinstance(value, list):
        return []
    if allow_scalars:
        return value
    return [item for item in value if isinstance(item, dict)]


def _number(value: Any) -> float:
    """A findings number, or 0.0 for anything unusable."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def _int(value: Any) -> int:
    """A findings integer, or 0 for anything unusable."""
    return int(_number(value))
