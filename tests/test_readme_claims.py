"""``README.md`` names what is here, and only what is here.

``SNAG-DOCS-013``: ``SNAG-DOCS-011``'s fix swept ``docs/ARCHITECTURE.md``
against the box and left the other two documents making the same class of
claim unguarded — and this is the **worse** exposure of the three, because
it is what ``github.com`` renders on arrival, with no click and no search.
A stranger who trusts a stale agent table here never reaches ``docs/``.

**Two live defects were sitting behind the missing guard**, which is worth
recording because the entry said there were none:

1. ``19 migrations`` in the repository layout, against **18** in Alembic's
   own revision graph.
2. A route table whose rows summed to **50** under a headline stating
   **51** — because the headline counted route *objects* and the table
   counted distinct *paths*, and ``/api/sysadmin/dnd`` is one path serving
   ``GET`` and ``POST``.  Two statements of one fact in two units, which is
   the shape this repository refuses in code (``SNAG-DB-003``,
   ``max_priority_for`` against ``PRIORITY_MAP``) arriving in a document.
   Neither half was individually wrong-looking, and a reader could not
   reconcile them; ``test_the_rows_sum_to_the_stated_total`` is what caught
   it, so the internal-consistency direction is guarded as well as the
   against-the-box one.

The entry's own claim — *"the population is measured-correct today"* — was
true of the five agent rows it had checked and false of the document.  That
is the entry's own lesson, instance against class, arriving one level down.

**What is not guarded, and why.**  The test count and the Markdown line
counts move on **every commit**, this one included, so an exact pin makes a
session's own work read as a documentation defect and nothing decides
anything off the figure.  They are hedged and dated in the document instead
(``SNAG-DOCS-012``'s remedy: state the population), and
:class:`TestTheMovingFiguresStayHedged` guards *that* — the two ways such a
sentence goes wrong are losing its hedge, which turns a snapshot into a
false precision, and drifting far enough to mislead.

Each sweep runs in **both directions** and carries an anti-vacuity premise:
an empty population makes a ``for`` loop green while asserting nothing
(``SNAG-TEST-006``, :mod:`sysadmin.vacuous_guards`).
"""

import re

import pytest

from sysadmin.core.config import REPO_ROOT
from tests.document_claims import (
    FIGURE_TOLERANCE,
    NUMBER_WORDS,
    interval_seconds,
    live_adr_ids,
    live_agents,
    live_dashboard_tabs,
    live_declared_services,
    live_migrations,
    live_packages,
    live_routers,
    live_routes,
    live_tables,
    planned_agent_intervals,
    routes_by_prefix,
    unresolved_links,
)

DOC_PATH = REPO_ROOT / "README.md"

@pytest.fixture(scope="module")
def document() -> str:
    return DOC_PATH.read_text()


@pytest.fixture(scope="module")
def flat(document: str) -> str:
    """The document with its line wrapping removed.

    Every prose claim below spans a line break somewhere — *"51 application
    routes across eight routers (55 including the four FastAPI\\ngenerates"* —
    so a pattern run over the raw text matches nothing and reads as a claim
    the document does not make.  ``ops_claims`` rule 1 settled this for
    ``STATUS.md``: flatten, then match.
    """
    return re.sub(r"\s+", " ", document)


# --------------------------------------------------------------------------
# What the document says


def _fenced_blocks(document: str) -> list[str]:
    return re.findall(r"\n```[a-z]*\n(.*?)\n```\n", document, re.S)


def layout_block(document: str) -> str:
    """The repository-layout listing, selected by content and not position.

    Three fenced blocks sit in this file and two are shell snippets.  Picking
    by index would go quietly wrong the day a fourth is added above it, which
    is the positional-selector trap this repository has paid for; the block is
    identified by the line it opens with.
    """
    blocks = [b for b in _fenced_blocks(document) if b.startswith("sysadmin/")]
    assert len(blocks) == 1, f"expected one layout block, found {len(blocks)}"
    return blocks[0]


def layout_packages(document: str) -> set[str]:
    """Package names indented one level under the ``sysadmin/`` node."""
    block = layout_block(document)
    start = block.index("sysadmin/")
    end = block.index("sysadmin_tray/")
    return set(re.findall(r"^  (\w+)/", block[start:end], re.M))


def agent_rows(document: str) -> dict[str, str]:
    """Agent class name to stated interval, from the agent table.

    The dialect is this document's own: the class is in backticks and the
    interval is a bare quantity (``5 min``), where ``ARCHITECTURE.md`` writes
    a bare class and ``every 300 s``.  The extraction is therefore per
    document and the *comparison* is not — :func:`interval_seconds` parses
    both spellings into one unit.
    """
    return {
        name: interval.strip()
        for name, interval in re.findall(
            r"^\| `(\w+Agent)` \| ([^|]+) \|", document, re.M
        )
    }


def route_rows(document: str) -> dict[str, int]:
    """Documented route prefix to stated count, from the API table."""
    return {
        prefix: int(count)
        for prefix, count in re.findall(r"^\| `(/[^`]+)` \| (\d+) \|", document, re.M)
    }


def stated(flat: str, pattern: str) -> int:
    """One figure the document states, as an int, refusing absence.

    A missing pattern is a failure rather than a skip: a claim that has been
    reworded out of reach is exactly the case a guard exists for, and reading
    it as "nothing to check" is ``ports_checked``'s collapse.
    """
    match = re.search(pattern, flat)
    assert match, f"the document states no figure matching {pattern!r}"
    token = match.group(1).replace(",", "").lower()
    return NUMBER_WORDS.get(token, 0) or int(token)


# --------------------------------------------------------------------------
# The premises. An empty population makes every sweep below vacuous.


class TestThePopulationsAreNotEmpty:
    def test_the_box_has_the_populations_the_document_describes(self) -> None:
        assert len(live_agents()) == 5, live_agents()
        assert len(live_packages()) >= 5, live_packages()
        assert len(live_tables()) >= 10, live_tables()
        assert len(live_migrations()) >= 10, live_migrations()
        assert len(live_routes()) >= 40, len(live_routes())
        assert len(live_dashboard_tabs()) == 5, live_dashboard_tabs()

    def test_the_document_states_the_claims(self, document: str) -> None:
        assert agent_rows(document), "no agent table"
        assert route_rows(document), "no API table"
        assert layout_packages(document), "no layout block"

    def test_every_interval_in_the_document_parses(self, document: str) -> None:
        """The comparison below is vacuous if the parse silently fails.

        ``interval_seconds`` raises on an unknown unit, so this asserts the
        five rows are reachable at all before any of them is compared.
        """
        for name, text in agent_rows(document).items():
            assert interval_seconds(text) > 0, (name, text)


# --------------------------------------------------------------------------
# Membership, both directions


class TestTheAgentsAgree:
    def test_the_table_names_every_agent_that_exists(self, document: str) -> None:
        missing = live_agents() - set(agent_rows(document))
        assert not missing, f"a BaseAgent subclass absent from the table: {sorted(missing)}"

    def test_the_table_names_no_agent_that_does_not(self, document: str) -> None:
        phantom = set(agent_rows(document)) - live_agents()
        assert not phantom, f"in the agent table, not in the code: {sorted(phantom)}"

    def test_the_stated_agent_count_is_the_measured_one(self, flat: str) -> None:
        assert stated(flat, r"(\w+) agents run on an APScheduler") == len(live_agents())


class TestTheIntervalsComeFromTheJobPlan:
    """The document's schedule is pinned to the scheduler's, not to the other
    document's.

    ``every 300 s`` in ``ARCHITECTURE.md`` and ``5 min`` here are **two
    statements of one fact**, free to disagree the day
    ``health_check_interval_seconds`` moves — and comparing them to each
    other would let both go wrong together.  Each is compared to
    :func:`planned_agent_intervals`, which reads ``plan_jobs``: the same
    function the lifespan and the reload call, so what is pinned is what the
    scheduler is actually asked to do.  ``max_priority_for`` against
    ``PRIORITY_MAP``'s rule, applied to a document.
    """

    def test_every_stated_interval_is_the_planned_one(self, document: str) -> None:
        planned = planned_agent_intervals()
        for name, text in agent_rows(document).items():
            assert name in planned, f"{name} is in the table and not in the job plan"
            assert interval_seconds(text) == planned[name], (
                f"{name}: the document says {text!r} "
                f"({interval_seconds(text)} s), the plan says {planned[name]} s"
            )

    def test_the_plan_has_no_agent_the_table_omits(self, document: str) -> None:
        missing = set(planned_agent_intervals()) - set(agent_rows(document))
        assert not missing, f"scheduled, absent from the table: {sorted(missing)}"


class TestTheRoutesAgree:
    def test_every_documented_prefix_carries_the_measured_count(
        self, document: str
    ) -> None:
        rows = route_rows(document)
        counts, _ = routes_by_prefix(list(rows))
        wrong = {
            prefix: (claimed, counts[prefix])
            for prefix, claimed in rows.items()
            if counts[prefix] != claimed
        }
        assert not wrong, f"prefix: (document, box) — {wrong}"

    def test_no_route_belongs_to_no_documented_prefix(self, document: str) -> None:
        """The table claims to partition the routes, so totality is the claim.

        A route matching none of the eight prefixes is reported rather than
        dropped: a new router mounted at ``/api/gpu`` would otherwise leave
        every stated count correct and the table silently incomplete, which
        is zero-because-blind served as zero-because-clean.
        """
        _, unclassified = routes_by_prefix(list(route_rows(document)))
        assert not unclassified, f"served, in no documented prefix: {sorted(unclassified)}"

    def test_the_rows_sum_to_the_stated_total(self, document: str, flat: str) -> None:
        """The direction that caught the defect this guard was written for.

        The headline and the rows are one fact stated twice, so they are
        checked against each other as well as against the box — the rows
        summed to 50 beneath a headline of 51 for as long as the document
        existed, and each half read plausibly on its own.
        """
        total = stated(flat, r"(\d+) application routes across")
        assert sum(route_rows(document).values()) == total

    def test_the_stated_total_is_the_measured_one(self, flat: str) -> None:
        assert stated(flat, r"(\d+) application routes across") == len(live_routes())

    def test_the_stated_router_count_is_the_measured_one(self, flat: str) -> None:
        assert stated(flat, r"application routes across (\w+) routers") == live_routers()

    def test_the_documented_total_admits_fastapis_own_four(self, flat: str) -> None:
        """The larger figure is the smaller one plus FastAPI's four.

        Stated in the document as a parenthesis and easy to leave behind when
        a route is added, since it is the only figure in the table's
        neighbourhood that is not about this repository's own routes.
        """
        with_docs = stated(flat, r"\((\d+) including the four FastAPI")
        assert with_docs == len(live_routes()) + 4


class TestTheLayoutAgrees:
    def test_the_layout_names_every_package_that_exists(self, document: str) -> None:
        missing = live_packages() - layout_packages(document)
        assert not missing, f"present on disk, absent from the layout: {sorted(missing)}"

    def test_the_layout_names_no_package_that_does_not(self, document: str) -> None:
        phantom = layout_packages(document) - live_packages()
        assert not phantom, f"in the layout, not on disk: {sorted(phantom)}"

    def test_the_stated_migration_count_is_the_measured_one(self, flat: str) -> None:
        """One of the two defects this module was written for.

        The count came from Alembic's own ``ScriptDirectory`` rather than a
        glob over ``alembic/versions/*.py`` — ``schema_guard``'s rule, so the
        document is pinned to the graph ``alembic upgrade head`` walks and
        not to a directory listing that can hold a file the graph never
        reaches.
        """
        assert stated(flat, r"alembic/ (\d+) migrations") == len(live_migrations())


class TestTheStructuralFiguresAgree:
    def test_the_stated_table_count_is_the_measured_one(self, flat: str) -> None:
        assert stated(flat, r"`sysadmin` schema, (\d+) tables") == len(live_tables())

    def test_the_stated_service_count_is_the_measured_one(self, flat: str) -> None:
        assert stated(flat, r"`services.yaml` — (\d+) declared services") == len(
            live_declared_services()
        )

    def test_the_named_dashboard_tabs_are_the_ones_the_tray_adds(self, flat: str) -> None:
        """Read as a set: the prose orders them for reading, the code for the
        widget row, and neither is a claim about the other."""
        match = re.search(r"dashboard with ([^.]+?) tabs", flat)
        assert match, "the document names no dashboard tabs"
        named = set(re.findall(r"\w+", match.group(1))) - {"and"}
        assert named == live_dashboard_tabs()

    def test_the_stated_adr_count_is_the_measured_one(self, flat: str) -> None:
        assert stated(flat, r"\[`docs/adr/`\]\(docs/adr/\) \| (\d+) architecture") == len(
            live_adr_ids()
        )


class TestTheLinksResolve:
    """A published index whose links 404 misleads the same way a stale table
    does — a reader following one concludes the thing is gone.

    Only repository-relative targets are reachable from here; the estate's
    documents are deliberately unresolvable for an outside reader and the
    document says so in its own closing paragraph, so they are not linked.
    """

    def test_every_relative_link_resolves(self) -> None:
        missing = unresolved_links(DOC_PATH)
        assert not missing, f"linked, not present: {missing}"


class TestTheMovingFiguresStayHedged:
    """A figure that moves on every commit is guarded as a *snapshot*.

    Pinning the test count exactly makes the commit that adds a test read as
    a documentation defect — and this commit adds tests — so what is checked
    is that the sentence stays honest rather than current: it keeps a hedge,
    it keeps the date it was measured, and it has not drifted far enough to
    mislead.  ``SNAG-DOCS-012``'s remedy was to state the population, and
    that entry exists because one number was carried between two arguments
    needing different denominators; the hedge is what stops the same figure
    being read as precise.
    """

    def test_the_line_count_sentence_names_both_populations_and_a_date(
        self, flat: str
    ) -> None:
        match = re.search(
            r"roadmap alone runs to about ([\d,]+) lines — of roughly ([\d,]+) "
            r"lines of Markdown in the repository altogether, measured "
            r"(\d{4}-\d{2}-\d{2})",
            flat,
        )
        assert match, (
            "the line-count sentence has lost its hedge, "
            "its second population or its date"
        )

    def test_the_line_counts_have_not_drifted_into_misleading(self, flat: str) -> None:
        import subprocess

        def tracked_lines(pathspec: str) -> int:
            files = subprocess.run(
                ["git", "ls-files", pathspec],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
            return sum(
                len((REPO_ROOT / f).read_text().splitlines())
                for f in files
                if (REPO_ROOT / f).exists()
            )

        for pattern, pathspec in (
            (r"roadmap alone runs to about ([\d,]+) lines", "docs/roadmap/*.md"),
            (r"of roughly ([\d,]+) lines of Markdown", "*.md"),
        ):
            claimed = stated(flat, pattern)
            measured = tracked_lines(pathspec)
            drift = abs(measured - claimed) / measured
            assert drift <= FIGURE_TOLERANCE, (
                f"{pathspec}: the document says ~{claimed:,}, the tree holds "
                f"{measured:,} ({drift:.0%} adrift) — re-measure the sentence"
            )
