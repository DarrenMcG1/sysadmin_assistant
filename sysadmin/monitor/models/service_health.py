"""Service health check results."""

from datetime import datetime
from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin

#: How one value of ``chk_health_status`` reads when a caller asks
#: whether the box is well.
#:
#: ``well``      the check ran and the service answered.
#: ``fault``     something is wrong with the service, or with the check.
#: ``unwatched`` nobody looked, *by declaration* — see :data:`SKIPPED`.
StatusReading = Literal["well", "fault", "unwatched"]

#: Every value the CHECK constraint below admits, classified.
#:
#: This exists because ``!= "ok"`` was written three times and is wrong
#: three times (``SNAG-API-004``).  Migration 009 added ``skipped`` to the
#: constraint, and every reader phrased as "not ok" silently reclassified
#: a *declaration* as a *fault* on the same day — ``GET
#: /api/sysadmin/status``, ``GET /api/summary`` and ``GET
#: /api/projects/managed`` all began serving a wrong flag, and two of the
#: three were masked by a genuine outage for eighteen days.
#:
#: The classification lives beside the constraint rather than beside any
#: one reader for the reason ``max_priority_for`` is derived from
#: ``PRIORITY_MAP`` and ``syslog_priority`` is round-tripped against it: a
#: vocabulary stated twice can disagree with itself, and the half that
#: drifts is the one no test drives.  ``tests/test_service_health_status.py``
#: asserts this map is **exactly total** over the constraint's own
#: ``sqltext`` — parsed from it, never re-typed — so a status added by a
#: future migration fails the suite rather than falling silently to one
#: side.
#:
#: Note which direction the fallback runs.  :func:`is_fault` reads an
#: unrecognised value as a fault, because the alternative is a monitor
#: going quiet about a state it does not understand — ``schema_guard``'s
#: posture, not ``collation.py``'s.  The totality guard is what makes
#: that branch unreachable in production rather than merely unlikely.
STATUS_READINGS: dict[str, StatusReading] = {
    "ok": "well",
    "degraded": "fault",
    "warning": "fault",
    "critical": "fault",
    "unreachable": "fault",
    # The *check* failed, not the service.  Still a fault: the state is
    # unknown and a monitor that reports unknown as well is not a
    # monitor.  ``reliability.py`` asks a different question of the same
    # value — "was this measured?" — and answers it separately and on
    # purpose; see :data:`~sysadmin.monitor.reliability.UNMEASURED_STATUSES`.
    "error": "fault",
    # A declared non-check.  Distinct from ``error`` in exactly the way
    # that matters here: somebody decided not to look, and recorded the
    # decision.  Reporting a decision as a fault names running units as
    # down and makes the flag beside them permanently false.
    "skipped": "unwatched",
}

#: Status recorded for a service the configuration says not to check.
#: Owned here because the CHECK constraint is the one statement of this
#: vocabulary; :mod:`sysadmin.monitor.services` re-exports it for the
#: writers, and :mod:`sysadmin.monitor.reliability` derives its own from
#: it, so the string is written once on this box.
SKIPPED = "skipped"


def is_fault(status: str) -> bool:
    """Does this recorded status mean something is wrong?

    The question every ``all_healthy`` flag is actually asking.  Prefer
    this over ``status != "ok"``, which reads a declared non-check as a
    fault, and over ``status in ("ok", SKIPPED)``, which is this
    classification restated at the call site and free to fall behind it.

    An unrecognised value reads as a fault — see :data:`STATUS_READINGS`
    for why that direction, and for the guard that keeps the branch
    unreachable.
    """
    return STATUS_READINGS.get(status, "fault") == "fault"


def is_unwatched(status: str) -> bool:
    """Was this service declared not-to-be-checked?

    The complement callers need when they partition rather than reduce —
    a count of *watched* services must not include one nobody looks at,
    or "3 of 30 failing" is computed against a denominator that contains
    three services no check has ever touched.

    Deliberately not ``not is_fault(...)``: ``ok`` is neither.
    """
    return STATUS_READINGS.get(status) == "unwatched"


class ServiceHealth(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "service_health"

    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __table_args__ = (
        # 'error' means the *check* failed (misconfigured, or systemctl
        # could not be queried) — distinct from 'critical'/'unreachable',
        # which are claims about the service itself. See migration 003.
        # 'skipped' is a service services.yaml says not to check — a
        # static or oneshot unit, or monitor: false. Distinct again from
        # 'error': nobody looked, rather than looking failed. Migration 009.
        CheckConstraint(
            "status IN ('ok', 'degraded', 'warning', 'critical', "
            "'unreachable', 'error', 'skipped')",
            name="chk_health_status",
        ),
        Index("idx_service_health_name_time", "service_name", checked_at.desc()),
    )
