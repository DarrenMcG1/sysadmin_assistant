"""Alerts raised by agents."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import ColumnElement

from sysadmin.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    agent: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    acknowledged: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="chk_alert_severity",
        ),
        # Kept in step with the migrations by hand, and it had drifted:
        # `service_discovery` was added to the database by migration 007
        # in Session 26 and never here, because alembic's autogenerate
        # does not diff CHECK constraints (the blind spot
        # `core/schema_guard.py` records for its own reasons). Nothing
        # broke, since no code path builds this table from metadata —
        # which is also why nothing caught it. `estate_judge` arrives
        # with migration 012.
        CheckConstraint(
            "agent IN ('sysadmin', 'project_organiser', 'file_organiser',"
            " 'log_aggregator', 'service_discovery', 'estate_judge')",
            name="chk_alert_agent",
        ),
        # Serves "the open rows, newest first" — the alerts route's
        # ordering.  Its predicate is the reason :func:`unresolved` exists
        # and is spelled the way it is; see there.
        Index("idx_alerts_active", "created_at", postgresql_where=text("resolved = FALSE")),
        # Serves "*this agent's* open rows", which is what every agent
        # asks on every run.  The index above bounds that read by the
        # whole open set rather than by the asking agent's share of it,
        # so one family's pile-up is paid for by every other family:
        # measured against the live table with 100,000 open
        # ``log_aggregator`` rows inserted in a rolled-back transaction,
        # ``SysAdminAgent._active_alerts`` scanned 100,001 index entries
        # (1,935 buffers, 6.7 ms) to return zero rows, and 2 buffers /
        # 0.02 ms with this one.  ``SNAG-AGENT-005`` reached 598,091 such
        # rows, so the shape is observed here rather than imagined.
        #
        # ``agent`` alone, not ``(agent, created_at)``: no caller of the
        # open set orders by anything, and the index above already owns
        # the one that does.
        Index(
            "idx_alerts_open_by_agent",
            "agent",
            postgresql_where=text("resolved = FALSE"),
        ),
    )


def unresolved() -> ColumnElement[bool]:
    """The open-alert predicate — the one statement of "not yet closed".

    Every family on this box asks for its own unresolved rows, and until
    2026-08-27 all nineteen readers spelled the question by hand as
    ``Alert.resolved.is_(False)``.  That compiles to ``resolved IS
    false``, and **the two partial indexes above declare ``resolved =
    FALSE``**.  PostgreSQL's predicate-implication prover matches a
    partial index structurally: ``IS false`` is a ``BooleanTest`` and ``=
    false`` an ``OpExpr``, so it will not prove one from the other, and
    every one of those reads fell to a sequential scan over the whole
    table.  Measured on the live table (666,936 rows, **zero** open
    ``sysadmin`` rows) the difference is 41,644 buffers and 33.3 ms
    against 13 buffers and 0.03 ms — the index has been eight lines from
    the readers that could not reach it since the table was created.

    So this returns ``Alert.resolved == false()``, which renders the
    index's own predicate **literally**.  ``~Alert.resolved`` renders
    ``NOT resolved`` and the planner does match that one, but it matches
    it by proving an implication rather than by reading the same string,
    and a fix that depends on a prover is a fix that can quietly stop
    working.  ``.is_(False)`` is the spelling being removed and
    ``== False`` is what ruff's ``E712`` refuses; ``false()`` is the only
    form that is both idiomatic and identical to the index.

    The substitution is *provably* semantics-preserving rather than
    merely safe-looking: ``resolved`` is ``NOT NULL`` (both here and in
    the live schema), which is exactly the condition under which ``IS
    false`` and ``= false`` cannot disagree about a row.  The column
    definition is the proof, which is why this lives beside it.

    It lives on the model beside the constraint and the indexes for
    :data:`~sysadmin.monitor.models.service_health.STATUS_READINGS`'
    reason — a vocabulary stated twice can disagree with itself, and the
    half that drifts is the one no test drives.
    ``tests/test_open_alert_predicate.py`` refuses a hand-written copy
    anywhere under ``sysadmin/`` by AST sweep, because the two earlier
    fixes of this shape (``SNAG-API-004``, ``SNAG-DB-003``) each stopped
    where somebody had noticed.

    Compose the agent scope on top rather than baking it in: "open" is
    the shared atom, and ``Alert.agent == name`` is not a definition
    worth naming.  :meth:`~sysadmin.monitor.agent.SysAdminAgent._open_alert_criteria`
    is where the two are joined for the family that reads it four times a
    run.
    """
    return Alert.resolved == false()
