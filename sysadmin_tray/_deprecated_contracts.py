"""Contract models the tray re-exports and nothing reads — pending removal.

These five described **estate-manager's** routes on port 8400, not this
service's.  Project state left this repository on 2026-08-13 (ADR-0005)
and the models stayed behind in ``sysadmin/core/contracts.py``, where
they were indistinguishable from a model something parses.  That is
``SNAG-CFG-001``'s shape — a pydantic model that validates and no caller
consumes — and it is why ``SNAG-DOCS-002`` was filed.

Ten of the fifteen unreachable models were deleted outright on
2026-08-25.  These five survive here, and only here, because
``sysadmin_tray`` ships in the wheel
(``packages = ["sysadmin", "sysadmin_tray"]``), so removing a name from
``sysadmin_tray.models`` is a change to a published surface rather than
an internal tidy.  They are kept **importable and deprecated** for one
cycle, not kept in the contract registry: a registry that describes
routes this service does not serve is the document defect
``SNAG-DOCS-001`` already cost a sitting.

Three rules, two of them the opposite of the obvious implementation:

1. **They left ``contracts.py`` rather than being marked in place.**  A
   deprecation comment beside a live model is a second statement of
   which models are load-bearing, and it can disagree with the file it
   annotates — ``ops_claims.py`` rule 1 arriving in a Python module.
   Moving them makes the registry's membership the only statement:
   reachability from a served route is now a property a test can
   compute, and ``tests/test_contract_reachability.py`` computes it.
2. **The warning fires on *access*, never at import.**  ``models.py``
   imports nothing from here at module scope; a module ``__getattr__``
   (PEP 562) resolves these names lazily.  Warning at import would fire
   for every tray start whether or not anything touched a deprecated
   name, which trains the reader to filter the category — the same
   reason ``judge_audit_findings`` rule 3 collapses six toasts into one.
3. **Nothing here is a member of a live model, and that is checked
   rather than asserted.**  The set is closed under its own field
   references — ``PortfolioActionsResponse`` → ``PortfolioAction`` →
   ``RecommendationInfo``, ``ProjectRecommendationsResponse`` →
   ``RecommendationInfo``, ``ProjectReviewResponse`` → nothing — so
   moving them cannot strand a served payload.

**Removal is owed.**  Delete this module and the ``__getattr__`` in
``sysadmin_tray/models.py`` once a sitting confirms nothing outside this
repository imports the five names.  Filed as ``SNAG-DOCS-003``.

The producer still serves every route these describe:
``GET :8400/api/projects/{name}/recommendations``, ``/actions`` and
``/review``.  Nothing here parses them — which is the whole finding.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from sysadmin.core.contracts import Contract


class RecommendationInfo(Contract):
    """One actionable finding for a project.

    ``severity`` is ``advice`` (points behind it) or ``risk`` (no score
    impact but ranked first — e.g. no remote means no off-disk copy).
    """

    kind: str = ""  # risk | docs | config | hygiene | git | activity | todos | roadmap
    severity: str = "advice"
    title: str = ""
    detail: str = ""
    points: int = 0
    action: str = ""


class ProjectRecommendationsResponse(Contract):
    """GET /api/projects/{name}/recommendations."""

    project: str = ""
    status: str = "active"
    health_score: int = 0
    # Score if every recommendation were acted on (clamped to 100)
    potential_score: int = 0
    recommendations: list[RecommendationInfo] = Field(default_factory=list)
    count: int = 0
    scanned_at: str | None = None


class PortfolioAction(RecommendationInfo):
    """A recommendation tagged with the project it belongs to."""

    project: str = ""
    health_score: int = 0


class PortfolioActionsResponse(Contract):
    """GET /api/projects/actions — top housekeeping wins across projects.

    Ranked risk-first then by recoverable points; ``count`` is what was
    returned after ``limit``, ``total_available`` what existed before it.

    ``dropped_by_kind`` names what the limit cut, because this list
    saturates.  Its currency is recoverable score points, so anything
    worth 0 sorts last by construction — and 11 projects sharing one
    ``no_remote`` risk filled the entire default view, hiding every
    ``roadmap`` item behind a single systemic finding.  A total that says
    "68 available, 10 returned" does not tell you *what kind* of advice
    you stopped seeing; this does.
    """

    actions: list[PortfolioAction] = Field(default_factory=list)
    count: int = 0
    total_available: int = 0
    projects_with_actions: int = 0
    dropped_by_kind: dict[str, int] = Field(default_factory=dict)


class ProjectReviewResponse(Contract):
    """GET /api/projects/review — the latest stored portfolio review.

    ``llm_used`` False means llama-server was unavailable and
    ``narrative`` is the deterministic digest, not prose.  ``stats`` is
    the structured input the narrative was written from.
    """

    generated_at: str | None = None
    period_days: int = 7
    narrative: str = ""
    llm_used: bool = False
    model_used: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)


#: The names ``sysadmin_tray.models`` still resolves, with a warning.
DEPRECATED_NAMES: frozenset[str] = frozenset(
    {
        "RecommendationInfo",
        "ProjectRecommendationsResponse",
        "PortfolioAction",
        "PortfolioActionsResponse",
        "ProjectReviewResponse",
    }
)
