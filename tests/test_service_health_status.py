"""The one classification of ``service_health.status``, and its guards.

``SNAG-API-004``.  ``status != "ok"`` was written in four readers and was
wrong in three of them from the day migration 009 added ``skipped`` to
the CHECK constraint.  The defect is not the phrasing, it is that seven
values had no single statement of what they *mean*, so a value added to
the vocabulary reclassified itself at every call site at once and no
test could see it happen.

Two properties are pinned here and they fail in opposite directions:

**Totality** — every value the constraint admits is classified, and
nothing else is.  A migration that widens the vocabulary fails this
suite rather than falling silently to the ``is_fault`` fallback.  The
expected set is parsed out of the constraint's own ``sqltext``, never
re-typed, for ``schema_guard``'s reason: a regex over the thing it is
supposed to be checked against is not a check.

**Agreement across modules that cannot import each other** —
:mod:`sysadmin.monitor.reliability` promises purity in its own docstring
and so types its two status strings rather than importing them.  That is
``syslog_priority`` against ``journal.PRIORITY_MAP``: the copy is
permitted and the drift is not, so both sides are driven against the
constraint here.
"""

import re

import pytest

from sysadmin.monitor import reliability
from sysadmin.monitor.models.service_health import (
    SKIPPED,
    STATUS_READINGS,
    ServiceHealth,
    is_fault,
    is_unwatched,
)
from sysadmin.monitor.services import SKIPPED as SERVICES_SKIPPED


def constraint_vocabulary() -> set[str]:
    """The statuses ``chk_health_status`` admits, read off the constraint.

    Not a list this file maintains beside the one it is checking.
    """
    for arg in ServiceHealth.__table__.constraints:
        if getattr(arg, "name", None) == "chk_health_status":
            return set(re.findall(r"'([a-z_]+)'", str(arg.sqltext)))
    raise AssertionError("chk_health_status is gone from ServiceHealth")


class TestVocabularyIsTotal:
    def test_the_constraint_is_readable_at_all(self):
        # Guards the guard: a renamed constraint or a rewritten sqltext
        # would otherwise make every assertion below vacuously true
        # against an empty set.
        assert len(constraint_vocabulary()) >= 7

    def test_every_admitted_status_is_classified(self):
        assert constraint_vocabulary() <= set(STATUS_READINGS)

    def test_nothing_is_classified_that_the_database_would_reject(self):
        # The other direction, and the one that catches a status removed
        # by a migration rather than added: a reading for a value no row
        # can hold is a rule nothing exercises.
        assert set(STATUS_READINGS) <= constraint_vocabulary()

    def test_exactly_one_status_is_unwatched(self):
        # The classification's whole point is that ``unwatched`` is a
        # third thing.  If it ever holds two members, every caller that
        # partitions on it needs re-reading.
        unwatched = {s for s, r in STATUS_READINGS.items() if r == "unwatched"}
        assert unwatched == {SKIPPED}


class TestReadings:
    @pytest.mark.parametrize(
        "status", ["degraded", "warning", "critical", "unreachable", "error"]
    )
    def test_fault_statuses_are_faults(self, status):
        assert is_fault(status) is True
        assert is_unwatched(status) is False

    def test_ok_is_neither_a_fault_nor_unwatched(self):
        # ``is_unwatched`` is deliberately not ``not is_fault``.
        assert is_fault("ok") is False
        assert is_unwatched("ok") is False

    def test_skipped_is_unwatched_and_not_a_fault(self):
        assert is_fault(SKIPPED) is False
        assert is_unwatched(SKIPPED) is True

    def test_error_is_a_fault_although_it_measures_nothing(self):
        # The distinction the whole entry turns on.  Both ``error`` and
        # ``skipped`` mean nothing was measured; only ``skipped`` means
        # somebody decided that.  A monitor reporting an unmeasurable
        # check as well is not a monitor.
        assert is_fault("error") is True
        assert is_fault(SKIPPED) is False

    def test_an_unrecognised_status_reads_as_a_fault(self):
        # Fails closed.  Unreachable in production because of
        # TestVocabularyIsTotal, which is the point of having both.
        assert is_fault("banana") is True
        assert is_unwatched("banana") is False


class TestOneStatementOfTheVocabulary:
    def test_services_module_re_exports_rather_than_restates(self):
        """Provenance, not value — and the first draft of this asserted
        value and passed against the code it was written to break.

        ``SERVICES_SKIPPED is SKIPPED`` is True whether services.py
        imports the name or types ``"skipped"`` again, because CPython
        interns short string literals.  So the assertion has to be about
        where the binding *comes from*, which only the source can say.
        """
        import ast
        import pathlib

        tree = ast.parse(pathlib.Path("sysadmin/monitor/services.py").read_text())

        imported = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "sysadmin.monitor.models.service_health"
            for alias in node.names
        }

        bindings = [
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "SKIPPED" for t in node.targets
            )
        ]
        assert len(bindings) == 1, "services.SKIPPED is assigned more than once"
        bound = bindings[0]
        assert isinstance(bound, ast.Name), (
            "services.SKIPPED restates the literal instead of re-exporting it"
        )
        assert bound.id in imported

        # Value too, once provenance is established — an import of the
        # wrong name would satisfy everything above.
        assert SERVICES_SKIPPED == SKIPPED

    def test_reliability_typed_copies_agree_with_the_constraint(self):
        # reliability.py cannot import the model without giving up the
        # purity its docstring promises, so its strings are typed.  They
        # are still not allowed to drift.
        assert set(reliability.UNMEASURED_STATUSES) <= constraint_vocabulary()
        assert reliability.SKIPPED_STATUS == SKIPPED

    def test_reliability_partitions_the_whole_vocabulary(self):
        # ``ok`` | DOWN_STATUSES | UNMEASURED_STATUSES covers every value
        # the database can hold, with nothing in two parts.  That is what
        # lets reliability.py ask "is this down?" positively while
        # staying pure, and it is the property a widened vocabulary
        # breaks first.
        parts = [{"ok"}, set(reliability.DOWN_STATUSES), set(reliability.UNMEASURED_STATUSES)]
        union: set[str] = set().union(*parts)
        assert union == constraint_vocabulary()
        assert sum(len(part) for part in parts) == len(union), "parts overlap"

    def test_reliability_and_this_module_disagree_on_purpose(self):
        # Not a copy to deduplicate: ``error`` is a fault *and*
        # unmeasured, and reliability excludes both of its statuses from
        # every rate while this module calls one of them a fault.  Two
        # questions, one vocabulary.  Pinned so the next reader does not
        # "unify" them.
        assert is_fault(reliability.UNMEASURED_STATUS) is True
        assert reliability.UNMEASURED_STATUS in reliability.UNMEASURED_STATUSES
        assert is_fault(reliability.SKIPPED_STATUS) is False
        assert reliability.SKIPPED_STATUS in reliability.UNMEASURED_STATUSES
        # ``error`` is a fault here and *not* down there, and that is the
        # disagreement rather than a bug in one of them: an unmeasurable
        # check must not be charged as an outage, and must not be
        # reported as health either.
        assert reliability.UNMEASURED_STATUS not in reliability.DOWN_STATUSES
        assert all(is_fault(s) for s in reliability.DOWN_STATUSES)


class TestNoReaderNegatesOkByHand:
    """The audit, kept running.

    Three routers computed a health flag as ``!= "ok"`` and the fix was
    applied to one of them, twice, by two earlier sittings that each
    stopped at the instance they had noticed.  What makes this the third
    instance rather than the first is that nothing looked for the
    others.  This does.
    """

    def test_no_module_compares_a_health_status_to_ok_by_hand(self):
        import ast
        import pathlib

        offenders: list[str] = []
        # ``status`` here means a health-check status.  The file
        # organiser's operation status and the agent-run status are
        # different columns with different vocabularies, so the sweep is
        # scoped to modules that read ``ServiceHealth``.
        for path in sorted(pathlib.Path("sysadmin").rglob("*.py")):
            source = path.read_text()
            if "ServiceHealth" not in source:
                continue
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                if not any(
                    isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops
                ):
                    continue
                names = {
                    n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
                } | {
                    c.value
                    for c in ast.walk(node)
                    if isinstance(c, ast.Constant) and isinstance(c.value, str)
                }
                if "status" in names and "ok" in names:
                    offenders.append(f"{path}:{node.lineno}")

        assert offenders == [], (
            "a health status is being compared to 'ok' by hand; use "
            f"is_fault()/is_unwatched() instead: {offenders}"
        )
