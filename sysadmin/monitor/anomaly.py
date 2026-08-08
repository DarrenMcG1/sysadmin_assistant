"""Resource anomaly detection — z-scores against ``resource_snapshots`` history.

Fixed thresholds (``agents.sysadmin.thresholds``) only fire at absolute
limits. This module flags values that are unusual *for this machine*: a
rolling mean/stdev is computed over the recent history of each metric and
anything more than ``z_threshold`` standard deviations away is reported.

Deliberately dependency-light and side-effect free — no DB, no config
loading, no alerting. The SysAdmin agent supplies the history it read and
turns the returned :class:`Anomaly` objects into alerts.

Guards:
    - **cold start** — a series shorter than ``min_samples`` is skipped
      entirely, so a fresh install does not alert on three data points
    - **flat series** — a stdev below ``min_stdev`` is skipped, so a
      near-constant metric cannot produce an enormous (or infinite)
      z-score from a rounding-sized deviation
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sysadmin.core.config import AnomalyConfig

# Metric keys are stable identifiers used for alert dedup/suppression:
#   "cpu", "ram", "disk:<mount>"
DISK_KEY_PREFIX = "disk:"


def metric_label(key: str) -> str:
    """Human-readable name for a metric key ('disk:/home' → 'disk /home')."""
    if key.startswith(DISK_KEY_PREFIX):
        return f"disk {key[len(DISK_KEY_PREFIX):]}"
    return {"cpu": "CPU", "ram": "RAM"}.get(key, key)


def mean(values: Iterable[float]) -> float:
    """Arithmetic mean. Returns 0.0 for an empty series."""
    items = list(values)
    if not items:
        return 0.0
    return math.fsum(items) / len(items)


def stdev(values: Sequence[float]) -> float:
    """Sample standard deviation (n-1). Returns 0.0 for fewer than 2 values."""
    n = len(values)
    if n < 2:
        return 0.0
    mu = mean(values)
    variance = math.fsum((v - mu) ** 2 for v in values) / (n - 1)
    return math.sqrt(variance)


def z_score(value: float, mu: float, sigma: float) -> float | None:
    """Standard score, or ``None`` when the spread is zero/degenerate.

    Returning ``None`` rather than ``inf``/``nan`` keeps callers from
    having to special-case non-finite maths.
    """
    if sigma <= 0.0 or not math.isfinite(sigma) or not math.isfinite(value):
        return None
    z = (value - mu) / sigma
    return z if math.isfinite(z) else None


@dataclass(frozen=True)
class Anomaly:
    """A metric whose current value is far from its recent history."""

    key: str
    label: str
    value: float
    mean: float
    stdev: float
    z: float
    samples: int

    @property
    def direction(self) -> str:
        """'above' or 'below' the historical mean."""
        return "above" if self.z >= 0 else "below"

    def as_details(self) -> dict[str, float | int | str | bool]:
        """Alert ``details`` payload — also carries the dedup key."""
        return {
            "anomaly": True,
            "resource": self.key,
            "value": round(self.value, 2),
            "mean": round(self.mean, 2),
            "stdev": round(self.stdev, 2),
            "z_score": round(self.z, 2),
            "samples": self.samples,
            "direction": self.direction,
        }


def detect_anomalies(
    current: dict[str, float],
    history: dict[str, list[float]],
    config: AnomalyConfig,
) -> list[Anomaly]:
    """Flag metrics in ``current`` that are outliers against ``history``.

    ``current`` and ``history`` share metric keys ("cpu", "ram",
    "disk:/home"). Metrics with no history, too little history, or a
    too-flat history are silently skipped. Results are ordered by
    descending |z| so the most extreme anomaly is reported first.
    """
    if not config.enabled:
        return []

    anomalies: list[Anomaly] = []

    for key, value in current.items():
        if value is None or not math.isfinite(value):
            continue

        series = [v for v in history.get(key, []) if v is not None and math.isfinite(v)]
        if len(series) < config.min_samples:
            continue  # cold-start guard

        sigma = stdev(series)
        if sigma < config.min_stdev:
            continue  # flat series — a z-score here would be meaningless

        z = z_score(value, mean(series), sigma)
        if z is None or abs(z) < config.z_threshold:
            continue

        anomalies.append(
            Anomaly(
                key=key,
                label=metric_label(key),
                value=float(value),
                mean=mean(series),
                stdev=sigma,
                z=z,
                samples=len(series),
            )
        )

    anomalies.sort(key=lambda a: abs(a.z), reverse=True)
    return anomalies
