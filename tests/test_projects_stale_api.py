"""GET /api/projects/stale — the endpoint that ignored its own parameter.

SNAG-PROJ-006: ``days`` was declared, defaulted to 30, bounded at 365,
and never read. The handler filtered on ``health_score <
needs_attention_min`` instead, which made it a duplicate of
``/overview`` wearing a name that promised idleness. A well-kept
repository untouched for a year scored 90 and never appeared; an
actively-developed one with a dirty tree appeared every day.

No consumer existed anywhere under ~/projects, so implementing the
parameter was a choice rather than a compatibility obligation — the
original spec line ("Projects with no activity > N days") is what it
now does.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from sysadmin.projects.models.project_snapshot import ProjectSnapshot


def make_snapshot(name="demo", score=90, last_commit_days=400, status="active"):
    return ProjectSnapshot(
        project_name=name,
        project_path=f"/home/gaddi/projects/{name}",
        health_score=score,
        last_commit_at=(
            datetime.now(UTC) - timedelta(days=last_commit_days)
            if last_commit_days is not None
            else None
        ),
        scanned_at=datetime.now(UTC),
        findings={"status": status},
    )


def stub_rows(session, rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute.return_value = result


@pytest.mark.anyio
class TestStaleContract:
    async def test_window_is_echoed_back(self, test_client, mock_session):
        """Without it, a cached body cannot be told apart from another window."""
        stub_rows(mock_session, [])

        body = (await test_client.get("/api/projects/stale?days=90")).json()
        assert body["days"] == 90

    async def test_default_window_is_thirty_days(self, test_client, mock_session):
        stub_rows(mock_session, [])

        body = (await test_client.get("/api/projects/stale")).json()
        assert body["days"] == 30

    async def test_days_idle_is_reported_per_project(self, test_client, mock_session):
        stub_rows(mock_session, [make_snapshot(last_commit_days=45)])

        entry = (await test_client.get("/api/projects/stale")).json()["stale_projects"][0]
        assert entry["days_idle"] == 45

    async def test_never_committed_is_null_not_zero(self, test_client, mock_session):
        """"Never" is the strongest form of the question, not the weakest."""
        stub_rows(mock_session, [make_snapshot(last_commit_days=None)])

        entry = (await test_client.get("/api/projects/stale")).json()["stale_projects"][0]
        assert entry["days_idle"] is None

    async def test_status_is_reported_so_dormancy_is_visible(
        self, test_client, mock_session
    ):
        """A dormant project is idle *on purpose* — the caller should see that."""
        stub_rows(mock_session, [make_snapshot(status="dormant")])

        entry = (await test_client.get("/api/projects/stale")).json()["stale_projects"][0]
        assert entry["status"] == "dormant"

    async def test_count_matches_the_list(self, test_client, mock_session):
        stub_rows(mock_session, [make_snapshot(name="a"), make_snapshot(name="b")])

        body = (await test_client.get("/api/projects/stale")).json()
        assert body["count"] == len(body["stale_projects"]) == 2


@pytest.mark.anyio
class TestStaleQueryUsesDays:
    """The parameter must reach the SQL, which is where it used to stop."""

    async def _sql(self, test_client, mock_session, query=""):
        stub_rows(mock_session, [])
        await test_client.get(f"/api/projects/stale{query}")
        return str(mock_session.execute.call_args.args[0])

    async def test_filters_on_last_commit_not_health_score(
        self, test_client, mock_session
    ):
        sql = await self._sql(test_client, mock_session)

        assert "last_commit_at <" in sql
        assert "health_score <" not in sql

    async def test_never_committed_projects_are_included(
        self, test_client, mock_session
    ):
        sql = await self._sql(test_client, mock_session)

        assert "last_commit_at IS NULL" in sql

    async def test_freshness_filter_still_applies(self, test_client, mock_session):
        """A deleted project is not a stale project — it is gone."""
        sql = await self._sql(test_client, mock_session)

        assert "scanned_at >=" in sql

    @pytest.mark.parametrize("days", [1, 30, 365])
    async def test_accepts_the_documented_range(
        self, test_client, mock_session, days
    ):
        stub_rows(mock_session, [])

        resp = await test_client.get(f"/api/projects/stale?days={days}")
        assert resp.status_code == 200

    @pytest.mark.parametrize("days", [0, -1, 366])
    async def test_rejects_values_outside_it(self, test_client, mock_session, days):
        stub_rows(mock_session, [])

        resp = await test_client.get(f"/api/projects/stale?days={days}")
        assert resp.status_code == 422
