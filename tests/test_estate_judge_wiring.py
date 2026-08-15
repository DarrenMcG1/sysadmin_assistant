"""The four places a new agent has to be wired, plus the fifth.

``CLAUDE.md`` records four — ``main.py``, a config class, the
``chk_alert_agent`` CHECK constraint, and ``self_monitor.AGENT_NAMES`` —
and each has its own silent failure mode:

- missing from ``AGENT_NAMES``: the agent runs completely unwatched, and
  the monitoring service fails to monitor its own newest agent;
- a ``job_id`` that disagrees with ``main.py``: the stall window is
  computed against a schedule that does not exist;
- missing from the constraint: the first live run is rejected by the
  database *after* the work has succeeded, which is how migration 007
  came to be written.

The fifth is this agent's own: ``base_url`` duplicates the address in
``services.yaml``, deliberately (deriving it would make a rename or a
``monitor: false`` stop the judging for an unrelated reason), so
something has to keep the two honest. This is that something.
"""

import importlib.util
from pathlib import Path

import yaml

from sysadmin.core.config import AppConfig, load_config
from sysadmin.core.models.alert import Alert
from sysadmin.monitor.self_monitor import AGENT_NAMES, agent_schedules

ROOT = Path(__file__).resolve().parents[1]


def _load_revision(filename: str):
    """alembic/versions is not a package — load a revision by path."""
    path = ROOT / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTheAgentIsWired:
    def test_it_is_self_monitored(self):
        assert "estate_judge" in AGENT_NAMES

    def test_its_schedule_matches_main(self):
        schedule = agent_schedules(AppConfig())["estate_judge"]
        assert schedule.job_id == "estate_judge_poll"
        assert schedule.interval_seconds == 3600

    def test_main_registers_that_job_id(self):
        """Planned *and* wired — the two halves live in different files now.

        ``core/jobs.py`` says when it runs and ``main.py`` says what runs;
        checking only one of them passes on an agent that is scheduled and
        pointed at nothing (or wired and never scheduled).
        """
        from sysadmin.core.jobs import plan_jobs
        from sysadmin.main import JOB_TARGETS, estate_judge_agent

        assert "estate_judge_poll" in {s.job_id for s in plan_jobs(AppConfig())}
        assert JOB_TARGETS["estate_judge_poll"] == estate_judge_agent.run

    def test_the_newest_constraint_migration_matches_agent_names(self):
        """The invariant, found rather than named.

        ``AGENT_NAMES`` must equal the agent list in the *newest*
        migration that widens ``chk_alert_agent`` — the one the live
        database holds, since ``core/schema_guard.py`` refuses to boot
        unless ``alembic_version`` is at the packaged head.

        Discovering that migration instead of naming it is deliberate.
        The Session 26 version of this test hardcoded ``007``, so it
        failed the moment a sixth agent was added and the fix was an
        edit to a test belonging to an unrelated session — a pin
        masquerading as an invariant. This one holds for agent seven
        without being touched.
        """
        widening = []
        for path in sorted((ROOT / "alembic" / "versions").glob("[0-9]*.py")):
            module = _load_revision(path.name)
            if hasattr(module, "AGENTS"):
                widening.append((module.revision, module))
        assert widening, "no migration defines an agent whitelist"

        _, newest = max(widening, key=lambda pair: pair[0])
        assert set(newest.AGENTS) == set(AGENT_NAMES)

    def test_the_alerts_constraint_admits_it(self):
        """Migration 012. ``AGENT_NAMES`` is add-only and mirrors it —
        ``project_organiser`` stays listed although the agent left this
        repository on 2026-08-13, because historical rows carry retired
        names and narrowing the constraint would orphan them."""
        module = _load_revision("012_allow_estate_judge_agent.py")
        assert "estate_judge" in module.AGENTS
        assert set(module.AGENTS) == set(AGENT_NAMES)

    def test_the_orm_model_agrees_with_the_migration(self):
        """The second copy of the whitelist, and it had drifted:
        ``service_discovery`` was added to the database by migration 007
        in Session 26 and never to the model, because alembic's
        autogenerate does not diff CHECK constraints. Nothing broke —
        no code path builds this table from metadata — which is also why
        nothing caught it."""
        constraint = next(
            c for c in Alert.__table__.constraints if getattr(c, "name", None) == "chk_alert_agent"
        )
        text = str(constraint.sqltext)
        for name in AGENT_NAMES:
            assert f"'{name}'" in text, name


class TestTheAddressIsNotDuplicatedByAccident:
    def test_base_url_matches_the_monitored_service(self):
        """``services.yaml`` already holds the estate's address under
        ``estate-manager-api``; this agent holds it again. Derived would
        be worse — a renamed service, or one set ``monitor: false``,
        would stop the judging silently and for an unrelated reason —
        but two copies need an assertion, not a comment."""
        services = yaml.safe_load((ROOT / "services.yaml").read_text())
        entry = next(s for s in services["services"] if s.get("name") == "estate-manager-api")
        base_url = load_config().agents.estate_judge.base_url

        assert entry["url"].startswith(base_url), (
            f"config.yaml base_url {base_url!r} does not match services.yaml url {entry['url']!r}"
        )
        assert entry["port"] == 8400


class TestTheSurfacesAreTheOnesTheEstatePublishes:
    def test_paths_match_the_producers_routes(self):
        """Pinned as literals rather than probed: the estate is another
        repository on its own release cycle, and this test failing when
        a path moves there is the point. The consumer-side contract test
        against the live producer is SNAG-TRAY-006's job, not this."""
        from sysadmin.estate.client import SURFACE_PATHS

        assert SURFACE_PATHS == {
            "projects_invariants": "/api/projects/invariants",
            "projects_attention": "/api/projects/attention",
            "audit_invariants": "/api/audit/invariants",
            "audit_findings": "/api/audit/findings",
            "queue_invariants": "/api/queue/invariants",
        }
