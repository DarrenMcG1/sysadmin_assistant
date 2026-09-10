"""What the box has, stated once, for the three documents that describe it.

``docs/ARCHITECTURE.md``, ``README.md`` and ``docs/README.md`` all make the
same *class* of claim — which agents run, which routes are served, how the
repository is laid out — and until now only the first was swept against the
box (``SNAG-DOCS-011``).  ``SNAG-DOCS-013`` is the residue that named: the
guard was scoped to the file the entry mentioned rather than to the claim the
entry was about, and ``README.md`` is the *worse* exposure of the two, being
what ``github.com`` renders on arrival with no click and no search.

**This module is the box side and only the box side.**  Each document's
extraction stays in its own test module, because the three write the same fact
in different dialects — ``| SysAdminAgent | every 300 s |`` against
``| `SysAdminAgent` | 5 min |``.  What must not be written three times is
*what the box actually has*: three copies of :func:`live_agents` is the
second-statement defect this repository refuses everywhere else
(``SNAG-DB-003``'s shape, ``max_priority_for`` against ``PRIORITY_MAP``).
``tests/review_prompts.py`` is the precedent — one rule, three consumers.

Four rules, three of them the opposite of the obvious implementation:

1. **An interval is read from the job plan, never from a ``config.yaml``
   leaf.**  The obvious move is to parse the YAML and compare
   ``agents.sysadmin.health_check_interval_seconds`` to the document.
   :func:`sysadmin.core.jobs.plan_jobs` is the function the lifespan *and*
   the reload both call, so it is the one statement of what the scheduler is
   asked to do — and one job's interval is a *derivation* rather than a leaf
   (``desktop_reminder_sweep`` is ``max(60, tray_grace_seconds)``), so a leaf
   read would be a second implementation of the plan for the sake of reading
   one number a simpler way.  ``JOB_TARGETS`` then supplies job → agent, so
   no hand-written map can drift from the wiring.

2. **The dialects are parsed to one unit, not rendered per document** — the
   reverse of what ``SNAG-DOCS-013`` proposed, and cheaper.  Rendering
   ``300`` as ``every 300 s`` *and* as ``5 min`` requires this module to know
   which unit each document chose, so a document changing "5 min" to "300 s"
   for its own reasons would go red for no defect.  :func:`interval_seconds`
   parses either spelling into seconds, so the guard compares *quantities*
   and each document keeps whatever unit reads best.  An unrecognised unit
   raises rather than defaulting — ``ports_checked``'s rule, since a silent
   fallback would make a typo'd unit read as agreement.

3. **``parse_config``, never ``load_config``.**  ``load_config`` is
   ``set_config(parse_config(...))``, so a helper that merely *reads* the
   shipped file would install it into the process the rest of the suite
   shares.

4. **AST walks, never imports, for the class and label populations.**  A walk
   sees a class the daemon has not imported yet; ``daemon_modules`` settled
   that reading for a different population, and reaching the tray's tab
   labels by import would need a live ``QApplication``.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

import yaml

from sysadmin.core.config import REPO_ROOT
from sysadmin.metadata import Base

PACKAGE_ROOT = REPO_ROOT / "sysadmin"
TRAY_ROOT = REPO_ROOT / "sysadmin_tray"
DOCS_ROOT = REPO_ROOT / "docs"
ADR_ROOT = DOCS_ROOT / "adr"

#: Directories under ``sysadmin/`` that are not domains: the bytecode cache,
#: and ``*/models``/``*/routers``, which the documents name by their parent.
NOT_A_DOMAIN = {"__pycache__", "models", "routers"}

#: The four routes FastAPI mounts for its own documentation.  Every document
#: that states a route count states it *without* these and then says so, so
#: they are named here rather than subtracted by arithmetic at each reader.
FASTAPI_OWN_PATHS = frozenset(
    {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
)

#: How far a hedged, dated figure may drift before it misleads.  **Invented
#: and says so** — ``NOISE_MIN_OCCURRENCES``' status.  What it is chosen
#: against is the direction of the error rather than its size: the figures it
#: bounds — the roadmap's line count, the repository's Markdown total — only
#: ever grow, so it bounds how long a hedge stays honest and never whether
#: the sentence is true.  Two documents state the roadmap's figure, so the
#: tolerance is stated **here** rather than in either of their guards: a
#: constant one test module imports from another is the second-statement
#: defect wearing a test's clothes.
FIGURE_TOLERANCE = 0.15

#: Number words the documents spell out ("Five agents", "Ten records").  A
#: count written as a word is the same claim as one written as a digit and
#: goes stale the same way, so it is read rather than exempted — but only
#: over the range these documents actually use, since a map covering every
#: English number would be asserting a vocabulary nobody writes in.
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
}

#: Unit spellings :func:`interval_seconds` admits, mapped to seconds.  A bare
#: ``m`` is deliberately absent: it reads as both minutes and metres, and a
#: guard that guessed would be asserting its own reading of the document.
_UNITS = {
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
}


# --------------------------------------------------------------------------
# Populations on disk


def live_packages() -> set[str]:
    """Every package directory directly under ``sysadmin/``."""
    return {
        child.name
        for child in PACKAGE_ROOT.iterdir()
        if child.is_dir()
        and child.name not in NOT_A_DOMAIN
        and (child / "__init__.py").exists()
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
                isinstance(base, ast.Name) and base.id == "BaseAgent"
                for base in node.bases
            ):
                found.add(node.name)
    return found


def live_tables() -> set[str]:
    """The mapped table set, from the module that exists to hold all of it.

    Keys are schema-qualified (``sysadmin.alerts``) because every model
    carries ``__table_args__['schema']``; the documents name the bare table,
    which is what a ``psql`` reader types, so the prefix is dropped here
    rather than added there.
    """
    return {name.rpartition(".")[2] for name in Base.metadata.tables}


def live_migrations() -> set[str]:
    """Every Alembic revision, from Alembic's own ``ScriptDirectory``.

    Never a glob over ``alembic/versions/*.py`` — ``schema_guard``'s rule.  A
    second implementation of the revision graph drifts from the command it
    exists to measure against, and it would also count a file the graph does
    not reach.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config(str(REPO_ROOT / "alembic.ini")))
    return {script.revision for script in scripts.walk_revisions()}


def live_declared_services() -> set[str]:
    """Service names declared in ``services.yaml``."""
    document = yaml.safe_load((REPO_ROOT / "services.yaml").read_text())
    return {entry["name"] for entry in document["services"]}


def live_adr_ids() -> set[str]:
    """Decision-record ids, from the filenames in ``docs/adr/``.

    The id is the numeric stem, so ``0002-estate-manager.md`` — a pointer at
    a record that moved to estate-manager — counts.  A moved document leaves
    a pointer, and the index is required to list it.
    """
    return {path.name.split("-")[0] for path in ADR_ROOT.glob("[0-9]*.md")}


def live_dashboard_tabs() -> set[str]:
    """Tab labels the tray actually adds, by an AST walk of ``add_tab`` calls.

    An import would need a live ``QApplication`` and the PyQt6 extra; the
    label is the second positional argument and is a literal at every call
    site, so the walk reads it with no Qt in the way.
    """
    found: set[str] = set()
    for path in TRAY_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_tab"
                and len(node.args) == 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                found.add(node.args[1].value)
    return found


# --------------------------------------------------------------------------
# The route population


def live_routes() -> list[str]:
    """Every application route path, one entry per route object.

    One entry per *route*, not per path: ``/api/sysadmin/dnd`` is registered
    by a ``@router.get`` and a ``@router.post`` and is therefore two routes
    serving one path.  The distinction is not pedantry — it is the defect
    ``SNAG-DOCS-013``'s fix found in ``README.md``, whose headline counted
    routes while its own table counted paths, so the rows summed to one less
    than the total above them and no reader could reconcile the two.
    """
    from sysadmin.main import create_app

    return [
        route.path
        for route in create_app().routes
        if route.path not in FASTAPI_OWN_PATHS
    ]


def live_routers() -> int:
    """How many routers ``create_app`` includes, by an AST walk of it.

    Counted at the source rather than off ``app.routes``, because FastAPI
    keeps no router identity once a route is mounted — a count taken from the
    running app would have to infer routers from path prefixes, which is the
    document's own claim and cannot check it.
    """
    tree = ast.parse((PACKAGE_ROOT / "main.py").read_text())
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
    )


def routes_by_prefix(prefixes: list[str]) -> tuple[Counter[str], list[str]]:
    """Partition :func:`live_routes` over a document's own prefix list.

    The document supplies the partition and this checks it for *totality*
    against the box, which is the honest direction: a document claiming eight
    prefixes is claiming they account for every route, so a route matching
    none of them is returned as unclassified rather than dropped — zero
    unaccounted-for must not be indistinguishable from nobody having looked
    (``ports_checked``'s rule).

    Longest prefix first, so ``/api/sysadmin/*`` cannot swallow a route that
    a more specific documented prefix owns.
    """
    ordered = sorted(prefixes, key=len, reverse=True)
    counts: Counter[str] = Counter()
    unclassified: list[str] = []
    for path in live_routes():
        for prefix in ordered:
            if path == prefix or path.startswith(prefix.rstrip("*")):
                counts[prefix] += 1
                break
        else:
            unclassified.append(path)
    return counts, unclassified


# --------------------------------------------------------------------------
# The schedule, derived rather than restated


def planned_agent_intervals() -> dict[str, int]:
    """Each agent class's scheduled interval in seconds, from the job plan.

    ``plan_jobs`` is the one statement of what the scheduler is asked to do —
    the lifespan and the reload both call it — and ``JOB_TARGETS`` maps a job
    id to the bound method it fires, so the owning class comes from the
    wiring rather than from a table written here.  Only agents are returned:
    ``desktop_reminder_sweep`` fires a :class:`DesktopNotifier` method and is
    not a ``BaseAgent``, so it falls out by the same test the documents use.
    """
    from sysadmin.core.config import parse_config
    from sysadmin.core.jobs import plan_jobs
    from sysadmin.main import JOB_TARGETS

    agents = live_agents()
    config = parse_config(REPO_ROOT / "config.yaml")
    intervals: dict[str, int] = {}
    for spec in plan_jobs(config):
        if spec.trigger != "interval":
            continue
        owner = getattr(JOB_TARGETS[spec.job_id], "__self__", None)
        name = type(owner).__name__
        if name not in agents:
            continue
        kwargs = spec.trigger_kwargs
        seconds = int(kwargs.get("seconds", 0)) + int(kwargs.get("hours", 0)) * 3600
        intervals[name] = seconds
    return intervals


def interval_seconds(text: str) -> int:
    """Parse a document's stated interval into seconds.

    Serves every dialect at once — ``every 300 s``, ``5 min``, ``1 h`` — so a
    document may state the quantity in whatever unit reads best and this
    compares the quantity rather than the spelling.  An unrecognised unit
    raises: returning a default would make a typo read as agreement, which is
    the collapse ``ports_checked`` refuses at the size of a word.
    """
    stripped = text.strip().removeprefix("every").strip()
    number, _, unit = stripped.partition(" ")
    unit = unit.strip().lower()
    if unit not in _UNITS:
        raise ValueError(f"unrecognised interval unit in {text!r}: {unit!r}")
    return int(number) * _UNITS[unit]


# --------------------------------------------------------------------------
# Link resolution


def unresolved_links(document: Path) -> list[str]:
    """Relative Markdown link targets in ``document`` that do not exist.

    Anchors are stripped and absolute URLs skipped: what is checkable from
    here is whether a path this repository ships resolves, and a published
    index whose links 404 is the same class of defect as one whose tables are
    stale — a reader following it concludes the thing is gone.
    """
    import re

    missing: list[str] = []
    for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path = target.split("#", 1)[0]
        if not path:
            continue
        if not (document.parent / path).exists():
            missing.append(target)
    return missing


# --------------------------------------------------------------------------
# The route → contract binding


#: HTTP methods Starlette adds to a route without anyone writing them.  They
#: are dropped rather than compared, because no document states them and a
#: registry row naming ``HEAD`` would be describing the framework.
_IMPLICIT_METHODS = frozenset({"HEAD", "OPTIONS"})

_PATH_PARAMETER = re.compile(r"\{[^}]+\}")


def normalise_path(path: str) -> str:
    """Replace every path parameter with ``{}``.

    ``CLAUDE.md``'s registry writes ``{id}`` and ``{name}`` where the handlers
    write ``{alert_id}`` and ``{service_name}``, and a set comparison over the
    raw strings reports three phantom gaps beside three phantom stale rows.  A
    parameter's *name* appears in no URL a client builds, so pinning the
    spelling would make the guard demand the document restate handler-local
    variable names — :func:`interval_seconds`' rule, one document over:
    compare the quantity, never the spelling.

    The collapse is only safe while it is injective over the live route set,
    which is a property of the box rather than of this function, so a test
    measures it rather than this docstring asserting it.
    """
    return _PATH_PARAMETER.sub("{}", path)


def live_route_contracts() -> dict[tuple[str, str], str | None]:
    """Every served ``(method, normalised path)`` → the contract pinning it.

    The value is the name of the :mod:`sysadmin.core.contracts` class the
    route declares as ``response_model=``, or ``None`` where it declares none
    or declares something that is not a contract — ``GET
    /api/services/by-project`` returns a bare ``dict``, which pins nothing.

    **The class must come from ``contracts.py`` itself**, not merely be a
    pydantic model: the registry is an index of that module, so a route
    pinned to a model defined beside its router is unpinned *for this
    purpose* and belongs in the document's exemption table with that as its
    reason.  Empty population today and stated rather than left silent.

    One entry per ``(method, path)`` rather than per path, because
    ``/api/sysadmin/dnd`` is one path registered by a ``@router.get`` and a
    ``@router.post`` — the distinction that produced ``README.md``'s
    irreconcilable headline in ``SNAG-DOCS-013``.
    """
    import inspect

    from sysadmin.core import contracts
    from sysadmin.main import create_app

    contract_names = {
        name
        for name, obj in vars(contracts).items()
        if inspect.isclass(obj) and obj.__module__ == contracts.__name__
    }

    bound: dict[tuple[str, str], str | None] = {}
    for route in create_app().routes:
        if route.path in FASTAPI_OWN_PATHS:
            continue
        model = getattr(route, "response_model", None)
        name = getattr(model, "__name__", None)
        pinned = name if name in contract_names else None
        for method in getattr(route, "methods", set()) - _IMPLICIT_METHODS:
            bound[(method, normalise_path(route.path))] = pinned
    return bound
