"""The briefing producer's ``data`` field names are additive, and this says so.

:mod:`tests.test_briefing_sections_are_additive` holds a ledger of section
**titles** and argues, at length, that a practice is not a constraint.  One
level down there was nothing, and the gap is not symmetric with the one it
closed: a consumer has *no* defence against a title that stops arriving and
therefore fails loudly-ish, while it has a documented defence against a field
that stops arriving and therefore fails **silently**.  Measured in Alfred's
tree on 2026-09-20:

``backend/alfred/services/briefings.py`` reads
``data.get("all_ok", data.get("all_services_healthy"))`` and falls to ``None``,
and reads ``data.get("entries")`` then ``data.get("services", [])`` and falls to
``[]`` — which renders as ``status="empty"``.  So renaming a key inside
``Infrastructure Status``'s ``data`` reddens nothing at runtime, and reddens
Alfred's own suite only *after* somebody refreshes its capture.  Between those
two moments production quietly loses ``all_ok``, which is in Alfred's
``frontend/types/api.ts``.

**The two ledgered sections break differently and the ledger records which.**
This was measured rather than assumed, and it is the finding that shaped the
file:

``status_grid``
    Field names are a **vocabulary Alfred looks up by name**, with the two
    fallbacks quoted above.  A rename is silently *dropped*.

``metrics``
    Field names are passed through verbatim —
    ``metrics = {str(k): coerce_cell(v) for k, v in data.items()}`` — and
    ``frontend/components/digest/DigestMetrics.vue`` states in writing that
    "the field set is open", humanising each key generically rather than
    mapping it.  A rename is silently *relabelled*: the value survives and the
    heading a reader sees changes.  A **removal** still loses the cell.

Both are quiet, so both are ledgered; the remedies differ, so
:data:`SECTION_FIELDS` carries the reading rather than leaving a later sitting
to infer that the two are alike.

**Four of the six sections cannot be pinned here and must not be made to.**
:data:`UNPINNED_SECTIONS` records why, per section, because a sitting that
reads "each section" and walks the whole producer will find them and try.  The
``Filesystem`` case is the instructive one and it is measured, not argued:
driven through the sibling's own fixture the producer renders that section's
``data`` as ``['total_mb']`` — a key ``render_sections`` never names and
``_gather_filesystem`` never returns.  It arrived from the fixture, because the
section builds its dict by comprehension over ``gathered["filesystem"]``.  A
rendered-keys assertion there would pin the fixture and pass over anything the
producer did, which is the circularity the sibling's
``test_the_fixture_supplies_every_key_the_producer_reads`` exists to prevent,
arriving one level down.

That is also why :class:`TestTheLedgeredSectionsSpellTheirFieldsInTheProducer`
exists: the guard proper reads **rendered** keys, which is only honest while
the producer spells those keys as literals.  The day one of the two becomes a
comprehension, the guard would silently stop measuring the producer and start
measuring the fixture — passing throughout.  That premise is the tripwire.

**The history walk has a real population and no departure in it.**  Walking
all 15 commits that have touched the producer under both of its paths, three
titles have ever carried literal ``data`` keys — ``Infrastructure Status``
(``all_services_healthy``, ``services``, unchanged since 2026-02-06),
``Overnight Logs`` (``Entries``, ``Errors``, ``Sources``, unchanged since it
was born on 2026-08-24) and ``Filesystem``.  **No field has ever left either
ledgered section**, so :data:`RETIRED_FIELDS` is empty *by measurement* rather
than by oversight, and :class:`TestARetirementNamesWhatCarriedIt` is driven at
a synthetic so an empty population cannot make it vacuously green.

``Filesystem``'s five names are the walk's one apparent departure and are **not
a departure**: they left ``render_sections`` on 2026-08-11 when the section
became a comprehension, and ``_gather_filesystem`` returns all five to this
day.  It is the ``SNAG-BRIEF-005`` shape one level down — a name that stops
being *spelled* looks exactly like a name that stops being *served* — and it is
what :class:`TestTheWalkIsNotVacuous` uses to prove the walk reads history at
all, since neither ledgered section offers a field the producer no longer
spells.

What that costs is recorded as ``SNAG-BRIEF-006`` rather than left to be
found: ``Filesystem``'s five published names are pinnable, but only from
``_gather_filesystem``'s literal return dict **minus the comprehension's own
``measured_at`` filter** — and restating that filter here would be a second
statement of a rule the producer owns, which is the shape this repository
names ``SNAG-DB-003``.

**This file has a ceiling and a floor, and the floor was filed as the measured
limit of the ceiling.**  Everything above the floor banner is driven at a
payload built to make every conditional in the producer true, so it says what
a section *can* publish.  ``SNAG-BRIEF-007`` recorded that the other question
— what a consumer receives on a morning when nothing was gathered — looked
answered by composing this ledger with the sibling's ``FLOOR_TITLES`` and was
not, because this half reads its keys back **off a render**, which is honest
only while the producer spells them as literals.  Driven 2026-09-22 rather
than argued: turning ``Overnight Logs``' ``data`` into a comprehension leaves
the sibling module **entirely green**, 21 passed, while reddening three tests
here — the composition failing in the one direction it was offered to cover.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from sysadmin.briefing.data import render_sections
from tests.test_briefing_sections_are_additive import (
    FLOOR_TITLES,
    PRODUCER_PATHS,
    _every_branch_taken,
    _nothing_gathered,
)

REPO = Path(__file__).resolve().parent.parent

#: What a rename of one of this section's field names costs at the consumer.
#: Both readings were measured in Alfred's tree on 2026-09-20 and are quoted
#: in this module's docstring; the closed set exists so that a third section
#: cannot be ledgered without somebody going and looking.
RENAME_READINGS = ("dropped", "relabelled")


class FieldSet(NamedTuple):
    """One ledgered section's published field names, in render order.

    ``on_rename`` is one of :data:`RENAME_READINGS` and ``note`` names the
    consumer code that produces that reading — prose rather than a path
    constant, for :data:`RETIRED_FIELDS`' reason in the sibling module: what a
    reader needs is the thing to go and read.
    """

    fields: tuple[str, ...]
    on_rename: str
    note: str


#: Every ``data`` field name this producer spells as a literal, by section.
#: **A name leaving this ledger is a change to a published surface**, and the
#: estate rule for one of those is a filing at the measured readers before the
#: commit that carries it — which for this seam is Alfred, whose ADR-0063 owns
#: the section contract.  Renaming is not cheaper than removing here: at the
#: consumer a rename *is* a removal plus an addition, and the addition is the
#: half nothing reads.
SECTION_FIELDS = {
    "Infrastructure Status": FieldSet(
        fields=("all_services_healthy", "services"),
        on_rename="dropped",
        note=(
            "Alfred renames both into its own vocabulary and falls back to "
            "ours: `backend/alfred/services/briefings.py` reads "
            '`data.get("all_ok", data.get("all_services_healthy"))` -> None '
            'and `data.get("entries")` then `data.get("services", [])` -> [], '
            'which renders `status="empty"`. `all_ok` is in Alfred\'s '
            "`frontend/types/api.ts`, so the loss reaches the page"
        ),
    ),
    "Overnight Logs": FieldSet(
        fields=("Entries", "Errors", "Sources"),
        on_rename="relabelled",
        note=(
            "a `metrics` section's keys are passed through verbatim by "
            "Alfred's `_build_section` and humanised generically by its "
            "`frontend/components/digest/DigestMetrics.vue`, which states "
            "that the field set is open. The value survives a rename and the "
            "reader's heading changes; a removal still loses the cell"
        ),
    ),
}

#: Field names this producer has published and no longer publishes, each
#: mapped to the announcement that carried the departure — the sibling's
#: ``RETIRED_TITLES`` one level down.  **Empty by measurement**: the walk in
#: :func:`history` reads 15 commits and finds no field ever spelled for a
#: ledgered section that is not spelled for it today.  Emptiness is stated
#: here rather than left as silence, because a reader cannot otherwise tell it
#: from nobody having looked.
RETIRED_FIELDS: dict[tuple[str, str], str] = {}

#: The sections whose field names this guard cannot reach, and why.  Not a
#: backlog: three of the four have no field names *at all*, and pinning the
#: fourth would restate a rule the producer owns.  The totality test below
#: makes adding a section a decision between this map and
#: :data:`SECTION_FIELDS` rather than a silent omission.
UNPINNED_SECTIONS = {
    "Filesystem": (
        "builds its `data` by comprehension over `gathered['filesystem']`, so "
        "the rendered keys are data rather than source — driven through the "
        "sibling's fixture it renders `['total_mb']`, a key the producer "
        "never names. The five real names are literals in "
        "`_gather_filesystem`, but the published set is those minus the "
        "comprehension's own `measured_at` filter, and restating that filter "
        "here would be a second statement of a rule the producer owns "
        "(SNAG-BRIEF-006)"
    ),
    "Weekly Log Review": (
        "a `text` section: `data` is the bare narrative string, so there are "
        "no field names to publish or retire"
    ),
    "Weekly Disk Review": (
        "a `text` section: `data` is the bare narrative string, so there are "
        "no field names to publish or retire"
    ),
    "Weekly System Health Review": (
        "a `text` section: `data` is the bare narrative string, so there are "
        "no field names to publish or retire"
    ),
}


def _rendered() -> list[dict[str, Any]]:
    """The producer driven at the payload that takes every branch.

    The fixture is **imported** from the sibling rather than restated: five of
    the six sections sit behind an ``if``, that module already derives the keys
    they gate from the producer, and a second copy here is a second statement
    of what the producer reads.
    """
    return render_sections(_every_branch_taken())


def _producer_function() -> ast.FunctionDef:
    source = ast.parse((REPO / PRODUCER_PATHS[0]).read_text())
    return next(
        node
        for node in ast.walk(source)
        if isinstance(node, ast.FunctionDef) and node.name == "render_sections"
    )


def _section_dicts_in_source() -> dict[str, ast.AST]:
    """``{title literal: the AST node its "data" key is bound to}``.

    Only sections whose ``title`` is spelled as a literal are reachable, which
    is every section today and is ``SNAG-BRIEF-005``'s known limit restated
    one level down.
    """
    found: dict[str, ast.AST] = {}
    for node in ast.walk(_producer_function()):
        if not isinstance(node, ast.Dict):
            continue
        title = data = None
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant):
                continue
            if key.value == "title" and isinstance(value, ast.Constant):
                title = value.value
            elif key.value == "data":
                data = value
        if isinstance(title, str) and data is not None:
            found[title] = data
    return found


def _fields_at(sha: str) -> dict[str, tuple[str, ...]] | None:
    """``{title: literal "data" keys}`` as the producer held them at ``sha``.

    ``None`` when the file is at neither path or will not parse, which is
    skipped rather than failed: a commit predating the module is not evidence
    about field names.
    """
    for path in PRODUCER_PATHS:
        shown = subprocess.run(
            ["git", "show", f"{sha}:{path}"],
            capture_output=True,
            text=True,
            cwd=REPO,
        )
        if shown.returncode != 0:
            continue
        try:
            tree = ast.parse(shown.stdout)
        except SyntaxError:  # pragma: no cover - no such commit today
            return None
        found: dict[str, tuple[str, ...]] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            title = data = None
            for key, value in zip(node.keys, node.values):
                if not isinstance(key, ast.Constant):
                    continue
                if key.value == "title" and isinstance(value, ast.Constant):
                    title = value.value
                elif key.value == "data":
                    data = value
            if not isinstance(title, str) or not isinstance(data, ast.Dict):
                continue
            keys = tuple(
                k.value
                for k in data.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            )
            if keys:
                found[title] = keys
        return found
    return None


@pytest.fixture(scope="module")
def history() -> tuple[int, dict[str, set[str]]]:
    """``(commits parsed, {title: every field name ever spelled for it})``.

    ``--follow`` is taken newest-first and reversed in Python for the sibling's
    reason: git documents it as unreliable with ``--reverse`` and here it
    returns one commit instead of fifteen, which looks like a young file rather
    than like an error.
    """
    if not (REPO / ".git").exists():  # pragma: no cover - always a checkout here
        pytest.skip("not a git checkout, so the producer has no history to read")
    log = subprocess.run(
        ["git", "log", "--follow", "--format=%H", "--", PRODUCER_PATHS[0]],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    ).stdout.split()
    ever: dict[str, set[str]] = {}
    parsed = 0
    for sha in log:
        at = _fields_at(sha)
        if at is None:
            continue
        parsed += 1
        for title, fields in at.items():
            ever.setdefault(title, set()).update(fields)
    return parsed, ever


# --------------------------------------------------------------------------
# The premises


class TestTheWalkIsNotVacuous:
    """A walk that found nothing agrees with every ledger, including a wrong
    one.  These pin that it looked, and that it looked at *history*."""

    def test_it_reaches_the_renamed_half_of_the_history(
        self, history: tuple[int, dict[str, set[str]]]
    ) -> None:
        parsed, _ = history
        assert parsed >= 15, (
            f"the walk parsed {parsed} commits; it parsed 15 on 2026-09-20 and "
            "the count only grows, so a smaller number means --follow stopped "
            "at the 2026-08-13 rename and the guard is reading a third of the "
            "history it believes it is reading"
        )

    def test_it_sees_a_field_set_the_producer_no_longer_spells(
        self, history: tuple[int, dict[str, set[str]]]
    ) -> None:
        """The sibling proves its walk reads history by finding a title no
        longer served.  No *field* has ever left a ledgered section, so this
        guard has no such specimen and borrows ``Filesystem``'s instead: its
        five names left ``render_sections`` on 2026-08-11 when the section
        became a comprehension, and are served by ``_gather_filesystem`` to
        this day.  A departure the walk cannot distinguish from an artefact is
        still proof that it is not reading the working tree.
        """
        _, ever = history
        live = _section_dicts_in_source()
        unspelled = {
            title: names
            for title, names in ever.items()
            if not isinstance(live.get(title), ast.Dict)
        }
        assert unspelled, (
            "every field set the walk found is still spelled in the producer, "
            "so the walk cannot be shown to read anything but the working "
            "tree and would pass over a field that was removed before HEAD. "
            "This reddens on an *improvement* as well as on a regression: "
            "giving Filesystem its literals back would make it ledgerable "
            "and take away this guard's only specimen at the same moment. "
            "The move then is to ledger that section and find the walk a new "
            "premise, never to delete this one"
        )


class TestTheLedgeredSectionsSpellTheirFieldsInTheProducer:
    """The guard proper reads **rendered** keys, which is honest only while
    those keys are literals in the source.

    Turn either ledgered section's ``data`` into a comprehension and the
    rendered keys start arriving from the fixture — the guard would go on
    passing while measuring nothing about the producer, which is exactly what
    ``Filesystem`` does today.  Without this premise that change is invisible.
    """

    @pytest.mark.parametrize("title", sorted(SECTION_FIELDS))
    def test_its_data_is_a_dict_of_string_literals(self, title: str) -> None:
        data = _section_dicts_in_source().get(title)
        assert isinstance(data, ast.Dict), (
            f"{title!r}'s `data` is not a dict literal in render_sections, so "
            "the rendered keys below come from the fixture rather than from "
            "the producer and the ledger has stopped measuring anything. "
            "Either restore the literals or move the section to "
            "UNPINNED_SECTIONS with the reason, as Filesystem is"
        )
        assert data.keys and all(
            isinstance(k, ast.Constant) and isinstance(k.value, str)
            for k in data.keys
        ), (
            f"{title!r} builds at least one `data` key from something other "
            "than a string literal, so that key is invisible to the history "
            "walk and its departure would be as quiet as the thing this guard "
            "exists to prevent (SNAG-BRIEF-005, one level down)"
        )


class TestTheFixtureRendersEveryLedgeredSection:
    def test_both_halves_of_the_ledger_are_reachable(self) -> None:
        """A ledger entry for a section the fixture never renders is asserted
        by nothing, and the assertion below would pass by absence."""
        rendered = {section["title"] for section in _rendered()}
        missing = set(SECTION_FIELDS) - rendered
        assert not missing, (
            f"{sorted(missing)} are ledgered and were not rendered, so the "
            "fixture does not take the branch that serves them and their "
            "field names are pinned by nothing"
        )


# --------------------------------------------------------------------------
# The guard


class TestTheProducerServesExactlyTheLedger:
    @pytest.mark.parametrize("title", sorted(SECTION_FIELDS))
    def test_the_fields_and_their_order(self, title: str) -> None:
        """Order is asserted as well as membership.  A ``metrics`` section's
        keys reach the reader as a figure grid in the order they arrive —
        ``DigestMetrics.vue`` renders ``Object.entries(data)`` — so reordering
        is visible on the page even where it breaks no lookup.
        """
        section = next(s for s in _rendered() if s["title"] == title)
        served = tuple(section["data"])
        assert served == SECTION_FIELDS[title].fields, (
            f"{title!r}'s published field names have moved: served {served!r} "
            f"against the ledger's {SECTION_FIELDS[title].fields!r}. Adding "
            "one: add it to SECTION_FIELDS. Removing or renaming one: record "
            "it in RETIRED_FIELDS with the announcement that carried it — and "
            "file that announcement at Alfred first, because "
            f"{SECTION_FIELDS[title].on_rename} is what its consumer does "
            "with a name it does not recognise, silently and in production"
        )


class TestHistoryHoldsNoFieldTheLedgerForgot:
    """The half that makes a quiet deletion impossible.

    Dropping a name from :data:`SECTION_FIELDS` alone is caught above, because
    the producer still serves it.  Dropping it from both halves is caught here,
    because git still holds the commit that published it.
    """

    @pytest.mark.parametrize("title", sorted(SECTION_FIELDS))
    def test_every_field_ever_published_is_accounted_for(
        self, title: str, history: tuple[int, dict[str, set[str]]]
    ) -> None:
        _, ever = history
        # may-not-turn: RETIRED_FIELDS is empty by measurement — no field has
        # ever left either ledgered section across the producer's whole
        # history — so this filter runs over nothing and empty is the
        # healthy state.  The subtraction below is the measurement; this
        # comprehension is only the exemption it applies, and it arms
        # itself the day a retirement is recorded.
        retired = {field for (section, field) in RETIRED_FIELDS if section == title}
        forgotten = ever.get(title, set()) - set(SECTION_FIELDS[title].fields) - retired
        assert not forgotten, (
            f"{sorted(forgotten)} were published under {title!r} and are in "
            "neither half of the ledger. A field name does not stop having "
            "been published by being deleted from the file"
        )

    def test_the_two_halves_do_not_overlap(self) -> None:
        both = {
            (title, field)
            for title, entry in SECTION_FIELDS.items()
            for field in entry.fields
        } & set(RETIRED_FIELDS)
        assert not both, (
            f"{sorted(both)} are both served and retired; a returning field "
            "name is an addition and leaves the retired half"
        )


class TestEverySectionIsPinnedOrExcused:
    """Totality, so that adding a section is a decision rather than an
    omission.

    Without it a seventh section with literal ``data`` keys would be published
    unledgered and this file would stay green — the shape the sibling's
    history half exists to refuse, at the level of the section rather than the
    title.
    """

    def test_the_partition_is_total(self) -> None:
        rendered = {section["title"] for section in _rendered()}
        unaccounted = rendered - set(SECTION_FIELDS) - set(UNPINNED_SECTIONS)
        assert not unaccounted, (
            f"{sorted(unaccounted)} are served and appear in neither "
            "SECTION_FIELDS nor UNPINNED_SECTIONS. If the section publishes "
            "field names, ledger them; if it cannot be pinned here, say why, "
            "because a section nobody classified reads exactly like one "
            "somebody decided about"
        )

    def test_the_partition_does_not_double_count(self) -> None:
        assert not set(SECTION_FIELDS) & set(UNPINNED_SECTIONS), (
            "a section cannot be both ledgered and excused from being ledgered"
        )

    def test_neither_half_names_a_section_that_is_not_served(self) -> None:
        """A stale entry stops describing the producer and starts hiding a
        gap — ``config_keys``' refusal of an exemption naming a key the model
        declares, one domain over."""
        rendered = {section["title"] for section in _rendered()}
        stale = (set(SECTION_FIELDS) | set(UNPINNED_SECTIONS)) - rendered
        assert not stale, (
            f"{sorted(stale)} are classified here and are not served. A "
            "section that has left belongs in the sibling module's "
            "RETIRED_TITLES, not in a field ledger that implies it is live"
        )


class TestAnExcusedSectionSaysWhyItCannotBePinned:
    @pytest.mark.parametrize("title", sorted(UNPINNED_SECTIONS))
    def test_it_names_the_mechanism(self, title: str) -> None:
        """*"cannot be pinned"* records that somebody decided, which the map's
        own existence already showed.  What a reader needs is which of the
        three mechanisms it is, so that they can tell a section that has no
        field names from one that has them somewhere else."""
        reason = UNPINNED_SECTIONS[title]
        assert any(
            token in reason
            for token in ("comprehension", "bare narrative string", "`text` section")
        ), (
            f"{title!r} does not say what puts its field names out of reach. "
            "Today that is one of: the dict is built by comprehension, or the "
            "section is `text` and has no field names at all"
        )


class TestARetirementNamesWhatCarriedIt:
    """:data:`RETIRED_FIELDS` is empty today — no field has ever left a
    ledgered section — so these are driven at a **synthetic** as well.

    A parametrised test over an empty mapping is green without running, and an
    empty population is the reason a check gets written wrong and nobody
    notices.  The synthetic pair is the control: the detector is shown to
    reject a retirement that dates nothing and names nothing, so the day a
    real one lands the shape is already enforced.
    """

    #: A retirement that says neither when nor by what.  It must fail both
    #: rules below; if it stops doing so the rules have stopped being rules.
    UNACCEPTABLE = ("Infrastructure Status", "an_old_field"), "removed"

    @pytest.mark.parametrize("entry", sorted(RETIRED_FIELDS))
    def test_it_dates_the_departure(self, entry: tuple[str, str]) -> None:
        # may-not-evaluate: parametrised over RETIRED_FIELDS, which is empty
        # by measurement, so this never runs on a healthy tree.  The rule is
        # witnessed instead by test_the_rules_reject_a_retirement_that_
        # records_nothing below, which drives the same two patterns at a
        # synthetic retirement — the control that exists because an empty
        # population is how a check gets written wrong and stays green.
        assert re.search(r"\b20\d{2}-\d{2}-\d{2}\b", RETIRED_FIELDS[entry]), (
            f"{entry!r} does not say when it left; a retirement with no date "
            "cannot be matched against a consumer's capture"
        )

    @pytest.mark.parametrize("entry", sorted(RETIRED_FIELDS))
    def test_it_names_a_document_or_says_there_was_none(
        self, entry: tuple[str, str]
    ) -> None:
        reason = RETIRED_FIELDS[entry]
        # may-not-evaluate: the same empty RETIRED_FIELDS as the rule above,
        # and witnessed by the same synthetic control below.
        assert re.search(r"ADR-\d{4}|`[0-9a-f]{8}`|not announced", reason), (
            f"{entry!r} names no ADR, no register message id and does not say "
            "it went unannounced. One of the three is true of every removal"
        )

    def test_the_rules_reject_a_retirement_that_records_nothing(self) -> None:
        _, reason = self.UNACCEPTABLE
        assert not re.search(r"\b20\d{2}-\d{2}-\d{2}\b", reason)
        assert not re.search(r"ADR-\d{4}|`[0-9a-f]{8}`|not announced", reason)


class TestTheLedgerRecordsWhatARenameCosts:
    """The two sections break differently, and a ledger that did not say so
    would assert something false about one of them.

    ``on_rename`` is the measured reading and ``note`` is where it was
    measured; a third section cannot be added without somebody going to the
    consumer and looking, because neither field has a default.
    """

    @pytest.mark.parametrize("title", sorted(SECTION_FIELDS))
    def test_it_declares_a_measured_reading(self, title: str) -> None:
        assert SECTION_FIELDS[title].on_rename in RENAME_READINGS, (
            f"{title!r} declares {SECTION_FIELDS[title].on_rename!r}, which is "
            f"not one of the readings measured at the consumer {RENAME_READINGS}"
        )

    @pytest.mark.parametrize("title", sorted(SECTION_FIELDS))
    def test_it_names_the_consumer_code_that_produces_it(self, title: str) -> None:
        note = SECTION_FIELDS[title].note
        assert "alfred" in note.lower(), (
            f"{title!r} states a consequence without naming where it was "
            "observed. The reading is a fact about Alfred's code and outside "
            "this checkout, so the note is the only thing a later sitting can "
            "re-measure it against"
        )

    def test_both_readings_are_exercised(self) -> None:
        """A closed set of two whose members all name the same reading is a
        constant wearing a set's clothes, and would not have caught the
        finding that shaped this file."""
        declared = {entry.on_rename for entry in SECTION_FIELDS.values()}
        assert declared == set(RENAME_READINGS), (
            f"the ledger declares {sorted(declared)} against a closed set of "
            f"{sorted(RENAME_READINGS)}; if a reading has no member the set "
            "has stopped being a measurement of this seam"
        )


# --------------------------------------------------------------------------
# The floor
#
# Everything above is a ceiling.  It is driven at
# :func:`~tests.test_briefing_sections_are_additive._every_branch_taken`, a
# payload built to make every conditional in the producer true, and it
# therefore asks what field names a section *can* publish.  A fixture of that
# shape cannot observe a floor, because a floor is a property of the **empty**
# case — the sibling's own floor comment says so one level up, and the same
# sentence is true one level down.
#
# **The guarantee looks covered by composing the two ledgers and is not.**
# The composition reads: the sibling pins that ``Overnight Logs`` arrives
# having gathered nothing, this module pins that its keys are ``Entries``,
# ``Errors``, ``Sources`` — therefore a consumer always receives those three.
# The second premise is the conditional one.  It is measured at a payload
# **with data in it**, and a ``data`` built by comprehension renders whatever
# the gathered block holds, so its key set moves with the data and can be
# three wide at the ceiling and empty at the floor.  That is not a shape
# invented for the argument: ``Filesystem`` has been exactly it since
# 2026-08-11 (``SNAG-BRIEF-006``), and it is a *ledgered* section that stopped
# being one.  A derivation that survives only while a second entry's condition
# holds is not a statement, which is why ``SNAG-BRIEF-007`` was filed rather
# than waved off.
#
# So the floor is driven, at :func:`~tests.test_briefing_sections_are_additive
# ._nothing_gathered` and against a ledger of its own.  What holds it honest
# is not the drive: it is
# :class:`TestTheLedgeredSectionsSpellTheirFieldsInTheProducer`, which
# :class:`TestTheTwoFloorLedgersAgree` routes onto every floored section by
# requiring that one be ledgered above as well.
#
# Measured while this was written, and recorded because it is the kind of
# thing a later reading would take for a mechanism: the floor fixture spells
# its logs block ``entries``/``errors``/``sources`` and the producer spells
# the cells ``Entries``/``Errors``/``Sources``, so turning that ``data`` into
# a comprehension reddens the drive below **directly** rather than only
# through the premise.  That is a coincidence of casing between a fixture and
# a producer, not a property of either, and nothing here rests on it.


#: The ``data`` field names a consumer receives on the producer's worst
#: morning, by section.  :data:`SECTION_FIELDS` says what a section's keys are
#: *when it arrives*; this says which of them arrive **whatever the box has
#: been doing**, and the two are different claims about one surface.
#:
#: **A name leaving this ledger is a guarantee withdrawn**, which is the
#: opposite kind of breakage from one leaving :data:`SECTION_FIELDS`: that is
#: a cell a consumer stops receiving *sometimes*, this is one it has received
#: every morning of its life and has no defence against losing.  Today the two
#: coincide for the one floored section, because its ``data`` is all literals
#: inside the producer's one unconditional append — a coincidence of this
#: section rather than a rule, and the subset test below is written as the
#: rule.
FLOOR_FIELDS = {
    "Overnight Logs": ("Entries", "Errors", "Sources"),
}


def _rendered_floor() -> list[dict[str, Any]]:
    """The producer driven at the payload that takes **no** branch.

    The fixture is imported from the sibling for :func:`_rendered`'s reason,
    and it carries its own premises there:
    ``TestTheFloorFixtureIsTheFloor`` derives from the producer both that
    every key it reads is present and that everything it gates on is falsy,
    so a fixture drifting upward cannot leave this half green while claiming
    a guarantee the producer does not give.
    """
    return render_sections(_nothing_gathered())


class TestTheFloorDriveIsAFloor:
    """The one thing this module's floor half cannot infer from its own
    assertions: that it is reading a different payload from the ceiling half.

    The sibling's floor drive is self-asserting — it renders one section where
    the ceiling renders six, so pointing it at the wrong fixture reddens it.
    This one is not, and that was measured rather than assumed: the floored
    section serves the same three names under both fixtures, so swapping
    :func:`_rendered_floor` for :func:`_rendered` leaves every assertion below
    green and the module claiming a guarantee it never measured.

    The obvious premise — that the two drives serve *different field sets* —
    is refused, because it is false and should be: a field set that survives
    the empty case unchanged is the strongest reading of this seam, not a
    defect.  What is pinned instead is that the two payloads differ at all.
    """

    def test_it_renders_strictly_less_than_the_ceiling_drive(self) -> None:
        floor = {section["title"] for section in _rendered_floor()}
        ceiling = {section["title"] for section in _rendered()}
        assert floor < ceiling, (
            f"the floor drive renders {sorted(floor)} against the ceiling "
            f"drive's {sorted(ceiling)}. Those are not two payloads: either "
            "this module has been pointed at _every_branch_taken twice, in "
            "which case its floor half is its ceiling half restated, or the "
            "producer has stopped gating sections and the two fixtures no "
            "longer separate"
        )


class TestTheTwoFloorLedgersAgree:
    """The section floor and the field floor describe one payload, and a
    disagreement between them is a gap rather than a contradiction.

    These are also what stop :data:`FLOOR_FIELDS` being emptied quietly.  The
    parametrised guard below is green without running over an empty mapping —
    ``RETIRED_FIELDS``' problem, which that ledger answers with a synthetic —
    and this one answers it structurally instead: a floored title that cannot
    be excused must be ledgered, so the population cannot reach zero while the
    sibling declares a floor at all.
    """

    def test_every_floor_field_set_names_a_floor_section(self) -> None:
        stranded = set(FLOOR_FIELDS) - set(FLOOR_TITLES)
        assert not stranded, (
            f"{sorted(stranded)} declare floor field names and are not in the "
            "sibling's FLOOR_TITLES, so they are not served on a morning when "
            "nothing was gathered and this ledger promises a consumer "
            "something it does not always get"
        )

    def test_every_floor_section_is_ledgered_or_excused(self) -> None:
        """Totality, so a second section joining the floor is a decision.

        A floored section with no field names at all — a ``text`` section, of
        which this producer serves three — is excused by
        :data:`UNPINNED_SECTIONS` for the reason it is already excused above.
        What must not happen is that it is in neither, because a section
        nobody classified reads exactly like one somebody decided about.
        """
        unaccounted = set(FLOOR_TITLES) - set(FLOOR_FIELDS) - set(UNPINNED_SECTIONS)
        assert not unaccounted, (
            f"{sorted(unaccounted)} are served on the producer's worst morning "
            "and appear in neither FLOOR_FIELDS nor UNPINNED_SECTIONS. A "
            "section that joins the floor makes its field names a guarantee, "
            "and a guarantee nobody wrote down is one nobody can withdraw "
            "deliberately"
        )

    def test_a_floored_section_is_a_ledgered_section(self) -> None:
        """The clause that routes the literals premise onto the floor.

        :class:`TestTheLedgeredSectionsSpellTheirFieldsInTheProducer` is
        parametrised over :data:`SECTION_FIELDS`, and it is the only thing
        keeping *any* rendered-keys assertion in this file honest.  A floored
        section excused from that ledger would have its floor measured by a
        drive with no tripwire under it — the ``Filesystem`` circularity,
        arriving at the one assertion that claims a guarantee.
        """
        unledgered = set(FLOOR_FIELDS) - set(SECTION_FIELDS)
        assert not unledgered, (
            f"{sorted(unledgered)} declare floor field names and are not in "
            "SECTION_FIELDS, so nothing asserts that those names are literals "
            "in the producer and the floor below is read off a render that may "
            "be quoting the fixture back"
        )


class TestTheFieldListHasAFloor:
    """What a consumer always receives, as one assertion rather than two.

    This is the statement ``SNAG-BRIEF-007`` says is owed: not *"the section
    arrives"* and *"its keys are these"*, but the pair, measured at the
    payload where the pair is in doubt.
    """

    @pytest.mark.parametrize("title", sorted(FLOOR_FIELDS))
    def test_the_producer_serves_them_when_it_has_gathered_nothing(
        self, title: str
    ) -> None:
        """Order is asserted for :meth:`TestTheProducerServesExactlyTheLedger
        .test_the_fields_and_their_order`'s reason — ``DigestMetrics.vue``
        renders ``Object.entries(data)``, so the cells reach the reader in the
        order they arrive."""
        rendered = {section["title"]: section for section in _rendered_floor()}
        assert title in rendered, (
            f"{title!r} declares floor field names and was not served at all "
            "by a producer that gathered nothing; the sibling's FLOOR_TITLES "
            "and this ledger disagree about the same payload"
        )
        served = tuple(rendered[title]["data"])
        assert served == FLOOR_FIELDS[title], (
            f"{title!r} serves {served!r} on a morning with nothing gathered, "
            f"against a declared floor of {FLOOR_FIELDS[title]!r}. A name "
            "joining the floor is a stronger guarantee and belongs here; one "
            "leaving it is a guarantee withdrawn, and "
            f"{SECTION_FIELDS[title].on_rename} is what Alfred does with a "
            "name it stops receiving — silently, and in production"
        )

    @pytest.mark.parametrize("title", sorted(FLOOR_FIELDS))
    def test_the_floor_is_inside_the_served_ledger(self, title: str) -> None:
        """A name always served and not served at the ceiling is incoherent,
        and would mean one of the two drives is measuring its fixture."""
        outside = set(FLOOR_FIELDS[title]) - set(SECTION_FIELDS[title].fields)
        assert not outside, (
            f"{sorted(outside)} are declared as {title!r}'s floor and are not "
            "in its served ledger, so a field arrives on the producer's worst "
            "morning and not on its best one"
        )
