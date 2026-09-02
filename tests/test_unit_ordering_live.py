"""``systemd/sysadmin.service`` orders against nothing this box cannot resolve.

The regression guard ``SNAG-SYSD-003`` closed onto, and it is
deliberately **wider than the entry**.  That entry was one retired name —
``ollama.service``, left in ``After=`` when the LLM runtime moved to
llama.cpp on 2026-07-24 and still there on 2026-09-02 — but its stated
cost was never that one name.  It is that *"the unit file is read as the
record of what this service depends on"* and that anyone deriving a new
project's unit from it, which ``monitorable-project.md`` invites, copies
the stale dependency forward.  A guard asserting the absence of the
string ``ollama.service`` would pin the instance and say nothing about
the next one, so what is asserted is the property: **every unit named in
``After=`` resolves in the manager this unit runs under**.

``check_sysd_ollama_ordering`` retired with the entry and this is where
its detector went — ``FROZEN_TABLES``' rule, and the fourth time this
repository has kept a detector while retiring the finding it was written
for.  Both of that check's limbs survive, and they are still reported
apart because they refute in opposite directions: a name that does not
resolve is the **fault**, and the control resolving is the **premise**
dying.

Three rules, two of them the opposite of the obvious implementation:

1. **The negative control is what makes an all-``loaded`` answer mean
   anything.**  ``systemctl show`` answers for a unit that does not exist
   and exits ``0`` — :func:`sysadmin.snag_claims.unit_load_state` records
   that trap and :class:`sysadmin.ops_claims.UnitState` records it from
   the other side — so a sweep that only ever sees ``loaded`` cannot tell
   a healthy ordering from a reader that has stopped discriminating.
   :data:`~sysadmin.snag_claims.RETIRED_UNIT` is read for exactly that:
   a name known to be absent, required to come back ``not-found``.  It is
   the constant's second job, and the reason it outlived its check.

2. **The reader is imported, never re-implemented.**  Shelling out to
   ``systemctl`` here would be a second statement of a fact
   ``unit_load_state`` already owns — ``max_priority_for`` against
   ``PRIORITY_MAP``'s rule — and the two would be free to disagree about
   what "no answer" means.  Retiring the check left that helper with no
   production caller; this file is its consumer, which is stated in its
   docstring rather than left to be inferred.

3. **The manager is the system one, and that is the half a name-based
   guard cannot see.**  ``sysadmin.service`` is a *system* unit.
   ``alfred-inference.service`` — the successor the entry named and did
   not settle — is a **user** unit at ``~/.config/systemd/user/`` and
   reports ``LoadState=not-found`` in the system manager, so ordering
   against it would rebuild the entry's own defect under a newer name.
   Measured 2026-09-02, and it is what closed the entry's open question:
   the successor is not one, and nothing replaced the removed line.

The premise is marked because this file is a live drive
(``tests/test_live_drive_premises.py``): it reads this box through
``systemctl`` rather than modelling it, so a negative here has to be
shown to be a fact about the unit file and not about a reader that
answered nothing.
"""

from __future__ import annotations

import re

import pytest

from sysadmin.snag_claims import RETIRED_UNIT, SYSADMIN_UNIT, unit_load_state

#: ``LoadState`` for a unit systemd has never heard of.  Written here
#: rather than imported because it is systemd's word and not this
#: repository's, and the string is the whole discrimination.
NOT_FOUND = "not-found"

#: What :func:`sysadmin.snag_claims.unit_load_state` returns when it could
#: not ask at all.  Every way of not-knowing carries this prefix, and it
#: is not a verdict about a unit — ``ports_checked``'s rule.
UNMEASURED = "unmeasured"

AFTER_RE = re.compile(r"^After=(.*)$", re.MULTILINE)


def ordered_units() -> list[str]:
    """Every unit named in the unit file's ``After=`` lines, in order.

    A unit may declare ``After=`` more than once and systemd unions them,
    so every line is read.  ``.target`` names are kept rather than
    filtered: ``network.target`` is a real unit that resolves, and a
    target that does not resolve is exactly as stale as a service that
    does not.
    """
    text = SYSADMIN_UNIT.read_text(encoding="utf-8")
    return [unit for line in AFTER_RE.findall(text) for unit in line.split()]


@pytest.mark.premise
class TestThePremises:
    """Neither assertion below means anything without these.

    The order matters: an empty ``After=`` line satisfies "every named
    unit resolves" vacuously, and a ``systemctl`` that has stopped
    answering satisfies it in a way that looks identical to health.
    """

    def test_the_unit_file_declares_an_ordering_at_all(self):
        assert ordered_units(), (
            f"{SYSADMIN_UNIT} declares no After= units, so the assertion below is "
            "vacuous — a deleted ordering is not a clean one"
        )

    def test_systemd_answers_and_can_still_say_not_found(self):
        """The negative control, and the reason :data:`RETIRED_UNIT` outlived its check.

        A reader that answered ``loaded`` to everything would pass the
        guard below over any ordering at all.  This asks for a name known
        to be absent and requires the absent answer back, so the guard
        rests on a reader shown to discriminate rather than on one
        assumed to.
        """
        state = unit_load_state(RETIRED_UNIT)
        assert not state.startswith(UNMEASURED), (
            f"systemctl would not answer for {RETIRED_UNIT} ({state}), so a clean "
            "sweep below would be zero-because-blind rather than zero-because-clean"
        )
        assert state == NOT_FOUND, (
            f"{RETIRED_UNIT} reads {state!r} rather than {NOT_FOUND!r} — the control "
            "has been installed on this box, so it no longer discriminates and this "
            "guard needs a different absent name. That is SNAG-SYSD-003's second "
            "refutation surviving its first: the premise dying, not the fault."
        )


class TestTheOrderingNamesNothingRetired:
    """``SNAG-SYSD-003``'s fault half, widened from one name to the property."""

    def test_every_ordered_unit_resolves_in_the_system_manager(self):
        named = ordered_units()
        readings = {unit: unit_load_state(unit) for unit in named}
        unmeasured = {u: s for u, s in readings.items() if s.startswith(UNMEASURED)}
        assert not unmeasured, (
            f"systemd would not answer for {sorted(unmeasured)} — reported rather "
            "than skipped, because a unit nobody could ask about is not a unit that "
            "resolved"
        )
        stale = sorted(u for u, s in readings.items() if s == NOT_FOUND)
        assert not stale, (
            f"{SYSADMIN_UNIT} orders after {stale}, which the system manager cannot "
            f"resolve. That is SNAG-SYSD-003 again: the ordering costs nothing at "
            "runtime and the unit file is read as the record of what this service "
            "depends on, so a name here that does not exist is copied forward by "
            "whoever derives their unit from it. Remove the name, or — if the "
            "dependency is real — check it is not a *user* unit, which a system "
            "unit cannot order against at all."
        )

    def test_the_retired_name_is_gone_rather_than_merely_unresolvable(self):
        """The instance, kept beside the property because it is the founding case.

        The sweep above would also pass if ``ollama.service`` were named
        and had been reinstalled — which is the entry's premise dying,
        not its remedy landing, and the two must not read alike.  This
        one is unconditional on what systemd says.
        """
        assert RETIRED_UNIT not in ordered_units(), (
            f"{RETIRED_UNIT} is back in the After= line. It was removed on "
            "2026-09-02 closing SNAG-SYSD-003; the LLM runtime moved to llama.cpp "
            "on 2026-07-24 and nothing replaced the ordering, deliberately."
        )
