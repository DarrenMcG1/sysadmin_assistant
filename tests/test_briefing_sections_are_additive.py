"""The briefing producer's section titles are additive, and this is what says so.

``docs/guides/`` has claimed since 2026-08-06 that this producer's sections
are *"added, never renumbered or removed"*, and
`ADR-0014 <../docs/adr/0014-a-sample-cannot-be-both-pinnable-and-real.md>`_
refused to publish a canonical sample partly on the strength of consumers
tolerating what arrives.  **Nothing enforced the producing half.**  Measured
2026-09-15 by walking all 15 commits that have touched the producer under
both of its paths: the section set has changed **6** times and a title has
**left** it in **2** of them.  This walk reports **three** departures, and
the third is its own blind spot rather than a removal — see below, and note
that estate-manager measured the same history independently on 2026-09-14
and recorded ``title_set_changed = 6, commits_removing_a_title = 2``
(``docs/adr/drivers/0179-what-this-seam-pins-report.json``), which agrees on
the first figure and is right about the second where a first reading here
was not —

====  ==========  =========  ====================================================
   #  date        kind       change
====  ==========  =========  ====================================================
   1  2026-08-04  additive   ``Weekly Project Review`` arrives
   2  2026-08-06  *artefact* the title is parameterised, not removed — see below
   3  2026-08-06  additive   ``Pick This Up`` arrives
   4  2026-08-13  removal    ``Project Health`` and ``Pick This Up`` leave (ADR-0005)
   5  2026-08-24  removal    ``Overnight Log Summary`` renamed to ``Overnight Logs``
   6  2026-08-25  additive   ``Weekly System Health Review`` arrives
====  ==========  =========  ====================================================

Both real removals were shipped green, because the titles live in scenario
assertions that the removing commit edits alongside the removal.  That is not
a lapse in those sittings — it is what a scattered assertion *is*, and it is
the difference between a practice and a constraint.

**So the ledger below is the mechanism, and its two halves fail in opposite
directions.**  Dropping a title from :data:`SERVED_TITLES` alone is caught by
:class:`TestTheProducerServesExactlyTheLedger`, because the function still
renders it.  Dropping it from *both* halves is caught by
:class:`TestHistoryHoldsNoTitleTheLedgerForgot`, because git still holds it.
A removal therefore has exactly one quiet path left — **move it to
:data:`RETIRED_TITLES` with the announcement that carried it** — which is the
act this guard exists to force, and is what estate rule *a change to a surface
a repository publishes is announced by a filing at its measured readers* asks
for anyway.

**The walk reads a title only where it is a literal, and that cuts both
ways.**  It reads ``{"title": <string literal>}`` out of each commit's AST,
so a title built from a variable is invisible to it — transition 2 above is
exactly that, and it *looks like a removal* until the diff is read
(``"title": "Weekly Project Review"`` became ``"title": title``, the literal
moving to the call site).  So the walk can **under-collect** a title it never
sees spelled out and **over-report** a departure when one stops being spelled
out, and only the first of those is a gap in the guard: an over-reported
departure changes no assertion, because the title is still in ``ever_served``
from the commits that did spell it, and the test below asks only that
everything there is in the ledger.  What it costs is a **reader**, which is
how a first reading of this history put 3 in a headline over a table whose
own second row says *artefact*.  Under-collection is the safe direction for
the assertion and that is why it is tolerated:
:class:`TestHistoryHoldsNoTitleTheLedgerForgot` asserts history is a
**subset** of the ledger, so a title the walk misses can never turn it red by
accident.  What it costs is recorded as ``SNAG-BRIEF-005`` rather than left to
be discovered: a title introduced already-parameterised is outside this
guard's reach, and its departure would be as quiet as the two above.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sysadmin.briefing.data import render_sections

REPO = Path(__file__).resolve().parent.parent

#: The producer's paths.  It was ``sysadmin/services/briefing.py`` until the
#: 2026-08-13 reshuffle, and ``git log`` without ``--follow`` stops at the
#: rename — 9 commits against 15, which is how the first measurement taken
#: for ADR-0014 read *"2 of 3"* where the full history holds **2** removals
#: across **6** title-set changes.  Both of that first reading's figures were
#: wrong and for different reasons: the denominator because the walk stopped
#: at the rename, and the numerator because it counted a parameterisation as
#: a departure (``SNAG-BRIEF-005``).
PRODUCER_PATHS = ("sysadmin/briefing/data.py", "sysadmin/services/briefing.py")

#: Every section title this producer serves today, in render order.  **A
#: title leaving this tuple is a breaking change for every consumer**, which
#: tolerance does not cover: a consumer degrades gracefully around a section
#: it does not recognise and has no defence against one that stops arriving.
#: Moving an entry to :data:`RETIRED_TITLES` is how that is done deliberately.
SERVED_TITLES = (
    "Infrastructure Status",
    "Overnight Logs",
    "Filesystem",
    "Weekly Log Review",
    "Weekly Disk Review",
    "Weekly System Health Review",
)

#: Titles this producer has served and no longer serves, each mapped to the
#: announcement that carried its departure.  The value is prose rather than a
#: structured record on purpose: what a reader needs is the document to go
#: and read, and a schema here would be a second statement of what those
#: documents already say.
RETIRED_TITLES = {
    "Project Health": (
        "left 2026-08-13 for estate-manager with the projects domain "
        "(ADR-0005); Alfred's ADR-0070 repoints the pull at :8400"
    ),
    "Pick This Up": (
        "left 2026-08-13 for estate-manager with the projects domain "
        "(ADR-0005); Alfred's ADR-0070 repoints the pull at :8400"
    ),
    "Weekly Project Review": (
        "left 2026-08-13 for estate-manager with the projects domain "
        "(ADR-0005); Alfred's ADR-0070 repoints the pull at :8400"
    ),
    "Overnight Log Summary": (
        "renamed to Overnight Logs on 2026-08-24 when the weekly log review "
        "landed; a rename is one title removed and one added to a consumer, "
        "and this one was not announced"
    ),
}


def _every_branch_taken() -> dict[str, Any]:
    """A ``gathered`` dict that makes every conditional in the producer true.

    :func:`render_sections` appends five of its six sections behind an ``if``,
    so a fixture built from one morning's data measures that morning rather
    than the producer.  This is the payload that renders **all** of them, and
    it is the only input from which "what titles can this serve" is a question
    with an answer.
    """
    return {
        "services": {
            "items": [{"name": "sysadmin", "status": "ok", "note": None}],
            "measured_at": "2026-09-15T06:00:00+00:00",
        },
        "logs": {"entries": 1, "errors": 0, "sources": 1},
        "filesystem": {"measured_at": "2026-09-15T06:00:00+00:00", "total_mb": 1},
        "log_review": SimpleNamespace(narrative="a log narrative"),
        "disk_review": SimpleNamespace(narrative="a disk narrative"),
        "health_review": SimpleNamespace(narrative="a health narrative"),
    }


def _titles_at(sha: str) -> list[str] | None:
    """Every ``{"title": <literal>}`` the producer held at one commit.

    ``None`` when the file cannot be found or parsed at that commit, which is
    skipped rather than failed: a commit predating the module is not evidence
    about titles.
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
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "title"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    found.append(value.value)
        return found
    return None


@pytest.fixture(scope="module")
def history() -> tuple[int, set[str]]:
    """``(commits walked, every title ever served)`` over the producer's life.

    ``--follow`` is taken newest-first and reversed in Python: git documents
    ``--follow`` as unreliable in combination with ``--reverse``, and here it
    returns **one** commit instead of fifteen — a wrong answer that looks like
    a young file rather than like an error.
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
    ever: set[str] = set()
    walked = 0
    for sha in log:
        titles = _titles_at(sha)
        if titles is None:
            continue
        walked += 1
        ever |= set(titles)
    return walked, ever


# --------------------------------------------------------------------------
# The premises


class TestTheWalkIsNotVacuous:
    """A walk that found nothing agrees with every ledger, including a wrong
    one.  These pin that it looked."""

    def test_it_reaches_the_renamed_half_of_the_history(
        self, history: tuple[int, set[str]]
    ) -> None:
        walked, _ = history
        assert walked >= 15, (
            f"the walk read {walked} commits; it read 15 on 2026-09-15 and the "
            "count only grows, so a smaller number means --follow stopped at "
            "the 2026-08-13 rename and the guard is reading a third of the "
            "history it believes it is reading"
        )

    def test_it_sees_titles_no_longer_served(
        self, history: tuple[int, set[str]]
    ) -> None:
        """The whole point is reaching titles the working tree does not hold."""
        _, ever = history
        assert ever - set(SERVED_TITLES), (
            "the walk found no title outside the live set, so it is measuring "
            "the working tree rather than the history and would pass over any "
            "removal at all"
        )

    def test_the_fixture_supplies_every_key_the_producer_reads(self) -> None:
        """Without this the ledger test could pass against a payload that
        renders one section, which is the shape ADR-0014 refused a sample for.

        The keys are **derived** from the producer rather than restated — an
        ``ast`` walk for ``gathered[...]`` inside :func:`render_sections` — so
        the premise is about the *fixture* and nothing else.  Asserting
        ``len(rendered) == len(SERVED_TITLES)`` here was the first version and
        was wrong: it reddened whenever the producer dropped a section, which
        is the event the guard proper exists to catch, so a premise was
        standing in front of its own subject and one mutation lit two tests.
        """
        source = ast.parse((REPO / PRODUCER_PATHS[0]).read_text())
        function = next(
            node
            for node in ast.walk(source)
            if isinstance(node, ast.FunctionDef) and node.name == "render_sections"
        )
        read = {
            node.slice.value
            for node in ast.walk(function)
            if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "gathered"
            and isinstance(node.slice, ast.Constant)
        }
        assert read, "the walk found no gathered[...] read, so it measured nothing"
        fixture = _every_branch_taken()
        missing = {key for key in read if not fixture.get(key)}
        assert not missing, (
            f"the fixture leaves {sorted(missing)} falsy, so the branches they "
            "gate never run and the ledger below is measured against a payload "
            "that renders only some of the producer's sections"
        )


# --------------------------------------------------------------------------
# The guard


class TestTheProducerServesExactlyTheLedger:
    def test_the_titles_and_their_order(self) -> None:
        """Order is asserted as well as membership, because a consumer renders
        the list as it arrives and reordering is visible to a reader even
        where it breaks no assertion."""
        rendered = [section["title"] for section in render_sections(_every_branch_taken())]
        assert rendered == list(SERVED_TITLES), (
            "the producer's section set has moved. Adding one: add it to "
            "SERVED_TITLES. Removing one: move it to RETIRED_TITLES with the "
            "announcement that carried it — and file that announcement at the "
            "consumers first, because tolerance does not cover a removal"
        )


class TestHistoryHoldsNoTitleTheLedgerForgot:
    def test_every_title_ever_served_is_accounted_for(
        self, history: tuple[int, set[str]]
    ) -> None:
        """The half that makes a quiet deletion impossible.

        Dropping a title from ``SERVED_TITLES`` alone is caught by the render
        test; dropping it from both halves is caught here, because git still
        holds the commit that served it.
        """
        _, ever = history
        forgotten = ever - set(SERVED_TITLES) - set(RETIRED_TITLES)
        assert not forgotten, (
            f"{sorted(forgotten)} were served by this producer and are in "
            "neither half of the ledger. A title does not stop having been "
            "published by being deleted from the file"
        )

    def test_the_two_halves_do_not_overlap(self) -> None:
        assert not set(SERVED_TITLES) & set(RETIRED_TITLES), (
            "a title cannot be both served and retired; a returning title is "
            "an addition and leaves the retired half"
        )


class TestARetirementNamesWhatCarriedIt:
    """A retired entry whose value is *"removed"* records that somebody did
    it, which is what the file already showed.  What a reader needs is where
    the announcement is."""

    @pytest.mark.parametrize("title", sorted(RETIRED_TITLES))
    def test_it_dates_the_departure(self, title: str) -> None:
        assert re.search(r"\b20\d{2}-\d{2}-\d{2}\b", RETIRED_TITLES[title]), (
            f"{title!r} does not say when it left; a retirement with no date "
            "cannot be matched against a consumer's capture"
        )

    @pytest.mark.parametrize("title", sorted(RETIRED_TITLES))
    def test_it_names_a_document_or_says_there_was_none(self, title: str) -> None:
        reason = RETIRED_TITLES[title]
        assert re.search(r"ADR-\d{4}|`[0-9a-f]{8}`|not announced", reason), (
            f"{title!r} names no ADR, no register message id and does not say "
            "it went unannounced. One of the three is true of every removal, "
            "and which one it is is the fact a consumer needs"
        )


# --------------------------------------------------------------------------
# The floor
#
# The ledger above is a ceiling: it asks what this producer *can* serve, and
# it asks it of :func:`_every_branch_taken`, a payload built to make every
# conditional true.  A fixture of that shape cannot observe a floor, because
# a floor is a property of the **empty** case — so what the producer emits
# when it has gathered nothing went unasserted here, and in
# ``tests/test_health_review.py`` it was rendered and looked straight past:
# ``test_the_briefing_omits_the_section_rather_than_emitting_it_empty``
# drives exactly the payload below and asks only whether one title is absent.
#
# estate-manager measured the six appends and filed the consequence at us
# (their ADR-0187 sweep of uninstrumented cross-repo measurements, message
# ``4bccc5e9``, 2026-09-21): their ``estate-map.md`` argued that a seam check
# cannot compare section sets *because* an omitting producer's list moves
# with its data, and the sentence it argued that from — "sysadmin omits
# sections rather than sending them empty" — is false at one section.  The
# floor is a second and independent reason the same check is blind, and it
# sat inside the sentence offered as the first.
#
# Three things in this tree stated the premise and none stated the
# consequence, which is why the item was not redundant: ``_gather_logs``
# says it never returns ``None``, the comment over the append says a count
# is always available, and ADR-0014 §2 re-measured the one-unconditional
# figure on 2026-09-14.  Every one of those is about the *producer*.  A
# floor of one, and a ``type`` a consumer is guaranteed, are about the
# **payload**.


#: What this producer emits having gathered nothing at all.  **A member
#: leaving this tuple is a breaking change of the opposite kind from one
#: leaving** :data:`SERVED_TITLES`: that is a section a consumer stops
#: receiving *sometimes*, this is the guarantee that it receives anything
#: at all.
FLOOR_TITLES = ("Overnight Logs",)

#: The section ``type`` values that survive the empty case, and therefore the
#: ones a consumer may assume.  ``status_grid`` and ``text`` are each
#: droppable; ``table`` is in Alfred's vocabulary and this producer has never
#: emitted it.
FLOOR_TYPES = frozenset({"metrics"})


def _nothing_gathered() -> dict[str, Any]:
    """A ``gathered`` dict in which every conditional in the producer is false.

    The mirror of :func:`_every_branch_taken`, and the only input from which
    "what does a consumer always receive" is a question with an answer.
    ``logs`` carries a real block because :func:`~sysadmin.briefing.data
    ._gather_logs` never returns ``None`` — that is the mechanism of the
    floor, not an omission here, and the premise below pins that this dict
    leaves everything the producer *gates* on falsy.
    """
    return {
        "services": None,
        "logs": {"entries": 0, "errors": 0, "sources": 0},
        "filesystem": None,
        "log_review": None,
        "disk_review": None,
        "health_review": None,
    }


def _appends() -> list[tuple[str, str, bool]]:
    """``(title, type, guarded)`` for every ``sections.append`` in the producer.

    ``guarded`` is whether the call sits inside any compound statement rather
    than at the function's own body level.  Read from the AST rather than by
    rendering, because the question is about the *structure* of the producer:
    a floor that holds only by the value of a condition is not a floor, and a
    drive cannot tell the two apart.
    """
    source = ast.parse((REPO / PRODUCER_PATHS[0]).read_text())
    function = next(
        node
        for node in ast.walk(source)
        if isinstance(node, ast.FunctionDef) and node.name == "render_sections"
    )
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(function):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def guarded(node: ast.AST) -> bool:
        cursor: ast.AST = node
        while cursor in parents:
            cursor = parents[cursor]
            if cursor is function:
                return False
            if isinstance(cursor, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                return True
        return False

    found = []
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "sections"
            and node.args
            and isinstance(node.args[0], ast.Dict)
        ):
            literal = {
                key.value: value.value
                for key, value in zip(node.args[0].keys, node.args[0].values)
                if isinstance(key, ast.Constant)
                and isinstance(value, ast.Constant)
                and key.value in ("title", "type")
            }
            found.append(
                (literal.get("title", ""), literal.get("type", ""), guarded(node))
            )
    return found


class TestTheFloorFixtureIsTheFloor:
    """:func:`_nothing_gathered` hand-writes the falsity the producer gates on.

    Without these the floor tests could be measuring a payload that happens
    to render one section — the same trap
    :class:`TestTheWalkIsNotVacuous.test_the_fixture_supplies_every_key_the_producer_reads`
    guards from the other end, and it is sharper here, because a fixture
    drifting *upward* leaves a green suite claiming a guarantee the producer
    does not give.
    """

    def test_every_key_the_producer_reads_is_present(self) -> None:
        """A missing key raises ``KeyError`` rather than omitting a section,
        so the drive below would fail for a reason that says nothing about
        the floor."""
        source = ast.parse((REPO / PRODUCER_PATHS[0]).read_text())
        function = next(
            node
            for node in ast.walk(source)
            if isinstance(node, ast.FunctionDef) and node.name == "render_sections"
        )
        read = {
            node.slice.value
            for node in ast.walk(function)
            if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "gathered"
            and isinstance(node.slice, ast.Constant)
        }
        assert read, "the walk found no gathered[...] read, so it measured nothing"
        missing = read - set(_nothing_gathered())
        assert not missing, (
            f"the floor fixture omits {sorted(missing)}, so render_sections "
            "raises KeyError and the floor below is unmeasured"
        )

    def test_everything_the_producer_gates_on_is_falsy(self) -> None:
        """Derived from the producer rather than restated: whatever it tests,
        this fixture must make false, or the result is some payload and not
        the floor."""
        source = ast.parse((REPO / PRODUCER_PATHS[0]).read_text())
        function = next(
            node
            for node in ast.walk(source)
            if isinstance(node, ast.FunctionDef) and node.name == "render_sections"
        )
        # **The alias is resolved rather than the net widened.**  The
        # producer binds each key to a local — ``filesystem =
        # gathered["filesystem"]`` — and gates on the *local*, so walking
        # the ``if`` tests for ``gathered[...]`` subscripts finds **nothing**
        # and the assertion below passes over any fixture at all, including
        # :func:`_every_branch_taken`.  That was this test's first draft and
        # it was measured empty before it was believed: keying on the wrong
        # node type is green and measures nothing, which is the registry
        # rule *a name is not a parse* one module over.
        aliases = {
            target.id: node.value.slice.value
            for node in ast.walk(function)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Subscript)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "gathered"
            and isinstance(node.value.slice, ast.Constant)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        gated = {
            aliases[node.id]
            for branch in ast.walk(function)
            if isinstance(branch, ast.If)
            for node in ast.walk(branch.test)
            if isinstance(node, ast.Name) and node.id in aliases
        }
        assert gated, (
            "the walk resolved no gated key, so the assertion below is "
            "vacuous and would pass over a fixture that renders every section"
        )
        fixture = _nothing_gathered()
        truthy = {key for key in gated if fixture.get(key)}
        assert not truthy, (
            f"the floor fixture leaves {sorted(truthy)} truthy, so the "
            "branches they gate render and this is a sample rather than a floor"
        )


class TestTheSectionListHasAFloor:
    """What a consumer receives on the producer's worst morning.

    The ledger above says what may arrive; this says what always does.  They
    are different assertions about one surface and neither implies the other.
    """

    def test_the_producer_emits_the_floor_when_it_has_gathered_nothing(self) -> None:
        rendered = [section["title"] for section in render_sections(_nothing_gathered())]
        assert rendered == list(FLOOR_TITLES), (
            f"the producer emits {rendered} with nothing gathered, and the "
            f"ledger says {list(FLOOR_TITLES)}. A section joining the floor is "
            "a stronger guarantee and belongs in FLOOR_TITLES; one leaving it "
            "is a guarantee withdrawn, and a consumer that has been receiving "
            "it every morning has no defence against the morning it stops"
        )

    def test_metrics_is_the_type_the_producer_cannot_drop(self) -> None:
        """The half a *consumer* can act on, and the half estate-manager's
        seam check needed: a section set that can shrink to nothing is one a
        comparison can be built over, and this one cannot."""
        served = {section["type"] for section in render_sections(_nothing_gathered())}
        assert served == FLOOR_TYPES, (
            f"the empty case serves types {sorted(served)} against a declared "
            f"floor of {sorted(FLOOR_TYPES)}; a type entering the floor is a "
            "promise to every consumer and a type leaving it breaks one"
        )

    def test_exactly_one_append_is_unconditional(self) -> None:
        """The structural half, and it is not the drive restated.

        Wrapping the floor section in ``if True:`` leaves the drive above
        green and this red, which is the distinction worth keeping: a floor
        that holds by the *value* of a condition holds until someone edits
        the condition, and only the source can tell the two apart.  This is
        also the figure estate-manager measured — five guarded, one not — so
        the next sweep of it can be answered from this suite.
        """
        unconditional = [
            (title, type_) for title, type_, guarded in _appends() if not guarded
        ]
        assert [title for title, _ in unconditional] == list(FLOOR_TITLES), (
            f"{[t for t, _ in unconditional]} are appended unconditionally "
            f"against a declared floor of {list(FLOOR_TITLES)}"
        )
        assert {type_ for _, type_ in unconditional} == FLOOR_TYPES

    def test_the_walk_sees_every_append(self) -> None:
        """A walk finding nothing reports an empty floor and agrees with a
        ledger declaring one."""
        found = _appends()
        assert len(found) == len(SERVED_TITLES), (
            f"the walk found {len(found)} appends against {len(SERVED_TITLES)} "
            "served titles, so it is reading the producer partially and the "
            "guarded/unguarded split above is measured over a subset"
        )
        assert all(title for title, _, _ in found), (
            "an append's title is not a string literal, so the split above "
            "cannot say which section it described"
        )

    def test_the_floor_is_inside_the_served_ledger(self) -> None:
        """The two ledgers cannot disagree about whether a title exists.

        Retiring a floor title would empty the floor without editing
        :data:`FLOOR_TITLES`, so the render test would redden with a message
        about a guarantee while the actual event was a removal.
        """
        stranded = set(FLOOR_TITLES) - set(SERVED_TITLES)
        assert not stranded, (
            f"{sorted(stranded)} is declared as a floor and is not in "
            "SERVED_TITLES; a floor title that has been retired is a "
            "guarantee withdrawn, and RETIRED_TITLES is where that is said"
        )
