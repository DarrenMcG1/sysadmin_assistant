"""``docs/ARCHITECTURE.md`` names what is here, and only what is here.

``SNAG-DOCS-011``: the file's diagram and prose showed ``ProjectOrganiserAgent``
and the ``projects/`` and ``registry/`` packages for four weeks after all three
left under ADR-0005, and the cost changed on 2026-09-09 when the repository went
public — a stranger who trusts the diagram concludes this service scans
repositories and scores them, which is the wrong half of the judging swap.

**The entry declined a snag check and was right to.**
``check-snag-claims.sh``'s ``ok`` means *the defect is still real*, so a check
keyed on "does the file name a departed component" reports ``still holds`` over
a landed correction for ever — ``check_review_schedule_unread``'s defect.  A
test has the opposite polarity: green means the file agrees with the box.  So
the finding retires and the detector does not, which is ``FROZEN_TABLES``' rule.

**What is guarded is membership, never prose.**  The file is allowed — and
required — to say that a component *left*, so the phantom sweeps read the fenced
blocks alone and never the narrative.  A sentence recording the departure is the
pointer ``SNAG-DOCS-001`` asks for; a diagram node is a claim that it is here.

**Both directions, because the entry measured only one.**  It counted lines
naming a departed component and found five; the file's worse fault was what it
never named — ``estate/`` and ``EstateJudgeAgent``, precisely the half ADR-0005
*gave* this repository.  A line count cannot measure an omission, so each sweep
below runs in both directions and each carries an anti-vacuity premise: an empty
population would make the loop green while asserting nothing (``SNAG-TEST-006``,
:mod:`sysadmin.vacuous_guards`).

**Extended by ``SNAG-DOCS-013``, which this file's own scoping opened.**  The
guard was written for the file the entry named and the claim it was about is
made by three documents; ``tests/test_readme_claims.py`` and
``tests/test_docs_index.py`` are the other two, and the box side all three
compare against is stated once in :mod:`tests.document_claims`.  What this
file gained is :class:`TestTheIntervalsComeFromTheJobPlan`: *every 300 s*
here and *5 min* in ``README.md`` were **two statements of one fact** with
neither derived from anything, free to disagree the day
``health_check_interval_seconds`` moved.  Both are now pinned to
``plan_jobs`` — the function the lifespan and the reload both call — rather
than to each other, which is ``max_priority_for`` against ``PRIORITY_MAP``'s
rule applied to a document.
"""

import re

import pytest

from sysadmin.core.config import REPO_ROOT
from tests.document_claims import (
    interval_seconds,
    live_agents,
    live_packages,
    live_tables,
    planned_agent_intervals,
)

DOC_PATH = REPO_ROOT / "docs" / "ARCHITECTURE.md"


@pytest.fixture(scope="module")
def document() -> str:
    return DOC_PATH.read_text()


# --------------------------------------------------------------------------
# What the document says


def _fenced_blocks(document: str) -> list[str]:
    return re.findall(r"\n```\n(.*?)\n```\n", document, re.S)


def diagram(document: str) -> str:
    """The system-architecture diagram — the first fenced block."""
    blocks = _fenced_blocks(document)
    assert blocks, "no fenced block in the document"
    return blocks[0]


def directory_tree(document: str) -> str:
    """The directory-structure listing — the second fenced block."""
    blocks = _fenced_blocks(document)
    assert len(blocks) >= 2, f"expected two fenced blocks, found {len(blocks)}"
    return blocks[1]


def diagram_packages(document: str) -> set[str]:
    """Package names drawn in the diagram's ``Packages`` column.

    Sliced by **column**, not matched by pattern.  Three lists sit on the same
    physical lines — the tray's parts to the left of the box and ``core/``'s
    modules to the right — so a regex over the line reads all three and calls
    ``scheduler`` a package.  The heading line supplies both boundaries.

    ``core`` is that heading rather than one of the column's entries, because
    every domain depends on it and it is drawn beside them; it is added back
    here so this set is comparable with :func:`live_packages`.
    """
    lines = diagram(document).splitlines()
    heading = next(i for i, line in enumerate(lines) if "Packages" in line)
    left = lines[heading].index("Packages")
    right = lines[heading].index("core/")
    names = set()
    for line in lines[heading + 1 :]:
        if "Agents (" in line:
            break
        names.update(re.findall(r"[├└] (\w+)", line[left:right]))
    return names | {"core"}


def tree_packages(document: str) -> set[str]:
    """Package names listed under the ``sysadmin/`` node of the tree."""
    tree = directory_tree(document)
    start = tree.index("├── sysadmin/")
    end = tree.index("├── sysadmin_tray/")
    # Exactly one level of nesting: ``│   ├── files/`` is a domain, and
    # ``│   │   └── models/`` is a directory inside one.
    return set(re.findall(r"^│   [├└]── (\w+)/", tree[start:end], re.M))


def table_agents(document: str) -> set[str]:
    """Agent class names in the first column of the agent table."""
    return set(re.findall(r"^\| (\w+Agent) \| ", document, re.M))


def diagram_agents(document: str) -> set[str]:
    """Agent class names drawn in the diagram's ``Agents`` column."""
    body = diagram(document).split("Agents (")[1]
    return set(re.findall(r"[├└] (\w+Agent)\b", body))  # names are unambiguous


def table_intervals(document: str) -> dict[str, str]:
    """Agent name to stated schedule, from the agent table's second column.

    This document's dialect: a bare class name and ``every 300 s``, against
    ``README.md``'s backticked name and bare ``5 min``.  The extraction is
    per document; the comparison is not.
    """
    return {
        name: schedule.strip()
        for name, schedule in re.findall(
            r"^\| (\w+Agent) \| ([^|]+) \|", document, re.M
        )
    }


def diagram_intervals(document: str) -> dict[str, str]:
    """Agent name to schedule as drawn in the diagram's ``Agents`` column."""
    body = diagram(document).split("Agents (")[1]
    return {
        name: schedule
        for name, schedule in re.findall(r"[\u251c\u2514] (\w+Agent)\s+(every \d+ \w+)", body)
    }


def named_tables(document: str) -> set[str]:
    """Table names in the database section's grouping table."""
    section = document.split("### Database")[1].split("### Auth")[0]
    rows = [line for line in section.splitlines() if line.startswith("| ") and "`" in line]
    return {name for row in rows for name in re.findall(r"`(\w+)`", row.split("|")[2])}


# --------------------------------------------------------------------------
# The premises. An empty population makes every sweep below vacuous.


class TestThePopulationsAreNotEmpty:
    """Anti-vacuity: each sweep loops over a set, and an empty set passes."""

    def test_the_box_has_packages_agents_and_tables(self) -> None:
        assert len(live_packages()) >= 5, live_packages()
        assert len(live_agents()) == 5, live_agents()
        assert len(live_tables()) >= 10, live_tables()

    def test_the_document_has_the_two_fenced_blocks(self, document: str) -> None:
        assert len(_fenced_blocks(document)) >= 2

    def test_the_document_names_packages_agents_and_tables(self, document: str) -> None:
        assert diagram_packages(document)
        assert tree_packages(document)
        assert diagram_agents(document)
        assert table_agents(document)
        assert named_tables(document)


# --------------------------------------------------------------------------
# Membership, both directions


class TestThePackagesAgree:
    def test_the_tree_names_every_package_that_exists(self, document: str) -> None:
        missing = live_packages() - tree_packages(document)
        assert not missing, f"present on disk, absent from the tree: {sorted(missing)}"

    def test_the_tree_names_no_package_that_does_not(self, document: str) -> None:
        phantom = tree_packages(document) - live_packages()
        assert not phantom, f"in the tree, not on disk: {sorted(phantom)}"

    def test_the_diagram_names_every_package_that_exists(self, document: str) -> None:
        missing = live_packages() - diagram_packages(document)
        assert not missing, f"present on disk, absent from the diagram: {sorted(missing)}"

    def test_the_diagram_names_no_package_that_does_not(self, document: str) -> None:
        phantom = diagram_packages(document) - live_packages()
        assert not phantom, f"in the diagram, not on disk: {sorted(phantom)}"


class TestTheAgentsAgree:
    def test_the_table_names_every_agent_that_exists(self, document: str) -> None:
        missing = live_agents() - table_agents(document)
        assert not missing, f"a BaseAgent subclass absent from the table: {sorted(missing)}"

    def test_the_table_names_no_agent_that_does_not(self, document: str) -> None:
        phantom = table_agents(document) - live_agents()
        assert not phantom, f"in the agent table, not in the code: {sorted(phantom)}"

    def test_the_diagram_and_the_table_are_the_same_set(self, document: str) -> None:
        """The founding defect was a disagreement between exactly these two.

        The diagram drew five agents and the table listed four, and the one it
        dropped was not the one that had left — so a reader reconciling them
        got two wrong answers rather than one.
        """
        assert diagram_agents(document) == table_agents(document)


class TestTheIntervalsComeFromTheJobPlan:
    """The schedule is pinned to the scheduler's, never to the other document's.

    ``SNAG-DOCS-013``.  ``every 300 s`` here and ``5 min`` in ``README.md``
    are two statements of one fact and **neither was derived from anything**,
    so the day ``health_check_interval_seconds`` moves they can disagree with
    the box together and with each other separately.  Comparing the two
    documents would have caught only the second.

    :func:`planned_agent_intervals` reads ``plan_jobs``, which is the one
    statement of what the scheduler is asked to do — the lifespan and the
    reload both call it — so a leaf read of ``config.yaml`` was refused for
    ``max_priority_for``'s reason: it would be a second implementation of a
    derivation the plan already owns.

    Three sets are compared rather than two, because the founding defect of
    this file was the diagram and the table disagreeing.  An interval can
    fork exactly as an agent list did.
    """

    def test_every_interval_in_the_document_parses(self, document: str) -> None:
        """Anti-vacuity: the comparisons below are empty if the parse fails."""
        assert len(table_intervals(document)) == 5, table_intervals(document)
        assert len(diagram_intervals(document)) == 5, diagram_intervals(document)
        for name, text in table_intervals(document).items():
            assert interval_seconds(text) > 0, (name, text)

    def test_the_table_states_the_planned_interval(self, document: str) -> None:
        planned = planned_agent_intervals()
        for name, text in table_intervals(document).items():
            assert name in planned, f"{name} is in the table and not in the job plan"
            assert interval_seconds(text) == planned[name], (
                f"{name}: the table says {text!r} ({interval_seconds(text)} s), "
                f"the plan says {planned[name]} s"
            )

    def test_the_diagram_states_the_planned_interval(self, document: str) -> None:
        planned = planned_agent_intervals()
        for name, text in diagram_intervals(document).items():
            assert name in planned, f"{name} is in the diagram and not in the job plan"
            assert interval_seconds(text) == planned[name], (
                f"{name}: the diagram says {text!r} ({interval_seconds(text)} s), "
                f"the plan says {planned[name]} s"
            )

    def test_the_diagram_and_the_table_state_the_same_schedule(
        self, document: str
    ) -> None:
        """Both agree with the plan above, so this can only fail where one of
        them has stopped being reachable by its own extraction — which is how
        a wrong figure stayed green in ``TestJournalCommand`` and in
        ``test_it_is_scoped_to_this_agents_unresolved_rows``."""
        table = {n: interval_seconds(v) for n, v in table_intervals(document).items()}
        drawn = {n: interval_seconds(v) for n, v in diagram_intervals(document).items()}
        assert table == drawn

    def test_the_plan_has_no_agent_the_document_omits(self, document: str) -> None:
        missing = set(planned_agent_intervals()) - set(table_intervals(document))
        assert not missing, f"scheduled, absent from the table: {sorted(missing)}"


class TestTheTablesAgree:
    def test_the_database_section_names_every_mapped_table(self, document: str) -> None:
        missing = live_tables() - named_tables(document)
        assert not missing, f"mapped, absent from the database section: {sorted(missing)}"

    def test_the_database_section_names_no_table_that_is_not_mapped(
        self, document: str
    ) -> None:
        phantom = named_tables(document) - live_tables()
        assert not phantom, f"in the database section, not mapped: {sorted(phantom)}"

    def test_the_stated_count_is_the_measured_one(self, document: str) -> None:
        stated = re.search(r"\*\*(\d+) tables\*\*", document)
        assert stated, "the database section states no table count"
        assert int(stated.group(1)) == len(live_tables())


class TestTheProseMayStillRecordADeparture:
    """A pointer is required where a diagram node is forbidden.

    ``SNAG-DOCS-001``'s rule and the estate's *a moved document leaves a
    pointer, never a copy*: the file must be able to say a component left
    without that sentence tripping the phantom sweeps above.  This asserts the
    sweeps are scoped to the fenced blocks — the narrative still names
    ``ProjectOrganiserAgent``, deliberately, and the guard stays green.
    """

    def test_the_narrative_names_the_departed_agent(self, document: str) -> None:
        assert "ProjectOrganiserAgent" in document
        assert "ProjectOrganiserAgent" not in diagram(document)
        assert "ProjectOrganiserAgent" not in table_agents(document)

    def test_the_narrative_names_the_departed_packages(self, document: str) -> None:
        assert "`projects/` and `registry/`" in document or "registry" in document
        assert "registry" not in tree_packages(document)
        assert "projects" not in tree_packages(document)
