"""Two claims ``services.yaml`` makes about this box, computed rather than read.

``SNAG-DOCS-027``'s guard, and the entry is precise about which half of
it is guardable.  Session 225 swept all **19** measurable claims in that
file's comments: **14** held, **5** were wrong, and three of the five had
been wrong for a month — ``estate-broker-provision``'s *"the unit is not
yet installed and this check will rightly complain"* for **32 days**
(installed 2026-08-12 08:56, the morning after it was written) and
``ethernet-optimise``'s *"this is the one oneshot on the box with no
timer that is still monitorable"* **on the day it was written**, its
counterexample already 250 lines above it in the same file.

**The class is not "true when written and false later".**  That was the
handoff's definition and the uniqueness claim refutes it: the property
the class turns on is that **nothing re-reads the sentence**, and a
uniqueness claim is its worst case, because what falsifies it is an edit
somewhere else in the file that its own author will never revisit.

**A lexical guard over the comments is refused and the refusal is the
entry's**, not a convenience here.  A test banning *not yet* /
*upcoming* / *until … has been run* would redden every correction that
sweep wrote — each preserves its original as *"this entry read … until
2026-09-13"*, which is the phrasing that makes a stale claim legible as
history — and would have caught **none** of the uniqueness claim, the
stale count, or the tray's wrong instruction.  Deciding that an English
sentence is a claim is a human's job: ``SNAG-ESTATE-012``, one file over
from where it was filed.

**What is computable is computable with no marker at all, because the
file is its own population.**  ``ops_claims.py``'s marker machinery
exists because ``STATUS.md`` has no declared subject; here every claim of
this shape sits beside the unit name it is about, so the two guards
below need no ``<!--check:…-->`` and no ``CLAIM_PATTERN``:

1. **Every unit the file declares is installed** — the
   ``estate-broker-provision`` claim's subject, generalised from one
   sentence to all 31 declared units.
2. **The standalone oneshots are exactly the pair the file names** —
   the ``ethernet-optimise`` uniqueness claim, computed as
   ``Type=oneshot`` + ``RemainAfterExit=yes`` + no triggering timer over
   this file's own ``kind: systemd`` ``.service`` entries.

Six rules, four of them the opposite of the obvious implementation and
every one settled against the box rather than by argument:

1. **A test, never a twenty-sixth snag check, and the entry says why.**
   What a check would drive is *"does anything compute the two
   computable claims"*, which asserts the **fix** — so
   ``check-snag-claims.sh``'s ``ok``, meaning *the bug is still real*,
   would report ``still holds`` over a landed closure.  That is
   ``check_review_schedule_unread``'s defect and this register has been
   caught by it four times.  A test outlives the entry, which is
   ``FROZEN_TABLES``' rule.

2. **This is box-dependent and is deliberately not ``SNAG-TEST-013``'s
   defect, which is a distinction about *what* is read rather than about
   whether the box is read at all.**  That entry was a live test pinned
   to a value the box flaps between — an alert count — and it blocked the
   commit **one run in twenty-seven**.  ``Type``, ``RemainAfterExit``,
   ``UnitFileState`` and ``TriggeredBy`` are properties of unit **files**
   and of the enablement tree: they do not oscillate, they change when
   somebody installs, edits or removes a unit, which is exactly the
   moment the sentences in ``services.yaml`` need re-reading.
   ``ActiveState`` is the flapping neighbour and is read **nowhere** in
   this file — a restarting ``ethernet-optimise.service`` must not refuse
   a commit, and asserting liveness here would duplicate the sysadmin
   agent, which owns that lifecycle.

3. **"No timer" is only a measurement on a unit already shown to be
   installed, and the premise below asserts the trap rather than
   claiming it.**  ``systemctl show`` answers for a unit that does not
   exist and exits ``0`` — :func:`sysadmin.snag_claims.unit_load_state`
   records that from one side and :class:`sysadmin.ops_claims.UnitState`
   from the other — and a minted absent name comes back with
   ``TriggeredBy=''``, which is **byte-identical** to a real unit that no
   timer triggers.  So the installedness sweep is a *premise* of the
   uniqueness half and not a sibling of it, and
   :meth:`TestThePremises.test_an_absent_unit_is_indistinguishable_from_an_untriggered_one`
   measures that indistinguishability instead of asserting it.

4. **``TriggeredBy`` is asked of the service, not derived from
   ``systemctl list-timers``.**  The comment this guards was measured
   that way and the reading is weaker in two directions: ``list-timers``
   omits inactive timers unless ``--all`` is passed, so a disabled timer
   folding a unit reads as no timer at all, and matching a service name
   out of its output is a second implementation of a relation systemd
   publishes per unit.  ``get_unit_status``' own comment records the same
   rule for ``Unit=`` — systemd does not require a timer's name to
   correspond to the service it starts (``SNAG-SYSD-005``).

5. **The positive control is derived from the file, per scope, and never
   hard-coded.**  A negative control shows the reader can say
   *not-found*; it says nothing about whether the reader can see a timer
   **relation**, which is the negative the uniqueness half believes.  The
   control is therefore a ``kind: timer`` entry of this same file, in the
   same scope, whose service must report its timer back — and the scopes
   required are computed from the partition, so a user-scope standalone
   oneshot arriving widens the premise by itself.  Any witness in the
   scope will do: the premise asks whether the reader discriminates, not
   whether one particular timer is healthy, so it must not key on a
   positionally-selected member.

6. **Membership is pinned and the residue is stated rather than
   implied.**  :data:`STANDALONE_ONESHOT_SERVICES` is the only place the
   pair is written here, and it is the shape
   ``tests/test_services_registry.py``'s ``DECLARED_JSON_SOURCES``
   already uses on the same file: hand-written *so that adding one costs
   a measurement*.  What it cannot do is notice a sitting that updates
   this constant and leaves the prose beside ``ethernet-optimise``
   saying *"there are two"* — the two statements can drift in that one
   direction, and the failure messages below name both comment sites for
   that reason.  Closing it would mean parsing the sentence, which
   rule's-worth of refusal is ``SNAG-ESTATE-012``'s above.

**What is deliberately not asserted**, so its silence is not read as
health.  A ``kind: systemd`` entry naming a unit nothing enables declares
a check that fails on every poll for ever — ``SNAG-UNITS-004``'s rule,
which ``units/recommendations.py`` already refuses to *create*.  The
population is uniform today (**9 of 9** ``kind: systemd`` units read
``UnitFileState=enabled``, measured 2026-09-13) and the rule is not
simply "enabled": ``static`` is legitimate for a unit pulled up by
another's ``Requires=``, and ``venture-chat-large`` is ``static`` here
under ``kind: static``.  Judging which enablement states a ``kind``
admits is a wider guard than this entry asked for and belongs beside the
sweep that already classifies units, not here.
"""

from __future__ import annotations

import subprocess
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from sysadmin.monitor.services import ServiceEntry, ServicesFile, load_services
from sysadmin.monitor.systemd import (
    SystemdQueryError,
    _base_cmd,
    build_env,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_SERVICES_YAML = REPO_ROOT / "services.yaml"

#: ``LoadState`` for a unit systemd has never heard of, and ``LoadState``
#: for one it has.  Written here rather than imported because they are
#: systemd's words and not this repository's, and the pair is the whole
#: discrimination the premise rests on.
NOT_FOUND = "not-found"
LOADED = "loaded"

#: ``Type=`` and ``RemainAfterExit=`` for a service that does its work
#: once and then reports ``active (exited)`` for ever.  That combination
#: is what makes ``kind: systemd`` a real check on a oneshot — inactive
#: means the work is not in force — and it is why neither of the two
#: below is folded under a timer the way ``paccache`` is.
ONESHOT_TYPE = "oneshot"
REMAINS_AFTER_EXIT = "yes"

#: The ``services.yaml`` entries whose units are ``Type=oneshot`` with
#: ``RemainAfterExit=yes`` and no timer to fold them under, **hand-written
#: so that a third one costs a measurement**.  Keyed on the service
#: ``name`` because that is one per entry and a unit name is not:
#: ``deadlock-api-ingest.service`` is declared in both scopes, and scope
#: is part of a unit's identity here.
#:
#: This is the set ``services.yaml`` asserts in prose in **two** places —
#: the ``ethernet-optimise`` entry's *"There are two, and the
#: counterexample was already 250 lines above it in this same file"* and
#: the ``estate-broker-provision`` entry above it.  A name added or
#: removed here without those sentences moving is the drift rule 6 of
#: this module's docstring records and cannot close.
STANDALONE_ONESHOT_SERVICES = frozenset(
    {
        "estate-broker-provision",
        "ethernet-optimise",
    }
)


@dataclass(frozen=True)
class UnitReading:
    """What systemd said about one unit, or why there is nothing to read.

    :class:`sysadmin.ops_claims.UnitState`'s shape and for its reason:
    ``systemctl show`` exits ``0`` for a unit that does not exist, so
    "nobody could ask" and "asked, and it is absent" are different facts
    and a reader that returns a bare dict cannot tell them apart.
    ``problem`` is non-empty only for the first.
    """

    unit: str
    scope: str
    properties: Mapping[str, str] = field(default_factory=dict)
    problem: str = ""

    @property
    def measured(self) -> bool:
        return not self.problem

    def prop(self, name: str) -> str:
        """One property, or ``""`` — which systemd also returns for an absent unit."""
        return self.properties.get(name, "")

    @property
    def installed(self) -> bool:
        """Whether systemd holds a unit file for this name.

        Both limbs, because they fail in different directions.
        ``LoadState`` is the gate every consumer in this repository
        already uses and is what turns ``masked`` and ``not-found`` into
        the same refusal; ``UnitFileState`` is the field
        ``SNAG-DOCS-027`` names, and it is empty for a unit with no unit
        file at all — a state that cannot be enabled, disabled, or
        reasoned about by anything reading this file.
        """
        return self.prop("LoadState") == LOADED and bool(self.prop("UnitFileState"))

    def __str__(self) -> str:
        if not self.measured:
            return f"{self.unit} ({self.scope}): {self.problem}"
        rendered = ", ".join(f"{k}={v!r}" for k, v in sorted(self.properties.items()))
        return f"{self.unit} ({self.scope}): {rendered}"


def read_unit(unit: str, scope: str, properties: Sequence[str]) -> UnitReading:
    """``systemctl show`` for one unit in one scope, as data.

    **The scope machinery is imported rather than restated.**
    :func:`~sysadmin.monitor.systemd._base_cmd` is the one statement of
    how a scope reaches ``systemctl`` and
    :func:`~sysadmin.monitor.systemd.build_env` carries ``SNAG-SYSD-001``
    — a ``--user`` call from a process with no ``XDG_RUNTIME_DIR``
    cannot reach the session bus, and the empty output it returns was
    once read as *"the unit is not active"* and reported a healthy timer
    as ``critical``.  A test that spelled ``["systemctl", "--user"]`` for
    itself would be free to disagree with production about which manager
    it asked, which is the fault it exists to detect wearing the clothes
    of a harness.

    The properties are *not* taken from
    :func:`~sysadmin.monitor.systemd.get_unit_status`, which reads eleven
    of them and none of these four.  Widening production's per-poll
    invocation to serve a guard is the direction that comment already
    refuses for ``--timestamp=unix``: the flag is a *command* flag, so
    asking for one more thing changes what every other consumer is
    handed.
    """
    try:
        env = build_env(scope == "user")
    except SystemdQueryError as exc:
        return UnitReading(unit, scope, problem=f"unmeasured ({exc})")
    command = [
        *_base_cmd(scope == "user"),
        "show",
        unit,
        *[argument for name in properties for argument in ("-p", name)],
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False, env=env
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return UnitReading(unit, scope, problem=f"unmeasured ({exc.__class__.__name__})")
    if result.returncode != 0:
        # Not the absent case: ``show`` exits 0 for a unit that does not
        # exist, so a non-zero status really does mean the query failed.
        return UnitReading(
            unit,
            scope,
            problem=f"unmeasured (systemctl exited {result.returncode}: "
            f"{result.stderr.strip() or 'no output'})",
        )
    parsed = dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )
    if not parsed:
        return UnitReading(unit, scope, problem="unmeasured (systemctl printed no properties)")
    return UnitReading(unit, scope, {k: v.strip() for k, v in parsed.items()})


#: Everything read about a declared unit, in one pass.  ``TriggeredBy``
#: is asked of every unit rather than only of the oneshots for
#: ``get_unit_status``' reason: systemctl omits properties that do not
#: apply, so asking costs nothing and a second call per unit would double
#: a subprocess count this file is otherwise careful about (31 units at
#: ~3 ms each, measured 2026-09-13).
UNIT_PROPERTIES = ("LoadState", "UnitFileState", "Type", "RemainAfterExit", "TriggeredBy")


def declared_entries(services: ServicesFile) -> list[ServiceEntry]:
    """Every entry that names a systemd unit, whatever its ``kind``.

    Wider than the ``kind: systemd`` population on purpose: a declared
    unit that does not exist is a fault for a timer and for an ``http``
    entry too, since both assert the unit when one is named.
    ``monitor: false`` entries are **in**, because that flag suppresses
    *checking* and not the declaration — a suppressed entry naming a unit
    nobody installed is the shape ``SNAG-DOCS-027`` is about, with the
    one reader that would have noticed switched off.
    """
    return [entry for entry in services.services if entry.systemd]


def checked_service_units(services: ServicesFile) -> list[ServiceEntry]:
    """The ``kind: systemd`` entries naming a ``.service``.

    The population the uniqueness sentence scopes itself to, computed
    from the file rather than counted into a constant.  The sentence says
    *"the nine"*; the nine is **not** pinned, because a count is
    arithmetic nobody can check and ``SNAG-DOCS-026`` is what a dated
    figure costs.  What is pinned is the partition inside it.
    """
    return [
        entry
        for entry in services.services
        if entry.kind == "systemd" and entry.systemd and entry.systemd.unit.endswith(".service")
    ]


def timer_entries(services: ServicesFile) -> list[ServiceEntry]:
    """The ``kind: timer`` entries — rule 5's controls, before resolution."""
    return [entry for entry in services.services if entry.kind == "timer" and entry.systemd]


def is_standalone_oneshot(reading: UnitReading) -> bool:
    """``Type=oneshot`` + ``RemainAfterExit=yes`` + nothing triggers it.

    Conjunction, and the third limb is why :meth:`UnitReading.installed`
    has to have been asserted first: an absent unit satisfies it
    vacuously, reporting ``TriggeredBy=''`` exactly as a real untriggered
    unit does.
    """
    return (
        reading.prop("Type") == ONESHOT_TYPE
        and reading.prop("RemainAfterExit") == REMAINS_AFTER_EXIT
        and not reading.prop("TriggeredBy")
    )


@pytest.fixture(scope="module")
def services() -> ServicesFile:
    return load_services(LIVE_SERVICES_YAML)


@pytest.fixture(scope="module")
def readings(services: ServicesFile) -> dict[str, UnitReading]:
    """One reading per declared entry, keyed on the service ``name``."""
    return {
        entry.name: read_unit(entry.systemd.unit, entry.systemd.scope, UNIT_PROPERTIES)
        for entry in declared_entries(services)
    }


@pytest.mark.premise
class TestThePremises:
    """Neither guard below means anything without these.

    The order is the order of the failures they exclude: a file that
    declares nothing satisfies both sweeps vacuously; a ``systemctl``
    that has stopped answering satisfies them in a way that looks
    identical to health; and a reader that cannot see a timer relation
    reports every unit on the box as unfolded.
    """

    def test_the_file_declares_units_to_read(self, services: ServicesFile):
        declared = declared_entries(services)
        checked = checked_service_units(services)
        assert declared, (
            f"{LIVE_SERVICES_YAML} declares no systemd units, so the installedness "
            "sweep below is vacuous — an emptied file is not a clean one"
        )
        assert checked, (
            f"{LIVE_SERVICES_YAML} has no kind: systemd .service entries, so the "
            "partition below is computed over nothing and would report the named "
            "pair missing for a reason that has nothing to do with the box"
        )

    def test_an_absent_unit_is_indistinguishable_from_an_untriggered_one(self):
        """The negative control, and it measures the trap rather than asserting it.

        A name minted per call rather than a retired one that is known to
        be absent today: a witness must be unwritable, and a control
        somebody could install is a control that stops discriminating
        without saying so.

        The second half is the one this file is built around.  ``show``
        exits ``0`` for the minted name and reports ``TriggeredBy=''``,
        which is byte-identical to what a real unit with no timer
        reports — so *"nothing folds this oneshot"* read off an absent
        unit is zero-because-blind, and the installedness sweep has to
        run first.  If systemd ever distinguishes the two, this premise
        fails and the gate in
        :meth:`TestTheStandaloneOneshotsAreTheNamedPair.test_neither_named_oneshot_is_folded_under_a_timer`
        is doing work it no longer needs to.
        """
        minted = f"sysadmin-guard-{uuid.uuid4().hex}.service"
        for scope in ("system", "user"):
            reading = read_unit(minted, scope, UNIT_PROPERTIES)
            assert reading.measured, (
                f"systemctl would not answer for {minted} in {scope} scope "
                f"({reading.problem}), so a clean sweep below would be "
                "zero-because-blind rather than zero-because-clean"
            )
            assert reading.prop("LoadState") == NOT_FOUND, (
                f"a name minted this second reads {reading} rather than "
                f"{NOT_FOUND!r} — the reader has stopped discriminating, and every "
                "assertion below rests on it being able to say a unit is absent"
            )
            assert not reading.prop("UnitFileState"), (
                f"{reading} — an absent unit reports a UnitFileState, so the "
                "installedness sweep below can no longer read an empty one as "
                "'systemd holds no unit file for this name'"
            )
            assert not reading.prop("TriggeredBy"), (
                f"{reading} — an absent unit now reports a triggering timer, which "
                "this file's third rule says is impossible. The gate ordering below "
                "was built on the two readings being indistinguishable."
            )

    def test_a_timer_relation_is_visible_in_every_scope_asserted(
        self, services: ServicesFile, readings: dict[str, UnitReading]
    ):
        """The positive control: rule 5, derived from the file per scope.

        The scopes are the ones the uniqueness half actually believes a
        negative in — the scopes of the named pair — so a user-scope
        standalone oneshot arriving widens this premise with no edit
        here.  Any ``kind: timer`` entry in the scope is an acceptable
        witness: the question is whether the reader can see a timer
        relation at all, not whether one particular schedule is healthy,
        and keying on a positionally-selected member would make the
        premise fail for a reason about that timer.
        """
        scopes = {
            readings[name].scope for name in STANDALONE_ONESHOT_SERVICES if name in readings
        }
        assert scopes, (
            "none of the named standalone oneshots is declared in "
            f"{LIVE_SERVICES_YAML}, so there is no scope to control for — which the "
            "partition test below reports as the fault it is"
        )
        for scope in sorted(scopes):
            witnesses: list[str] = []
            for entry in timer_entries(services):
                if entry.systemd.scope != scope:
                    continue
                timer = read_unit(entry.systemd.unit, scope, ("Unit",))
                started = timer.prop("Unit")
                if not started:
                    continue
                # ``Unit=`` is asked of the timer rather than derived by
                # swapping the suffix: systemd does not require the two
                # names to correspond (SNAG-SYSD-005).
                service = read_unit(started, scope, ("TriggeredBy",))
                if service.prop("TriggeredBy"):
                    witnesses.append(f"{entry.systemd.unit} -> {started}")
            assert witnesses, (
                f"no kind: timer entry in {scope} scope could be shown to trigger "
                "anything, so 'nothing folds this oneshot' is a negative read by a "
                "reader that has never been seen to report a timer relation. Either "
                f"{LIVE_SERVICES_YAML} declares no timer in this scope, or "
                "TriggeredBy has stopped answering."
            )


class TestEveryDeclaredUnitIsInstalled:
    """``SNAG-DOCS-027``'s ``estate-broker-provision`` half, widened to the file.

    That entry's sentence — *"the unit is not yet installed and this
    check will rightly complain"* — was true for the few hours between
    being written on 2026-08-11 and the install script being run the next
    morning, and false for the **32 days** after it.  What makes it worth
    a guard rather than a correction is that the sentence had named its
    own expiry condition: its author had already reasoned about the flip
    and still left no reader.
    """

    def test_every_declared_unit_is_installed(self, readings: dict[str, UnitReading]):
        unmeasured = sorted(
            str(reading) for reading in readings.values() if not reading.measured
        )
        assert not unmeasured, (
            f"systemd would not answer for {unmeasured} — reported rather than "
            "skipped, because a unit nobody could ask about is not a unit that "
            "resolved (ports_checked's rule)"
        )
        absent = sorted(str(reading) for reading in readings.values() if not reading.installed)
        assert not absent, (
            f"{LIVE_SERVICES_YAML} declares units this box does not hold: {absent}. "
            "A check on a unit systemd has never heard of fails on every poll for "
            "ever, and systemctl show exits 0 for it, so nothing else in this "
            "repository would say so. Either install the unit, or delete the entry "
            "— and if a comment beside it explains that the unit is not installed "
            "yet, that comment is SNAG-DOCS-027's class and needs a date on it."
        )


class TestTheStandaloneOneshotsAreTheNamedPair:
    """``SNAG-DOCS-027``'s ``ethernet-optimise`` half: the uniqueness claim.

    Until 2026-09-13 that entry read *"Note this is the one oneshot on
    the box with no timer that is still monitorable, which is why it is
    not folded"*.  It was written 2026-08-15 in ``82b8824``, four days
    after ``estate-broker-provision`` — ``Type=oneshot``,
    ``RemainAfterExit=yes``, no timer, ``kind: systemd`` — had been added
    250 lines above it, so the sentence was **false on the day it was
    written** and nothing re-read it for a month.
    """

    def test_the_partition_is_exactly_the_pair_the_file_names(
        self, services: ServicesFile, readings: dict[str, UnitReading]
    ):
        """The census, which is the claim.  The property test below is the reason.

        Computed over the ``kind: systemd`` ``.service`` entries the file
        itself supplies, so a third standalone oneshot declared anywhere
        in it turns this red and sends the next reader to the two
        sentences that say there are two.
        """
        population = checked_service_units(services)
        unmeasured = sorted(
            str(readings[entry.name])
            for entry in population
            if not readings[entry.name].measured
        )
        assert not unmeasured, (
            f"systemd would not answer for {unmeasured}, so the partition below "
            "would be computed from a reader that answered nothing — an empty "
            "partition read as a census"
        )
        standalone = {
            entry.name for entry in population if is_standalone_oneshot(readings[entry.name])
        }
        assert standalone == set(STANDALONE_ONESHOT_SERVICES), (
            f"services.yaml's kind: systemd .service entries hold {sorted(standalone)} "
            f"as Type=oneshot + RemainAfterExit=yes with no triggering timer, and "
            f"this file names {sorted(STANDALONE_ONESHOT_SERVICES)}. Two comments in "
            "services.yaml assert the membership in prose — the ethernet-optimise "
            "entry's 'There are two, and the counterexample was already 250 lines "
            "above it' and the estate-broker-provision entry above it — so a change "
            "here that leaves those sentences alone rebuilds SNAG-DOCS-027 exactly: "
            "a uniqueness claim falsified by an edit its author will never revisit. "
            f"Readings: { {e.name: str(readings[e.name]) for e in population} }"
        )

    def test_neither_named_oneshot_is_folded_under_a_timer(
        self, readings: dict[str, UnitReading]
    ):
        """The *reason* ``kind: systemd`` is right for these two.

        A oneshot with a timer is reported under its **timer** — the half
        carrying ``[Install]`` — because the service is ``inactive
        (dead)`` between runs by design and a ``kind: systemd`` check on
        it would alert continuously.  ``services.yaml``'s own header
        records that rule and ``ethernet-optimise``'s comment invokes it:
        *"It is not folded because there is no timer to fold it under"*.
        A timer arriving for either unit makes the entry's ``kind`` wrong
        and the sentence with it.

        Stated apart from the census above because the two refute in
        different directions: the census dies when a **third** unit
        arrives, and this dies when one of **these two** gains a
        schedule, and a single assertion would report either as the
        other.
        """
        for name in sorted(STANDALONE_ONESHOT_SERVICES):
            reading = readings.get(name)
            assert reading is not None, (
                f"{name} is no longer declared in {LIVE_SERVICES_YAML}; the census "
                "test above is the one that should be read first"
            )
            assert reading.measured, f"systemd would not answer for {reading}"
            assert reading.installed, (
                f"{reading} — an absent unit reports TriggeredBy='' just as an "
                "untriggered one does, so this assertion would pass by being blind"
            )
            assert not reading.prop("TriggeredBy"), (
                f"{reading} is now triggered by a timer, so services.yaml's "
                f"'{name} … is not folded because there is no timer to fold it "
                "under' is false and the entry's kind: systemd will alert on every "
                "poll between runs. Fold it: make the entry kind: timer naming the "
                "timer, which is the half that carries [Install]."
            )
