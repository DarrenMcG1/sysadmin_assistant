"""The agent-to-timer handover guard (``SNAG-SVC-002``).

Every case here is driven at the **real** ``services.yaml`` and
``config.yaml`` with one line edited in a copy, rather than at a
hand-built pair. That matters for this entry specifically: its own check
is built on a synthetic subject because the box has no overlapping one,
and the whole finding of Session 160 is that reasoning about the
populations gave the wrong answer where measuring them gave the right
one. A fixture I wrote would be reasoning again.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from sysadmin.core.config import parse_config
from sysadmin.monitor.handover import (
    LINKABLE_KIND,
    HandoverReport,
    handover_report,
)
from sysadmin.monitor.self_monitor import AGENT_NAMES, agent_schedules
from sysadmin.monitor.services import default_services_path, parse_services

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"


@pytest.fixture
def services_raw() -> dict:
    return yaml.safe_load(default_services_path().read_text(encoding="utf-8"))


@pytest.fixture
def config_raw() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def config(config_raw, tmp_path) -> object:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config_raw), encoding="utf-8")
    return parse_config(path)


def _linked(raw: dict, service: str, agent: str | None) -> dict:
    """The real file with one timer's ``agent:`` key set."""
    out = yaml.safe_load(yaml.safe_dump(raw))
    for entry in out["services"]:
        if entry["name"] == service:
            if agent is None:
                entry.pop("agent", None)
            else:
                entry["agent"] = agent
    return out


def _with_config(config_raw, tmp_path, agent: str, enabled: bool):
    out = yaml.safe_load(yaml.safe_dump(config_raw))
    out["agents"][agent]["enabled"] = enabled
    path = tmp_path / "config_edited.yaml"
    path.write_text(yaml.safe_dump(out), encoding="utf-8")
    return parse_config(path)


#: The timer the shipped file links, and a name it can be re-pointed at.
LINKED_TIMER = "estate-manager-scan-timer"
LIVE_AGENT = "file_organiser"


class TestTheShippedFilesAreClean:
    def test_the_declared_link_names_a_retired_agent(self, services_raw, config):
        """The completed handover is silent, which is the key's purpose."""
        report = handover_report(parse_services(services_raw), config)
        assert report.walked
        assert report.declared == 1
        assert report.clean, report

    def test_the_link_names_an_agent_the_constraint_admits(self, services_raw):
        """A link is meaningless unless the alerts table has heard of it."""
        linked = [
            entry
            for entry in parse_services(services_raw).services
            if entry.agent is not None
        ]
        assert linked, "the shipped file declares no link — this suite proves nothing"
        for entry in linked:
            assert entry.agent in AGENT_NAMES

    def test_the_link_is_the_reason_that_agent_left_the_schedule(
        self, services_raw, config
    ):
        """The two sets answer different questions and both are read.

        ``project_organiser`` is in ``AGENT_NAMES`` because historical
        alert rows carry it, and absent from ``agent_schedules`` because
        ADR-0005 moved the work. That pair *is* the completed handover,
        so a link naming it must be silent — and the test asserts the
        premise as well as the verdict, or a day when the agent comes
        back reads as agreement.
        """
        linked = [
            entry.agent
            for entry in parse_services(services_raw).services
            if entry.agent is not None
        ]
        schedules = agent_schedules(config)
        for name in linked:
            assert name in AGENT_NAMES
            assert name not in schedules


class TestTheThreeRungs:
    def test_a_link_to_an_enabled_agent_is_a_breach(self, services_raw, config):
        raw = _linked(services_raw, LINKED_TIMER, LIVE_AGENT)
        report = handover_report(parse_services(raw), config)
        assert report.breached == [f"{LINKED_TIMER} -> {LIVE_AGENT}"]
        assert not report.flag_carried
        assert not report.clean

    def test_a_link_to_a_disabled_agent_is_flag_carried(
        self, services_raw, config_raw, tmp_path
    ):
        """The 2026-08-08 state, reconstructed from what the box did.

        Commit ``5cc04cc`` declared ``sysadmin-organiser.timer`` as
        ``kind: timer`` and set ``agents.project_organiser.enabled:
        false`` in the same sitting, because the flag was the only thing
        keeping the daemon from scanning the estate twice. That is a real
        configuration this repository once served, and it is the rung
        that must not be reported as a fault: the handover was working.
        """
        raw = _linked(services_raw, LINKED_TIMER, LIVE_AGENT)
        config = _with_config(config_raw, tmp_path, LIVE_AGENT, enabled=False)
        report = handover_report(parse_services(raw), config)
        assert report.flag_carried == [f"{LINKED_TIMER} -> {LIVE_AGENT}"]
        assert not report.breached

    def test_a_link_naming_no_agent_is_reported_not_skipped(
        self, services_raw, config
    ):
        raw = _linked(services_raw, LINKED_TIMER, "file_organizer")
        report = handover_report(parse_services(raw), config)
        assert report.unknown_agents == [f"{LINKED_TIMER} -> file_organizer"]
        assert not report.breached and not report.flag_carried

    def test_the_rungs_are_distinct_states_of_one_link(
        self, services_raw, config_raw, config, tmp_path
    ):
        """Collapsing enabled and disabled would misreport both.

        Driven as one link at two config values so the only difference
        between the two readings is the flag — the discriminator the
        entry's own reasoning did not have.
        """
        raw = _linked(services_raw, LINKED_TIMER, LIVE_AGENT)
        parsed = parse_services(raw)
        enabled = handover_report(parsed, config)
        disabled = handover_report(
            parsed, _with_config(config_raw, tmp_path, LIVE_AGENT, enabled=False)
        )
        assert enabled.breached and not enabled.flag_carried
        assert disabled.flag_carried and not disabled.breached


class TestZeroBecauseBlind:
    def test_a_report_that_did_not_walk_carries_no_agreement(self):
        """``ports_checked``'s rule at the size of a dataclass default."""
        blank = HandoverReport()
        assert blank.walked is False
        assert not blank.clean
        assert not (blank.breached or blank.flag_carried or blank.unknown_agents)

    def test_declared_separates_no_findings_from_no_links(
        self, services_raw, config
    ):
        """Zero findings over zero links is not the same bill of health."""
        stripped = _linked(services_raw, LINKED_TIMER, None)
        report = handover_report(parse_services(stripped), config)
        assert report.clean
        assert report.declared == 0


class TestTheFieldIsConstrainedWhereItIsDeclared:
    def test_the_key_is_refused_on_a_kind_that_holds_no_schedule(
        self, services_raw
    ):
        raw = yaml.safe_load(yaml.safe_dump(services_raw))
        for entry in raw["services"]:
            if entry["name"] == "postgresql":
                entry["agent"] = "sysadmin"
        with pytest.raises(Exception, match="only meaningful on kind timer"):
            parse_services(raw)

    def test_a_misspelt_key_fails_at_load_rather_than_being_dropped(
        self, services_raw
    ):
        """``extra="forbid"`` is the half ``SNAG-CFG-004`` does not have.

        config.yaml's models ignore an unknown key, which is why that
        entry needed a reporting walk. This file forbids one, so a typo
        in the handover key is a refused parse rather than a silent
        omission — and that asymmetry is the reason the link is declared
        on this side.
        """
        raw = _linked(services_raw, LINKED_TIMER, None)
        for entry in raw["services"]:
            if entry["name"] == LINKED_TIMER:
                entry["agentt"] = "project_organiser"
        with pytest.raises(Exception):
            parse_services(raw)

    def test_the_linkable_kind_is_the_one_the_validator_admits(self):
        """The constant and the validator state one fact, so pin them.

        Read from the source rather than by driving every kind: what is
        being asserted is provenance — that the module's constant is the
        string the model checks — and only the source answers that.
        """
        source = (ROOT / "sysadmin" / "monitor" / "services.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        compared: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            left = node.left
            if not (isinstance(left, ast.Attribute) and left.attr == "kind"):
                continue
            for op, comp in zip(node.ops, node.comparators, strict=True):
                if isinstance(op, ast.NotEq) and isinstance(comp, ast.Constant):
                    compared.add(comp.value)
        assert LINKABLE_KIND in compared, (
            "the validator no longer refuses every kind but "
            f"{LINKABLE_KIND!r} — the constant and the check have parted"
        )
