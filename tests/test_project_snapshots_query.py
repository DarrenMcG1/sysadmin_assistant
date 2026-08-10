"""The shared snapshot query, and the guarantee that everyone uses it.

SNAG-PROJ-001/002: the ``newest_scan − 1h`` freshness test existed on
``GET /api/projects/board`` and nowhere else, so a project deleted from
disk was dropped from the board and reported as live by the other eight
surfaces. ``PA-worktrees`` was removed during the ~/projects
reorganisation and still held a row two days later, with a health score
and a next action.

**What these tests can and cannot show.** The suite has no live
database — sessions are mocked, and a mock returns whatever rows the
test hands it regardless of any ``WHERE`` clause. So the filter's
*effect* is unobservable here, and asserting on compiled SQL is the
honest substitute: it proves the predicate is in the statement, not that
Postgres evaluates it as intended. What that buys, which the previous
Python-side filter could not, is the second class of test below —
covering every call site rather than the one that happened to have the
filter written out by hand.
"""

import ast
from pathlib import Path

from sqlalchemy.dialects import postgresql

from sysadmin.projects.snapshots import FRESHNESS_WINDOW, latest_snapshot_query

SYSADMIN = Path(__file__).resolve().parents[1] / "sysadmin"


def _sql(query) -> str:
    return str(query.compile(dialect=postgresql.dialect()))


class TestFreshnessIsInTheQuery:
    MAX_SCANNED = "max(sysadmin.project_snapshots.scanned_at)"

    def test_default_carries_the_cutoff(self):
        sql = _sql(latest_snapshot_query())

        # Twice: the newest-per-project subquery, and the scalar
        # subquery the cutoff is measured from.
        assert sql.count(self.MAX_SCANNED) == 2
        assert "WHERE sysadmin.project_snapshots.scanned_at >=" in sql

    def test_cutoff_is_evaluated_in_the_same_statement(self):
        """Two round trips could straddle a scan writing rows between them."""
        sql = _sql(latest_snapshot_query())

        assert "scanned_at >= (SELECT " + self.MAX_SCANNED in sql

    def test_fresh_false_omits_it(self):
        """History questions must still see projects that have since gone."""
        sql = _sql(latest_snapshot_query(fresh=False))

        assert sql.count(self.MAX_SCANNED) == 1
        assert "WHERE" not in sql

    def test_both_forms_still_select_newest_per_project(self):
        for query in (latest_snapshot_query(), latest_snapshot_query(fresh=False)):
            sql = _sql(query)
            assert "GROUP BY sysadmin.project_snapshots.project_name" in sql

    def test_window_is_slack_not_a_policy(self):
        """An hour is against a straddling scan, well inside the 6h interval.

        If this ever grows past a scan interval the filter stops
        dropping anything, so the value is worth pinning.
        """
        assert FRESHNESS_WINDOW.total_seconds() == 3600


class TestNobodyReimplementsTheJoin:
    """The defect's real shape was nine copies, not one missing filter.

    A caller cannot forget a ``WHERE`` clause it does not know exists,
    so the guarantee worth testing is that no module builds the
    latest-per-project join for itself. Textual, like
    ``test_import_boundary``: it will not catch an indirection, and is
    a tripwire rather than a proof.
    """

    #: The only module allowed to group snapshots by name.
    OWNER = SYSADMIN / "projects" / "snapshots.py"

    def _offenders(self) -> list[str]:
        offenders = []
        for path in SYSADMIN.rglob("*.py"):
            if path == self.OWNER:
                continue
            source = path.read_text(encoding="utf-8")
            if "ProjectSnapshot.scanned_at" not in source:
                continue
            tree = ast.parse(source)
            for node in ast.walk(tree):
                # func.max(ProjectSnapshot.scanned_at)
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Attribute) and func.attr == "max"):
                    continue
                arg = node.args[0] if node.args else None
                if (
                    isinstance(arg, ast.Attribute)
                    and arg.attr == "scanned_at"
                    and isinstance(arg.value, ast.Name)
                    and arg.value.id == "ProjectSnapshot"
                ):
                    offenders.append(f"{path.relative_to(SYSADMIN.parent)}:{node.lineno}")
        return offenders

    def test_no_module_builds_its_own_latest_per_project_query(self):
        offenders = self._offenders()
        assert not offenders, (
            "latest-per-project query re-implemented outside snapshots.py — "
            "use latest_snapshot_query():\n" + "\n".join(offenders)
        )

    def test_the_owner_module_still_builds_one(self):
        """Guard against the test above passing because the pattern changed."""
        assert "func.max(ProjectSnapshot.scanned_at)" in self.OWNER.read_text(
            encoding="utf-8"
        )


class TestEveryReportingSurfaceUsesIt:
    """Each module that reports on projects must import the shared query."""

    CONSUMERS = (
        SYSADMIN / "projects" / "router.py",
        SYSADMIN / "projects" / "review.py",
        SYSADMIN / "briefing" / "router.py",
        SYSADMIN / "briefing" / "data.py",
    )

    def test_consumers_import_the_shared_query(self):
        missing = [
            str(path.relative_to(SYSADMIN.parent))
            for path in self.CONSUMERS
            if "latest_snapshot_query" not in path.read_text(encoding="utf-8")
        ]
        assert not missing, f"no longer using the shared query: {missing}"

    def test_consumer_paths_exist(self):
        """The list above is only meaningful if the files are really there."""
        for path in self.CONSUMERS:
            assert path.is_file(), f"{path} not found — the module list is stale"
