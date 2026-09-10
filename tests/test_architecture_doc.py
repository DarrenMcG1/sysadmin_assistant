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
"""

import ast
import re

import pytest

from sysadmin.core.config import REPO_ROOT
from sysadmin.metadata import Base

DOC_PATH = REPO_ROOT / "docs" / "ARCHITECTURE.md"
PACKAGE_ROOT = REPO_ROOT / "sysadmin"

#: Directories under ``sysadmin/`` that are not domains: the bytecode cache, and
#: ``core/models``/``*/models`` which the tree names by their parent instead.
NOT_A_DOMAIN = {"__pycache__", "models", "routers"}


@pytest.fixture(scope="module")
def document() -> str:
    return DOC_PATH.read_text()


# --------------------------------------------------------------------------
# What the box has


def live_packages() -> set[str]:
    """Every package directory directly under ``sysadmin/``."""
    return {
        child.name
        for child in PACKAGE_ROOT.iterdir()
        if child.is_dir() and child.name not in NOT_A_DOMAIN and (child / "__init__.py").exists()
    }


def live_agents() -> set[str]:
    """Every ``BaseAgent`` subclass, by an AST walk rather than an import.

    A walk sees a class the daemon has not imported yet; constructing the app
    to enumerate them would drop any agent behind a lazy import — the reading
    ``daemon_modules`` settled for a different population.
    """
    found: set[str] = set()
    for path in PACKAGE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                isinstance(base, ast.Name) and base.id == "BaseAgent" for base in node.bases
            ):
                found.add(node.name)
    return found


def live_tables() -> set[str]:
    """The mapped table set, from the module that exists to hold all of it.

    Keys are schema-qualified (``sysadmin.alerts``) because every model carries
    ``__table_args__['schema']``; the document names the bare table, which is
    what a ``psql`` reader types, so the prefix is dropped here rather than
    added there.
    """
    return {name.rpartition(".")[2] for name in Base.metadata.tables}


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
