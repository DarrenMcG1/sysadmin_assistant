"""Pure forecasting helpers — least-squares growth fits and projections.

Qt-free, DB-free and side-effect-free on purpose.  Every function takes
already-parsed contract objects (or plain numbers) and returns plain
data, so the maths can be tested without a QApplication, a backend or a
database.

Lives under ``sysadmin.services`` rather than the tray because three
consumers need it: the tray's Disk Growth widget, the file-organiser
recommendations (a threshold crossing inside 30 days outranks raw
megabytes) and the weekly disk review.  Like :mod:`sysadmin.core.contracts`
it is dependency-light — pydantic + stdlib only — so importing it from
the tray does not pull FastAPI or SQLAlchemy in.

Two separate forecasts feed the Disk Growth widget:

``project_disk_thresholds``
    Least-squares fit over the *disk usage percentage* recorded in
    ``GET /api/sysadmin/resources/history``, projecting the date each
    configured threshold (80 % warning, 90 % critical) is crossed.
    This is the only series that actually answers "when does the disk
    fill up".

``describe_reclaimable_forecast``
    Presentation of the regression the backend already computes in
    ``GET /api/files/trends`` — how fast reclaimable junk accumulates
    and when it passes the configured milestones.  The backend owns
    that maths; we only format it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from sysadmin.core.contracts import (
    FileTrendForecast,
    ResourceHistoryResponse,
)

# Matches the disk gauge thresholds on the Overview tab.
DISK_WARNING_PERCENT = 80
DISK_CRITICAL_PERCENT = 90


class LinearFit(NamedTuple):
    """Result of a least-squares fit ``y = slope * x + intercept``."""

    slope: float
    intercept: float
    points: int


class ThresholdProjection(NamedTuple):
    """When a growing series is expected to cross a threshold.

    ``days_from_now`` and ``date`` are ``None`` when the crossing cannot
    be projected; ``state`` explains why:

    ``"projected"``  — a future crossing date was computed
    ``"exceeded"``   — the latest reading is already at or past it
    ``"not_growing"``— the series is flat or shrinking
    """

    percent: float
    state: str
    days_from_now: float | None = None
    date: str | None = None


def linear_fit(points: Sequence[tuple[float, float]]) -> LinearFit | None:
    """Least-squares fit through ``(x, y)`` pairs.

    Returns ``None`` for fewer than two points or a degenerate x-range
    (every sample at the same instant), which would divide by zero.
    """
    n = len(points)
    if n < 2:
        return None

    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_xx = sum(p[0] ** 2 for p in points)

    denom = n * sum_xx - sum_x**2
    if denom == 0:
        return None

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return LinearFit(slope=slope, intercept=intercept, points=n)


def _parse_ts(value: Any) -> datetime | None:
    """Coerce a timestamp to ``datetime``, tolerating ISO strings and junk.

    Accepts ``datetime`` unchanged so ORM rows can be fed in directly;
    accepts ISO text (with a trailing ``Z``) for contract objects, which
    carry timestamps as strings.
    """
    if isinstance(value, datetime):
        return value
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def disk_series_from(
    entries: Iterable[tuple[Any, Any]],
    mount: str = "/",
) -> list[tuple[datetime, float]]:
    """``(timestamp, used percent)`` pairs from raw snapshot data.

    ``entries`` yields ``(recorded_at, disk_usage)`` pairs — the shape
    both a :class:`ResourceSnapshot` ORM row and a parsed contract
    object can produce, which is why this takes tuples rather than
    either type.  ``recorded_at`` may be a ``datetime`` or an ISO
    string.

    Snapshots missing the mount (or the whole ``disk_usage`` block) are
    skipped rather than treated as 0 % — a gap must not look like an
    empty disk.  Mixed naive/aware timestamps are left alone; callers
    within one source are consistent, and comparing across sources is
    not a supported use.
    """
    series: list[tuple[datetime, float]] = []
    for recorded_at, disk_usage in entries:
        ts = _parse_ts(recorded_at)
        if ts is None or not isinstance(disk_usage, dict):
            continue
        info = disk_usage.get(mount)
        if not isinstance(info, dict):
            continue
        pct = info.get("percent")
        if isinstance(pct, int | float) and not isinstance(pct, bool):
            series.append((ts, float(pct)))
    series.sort(key=lambda p: p[0])
    return series


def disk_series(
    history: ResourceHistoryResponse,
    mount: str = "/",
) -> list[tuple[datetime, float]]:
    """Extract ``(timestamp, used percent)`` pairs for one mount point.

    Contract-shaped adapter over :func:`disk_series_from`, used by the
    tray, which only ever sees parsed HTTP responses.
    """
    return disk_series_from(
        ((snap.recorded_at, snap.disk_usage) for snap in history.snapshots),
        mount,
    )


def growth_rate_per_day(series: list[tuple[datetime, float]]) -> float | None:
    """Percentage points gained per day, or ``None`` if unfittable."""
    if len(series) < 2:
        return None
    t0 = series[0][0]
    fit = linear_fit(
        [((ts - t0).total_seconds() / 86400.0, value) for ts, value in series]
    )
    return None if fit is None else fit.slope


def project_disk_thresholds(
    series: list[tuple[datetime, float]],
    thresholds: tuple[int, ...] = (DISK_WARNING_PERCENT, DISK_CRITICAL_PERCENT),
) -> list[ThresholdProjection]:
    """Project when disk usage crosses each threshold.

    Days are measured from the *most recent* sample, matching how the
    backend's reclaimable forecast reports its projections.  Returns an
    empty list when there is not enough history to fit a line at all.
    """
    if len(series) < 2:
        return []

    t0 = series[0][0]
    fit = linear_fit(
        [((ts - t0).total_seconds() / 86400.0, value) for ts, value in series]
    )
    if fit is None:
        return []

    latest_ts, current = series[-1]
    days_elapsed = (latest_ts - t0).total_seconds() / 86400.0

    projections: list[ThresholdProjection] = []
    for threshold in thresholds:
        if current >= threshold:
            projections.append(ThresholdProjection(float(threshold), "exceeded"))
            continue
        if fit.slope <= 0:
            projections.append(ThresholdProjection(float(threshold), "not_growing"))
            continue

        days_to_target = (threshold - fit.intercept) / fit.slope
        days_from_now = days_to_target - days_elapsed
        if days_from_now <= 0:
            # The fitted line already sits above the threshold even
            # though the last reading does not — treat as imminent
            # rather than claiming a date in the past.
            projections.append(ThresholdProjection(float(threshold), "not_growing"))
            continue

        target_date = latest_ts + timedelta(days=days_from_now)
        projections.append(
            ThresholdProjection(
                percent=float(threshold),
                state="projected",
                days_from_now=round(days_from_now, 1),
                date=target_date.strftime("%Y-%m-%d"),
            )
        )
    return projections


def most_urgent_projection(
    projections: list[ThresholdProjection],
    horizon_days: float = 30.0,
) -> ThresholdProjection | None:
    """The single crossing worth warning about, or ``None``.

    Preference order, chosen so the *most specific true statement* wins:

    1. A crossing projected within ``horizon_days`` — soonest first.
       "90 % in 10 days" beats "already past 80 %" because it is both
       more urgent and more actionable.
    2. Otherwise the highest threshold already exceeded.  Being past
       80 % is worth saying even when the 90 % crossing is a year out.
    3. Otherwise the soonest projection of any horizon, so a caller that
       wants to display a distant trend still gets one.

    ``not_growing`` entries are never chosen — a disk that is not
    filling has no crossing to report.
    """
    projected = sorted(
        (
            p for p in projections
            if p.state == "projected" and p.days_from_now is not None
        ),
        key=lambda p: p.days_from_now,  # type: ignore[arg-type,return-value]
    )
    imminent = [p for p in projected if p.days_from_now <= horizon_days]  # type: ignore[operator]
    if imminent:
        return imminent[0]

    exceeded = [p for p in projections if p.state == "exceeded"]
    if exceeded:
        return max(exceeded, key=lambda p: p.percent)

    return projected[0] if projected else None


def format_days(days: float) -> str:
    """Human-readable horizon, e.g. ``"12 days"`` / ``"~1.4 years"``."""
    if days < 1:
        return "under a day"
    if days < 60:
        return f"{days:.0f} days"
    if days < 730:
        return f"~{days / 30.44:.0f} months"
    return f"~{days / 365.25:.1f} years"


def describe_reclaimable_forecast(
    forecast: FileTrendForecast,
) -> list[tuple[str, str]]:
    """Turn ``/api/files/trends``'s forecast block into label/value rows.

    Always returns at least one row so the widget never renders blank —
    the "not enough scans yet" case is a legitimate backend answer, not
    an error.
    """
    if forecast.insufficient_data or forecast.data_points < 2:
        return [("Reclaimable trend", "Not enough scans yet")]

    rate = forecast.growth_rate_mb_per_day
    if rate > 0:
        rate_text = f"+{rate:.1f} MB/day"
    elif rate < 0:
        rate_text = f"{rate:.1f} MB/day (shrinking)"
    else:
        rate_text = "steady"

    rows = [
        ("Reclaimable now", format_mb(forecast.current_reclaimable_mb)),
        ("Junk growth", f"{rate_text}  ({forecast.data_points} scans)"),
    ]
    for label, date in sorted(forecast.projected_milestones.items()):
        rows.append((f"Reaches {label.upper()}", date))
    return rows


def format_mb(mb: float) -> str:
    """Format megabytes as MB or GB with sensible precision."""
    if abs(mb) >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"
