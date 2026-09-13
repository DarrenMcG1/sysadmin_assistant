"""What estate-manager does with a pid, driven rather than read off a flag.

``SNAG-PORT-006``'s replacement pin, and the entry is precise about what
went wrong with the one it replaces.
``tests/test_unit_ports.py::test_the_estate_still_runs_ss_without_p_which_is_why_this_module_exists``
asserted the literal ``'["ss", "-H", "-tln"]'`` in
``estate_service/audit/checks/ports.py``.  Its docstring's stated
conclusion is a **conjunction** — *"if estate-manager ever adds ``-p``
and attributes ports itself, this module is a second implementation of
their check"* — and their ``4c3ad2d`` (2026-09-13, ADR-0166) satisfied
only the first limb.  The suite went red on a clean tree, correctly, over
a conclusion that does not follow.

**The defect is that a noun was pinned where the claim is about a verb.**
*Do they attribute ports themselves* was readable off ``-p``'s absence
while ``-p`` had one possible use.  It now has two: a pid joins to a
**working directory** (theirs, ``/proc/<pid>/cwd`` → a registry tree) or
to a **unit with its scope** (ours, ``/proc/<pid>/cgroup``).  Their
``working_directory`` docstring refuses ours in writing — *"a unit name
reaches a project only through ``services.yaml``'s ``project:`` or the
monitor's ``scan_units`` map, both ``sysadmin_assistant``'s, and reading
either as ground truth would make this check verify its registry against
another repository's document"* (ADR-0166 §4) — so the flag moved and the
answer did not.  ``check_markers``' rule from the other side: a marker
names a check and never a value.

Five rules, four of them the opposite of the obvious implementation:

1. **The instrument is a differential and never a second string.**  The
   obvious re-key is to assert ``'["ss", "-H", "-ltnp"]'``, which is the
   same proxy in a new spelling and would go red the day they add
   ``--processes`` or reorder a flag, while staying green through a unit
   join added in the next function.  What is asked instead is *what
   happens when the directory is taken away*:
   :meth:`TestTheDirectoryIsTheirOnlyRouteToAHolder.test_blinding_the_directory_leaves_their_check_with_nothing`
   blinds ``directory_of`` and requires every attribution to collapse to
   ``no_directory``.  A unit route added **anywhere** — injected beside
   ``directory_of``, or reading ``/proc`` directly — survives that
   blinding and reddens this, which is the conclusion the old pin was
   trying to reach.

2. **It is asked at both altitudes, because a route could land above the
   join.**  ``attribute`` is where the join lives today and ``run_check``
   is the whole check; blinding only the first is green over a unit
   lookup added in the caller, and blinding only the second cannot say
   *where*.  Both are cheap — one further ``ss`` read apiece — so both
   are driven.

3. **A green collapse is evidence only where the two joins can disagree,
   and that is a premise rather than a hope.**  If every holder on this
   box resolved the same way under both designs, "blinding theirs
   resolves nothing" would be agreement and not a measurement.
   :meth:`TestThePremises.test_the_two_joins_separate_on_this_box` is the
   separator, and it is richly non-empty: measured 2026-09-13, **21** of
   the 29 named ports have a unit from our cgroup read and no registry
   tree from their directory read, four of them in the audited band
   (8080 ``venture-chat``, 8081 ``alfred-inference``, 8082
   ``venture-embed``, 8384 ``syncthing@gaddi``), every one of them a
   service whose ``WorkingDirectory`` is ``/`` or ``$HOME``.  The reverse
   eight resolve under both and name *different vocabularies* —
   ``alfred-frontend.service`` against the registry id ``alfred``.

4. **The blinding is driven at a stand-in modelling the fix, not only at
   the producer.**  A collapse assertion that has never been seen to fail
   is a constant observation wearing a verdict:
   :func:`_attribute_with_a_unit_fallback` is what their ``attribute``
   would look like the day a cgroup route lands — deliberately built out
   of *our* reader, because that is the duplication this pin exists to
   detect — and
   :meth:`TestTheDirectoryIsTheirOnlyRouteToAHolder.test_the_blinding_can_say_not_collapsed`
   requires it to survive.  A control a fix breaks is not a control; a
   control nothing can break is not one either.

5. **The skip is gated on the tree and never on the import.**
   ``estate_service`` reaches this checkout by an editable ``.pth`` that
   is in no lockfile, so ``pytest.importorskip`` would pass on the box
   where the pin matters the moment a ``uv sync`` prunes it — a control
   disarmed by routine housekeeping, with the suite green.  A checkout
   without estate-manager beside it has nothing to pin against and skips;
   one *with* it and no importable module is a red, because that is the
   state where the pin was silently lost.
   ``test_handoff_shape.py``'s idiom, reused.

**What this does not do**: decide whether ``sysadmin/units/ports.py``
should exist.  That question was answered by measurement before this file
was written — they attribute to a **directory**, we attribute to a
**unit**, nothing is duplicated — and the module keeps its reason to
exist.  This is the instrument that would say so again, at the next
change.
"""

from __future__ import annotations

import importlib
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from sysadmin.units import ports as ours

#: The checkout, not the import — rule 5.
ESTATE_TREE = Path("/home/gaddi/projects/estate-manager")
ESTATE_PORTS_CHECK = (
    ESTATE_TREE / "service" / "estate_service" / "audit" / "checks" / "ports.py"
)

pytestmark = pytest.mark.skipif(
    not ESTATE_PORTS_CHECK.is_file(),
    reason=f"{ESTATE_PORTS_CHECK} is not on this box — nothing to pin against",
)


def _blind(_pid: int) -> str | None:
    """A directory reader that can answer nothing.

    Not a failure being simulated: it is the *counterfactual*.  Whatever
    survives it is reached by some route other than the working
    directory, which is the whole question.
    """
    return None


@pytest.fixture(scope="module")
def theirs() -> Any:
    return importlib.import_module("estate_service.audit.checks.ports")


@pytest.fixture(scope="module")
def registry() -> Any:
    """``estate.registry`` is ``estate-lib``, which *is* a dependency here
    (ADR-0004) — so only the check itself needs the undeclared install."""
    from estate.registry import load_registry

    return load_registry()


@pytest.fixture(scope="module")
def observation(theirs: Any) -> Any:
    """One ``ss`` read, theirs."""
    return theirs.observe_listeners()


@pytest.fixture(scope="module")
def our_units() -> dict[int, tuple[str, str | None]]:
    """``pid -> (unit, scope)`` from this repository's cgroup join."""
    report = ours.observe_listeners()
    return {
        listener.pid: (listener.unit, listener.scope)
        for listener in report.listeners
        if listener.pid is not None and listener.unit
    }


def _outcomes(theirs: Any, observation: Any, registry: Any, directory_of: Any) -> set[str]:
    """Every outcome their join reaches, over every port ``ss`` named."""
    return {
        row.outcome
        for port in observation.holders
        for row in theirs.attribute(port, observation, registry, directory_of)
    }


def _attribute_with_a_unit_fallback(
    theirs: Any,
    our_units: dict[int, tuple[str, str | None]],
) -> Any:
    """Their ``attribute``, as it would read the day a unit route lands.

    Rule 4's stand-in.  It resolves exactly the holders the directory
    could not — which is what "attributes ports itself" would mean here —
    and it does so out of :mod:`sysadmin.units.ports`' own cgroup read,
    so the stand-in *is* the duplication rather than a token standing in
    for it.
    """

    def attribute(port: int, observation: Any, registry: Any, directory_of: Any) -> Any:
        rows = []
        for row in theirs.attribute(port, observation, registry, directory_of):
            if (
                row.outcome == theirs.UNRESOLVED_NO_DIRECTORY
                and row.holder is not None
                and row.holder.pid in our_units
            ):
                row = replace(
                    row,
                    outcome=theirs.RESOLVED_REGISTRY_TREE,
                    project=our_units[row.holder.pid][0],
                )
            rows.append(row)
        return tuple(rows)

    return attribute



@pytest.mark.premise
class TestThePremises:
    """Neither reading below means anything without these.

    The order is the order of the failures they exclude: an ``ss`` that
    named nobody makes every collapse vacuous; a join that resolves
    nothing makes "blinding it resolves nothing" a statement about a
    reader that already knew nothing; and two joins that cannot disagree
    on this box make a green pin agreement rather than evidence.
    """

    def test_ss_named_holders_on_both_sides(
        self, observation: Any, our_units: dict[int, tuple[str, str | None]]
    ) -> None:
        assert observation.holders, (
            "estate-manager's observe_listeners() named no process on any port, so "
            "every attribution below is zero-because-blind rather than "
            "zero-because-the-directory-is-their-only-route"
        )
        assert our_units, (
            "sysadmin.units.ports named no unit for any listener, so the separator "
            "below has nothing to separate and the two joins cannot be compared"
        )

    def test_their_join_resolves_at_least_one_holder(
        self, theirs: Any, observation: Any, registry: Any
    ) -> None:
        """Or the counterfactual removes nothing."""
        reached = _outcomes(theirs, observation, registry, theirs.working_directory)
        assert reached & set(theirs.RESOLVED_OUTCOMES), (
            f"their join resolved nothing on this box ({sorted(reached)}), so "
            "blinding it below changes no answer and the pin measures nothing"
        )

    def test_the_two_joins_separate_on_this_box(
        self,
        theirs: Any,
        observation: Any,
        registry: Any,
        our_units: dict[int, tuple[str, str | None]],
    ) -> None:
        """Rule 3.  The population that tells the two designs apart.

        A port we attribute to a unit and they attribute to no registry
        tree at all.  Its members are services whose ``WorkingDirectory``
        is ``/`` or ``$HOME`` — their own ``SNAG-ESTATE-188`` — plus every
        editor, browser and game on the box.  If this ever empties, the
        two joins have started agreeing and a green pin below stops being
        evidence, which is a thing to be told rather than to pass
        silently.
        """
        separating = [
            port
            for port, holders in observation.holders.items()
            if theirs.port_outcome(
                theirs.attribute(port, observation, registry, theirs.working_directory)
            )
            not in theirs.RESOLVED_OUTCOMES
            and any(holder.pid in our_units for holder in holders)
        ]
        assert separating, (
            "every port this box's cgroup join names a unit for is also resolved to "
            "a registry tree by estate-manager's directory join, so the two joins "
            "agree everywhere here and the blinding below would be green whichever "
            "of them their check used"
        )


class TestTheDirectoryIsTheirOnlyRouteToAHolder:
    """The pin.  Keyed on what they do with a pid, not on how they fetch it."""

    def test_blinding_the_directory_leaves_their_check_with_nothing(
        self, theirs: Any, observation: Any, registry: Any
    ) -> None:
        reached = _outcomes(theirs, observation, registry, _blind)
        assert reached <= {theirs.UNRESOLVED_NO_DIRECTORY}, (
            f"estate-manager's attribute() still reaches {sorted(reached)} with the "
            "working directory unreadable, so a pid now reaches an identity by some "
            "other route. If that route is /proc/<pid>/cgroup, their check has "
            "started attributing ports to units and sysadmin/units/ports.py is a "
            "second implementation of it rather than the half they were blocked "
            "from — which is the question this pin exists to ask."
        )

    def test_blinding_it_leaves_the_whole_check_with_nothing(
        self, theirs: Any, registry: Any
    ) -> None:
        """Rule 2's upper altitude: the same counterfactual at ``run_check``.

        ``coverage['resolved']`` is the join's own answer count, added by
        ADR-0166 and announced here as estate message ``16d3a757``.  A
        unit route added *above* ``attribute`` — in the caller, or in a
        second reader handed in beside ``directory_of`` — is invisible to
        the test above and lands here.
        """
        from sysadmin.core.config import get_config

        document = Path(
            get_config().agents.service_discovery.ports.document
        ).expanduser()
        if not document.exists():
            pytest.skip(f"{document} is not on this box")
        text = document.read_text(encoding="utf-8")
        config = theirs.PortRegistryConfig()

        sighted = theirs.run_check(config, text, registry=registry)
        blinded = theirs.run_check(
            config, text, registry=registry, directory_of=_blind
        )
        assert not sighted.error and not blinded.error, (
            f"their check errored ({sighted.error or blinded.error}), so neither "
            "coverage figure is a reading of the join"
        )
        assert sum(sighted.coverage["resolved"].values()) > 0, (
            "their check resolved no claimed listening port at all, so the "
            "comparison below is between two piles of nothing"
        )
        assert sum(blinded.coverage["resolved"].values()) == 0, (
            f"run_check still resolves {blinded.coverage['resolved']} with the "
            "working directory unreadable, so the check reaches a holder's identity "
            "by a route other than /proc/<pid>/cwd. See the sibling test — the same "
            "question one layer down, which says whether the route is in attribute()"
        )

    def test_the_blinding_can_say_not_collapsed(
        self,
        theirs: Any,
        observation: Any,
        registry: Any,
        our_units: dict[int, tuple[str, str | None]],
    ) -> None:
        """Rule 4.  The positive control, and it models the fix.

        Driven at :func:`_attribute_with_a_unit_fallback`, which is the
        shape the pin above exists to catch.  Without this, a collapse
        that has never been observed to fail is indistinguishable from an
        assertion that cannot fail — and this register has shipped that
        three times (``check_review_schedule_unread``'s defect).
        """
        reached = _outcomes(
            theirs,
            observation,
            registry,
            theirs.working_directory,
        )
        assert reached, "nothing to control against"

        fallback = _attribute_with_a_unit_fallback(theirs, our_units)
        survived = {
            row.outcome
            for port in observation.holders
            for row in fallback(port, observation, registry, _blind)
        }
        assert survived - {theirs.UNRESOLVED_NO_DIRECTORY}, (
            "a stand-in that resolves a blinded holder through its cgroup collapsed "
            "anyway, so the assertion above would stay green over exactly the change "
            "it is written to catch"
        )
        assert theirs.RESOLVED_REGISTRY_TREE in survived
