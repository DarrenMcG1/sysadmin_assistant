"""The declared systemd dependency graph (``SNAG-LOG-001``).

``GET /api/logs/actions`` uses it to tell one incident from two.  The
fixtures are this box's real unit files, trimmed to the ``[Unit]``
section: ``estate-broker-provision.service`` is the one live relation
between two declared log sources, and it is the reason the family
exists.
"""

from pathlib import Path

import pytest

from sysadmin.units.scan import (
    RELATION_DIRECTIVES,
    UnitRelation,
    declared_relations,
    discover_units,
    load_unit,
    qualify_unit,
)

#: Verbatim ``[Unit]`` section of ``/etc/systemd/system/estate-broker-provision.service``.
PROVISIONER = """\
[Unit]
Description=Assert the estate MQTT dynsec schema (roles, ACLs, static clients)
After=mosquitto.service
Wants=mosquitto.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 scripts/estate-broker-provision

[Install]
WantedBy=multi-user.target
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return load_unit(path, "system", "/home/gaddi")


class TestParsing:
    def test_the_live_provisioner_declares_both_directives(self, tmp_path):
        unit = _write(tmp_path, "estate-broker-provision.service", PROVISIONER)
        assert unit.relations == (
            UnitRelation("After", "mosquitto.service"),
            UnitRelation("Wants", "mosquitto.service"),
        )

    def test_one_directive_may_name_several_units(self, tmp_path):
        unit = _write(tmp_path, "a.service",
                      "[Unit]\nAfter=b.service c.service\n")
        assert [r.unit for r in unit.relations] == ["b.service", "c.service"]

    def test_a_repeated_directive_accumulates(self, tmp_path):
        """systemd's own semantics, and ``parse_unit_text`` preserves it."""
        unit = _write(tmp_path, "a.service",
                      "[Unit]\nAfter=b.service\nAfter=c.service\n")
        assert [r.unit for r in unit.relations] == ["b.service", "c.service"]

    def test_an_empty_assignment_resets_the_list(self, tmp_path):
        unit = _write(tmp_path, "a.service",
                      "[Unit]\nAfter=b.service\nAfter=\nAfter=c.service\n")
        assert [r.unit for r in unit.relations] == ["c.service"]

    def test_a_bare_stem_is_qualified_to_a_service(self, tmp_path):
        unit = _write(tmp_path, "a.service", "[Unit]\nRequires=postgresql\n")
        assert unit.relations == (UnitRelation("Requires", "postgresql.service"),)

    @pytest.mark.parametrize("suffix", [".timer", ".socket", ".target", ".path"])
    def test_a_suffixed_name_is_left_alone(self, suffix):
        assert qualify_unit(f"thing{suffix}") == f"thing{suffix}"

    def test_conflicts_is_not_a_relation(self, tmp_path):
        """The one *negative* directive: a stop performed on purpose.

        Including it would correlate a successful handover with a crash.
        """
        assert "Conflicts" not in RELATION_DIRECTIVES
        unit = _write(tmp_path, "a.service", "[Unit]\nConflicts=b.service\n")
        assert unit.relations == ()

    def test_relations_are_read_from_the_unit_section_only(self, tmp_path):
        unit = _write(tmp_path, "a.service",
                      "[Unit]\nAfter=b.service\n[Service]\nAfter=c.service\n")
        assert [r.unit for r in unit.relations] == ["b.service"]

    def test_a_unit_declaring_nothing_has_no_relations(self, tmp_path):
        unit = _write(tmp_path, "a.service",
                      "[Unit]\nDescription=quiet\n[Service]\nExecStart=/bin/true\n")
        assert unit.relations == ()


class TestGraph:
    def test_the_map_is_symmetric_because_only_one_side_declares(self, tmp_path):
        """Nothing in ``mosquitto.service`` mentions the provisioner.

        A lookup keyed on the declaring unit alone answers "what is
        mosquitto related to" with nothing — and mosquitto is the unit
        that fails first, so it is the direction the incident is read in.
        """
        unit = _write(tmp_path, "estate-broker-provision.service", PROVISIONER)
        graph = declared_relations([unit])
        assert graph[("system", "estate-broker-provision.service")] == frozenset(
            {"mosquitto.service"}
        )
        assert graph[("system", "mosquitto.service")] == frozenset(
            {"estate-broker-provision.service"}
        )

    def test_scope_is_part_of_the_key(self, tmp_path):
        """``deadlock-api-ingest.service`` is installed in both scopes here.

        systemd never orders across managers, so a user unit's
        declaration can only mean the user-scope unit of that name.
        """
        path = tmp_path / "a.service"
        path.write_text("[Unit]\nAfter=b.service\n")
        graph = declared_relations([
            load_unit(path, "user", "/home/gaddi"),
        ])
        assert ("user", "a.service") in graph
        assert ("system", "a.service") not in graph
        assert ("system", "b.service") not in graph

    def test_a_self_relation_is_refused(self, tmp_path):
        """``OnFailure=`` pointing home would give every unit a self-edge.

        True, useless, and it would hide that same-source grouping is a
        separate rule with a separate justification.
        """
        unit = _write(tmp_path, "a.service", "[Unit]\nOnFailure=a.service\n")
        assert declared_relations([unit]) == {}

    def test_an_empty_input_yields_an_empty_graph(self):
        """Fails open: not knowing means not collapsing."""
        assert declared_relations([]) == {}


class TestAgainstThisBox:
    """Driven against the real ``/etc/systemd/system``, not a fixture."""

    @pytest.fixture(scope="class")
    def live(self):
        system = Path("/etc/systemd/system")
        if not system.is_dir():
            pytest.skip("no /etc/systemd/system on this host")
        units, _ = discover_units(
            Path.home() / ".config/systemd/user", system, str(Path.home())
        )
        return declared_relations(units)

    def test_the_live_specimen_relation_is_readable_from_the_sweeps_dirs(self, live):
        """The measurement the whole design rests on.

        ``mosquitto.service`` is a *packaged* unit that
        :func:`discover_units` excludes as distro-owned, and its own file
        lives in ``/usr/lib/systemd/system`` which the sweep never walks.
        The relation is still readable, because the unit that *depends*
        is the hand-written one — which is why parsing ``/usr/lib`` was
        measured (629 further files) and found to add nothing.
        """
        pair = live.get(("system", "estate-broker-provision.service"))
        if pair is None:
            pytest.skip("estate-broker-provision.service not installed here")
        assert "mosquitto.service" in pair
        assert "estate-broker-provision.service" in live[("system", "mosquitto.service")]

    def test_no_unit_is_related_to_itself(self, live):
        for (_, name), related in live.items():
            assert name not in related
