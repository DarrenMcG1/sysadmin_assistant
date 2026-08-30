"""``GET /api/logs`` route shape — the catch-all and the two tombstones.

``SNAG-LOG-011``.  Session 69 removed ``GET /api/logs/summary`` and
``/summary/history`` with the producer behind them, and migration 014
then dropped ``log_summaries`` itself; ``/summary`` went on answering
``200`` with an empty list, because ``GET /api/logs/{source}`` matched
``summary`` as though it were a log source.

**This file exists because the route had no tests at all.**  Nothing in
the suite asserted ``/{source}``'s behaviour before Session 75, which is
how a route describing a dropped table stayed green through the sitting
that dropped it — ``TestJournalCommand``'s defect one router over.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, text

from sysadmin.core.config import LogSource
from sysadmin.monitor.log_query import declared_source_names
from sysadmin.monitor.services import composed_log_sources, stored_source_name

from .conftest import set_services

SYNC_URL = "postgresql+psycopg2://gaddi@localhost:5432/projects"

#: A service whose journal is declared beside it, with a **name distinct
#: from its unit** — the shape that makes the identity choice testable.
#: The real file is not used, so these tests say what they depend on.
LOGGING_SERVICES = [
    {"name": "test-api", "kind": "http", "url": "http://localhost:9999/health"},
    {
        "name": "alfred",
        "kind": "systemd",
        "systemd": {"unit": "alfred-backend.service", "scope": "user"},
        "log": {"type": "journalctl"},
    },
]


class _Cfg:
    """Just enough of ``LogAggregatorConfig`` for the composition."""

    def __init__(self, sources):
        self.sources = sources


@pytest.fixture
def logging_services():
    """A services.yaml that declares a journal source.

    ``DEFAULT_TEST_SERVICES`` declares none, so without this the route
    admits nothing and every assertion below passes vacuously — which is
    the failure mode a validator test has, and the reason the set is
    asserted non-empty before it is used.
    """
    return set_services(*LOGGING_SERVICES)


def _mock_scalars_all(mock_session, rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=result)


def _db_available() -> bool:
    try:
        engine = create_engine(SYNC_URL, connect_args={"connect_timeout": 2})
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


class TestRetiredSummaryRoutes:
    """The two paths Session 69 removed answer ``410``, not ``200``."""

    async def test_summary_is_gone_not_empty(self, test_client, mock_session):
        """The founding symptom: it answered ``200`` with an empty list.

        Falsified by deleting the tombstone — the catch-all then matches
        ``summary`` again and this returns ``200``.  Also falsified by
        declaring the tombstone *below* ``/{source}``, which is the whole
        mechanism: FastAPI matches in declaration order.
        """
        _mock_scalars_all(mock_session, [])
        response = await test_client.get("/api/logs/summary")
        assert response.status_code == 410
        assert "log_summaries" in response.json()["detail"]

    async def test_summary_history_answers_with_the_same_voice(
        self, test_client, mock_session
    ):
        """It already 404'd — the catch-all takes one segment.

        Named anyway so the pair cannot disagree: a client told ``410``
        by one and ``404`` by the other would read the second as a typo.
        """
        _mock_scalars_all(mock_session, [])
        response = await test_client.get("/api/logs/summary/history")
        assert response.status_code == 410
        assert response.json()["detail"] == (
            await test_client.get("/api/logs/summary")
        ).json()["detail"]

    async def test_the_tombstones_stay_out_of_the_schema(self, test_app):
        """A dead path is not API surface, and ``/docs`` must not list it."""
        paths = test_app.openapi()["paths"]
        assert "/api/logs/summary" not in paths
        assert "/api/logs/summary/history" not in paths
        assert "/api/logs/{source}" in paths


class TestSourceValidation:
    """``/{source}`` admits a declared source and 404s everything else."""

    async def test_a_declared_source_is_served(
        self, test_client, mock_session, logging_services
    ):
        _mock_scalars_all(mock_session, [])
        declared = sorted(declared_source_names())
        assert declared, "the fixture's services.yaml declares no log source"
        response = await test_client.get(f"/api/logs/{declared[0]}")
        assert response.status_code == 200
        assert response.json()["source"] == declared[0]

    async def test_an_unknown_segment_is_404_and_names_the_set(
        self, test_client, mock_session, logging_services
    ):
        """The class the tombstones only patch.

        Falsified by removing the validator: this returns ``200`` with
        an empty list, which is the defect wearing a different path.
        """
        _mock_scalars_all(mock_session, [])
        response = await test_client.get("/api/logs/not-a-source")
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "not-a-source" in detail
        assert sorted(declared_source_names())[0] in detail

    async def test_the_source_name_is_rejected_where_the_unit_is_stored(
        self, test_client, mock_session, logging_services
    ):
        """``alfred`` is a source *name*; the column holds the unit.

        This is the same defect one level down — it used to return an
        empty list, indistinguishable from a quiet service.  Falsified by
        keying :func:`declared_source_names` on ``name``, which also
        breaks the test above it.
        """
        _mock_scalars_all(mock_session, [])
        names = {s.name for s in composed_log_sources(_no_extra_sources())}
        units = declared_source_names()
        name_only = sorted(names - units)
        assert name_only, "no declared source has a name distinct from its unit"

        response = await test_client.get(f"/api/logs/{name_only[0]}")
        assert response.status_code == 404


def _no_extra_sources():
    return _Cfg([])


class TestDeclaredSet:
    """What the validated set is built from, and what it stores."""

    def test_a_config_only_source_is_admitted(self):
        """``kernel`` belongs to no service and is 99.9 % of the table.

        A set built from services.yaml alone passes every other test in
        this file and rejects 451,319 of the 451,569 live rows.
        Falsified by dropping the config.yaml half of
        :func:`composed_log_sources`.
        """
        extra = LogSource(name="kernel", type="journalctl", unit="kernel")
        with patch(
            "sysadmin.monitor.log_query.get_config"
        ) as get_config:
            get_config.return_value.agents.log_aggregator = _Cfg([extra])
            assert "kernel" in declared_source_names()

    def test_a_journal_source_stores_its_unit(self):
        source = LogSource(
            name="alfred", type="journalctl", unit="alfred-backend.service"
        )
        assert stored_source_name(source) == "alfred-backend.service"

    def test_a_file_source_stores_its_name(self):
        """Empty population on this box, and the reason it is written.

        Every declared source is ``type: journalctl`` today, so a rule
        derived from the live table would omit this branch and stay green
        until the first file source was declared — at which point the
        route would 404 its own rows.  Mirrors
        ``LogAggregatorAgent._execute``'s dispatch, where
        ``_read_log_file`` is handed ``source.name``.
        """
        source = LogSource(name="pacman", type="file", path="/var/log/pacman.log")
        assert stored_source_name(source) == "pacman"

    def test_a_source_that_is_never_read_is_not_admitted(self):
        """``else: continue`` in the ingestion loop, stated as ``None``.

        A journalctl source with no unit and a file source with no path
        are never read, so they can produce no rows and must not be
        admitted as though they could.
        """
        assert stored_source_name(LogSource(name="x", type="journalctl")) is None
        assert stored_source_name(LogSource(name="x", type="file")) is None
        assert stored_source_name(LogSource(name="x", type="nonsense")) is None


def _live_source_reading() -> tuple[set[str], set[str]]:
    """The declared set and the stored set, read once for both tests below."""
    from sysadmin.monitor import services as services_module
    from sysadmin.monitor.services import default_services_path, load_services

    # The autouse fixture installs a stub file; this claim is about the
    # *real* declaration, so it is read here explicitly rather than left
    # to whichever fixture ran last.
    services_module._services = load_services(default_services_path())
    declared = declared_source_names()

    engine = create_engine(SYNC_URL)
    try:
        with engine.connect() as conn:
            stored = {
                row[0]
                for row in conn.execute(
                    text("SELECT DISTINCT source FROM sysadmin.log_entries")
                )
            }
    finally:
        engine.dispose()

    return declared, stored


@pytest.mark.skipif(
    not _db_available(),
    reason="local postgres (projects DB) not reachable — this claim needs the real rows",
)
class TestAgainstTheLiveTable:
    """The claim the design rests on, checked against the real rows.

    **The claim is a subset, and a subset of nothing holds** (Session
    132).  ``stored <= declared`` is green over an emptied
    ``log_entries`` and says the same thing it says over a table that
    agrees — which is this file's own vacuity argument, already written
    into the ``logging_services`` fixture and into
    ``assert name_only`` above, applied at last to the half that reads
    the box.  Measured 2026-08-30: 10 stored values inside 15 declared,
    so five declared names carry no rows and the containment is a real
    constraint rather than an identity.
    """

    @pytest.mark.premise
    def test_the_table_holds_rows_to_be_declared(self):
        """Ordered first, so a failure names the empty table and not a retirement."""
        _, stored = _live_source_reading()
        assert stored, (
            "log_entries holds no distinct source at all, so the containment "
            "below is a subset of nothing and would hold whatever the "
            "validator admitted"
        )

    def test_every_stored_source_is_declared(self):
        """Otherwise the validator 404s rows this box actually holds.

        Measured 2026-08-30: 10 distinct values, all declared.  The day
        this fails, a source was retired without its rows ageing out —
        the cost the route's docstring states, arriving.
        """
        declared, stored = _live_source_reading()
        assert stored <= declared, sorted(stored - declared)
