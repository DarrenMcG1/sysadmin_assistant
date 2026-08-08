"""Per-service reliability scores from the daily scoring job (Session 25)."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin


class ReliabilityScore(UUIDPrimaryKeyMixin, Base):
    """One service's reliability over one scoring window.

    Rows are written once a day by the ``reliability_scoring`` cron job so
    the score becomes trendable.  ``GET /api/services/reliability`` does
    **not** read them: the score is recomputed live from
    ``service_health`` on every request (one aggregate over at most a
    week of rows), because a stored answer would be up to 24 hours stale
    and would 404 before the first job ran.  This table is history, not
    the serving path.

    Every measured quantity is its own column rather than a key in
    ``deductions``.  That is the Session 24 lesson generalised: a number
    a reader has to dig out of JSONB is a number nothing can index,
    constrain, or trend.  ``deductions`` holds only the attribution — the
    list of ``(kind, points, detail, waived)`` behind ``score`` — which
    is prose and genuinely belongs in a blob.

    ``coverage_percent`` deliberately never affects ``score``.  A gap in
    the series means the *monitor* was down, and deducting for that would
    charge the service for this application's downtime.  It lowers
    ``confidence`` instead.
    """

    __tablename__ = "reliability_scores"

    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)

    # --- what was measured ---
    uptime_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    checks_recorded: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    #: Recorded checks minus unmeasurable ones — the denominator of every
    #: rate above.  An 'error' row means systemctl could not be queried,
    #: so the service's state is unknown, not bad.
    checks_measured: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    failed_checks: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    error_checks: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    #: Runs of consecutive failing checks, not failing checks. One outage
    #: writes one episode however long it lasts.
    outage_episodes: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    longest_outage_minutes: Mapped[float | None] = mapped_column(
        Numeric(10, 1), nullable=True
    )
    #: NULL below two episodes — one incident establishes no interval.
    mean_hours_between_incidents: Mapped[float | None] = mapped_column(
        Numeric(10, 1), nullable=True
    )

    # --- how far to trust it ---
    checks_expected: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    coverage_percent: Mapped[float] = mapped_column(
        Numeric(6, 2), server_default=text("0")
    )
    observed_days: Mapped[float] = mapped_column(
        Numeric(6, 2), server_default=text("0")
    )
    confidence: Mapped[str] = mapped_column(String(10), server_default=text("'high'"))
    confidence_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- provenance ---
    window_days: Mapped[int] = mapped_column(Integer, server_default=text("7"))
    window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: An expected-down service is scored and its deductions listed, but
    #: they are not applied — see sysadmin.monitor.reliability.
    muted: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    waived_points: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    deductions: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("score BETWEEN 0 AND 100", name="chk_reliability_score_range"),
        CheckConstraint(
            "grade IN ('reliable', 'degraded', 'unreliable', 'failing')",
            name="chk_reliability_grade",
        ),
        CheckConstraint(
            "confidence IN ('high', 'low')", name="chk_reliability_confidence"
        ),
        Index(
            "idx_reliability_scores_service_time",
            "service_name",
            computed_at.desc(),
        ),
    )
