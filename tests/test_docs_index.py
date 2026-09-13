"""``docs/README.md`` accounts for everything in ``docs/``, and for nothing else.

``SNAG-DOCS-013``'s third document.  ``README.md`` and ``docs/ARCHITECTURE.md``
claim what the *system* contains; this one claims what the *directory*
contains — ten decision records, four roadmap files, three retrospectives,
two empty placeholders, one guide and four pointers — and until now nothing
checked any of it.  An index is the one document whose whole content is a
membership claim, so it is the one where an omission costs most: a reader who
trusts it concludes a file they were not shown does not exist.

**The omission direction is the one that matters here, and it is the one a
count cannot see** — ``SNAG-DOCS-011``'s fix learned that against
``ARCHITECTURE.md``, where the worse fault was ``estate/`` being *absent and
needed* rather than a departed name being present and wrong.  So every sweep
runs both ways, and the against-the-box direction found the live defect this
module was written alongside: ``docs/projects-registry-legacy.yaml`` sat in
the indexed directory and the index did not name it.

**What a "pointer" is, is read rather than guessed.**  The index claims one
of the five files in ``guides/`` is a document and the other four are
pointers into ``estate-manager``.  A line-count threshold would be an
invented constant standing in for a judgement; all four stubs open their
first heading with ``# Moved:``, which is the estate convention *a moved
document leaves a pointer, never a copy* written down in the file itself, so
the discriminator is the convention and not a proxy for it.

Each sweep carries an anti-vacuity premise: an empty population makes a
``for`` loop green while asserting nothing (``SNAG-TEST-006``,
:mod:`sysadmin.vacuous_guards`).
"""

import re

import pytest

from sysadmin.core.config import REPO_ROOT
from tests.document_claims import (
    ADR_ROOT,
    DOCS_ROOT,
    FIGURE_TOLERANCE,
    NUMBER_WORDS,
    live_adr_ids,
    tracked_lines,
    unresolved_links,
)

DOC_PATH = DOCS_ROOT / "README.md"

#: Directories under ``docs/`` the index is not required to name, and why.
#: ``roadmap/archive`` is reached through ``roadmap/``'s own section, which
#: describes the roadmap as a whole; naming it here would make the index a
#: second statement of that section's contents.
NOT_INDEXED = {"roadmap/archive"}

#: A moved document's first heading, which is how the estate convention
#: *a moved document leaves a pointer, never a copy* shows up in a file.
POINTER_HEADING = "# Moved:"


@pytest.fixture(scope="module")
def document() -> str:
    return DOC_PATH.read_text()


@pytest.fixture(scope="module")
def flat(document: str) -> str:
    """Line wrapping removed — ``ops_claims`` rule 1's treatment.

    Every prose count in this file wraps: *"Only ``api_auth.md`` is a
    document. **The other four are\\npointers into ``estate-manager``"*.
    """
    return re.sub(r"\s+", " ", document)


# --------------------------------------------------------------------------
# What the directory holds


def _tracked() -> set[str]:
    """Paths under ``docs/`` that the repository ships, relative to ``docs/``.

    **Tracked, not on-disk, and that was found by the falsification pass
    rather than reasoned out.**  The mutation harness writes ``*.bak``
    alongside each file it breaks, and a working-tree walk counted those as
    documents the index had failed to mention — so four mutations about
    ``ARCHITECTURE.md``'s schedule went red on this module's file sweep.
    The harness contaminating its own measurement is the visible half; the
    durable half is that an editor's ``.orig``, a merge ``.rej`` or a swap
    file would each turn a documentation guard red for no documentation
    fault.  What an index owes a reader is an account of what is
    **published**, so the population is what ``git ls-files`` reports.

    The trade is stated rather than left to be met: a document created and
    not yet staged is outside this sweep, so a session adding one is told
    about it at ``git add`` rather than at ``pytest``.  That is the correct
    side — an unstaged file is not yet something a reader can arrive at —
    and it is the same population rule ``daemon_modules`` settled for a
    different question.
    """
    import subprocess

    listing = subprocess.run(
        ["git", "ls-files", "docs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return {path.removeprefix("docs/") for path in listing}


def live_subtrees() -> set[str]:
    """Every directory the shipped tree holds under ``docs/``, minus the exempt.

    Derived from the tracked paths rather than walked, so an untracked
    directory — a scratch copy, a ``.bak`` tree — cannot demand an entry in
    a published index.  ``refactors/`` and ``templates/`` are reachable at
    all because each ships a ``.gitkeep``, which is the only way git holds
    an empty directory and is why
    :class:`TestThePlaceholdersAreStillEmpty` must not count one as content.
    """
    found: set[str] = set()
    for path in _tracked():
        parent = path.rpartition("/")[0]
        while parent:
            found.add(parent)
            parent = parent.rpartition("/")[0]
    return found - NOT_INDEXED


def live_top_level_files() -> set[str]:
    """Shipped files sitting directly in ``docs/``, excluding the index itself.

    The index cannot be required to list itself, and a reader holding it does
    not need to be told it exists.
    """
    return {path for path in _tracked() if "/" not in path and path != "README.md"}


def live_roadmap_documents() -> set[str]:
    return {path.name for path in (DOCS_ROOT / "roadmap").glob("*.md")}


def live_guide_split() -> tuple[set[str], set[str]]:
    """The ``guides/`` directory split into documents and pointers."""
    documents, pointers = set(), set()
    for path in (DOCS_ROOT / "guides").glob("*.md"):
        target = pointers if path.read_text().startswith(POINTER_HEADING) else documents
        target.add(path.name)
    return documents, pointers


def live_insights() -> set[str]:
    return {path.name for path in (DOCS_ROOT / "insights").glob("*.md")}


# --------------------------------------------------------------------------
# What the index says


def indexed_adr_ids(document: str) -> set[str]:
    """Record ids the index links, taken from the link target and not the label.

    The label (``ADR-0007``) and the path (``adr/0007-…``) are two statements
    of one id and free to disagree — a row can link the wrong file while
    reading correctly — so the target is the authority here and
    :meth:`TestTheDecisionRecordsAgree.test_every_label_matches_its_target`
    pins the pair.
    """
    return set(re.findall(r"\]\(adr/(\d+)-[^)]*\)", document))


def indexed_labels(document: str) -> dict[str, str]:
    """Every ``[ADR-nnnn](adr/mmmm-…)`` pair the index writes, label to target."""
    return {
        label: target
        for label, target in re.findall(
            r"\[ADR-(\d+)\]\(adr/(\d+)-[^)]*\)", document
        )
    }


def indexed_paths(document: str) -> set[str]:
    """Every repository-relative path the index links, normalised.

    Directories keep their trailing slash stripped so ``adr/`` and a file
    under it are comparable with :func:`live_subtrees`' spelling.
    """
    found = set()
    for target in re.findall(r"\]\(([^)]+)\)", document):
        if target.startswith(("http://", "https://", "mailto:", "#", "../")):
            continue
        found.add(target.split("#", 1)[0].rstrip("/"))
    return found


def indexed_subtrees(document: str) -> set[str]:
    """Directories the index accounts for, by either of the two ways it does it.

    Written first as *linked targets alone* and that was wrong about the
    document rather than about the box: the index accounts for ``roadmap/``
    with a whole section and links to the files **inside** it, and for
    ``guides/`` with a heading naming it in backticks — neither is a
    ``](roadmap/)`` link.  A guard reading only link targets called five of
    the seven subtrees unnamed, so it would have demanded the index be
    rewritten to satisfy the guard's reading of it, which is the wrong
    direction of authority.

    So a subtree counts as accounted for if the index **names it** as
    ``` `name/` ``` or **links into it**.  Both are the index doing its job;
    requiring one particular spelling would pin the prose rather than the
    claim.
    """
    named = set(re.findall(r"`([A-Za-z0-9_./-]+)/`", document))
    for path in indexed_paths(document):
        parent = path.rpartition("/")[0]
        while parent:
            named.add(parent)
            parent = parent.rpartition("/")[0]
    return named


def stated(flat: str, pattern: str) -> int:
    """One count the index states, refusing absence.

    A pattern that finds nothing fails rather than skipping: a count reworded
    out of reach is the case a guard exists for, and reading it as "nothing to
    check" is ``ports_checked``'s collapse.
    """
    match = re.search(pattern, flat)
    assert match, f"the index states no count matching {pattern!r}"
    token = match.group(1).replace(",", "").lower()
    return NUMBER_WORDS.get(token, 0) or int(token)


# --------------------------------------------------------------------------
# The premises


class TestThePopulationsAreNotEmpty:
    def test_the_directory_holds_what_the_index_describes(self) -> None:
        assert len(live_adr_ids()) >= 5, live_adr_ids()
        assert len(live_subtrees()) >= 5, live_subtrees()
        assert live_top_level_files(), live_top_level_files()
        assert len(live_roadmap_documents()) >= 4, live_roadmap_documents()
        documents, pointers = live_guide_split()
        assert documents and pointers, (documents, pointers)
        assert live_insights(), live_insights()

    def test_the_index_states_the_claims(self, document: str) -> None:
        assert indexed_adr_ids(document), "the index links no decision record"
        assert indexed_labels(document), "the index writes no ADR label"
        assert indexed_paths(document), "the index links nothing"


# --------------------------------------------------------------------------
# Membership, both directions


class TestTheDecisionRecordsAgree:
    def test_the_index_links_every_record_that_exists(self, document: str) -> None:
        missing = live_adr_ids() - indexed_adr_ids(document)
        assert not missing, f"in docs/adr/, unlisted by the index: {sorted(missing)}"

    def test_the_index_links_no_record_that_does_not(self, document: str) -> None:
        phantom = indexed_adr_ids(document) - live_adr_ids()
        assert not phantom, f"listed by the index, not in docs/adr/: {sorted(phantom)}"

    def test_the_stated_count_is_the_measured_one(self, flat: str) -> None:
        """Written as a word — *"Ten records."* — and a word goes stale exactly
        as a digit does, so it is read rather than exempted."""
        assert stated(flat, r"(\w+) records\.") == len(live_adr_ids())

    def test_every_label_matches_its_target(self, document: str) -> None:
        """``[ADR-0007](adr/0007-…)`` states one id twice.

        A row whose label and link disagree sends a reader to the wrong
        record while reading correctly, which is the failure mode a
        two-statement fact always has here.
        """
        wrong = {
            label: target
            for label, target in indexed_labels(document).items()
            if label != target
        }
        assert not wrong, f"label: linked target — {wrong}"


class TestTheSubtreesAgree:
    def test_the_index_names_every_subtree(self, document: str) -> None:
        missing = live_subtrees() - indexed_subtrees(document)
        assert not missing, f"a directory under docs/ the index never names: {sorted(missing)}"

    def test_the_index_names_no_subtree_that_does_not_exist(self, document: str) -> None:
        phantom = {
            path
            for path in indexed_paths(document)
            if not (DOCS_ROOT / path).exists()
        }
        assert not phantom, f"named by the index, not present: {sorted(phantom)}"

    def test_the_index_accounts_for_every_file_in_the_directory(
        self, document: str
    ) -> None:
        """The direction that found the live defect.

        ``docs/projects-registry-legacy.yaml`` sat beside the index and the
        index did not name it, so a reader browsing ``docs/`` met a file the
        document that exists to explain the directory had nothing to say
        about.  An unaccounted-for file is the omission a count cannot see.
        """
        named = {path.rpartition("/")[2] for path in indexed_paths(document)}
        missing = live_top_level_files() - named
        assert not missing, f"in docs/, unaccounted for by the index: {sorted(missing)}"


class TestTheRoadmapFilesAgree:
    def test_the_index_names_every_roadmap_document(self, document: str) -> None:
        named = {
            path.rpartition("/")[2]
            for path in indexed_paths(document)
            if path.startswith("roadmap/")
        }
        missing = live_roadmap_documents() - named
        assert not missing, f"in docs/roadmap/, unlisted: {sorted(missing)}"

    def test_the_index_names_no_roadmap_document_that_does_not_exist(
        self, document: str
    ) -> None:
        phantom = {
            path
            for path in indexed_paths(document)
            if path.startswith("roadmap/") and not (DOCS_ROOT / path).exists()
        }
        assert not phantom, f"listed under roadmap/, not present: {sorted(phantom)}"


class TestTheGuidesSplitIsTrue:
    """One document and four pointers, counted at the files rather than trusted.

    The index tells an outside reader that four of these links *will not
    resolve for them*, which is a promise about what they are about to
    experience; it is the one claim in this file whose being wrong wastes a
    stranger's time directly.
    """

    def test_the_stated_pointer_count_is_the_measured_one(self, flat: str) -> None:
        _, pointers = live_guide_split()
        assert stated(flat, r"The other (\w+) are pointers") == len(pointers)

    def test_the_named_document_is_the_one_that_is_not_a_pointer(
        self, flat: str
    ) -> None:
        documents, _ = live_guide_split()
        match = re.search(r"Only \[`([^`]+)`\]\([^)]*\) is a document", flat)
        assert match, "the index names no guide as a document"
        assert {match.group(1)} == documents, documents

    def test_every_pointer_points_at_the_estate(self) -> None:
        """A pointer that names no target is a copy that lost its content.

        The estate rule is *a moved document leaves a pointer, never a copy*;
        a stub opening ``# Moved:`` and then not saying where satisfies the
        heading and defeats the rule.
        """
        _, pointers = live_guide_split()
        for name in sorted(pointers):
            body = (DOCS_ROOT / "guides" / name).read_text()
            assert "estate-manager" in body, name


class TestThePlaceholdersAreStillEmpty:
    """*"``refactors/``, ``templates/`` — empty placeholders."*

    Guarded in the direction the sentence can go wrong: a document arriving
    in one of them makes the index actively misleading, and nothing else
    would say so — an empty directory is not something anyone re-reads.

    **A ``.gitkeep`` is not content, and the first draft of this test said it
    was.**  Git cannot track an empty directory, so the placeholder exists
    *because* of that file: counting it made the claim unsatisfiable in both
    directions at once — the directory could not be both tracked and empty —
    which is a guard asserting something no state can satisfy rather than a
    document being wrong.  Dotfiles are therefore excluded, and the exclusion
    is stated because a future reader meeting it would otherwise read it as
    laxity.
    """

    def test_the_directories_the_index_calls_empty_are_empty(
        self, flat: str
    ) -> None:
        match = re.search(r"`([^`]+)/`, `([^`]+)/` — empty placeholders", flat)
        assert match, "the index no longer calls any directory an empty placeholder"
        for name in match.groups():
            contents = [
                p.name
                for p in (DOCS_ROOT / name).iterdir()
                if not p.name.startswith(".")
            ]
            assert not contents, f"docs/{name}/ is called empty and holds {contents}"


class TestTheInsightsCountIsMeasured:
    def test_the_stated_retrospective_count_is_the_measured_one(
        self, flat: str
    ) -> None:
        assert stated(flat, r"(\w+) retrospectives") == len(live_insights())


class TestTheRoadmapFigureStaysHedged:
    """The roadmap's line count is stated here **and** in ``README.md``.

    ``SNAG-DOCS-012``'s shape: one figure copied into several documents,
    where the copies are free to disagree and nothing reads either.  Both
    are guarded the same way and neither is compared to the other — a
    figure that moves on every commit is guarded as a *snapshot*, so what is
    checked is that the sentence keeps its hedge, keeps the date it was
    measured, and has not drifted far enough to mislead.  Comparing the two
    documents would let both go stale together, which is exactly the
    argument ``SNAG-DOCS-013`` settled for the agent intervals one file
    over.
    """

    def test_the_figure_keeps_its_hedge_and_its_date(self, flat: str) -> None:
        assert re.search(
            r"About ([\d,]+) lines, measured (\d{4}-\d{2}-\d{2})", flat
        ), "the roadmap figure has lost its hedge or its measurement date"

    def test_the_figure_has_not_drifted_into_misleading(self, flat: str) -> None:
        claimed = stated(flat, r"About ([\d,]+) lines, measured")
        measured = tracked_lines("docs/roadmap/*.md")
        drift = abs(measured - claimed) / measured
        assert drift <= FIGURE_TOLERANCE, (
            f"the index says ~{claimed:,}, the roadmap holds {measured:,} "
            f"({drift:.0%} adrift) — re-measure the sentence"
        )


class TestTheLinksResolve:
    """A published index whose links 404 misleads the way a stale table does.

    The four ``guides/`` pointers link *out* of this repository and are
    expected not to resolve for an outside reader — the index says so — but
    they are ``../../../`` targets and :func:`unresolved_links` resolves them
    against this box, where the sibling tree does exist.  So a red here is a
    link into ``docs/`` that is broken, which is always a defect.
    """

    def test_every_relative_link_resolves(self) -> None:
        # may-not-turn: the population is the links in this index that do NOT
        # resolve, so an empty one is the healthy state and the only one a
        # green suite can produce.  The guard is the assert below, which fires
        # the moment `unresolved_links` returns anything this filter keeps —
        # the comprehension is the filter, never the measurement.
        missing = [
            target
            for target in unresolved_links(DOC_PATH)
            if not target.startswith("../../../")
        ]
        assert not missing, f"linked, not present: {missing}"


class TestTheAdrDirectoryIsWhereItIsClaimedToBe:
    """The one path this module hard-codes, pinned to the shared helper.

    ``ADR_ROOT`` is imported rather than rebuilt so this module and
    ``README.md``'s guard cannot come to disagree about where the records
    live — the copied-constant defect at the size of a path.
    """

    def test_the_helper_and_this_module_mean_the_same_directory(self) -> None:
        assert ADR_ROOT == DOCS_ROOT / "adr"
        assert ADR_ROOT.is_relative_to(REPO_ROOT)
