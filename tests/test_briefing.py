"""Tests for the morning briefing — envelope, facts, prose and sections.

DB access is mocked at the session level (same pattern as
tests/test_routers.py); psutil and the notifier are patched.  ``_gather``
runs its queries in a fixed order — services, logs, filesystem, alerts,
then the disk review — so ``session.execute`` uses ``side_effect`` to
feed each one its result.

The project sections left with the scanner at the Session 4 cutover
(ADR-0005): "Project Health", "Pick This Up" and "Weekly Project Review"
are the estate producer's to test now.  What remains here is the machine
half — Infrastructure, Overnight Logs, Filesystem, Weekly Disk Review —
and the alert digest.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.briefing.data import (
    SCHEMA_VERSION,
    build_facts,
    generate_briefing_data,
    send_morning_briefing,
    summarise,
)
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.log_summary import LogSummary
from sysadmin.monitor.models.service_health import ServiceHealth

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result_all(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


def _result_one(row):
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    return result


def _service(name: str, status: str = "ok", details: dict | None = None) -> ServiceHealth:
    row = ServiceHealth(service_name=name, status=status, details=details or {})
    row.checked_at = datetime.now(UTC)
    return row


def _log_summary(text: str = "All quiet overnight.") -> LogSummary:
    row = LogSummary(summary=text)
    row.created_at = datetime.now(UTC)
    return row


def _audit(days_old: int = 0) -> FilesystemAudit:
    row = FilesystemAudit()
    row.total_reclaimable_mb = 1234
    row.empty_dirs_count = 5
    row.stale_project_dirs_count = 2
    row.duplicate_groups_count = 3
    row.scanned_at = datetime.now(UTC) - timedelta(days=days_old)
    return row


def _result_first(row):
    result = MagicMock()
    result.scalars.return_value.first.return_value = row
    return result


def _disk_review(narrative: str = "Disk held steady.", days_old: int = 0):
    from sysadmin.files.models.disk_review import DiskReview

    row = DiskReview(period_days=7, narrative=narrative, llm_used=True)
    row.generated_at = datetime.now(UTC) - timedelta(days=days_old)
    return row


def _result_rows(rows):
    """A grouped result — ``.all()`` rather than ``.scalars().all()``.

    The alert query aggregates in SQL (``GROUP BY severity, title``), so
    it yields Rows of labelled columns rather than ORM objects.
    """
    result = MagicMock()
    result.all.return_value = rows
    return result


def _alert_row(title, severity="warning", occurrences=1, latest=None):
    return SimpleNamespace(
        severity=severity,
        title=title,
        occurrences=occurrences,
        latest=latest or datetime.now(UTC),
    )


def _session_returning(
    infra,
    log,
    filesystem,
    disk_review=None,
    alerts=None,
):
    """Mock session whose execute() feeds each gather step in order.

    Order matters and is positional: adding a query to ``_gather``
    without adding a result here exhausts the iterator and every test in
    this file fails at once.  (It did, when "Pick This Up" was added, and
    again when the envelope added alerts — the docstring was right twice.
    The Session 4 cutover then *removed* the two project reads, which
    broke every test the other way.)
    """
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result_all(infra),
            _result_one(log),
            _result_one(filesystem),
            _result_rows(alerts or []),
            _result_first(disk_review),
        ]
    )
    return session


# ---------------------------------------------------------------------------
# generate_briefing_data
# ---------------------------------------------------------------------------


class TestGenerateBriefingData:
    @pytest.mark.asyncio
    async def test_all_sections_present_when_data_exists(self):
        session = _session_returning(
            infra=[_service("postgres"), _service("redis")],
            log=_log_summary(),
            filesystem=_audit(),
        )

        with patch("sysadmin.briefing.data.psutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(percent=89.0)
            briefing = await generate_briefing_data(session)

        assert briefing["source"] == "sysadmin-service"
        assert "generated_at" in briefing
        titles = [s["title"] for s in briefing["sections"]]
        assert titles == [
            "Infrastructure Status",
            "Overnight Log Summary",
            "Filesystem",
        ]

    @pytest.mark.asyncio
    async def test_empty_database_yields_no_sections(self):
        session = _session_returning(infra=[], log=None, filesystem=None)
        briefing = await generate_briefing_data(session)
        assert briefing["sections"] == []

    @pytest.mark.asyncio
    async def test_infrastructure_section_flags_unhealthy(self):
        session = _session_returning(
            infra=[
                _service("postgres", "ok"),
                _service("pa", "unreachable", details={"reason": "Connection refused"}),
            ],
            log=None,
            filesystem=None,
        )
        briefing = await generate_briefing_data(session)

        (infra,) = briefing["sections"]
        assert infra["type"] == "status_grid"
        assert infra["data"]["all_services_healthy"] is False
        pa = next(s for s in infra["data"]["services"] if s["name"] == "pa")
        assert pa["note"] == "Connection refused"

    @pytest.mark.asyncio
    async def test_log_section_carries_summary_text(self):
        session = _session_returning(
            infra=[], log=_log_summary("Two errors from redis."), filesystem=None
        )
        briefing = await generate_briefing_data(session)

        (log_section,) = briefing["sections"]
        assert log_section["type"] == "text"
        assert log_section["data"] == "Two errors from redis."

    @pytest.mark.asyncio
    async def test_filesystem_section_metrics(self):
        session = _session_returning(infra=[], log=None, filesystem=_audit())

        with patch("sysadmin.briefing.data.psutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(percent=89.0)
            briefing = await generate_briefing_data(session)

        (fs,) = briefing["sections"]
        assert fs["type"] == "metrics"
        assert fs["data"]["disk_used_percent"] == 89.0
        assert fs["data"]["reclaimable_mb"] == 1234
        assert fs["data"]["empty_dirs"] == 5

    @pytest.mark.asyncio
    async def test_filesystem_section_survives_psutil_failure(self):
        session = _session_returning(infra=[], log=None, filesystem=_audit())

        with patch(
            "sysadmin.briefing.data.psutil.disk_usage", side_effect=OSError("no mount")
        ):
            briefing = await generate_briefing_data(session)

        (fs,) = briefing["sections"]
        assert fs["data"]["disk_used_percent"] is None


# ---------------------------------------------------------------------------
# send_morning_briefing
# ---------------------------------------------------------------------------


def _mock_notifier(send_result: bool = True) -> MagicMock:
    notifier = MagicMock()
    notifier.startup = AsyncMock()
    notifier.shutdown = AsyncMock()
    notifier.send_briefing_data = AsyncMock(return_value=send_result)
    return notifier


def _patch_scheduler_session(session):
    @asynccontextmanager
    async def fake_session():
        yield session

    return patch("sysadmin.briefing.data.get_scheduler_session", fake_session)


class TestSendMorningBriefing:
    @pytest.mark.asyncio
    async def test_sends_generated_sections(self):
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None
        )
        notifier = _mock_notifier(send_result=True)

        with _patch_scheduler_session(session):
            with patch("sysadmin.monitor.notifier.Notifier", return_value=notifier):
                await send_morning_briefing()

        notifier.startup.assert_awaited_once()
        notifier.send_briefing_data.assert_awaited_once()
        (sections,) = notifier.send_briefing_data.await_args.args
        assert sections[0]["title"] == "Infrastructure Status"
        notifier.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_notifier_shutdown_runs_even_on_delivery_failure(self):
        session = _session_returning(infra=[], log=None, filesystem=None)
        notifier = _mock_notifier(send_result=False)

        with _patch_scheduler_session(session):
            with patch("sysadmin.monitor.notifier.Notifier", return_value=notifier):
                await send_morning_briefing()

        notifier.shutdown.assert_awaited_once()


# ---------------------------------------------------------------------------
# Weekly disk review section (Session 24 Tier 3)
# ---------------------------------------------------------------------------


class TestDiskReviewSection:
    """The 8-day freshness rule, exercised through its one remaining caller."""

    @pytest.mark.asyncio
    async def test_fresh_disk_review_included(self):
        session = _session_returning(
            infra=[_service("postgres")],
            log=None,
            filesystem=None,
            disk_review=_disk_review("Junk is coming from Downloads."),
        )
        briefing = await generate_briefing_data(session)

        section = next(
            s for s in briefing["sections"] if s["title"] == "Weekly Disk Review"
        )
        assert section["type"] == "text"
        assert section["data"] == "Junk is coming from Downloads."

    @pytest.mark.asyncio
    async def test_stale_disk_review_excluded(self):
        session = _session_returning(
            infra=[_service("postgres")],
            log=None,
            filesystem=None,
            disk_review=_disk_review(days_old=9),
        )
        briefing = await generate_briefing_data(session)

        assert "Weekly Disk Review" not in [
            s["title"] for s in briefing["sections"]
        ]

    @pytest.mark.asyncio
    async def test_no_disk_review_no_section(self):
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None
        )
        briefing = await generate_briefing_data(session)

        assert "Weekly Disk Review" not in [
            s["title"] for s in briefing["sections"]
        ]


# ---------------------------------------------------------------------------
# The envelope (Session 36)
# ---------------------------------------------------------------------------


class TestEnvelope:
    """`schema`, `period`, `summary`, `alerts`, `facts` — added, never swapped."""

    @pytest.mark.asyncio
    async def test_alfreds_two_keys_survive(self):
        """The regression this whole design is arranged around.

        `adapt_sysadmin` reads `payload["sections"]` and returns a single
        red error section if it is absent or not a list, and reads
        `generated_at` into `produced_at`.  The envelope is additive
        precisely so that neither moves.
        """
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None
        )
        briefing = await generate_briefing_data(session)

        assert isinstance(briefing["sections"], list)
        assert briefing["generated_at"]
        # No second stamp holding the same value — one name, one meaning.
        assert "generated" not in briefing

    @pytest.mark.asyncio
    async def test_envelope_keys_present(self):
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None
        )
        briefing = await generate_briefing_data(session)

        assert briefing["schema"] == SCHEMA_VERSION
        assert briefing["source"] == "sysadmin-service"
        assert set(briefing["period"]) == {"from", "to", "anchor"}
        assert isinstance(briefing["summary"], str) and briefing["summary"]
        assert isinstance(briefing["alerts"], list)
        assert isinstance(briefing["facts"], dict)

    @pytest.mark.asyncio
    async def test_period_is_anchored_to_the_schedule(self):
        """Not to the last pull — two consumers polling would each shorten
        the other's window, and the span must mean one thing."""
        session = _session_returning(infra=[], log=None, filesystem=None)
        briefing = await generate_briefing_data(session)

        period = briefing["period"]
        assert period["anchor"] == "schedule"
        start = datetime.fromisoformat(period["from"])
        end = datetime.fromisoformat(period["to"])
        assert start < end
        assert end - start <= timedelta(days=1)
        assert start.astimezone().hour == 6

    @pytest.mark.asyncio
    async def test_facts_holds_no_rows(self):
        """A facts block containing the whole payload cannot be diffed.

        Counts and identifiers only: every list in it is a list of
        scalars, never of the rows the sections render.
        """
        session = _session_returning(
            infra=[_service("postgres"), _service("redis", "unreachable")],
            log=None,
            filesystem=_audit(),
        )
        with patch("sysadmin.briefing.data.psutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(percent=42.0)
            briefing = await generate_briefing_data(session)

        def scalars_only(value, path="facts"):
            if isinstance(value, dict):
                for key, item in value.items():
                    scalars_only(item, f"{path}.{key}")
            elif isinstance(value, list):
                for item in value:
                    assert not isinstance(item, (dict, list)), f"{path} carries rows"

        scalars_only(briefing["facts"])


# ---------------------------------------------------------------------------
# Alerts — grouped by incident, counted by row
# ---------------------------------------------------------------------------


class TestAlerts:
    @pytest.mark.asyncio
    async def test_counts_are_exact_while_the_list_is_capped(self):
        """Grouping in SQL and capping in Python, in that order.

        Capping in SQL would quietly make `open` mean "open, of the ten I
        looked at" — and this table holds 547,814 rows for one unresolved
        `Log error: kernel`.
        """
        rows = [
            _alert_row(f"incident {i}", severity="warning", occurrences=100)
            for i in range(15)
        ]
        session = _session_returning(
            infra=[], log=None, filesystem=None, alerts=rows
        )
        briefing = await generate_briefing_data(session)

        assert len(briefing["alerts"]) == 10
        assert briefing["facts"]["alerts"]["incidents"] == 15
        assert briefing["facts"]["alerts"]["open"] == 1500
        assert briefing["facts"]["alerts"]["by_severity"]["warning"] == 1500

    @pytest.mark.asyncio
    async def test_summary_counts_incidents_not_rows(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            alerts=[_alert_row("kernel noise", "critical", occurrences=547814)],
        )
        briefing = await generate_briefing_data(session)

        assert "1 open alert incident" in briefing["summary"]

    @pytest.mark.asyncio
    async def test_no_alerts_no_clause(self):
        session = _session_returning(infra=[], log=None, filesystem=None)
        briefing = await generate_briefing_data(session)

        assert "alert" not in briefing["summary"]


# ---------------------------------------------------------------------------
# The prose — deterministic, and the staleness Alfred cannot see
# ---------------------------------------------------------------------------


class TestSummary:
    @pytest.mark.asyncio
    async def test_summary_reports_what_the_facts_say(self):
        session = _session_returning(
            infra=[_service("postgres"), _service("redis", "unreachable")],
            log=None,
            filesystem=None,
        )
        briefing = await generate_briefing_data(session)

        assert briefing["summary"].startswith("1 of 2 services healthy; redis down.")

    def test_summary_is_a_pure_function_of_facts(self):
        """No LLM in the 06:00 path.  The weekly reviews pay for
        narration with a figure-free prompt and a markdown stripper; a
        summary that is only numbers has nothing to gain from that and a
        down llama-server to lose."""
        facts = {
            "services": {"total": 3, "healthy": 3, "failing": [], "measured_at": None},
            "alerts": {
                "open": 0,
                "incidents": 0,
                "shown": 0,
                "by_severity": {"critical": 0, "warning": 0, "info": 0},
            },
        }
        assert summarise(facts) == summarise(facts) == "All 3 services healthy."

    def test_nothing_measured_says_so(self):
        assert "Nothing has been measured yet" in summarise({})

    @pytest.mark.asyncio
    async def test_stale_data_is_named_because_generated_at_cannot_say_it(self):
        """The hole this envelope exists to close.

        Alfred's staleness rule reads `generated_at`, which on a pulled
        payload is seconds old however long ago the agent behind it died.
        """
        session = _session_returning(
            infra=[], log=None, filesystem=_audit(days_old=3)
        )
        with patch("sysadmin.briefing.data.psutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(percent=42.0)
            briefing = await generate_briefing_data(session)

        assert briefing["facts"]["stale_sources"] == ["filesystem"]
        assert "filesystem is over a day old" in briefing["summary"]

    @pytest.mark.asyncio
    async def test_fresh_data_is_not_flagged(self):
        session = _session_returning(
            infra=[], log=None, filesystem=_audit()
        )
        with patch("sysadmin.briefing.data.psutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(percent=42.0)
            briefing = await generate_briefing_data(session)

        assert briefing["facts"]["stale_sources"] == []
        assert "over a day old" not in briefing["summary"]


class TestBuildFacts:
    def test_facts_are_derived_never_measured_separately(self):
        """A facts block with its own queries would be a second producer
        able to disagree with the first."""
        gathered = {
            "services": {
                "items": [{"name": "a", "status": "ok"}, {"name": "b", "status": "down"}],
                "measured_at": datetime.now(UTC).isoformat(),
            },
            "logs": None,
            "filesystem": None,
            "alerts": {
                "items": [],
                "open": 0,
                "incidents": 0,
                "shown": 0,
                "by_severity": {"critical": 0, "warning": 0, "info": 0},
            },
            "disk_review": None,
        }
        facts = build_facts(gathered, datetime.now(UTC))

        assert facts["services"] == {
            "total": 2,
            "healthy": 1,
            "failing": ["b"],
            "unmonitored": 0,
            "measured_at": gathered["services"]["measured_at"],
        }
        assert "projects" not in facts


class TestSkippedServices:
    """A declared non-check is not a failure.

    `skipped` (migration 009) marks a service the estate has decided not
    to monitor and said why — a GUI unit bound to
    `graphical-session.target`, or `monitor: false` with a reason.
    Counting it as failing reports a *decision* as a fault.
    """

    @pytest.mark.asyncio
    async def test_a_skipped_service_is_not_reported_down(self):
        session = _session_returning(
            infra=[
                _service("postgres", "ok"),
                _service("sysadmin-tray", "skipped"),
                _service("ollama", "unreachable"),
            ],
            log=None,
            filesystem=None,
        )
        briefing = await generate_briefing_data(session)

        services = briefing["facts"]["services"]
        assert services["failing"] == ["ollama"]
        assert services["total"] == 2
        assert services["unmonitored"] == 1
        assert "sysadmin-tray" not in briefing["summary"]

    @pytest.mark.asyncio
    async def test_skipped_alone_still_reads_healthy(self):
        """Four units on this estate are skipped by design.  Treating them
        as unhealthy pinned Alfred's grid permanently false."""
        session = _session_returning(
            infra=[_service("postgres", "ok"), _service("sysadmin-tray", "skipped")],
            log=None,
            filesystem=None,
        )
        briefing = await generate_briefing_data(session)

        (infra,) = briefing["sections"]
        assert infra["data"]["all_services_healthy"] is True
        assert briefing["summary"].startswith("All 1 services healthy.")
