"""Every model in the contract registry is reachable from a reader.

``SNAG-DOCS-002``: ``sysadmin/core/contracts.py`` carried eight response
models describing routes that left for estate-manager on 2026-08-13
(ADR-0005), plus seven members reachable only from those eight.  Fifteen
models pydantic validated and nothing consumed — ``SNAG-CFG-001``'s shape
in the file ``CLAUDE.md`` calls the contract registry.

The entry was measured three times and wrong three times, always in the
same way: **by grepping for the model's name**.  That question is "does
anything mention this", and it is not the question.  Two failures follow
from it, in opposite directions:

* A member of a served payload has **no mention anywhere** and is
  load-bearing.  ``RamInfo`` is a field of ``ResourceResponse``; nothing
  outside this file names it.  A grep reports 32 models with no external
  reader and 17 of them are like that.  Session 76 put ``ProjectHealthInfo``
  in the dead set on exactly this evidence — it is a field of
  ``ManagedProjectInfo``, the ``response_model`` of the one ``/api/projects``
  route this service still serves.
* A **docstring** counts as a mention.  ``RecommendationInfo``'s only
  reference outside this file was a line of prose in
  ``units/recommendations.py`` contrasting it with
  ``UnitRecommendationInfo``.

So the property is *reachability*, not reference count, and the detector
is an **AST walk rather than a grep**.  Three rules:

1. **A root is a name used, never a name imported.**  ``ast.Import`` and
   ``ast.ImportFrom`` are skipped, which is what makes the tray's
   re-export list not a reader — the distinction Session 58 stated in
   prose ("a name in an import list and not a caller") and then measured
   with a tool that cannot draw it.  Docstrings are ``ast.Constant`` and
   fall out for free, so no prose heuristic is needed.
2. **``response_model=`` needs no special case.**  It is an ``ast.Name``
   in a keyword argument, so rule 1 already catches it.  A second rule
   naming it would be a second statement of one fact.
3. **The closure follows field annotations and base classes**, which is
   how a served payload keeps its members alive.  ``PortfolioAction``
   subclasses ``RecommendationInfo``; deleting the parent while the child
   lives is the failure this direction of the edge prevents.

Two of the tests below exist so the detector can be seen to fail —
``tests/test_autogenerate_config.py``'s rule, for its reason: a walker
that reports nothing is indistinguishable from a walker that finds
nothing.

**One limit, measured rather than reasoned about.**  ``tests`` is a
consumer package on purpose — a model exercised only by its round-trip
test is consumed, and excluding them would report every parse-side
contract as dead.  The cost is that a name this suite mentions is a root
by that mention alone.  Driving the walker at the pre-fix registry
reports **12** of the 15, not 15: ``PortfolioAction`` and
``RecommendationInfo`` leak in from ``_deprecated_contracts``'s own field
annotations and base class, and ``PortfolioActionsResponse`` from
``models.PortfolioActionsResponse`` in ``TestDeprecatedNamesLeftTheRegistry``
below.  So those three cannot be judged by reachability any more, and
``test_none_of_them_are_defined_in_contracts`` is what covers them —
two tests composing rather than one doing both.  A synthetic name is not
subject to it, which is why the falsification below uses one and why
this had to be driven at the real pre-fix file to be seen at all.
"""

from __future__ import annotations

import ast
import pathlib
import warnings

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "sysadmin/core/contracts.py"

#: Packages searched for readers.  ``tests`` is included deliberately: a
#: model exercised only by its round-trip test is still consumed, and
#: excluding them would report every parse-side contract as dead.
CONSUMER_PACKAGES = ("sysadmin", "sysadmin_tray", "tests")

#: Names ``sysadmin_tray.models`` still resolves, deprecated, pending
#: removal under ``SNAG-DOCS-003``.  They must not be back in the
#: registry — that is what this session moved them out of.
DEPRECATED_NAMES = frozenset(
    {
        "RecommendationInfo",
        "ProjectRecommendationsResponse",
        "PortfolioAction",
        "PortfolioActionsResponse",
        "ProjectReviewResponse",
    }
)


def model_graph(source: str) -> tuple[set[str], dict[str, set[str]]]:
    """Models defined in ``source``, and what each one references.

    An edge runs from a model to every model it names in a field
    annotation or a base class — the direction that keeps a member of a
    served payload alive.
    """
    tree = ast.parse(source)
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    edges: dict[str, set[str]] = {name: set() for name in classes}
    for name, node in classes.items():
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in classes:
                edges[name].add(base.id)
        for sub in ast.walk(node):
            if isinstance(sub, ast.AnnAssign) and sub.annotation is not None:
                for ref in ast.walk(sub.annotation):
                    if isinstance(ref, ast.Name) and ref.id in classes:
                        edges[name].add(ref.id)
    return set(classes), edges


def roots(sources: dict[pathlib.Path, str], classes: set[str]) -> set[str]:
    """Models *used* by something other than the registry itself.

    Import statements are skipped, so a name that only appears in an
    import list is not a root.  That is the whole distinction the
    grep-based measurements could not draw.
    """
    found: set[str] = set()
    for path, source in sources.items():
        for node in ast.walk(ast.parse(source, filename=str(path))):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Name) and node.id in classes:
                found.add(node.id)
            elif isinstance(node, ast.Attribute) and node.attr in classes:
                found.add(node.attr)
    return found


def reachable(classes: set[str], edges: dict[str, set[str]], seeds: set[str]) -> set[str]:
    """Transitive closure of ``seeds`` over ``edges``."""
    seen: set[str] = set()
    stack = list(seeds & classes)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        stack.extend(edges[name] - seen)
    return seen


def _consumer_sources() -> dict[pathlib.Path, str]:
    out: dict[pathlib.Path, str] = {}
    for package in CONSUMER_PACKAGES:
        for path in (REPO / package).rglob("*.py"):
            if path == CONTRACTS:
                continue
            out[path] = path.read_text()
    return out


@pytest.fixture(scope="module")
def registry() -> tuple[set[str], dict[str, set[str]], set[str]]:
    classes, edges = model_graph(CONTRACTS.read_text())
    return classes, edges, roots(_consumer_sources(), classes)


class TestRegistryIsReachable:
    def test_every_model_is_reachable_from_a_reader(self, registry) -> None:
        classes, edges, seeds = registry
        orphans = sorted(classes - reachable(classes, edges, seeds))
        assert orphans == [], (
            "contract models with no reader and no live model reaching them — "
            "either wire them to a consumer or move them out of the registry "
            f"(SNAG-DOCS-002): {orphans}"
        )

    def test_a_member_of_a_served_payload_counts_as_reachable(self, registry) -> None:
        """The false positive that put ``ProjectHealthInfo`` in the dead set."""
        classes, edges, seeds = registry
        assert "ProjectHealthInfo" not in seeds  # nothing names it
        assert "ProjectHealthInfo" in edges["ManagedProjectInfo"]
        assert "ProjectHealthInfo" in reachable(classes, edges, seeds)


class TestDetectorCanFail:
    """Two tests that trip the walker, so its silence means something."""

    SYNTHETIC = (
        "class Contract:\n"
        "    pass\n"
        "\n"
        "class Served(Contract):\n"
        "    member: Member | None = None\n"
        "\n"
        "class Member(Contract):\n"
        "    x: int = 0\n"
        "\n"
        "class Stranded(Contract):\n"
        "    y: int = 0\n"
    )

    def test_an_unreachable_model_is_reported(self) -> None:
        classes, edges = model_graph(self.SYNTHETIC)
        seeds = roots({pathlib.Path("c.py"): "print(Served())"}, classes)
        orphans = classes - reachable(classes, edges, seeds)
        assert orphans == {"Stranded"}, orphans

    def test_an_import_list_entry_is_not_a_reader(self) -> None:
        """The rule the three grep measurements could not express."""
        classes, _ = model_graph(self.SYNTHETIC)
        importer = {pathlib.Path("m.py"): "from x import Served, Member, Stranded\n"}
        assert roots(importer, classes) == set()


class TestDeprecatedNamesLeftTheRegistry:
    def test_none_of_them_are_defined_in_contracts(self) -> None:
        classes, _ = model_graph(CONTRACTS.read_text())
        assert classes & DEPRECATED_NAMES == set()

    def test_the_deprecated_set_is_closed_under_its_own_references(self) -> None:
        """Moving them cannot strand a member behind in the registry."""
        from sysadmin_tray import _deprecated_contracts as dep

        assert dep.DEPRECATED_NAMES == DEPRECATED_NAMES
        classes, edges = model_graph(
            (REPO / "sysadmin_tray/_deprecated_contracts.py").read_text()
        )
        for name in DEPRECATED_NAMES:
            assert edges[name] <= classes, name

    def test_a_deprecated_name_resolves_and_warns(self) -> None:
        from sysadmin_tray import models

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parsed = models.PortfolioActionsResponse.model_validate({})
        assert parsed.count == 0
        assert [w.category for w in caught] == [DeprecationWarning]
        assert "SNAG-DOCS-003" in str(caught[0].message)

    def test_a_live_re_export_does_not_warn(self) -> None:
        """``__getattr__`` runs only after normal lookup fails."""
        from sysadmin_tray import models

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            models.ManagedProjectsResponse.model_validate({})
        assert caught == []

    def test_an_unknown_name_still_raises_attribute_error(self) -> None:
        from sysadmin_tray import models

        with pytest.raises(AttributeError, match="NoSuchContract"):
            models.NoSuchContract
