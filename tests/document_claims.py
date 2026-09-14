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
import subprocess
from collections import Counter
from dataclasses import dataclass
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
    "fourteen": 14,
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


def tracked_lines(pathspec: str) -> int:
    """Lines in every **tracked** file matching ``pathspec``.

    The box side of every hedged line-count sentence, stated once here for
    :data:`FIGURE_TOLERANCE`'s own reason — it was written inline in
    ``test_readme_claims.py`` and again in ``test_docs_index.py``, two
    implementations of one measurement, which is the defect those guards
    exist to catch arriving inside the guards (``SNAG-DB-003``'s shape).

    Three rules, two of them the opposite of the obvious implementation:

    1. **Tracked, never a filesystem walk.**  ``git ls-files`` is what
       decides the population, so an untracked scratch file, a ``.venv``
       and this session's own ``.bak`` artefacts are excluded by the same
       fact that makes them absent from the published repository — which
       is the population every one of these sentences is about.  A
       ``Path.rglob`` would count whatever happens to be lying about and
       give a different answer on two checkouts of one commit.
    2. **The pathspec is git's, so ``*.md`` is recursive.**  Git's
       wildmatch lets ``*`` cross ``/`` unless ``:(glob)`` magic says
       otherwise, which is why ``*.md`` reaches ``docs/adr/`` and reads as
       the whole-repository total the sentences claim.  Spelling it
       ``**/*.md`` would be the same set by accident rather than by rule.
    3. **A deleted-but-still-indexed path is skipped, not an error.**
       ``git ls-files`` lists the index; a file removed from the worktree
       without ``git rm`` is named and absent, and raising there would
       make an unrelated dirty tree read as a documentation defect.
    """
    files = subprocess.run(
        ["git", "ls-files", pathspec],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return sum(
        len((REPO_ROOT / name).read_text().splitlines())
        for name in files
        if (REPO_ROOT / name).exists()
    )


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


def contract_class_names() -> set[str]:
    """Every class :mod:`sysadmin.core.contracts` itself defines.

    Stated once because both halves of the membership rule need it: the
    producer half asks whether a route's ``response_model`` is one of these,
    and the consumer half whether the model the tray parses with is.  Two
    copies of this set is the second-statement defect the registry exists to
    keep out of the document.

    Membership is by ``__module__``, so a name merely *imported* into that
    module is not a contract — the registry is an index of what that file
    declares.
    """
    import inspect

    from sysadmin.core import contracts

    return {
        name
        for name, obj in vars(contracts).items()
        if inspect.isclass(obj) and obj.__module__ == contracts.__name__
    }


def live_route_contracts() -> dict[tuple[str, str], str | None]:
    """Every served ``(method, normalised path)`` → the contract pinning it.

    The value is the name of the :mod:`sysadmin.core.contracts` class the
    route declares as ``response_model=``, or ``None`` where it declares none
    or declares something that is not a contract.

    **Both halves of that ``None`` have an empty population as of
    2026-09-10**, stated rather than left silent — ``ports_checked``'s rule
    at the size of a docstring, since twenty routes reaching ``None`` by the
    first limb reads exactly like a walk finding the second.  ``GET
    /api/services/by-project`` was the second limb's only member: it
    annotated ``-> dict``, from which FastAPI infers a ``response_model`` of
    ``dict``, so it *declared* one and pinned nothing.  ``SNAG-DOCS-018``
    pinned it, and what is left under ``None`` is twenty routes declaring no
    model at all.

    **The class must come from ``contracts.py`` itself**, not merely be a
    pydantic model: the registry is an index of that module, so a route
    pinned to a model defined beside its router is unpinned *for this
    purpose* and belongs in the document's exemption table with that as its
    reason.  Empty population today, and it is the same emptiness as above
    read from the other end.

    One entry per ``(method, path)`` rather than per path, because
    ``/api/sysadmin/dnd`` is one path registered by a ``@router.get`` and a
    ``@router.post`` — the distinction that produced ``README.md``'s
    irreconcilable headline in ``SNAG-DOCS-013``.
    """
    from sysadmin.main import create_app

    contract_names = contract_class_names()

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


# --------------------------------------------------------------------------
# The consumer half of the contract registry


#: Attributes holding a base URL in :mod:`sysadmin_tray.client`, mapped to the
#: prefix ``CLAUDE.md`` writes for that producer.  The estate's routes are
#: written ``:8400/api/projects/overview`` in the *consumed* table, and this
#: is what keeps the walk from claiming this service serves them —
#: ``SNAG-DOCS-001``'s shape, a document naming a route its subject does not
#: serve, arriving from the consumer side.
_TRAY_BASE_URLS = {"_api_url": "", "_estate_api_url": ":8400"}

#: Call attributes that parse a payload into a model.  ``from_dict`` is this
#: repository's; ``model_validate`` is pydantic's own and is admitted because
#: a future parse written the pydantic way is the same claim.
_PARSE_ATTRS = frozenset({"from_dict", "model_validate"})

_HTTP_VERBS = frozenset({"get", "post", "put", "delete", "patch"})


@dataclass(frozen=True)
class TrayConsumption:
    """What the tray asks for, and what it parses the answer with."""

    #: Every ``(METHOD, path)`` the tray requests, whether or not it parses
    #: the body.  ``POST /api/files/scan`` is here and absent from
    #: :attr:`parses`, which is exactly what its exemption reason claims.
    requests: frozenset[tuple[str, str]]
    #: ``(METHOD, path)`` → the model names the reply is handed to.  Names are
    #: **raw**: whether a name is a ``contracts.py`` class is a fact about
    #: that module rather than about this source, and filtering here would
    #: make "parsed by something that is not a contract" and "not parsed at
    #: all" spell the same way.
    parses: dict[tuple[str, str], frozenset[str]]
    #: Functions that issue a request whose path is a *parameter* and parse
    #: through a parameter — the ``_fetch_file_endpoint`` shape.  Reported so
    #: a test can pin the population rather than the walk assuming it.
    indirect_helpers: frozenset[str]


def _tray_literal_path(node: ast.AST) -> str | None:
    """The URL out of ``f"{self._api_url}/api/x"``, or ``None`` if not literal.

    A path parameter interpolated mid-string (``{project_name}``) renders as
    ``{}``, which is :func:`normalise_path`'s spelling — so the two halves of
    the registry are compared in one vocabulary without a second conversion.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value if node.value.startswith("/") else None
    if not isinstance(node, ast.JoinedStr):
        return None
    prefix, parts = None, []
    for part in node.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            parts.append(part.value)
        elif isinstance(part, ast.FormattedValue):
            attr = ast.unparse(part.value).rsplit(".", 1)[-1]
            if attr in _TRAY_BASE_URLS and not parts:
                prefix = _TRAY_BASE_URLS[attr]
            else:
                parts.append("{}")
    joined = "".join(parts)
    if not joined.startswith("/"):
        return None
    return (prefix or "") + joined


def _tray_request_verb(node: ast.AST) -> str | None:
    """``GET`` for ``self._client.get(...)``, path literal or not.

    Deliberately does **not** require a literal path, unlike
    :func:`_tray_request`.  The indirect helper's whole shape is that its
    path is a parameter, so a single predicate demanding one drops it —
    silently, and with it five of this tray's sixteen parses.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr in _HTTP_VERBS):
        return None
    if not (isinstance(func.value, ast.Attribute) and func.value.attr == "_client"):
        return None
    return func.attr.upper()


def _tray_request(node: ast.AST) -> tuple[str, str] | None:
    """``(METHOD, path)`` for a request written with a literal path."""
    verb = _tray_request_verb(node)
    if verb is None or not getattr(node, "args", None):
        return None
    path = _tray_literal_path(node.args[0])
    return (verb, path) if path else None


def _tray_parsed_name(node: ast.AST) -> str | None:
    """The model name in ``Model.from_dict(...)``.

    Keyed on the **call**, never on the name appearing in the module.
    ``sysadmin_tray/models.py`` re-exports ``contracts.py`` wholesale, so a
    name is present for reasons unrelated to any route and a name-keyed sweep
    answers "true" for all of them — which is why ``SNAG-DOCS-017`` was an
    entry rather than an extension of the producer half.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in _PARSE_ATTRS:
        if isinstance(func.value, ast.Name):
            return func.value.id
    return None


def _tray_functions() -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]]:
    out = []
    for path in sorted(TRAY_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append((node, path.name))
    return out


def tray_consumption() -> TrayConsumption:
    """Pair every tray request with the model its reply is parsed by.

    The producer half of the registry's membership rule is readable off
    ``create_app()``, because FastAPI *stores* ``response_model`` on the route
    object.  The consumer half has no such object: the pairing exists only as
    adjacency in a function body, so it is a syntax walk or it is nothing.

    Four rules, three of them the opposite of the obvious implementation:

    1. **The anchor is the nearest preceding request, never the enclosing
       function.**  ``fetch_status`` issues ``/health`` for liveness and then
       ``/api/sysadmin/status``, and parses once — so a function-level
       pairing claims the tray parses ``/health`` with ``StatusResponse``.
       It is the only method here that requests twice, which makes the rule
       observable on exactly one specimen and that specimen the reason it is
       needed.  ``log_actions.group_incidents``' anchor rule, one seam over.

    2. **The base URL is part of the identity.**  ``_estate_api_url`` renders
       the ``:8400`` prefix the *consumed* table already writes; without it
       the walk reports this service as serving the estate's two project
       routes.

    3. **The indirect helper is found by shape, never by name, and the
       benefit is measured rather than argued.**  A helper is a function
       that requests with a non-literal path *and* parses through one of its
       own parameters.  Keying on ``_fetch_file_endpoint`` gives the
       identical answer today — one helper, sixteen parses — so the two
       implementations are indistinguishable on this population and the
       structural one looks like ceremony.  Driven at a *second* helper
       added under a different name and parsing an exempted route, the
       name-keyed version ships **entirely green** while this one goes red
       on three tests.  That is the silence this whole entry is about,
       reproduced inside the fix for it.

    4. **The whole tray is walked, not ``client.py``.**  Measured 2026-09-10
       every HTTP call in this package is in that one module, and walking
       only it would turn that measurement into an assumption a later commit
       could falsify without failing anything.
    """
    requests: set[tuple[str, str]] = set()
    parses: dict[tuple[str, str], set[str]] = {}
    helpers: dict[str, tuple[str, int, int]] = {}

    for func, _module in _tray_functions():
        params = [arg.arg for arg in func.args.args]
        events: list[tuple[int, int, int, object]] = []
        verbs: set[str] = set()
        non_literal = False
        for node in ast.walk(func):
            verb = _tray_request_verb(node)
            if verb is not None:
                verbs.add(verb)
                pair = _tray_request(node)
                if pair is None:
                    non_literal = True
                else:
                    events.append((node.lineno, node.col_offset, 0, pair))
            name = _tray_parsed_name(node)
            if name is not None:
                events.append((node.lineno, node.col_offset, 1, name))

        # Rule 3: a helper requests a path it was handed and parses through a
        # parameter.  Both halves are required — a function taking a model and
        # requesting a literal path is an ordinary fetcher.
        if non_literal and verbs:
            parsed_params = {
                name
                for _l, _c, kind, name in events
                if kind == 1 and isinstance(name, str) and name in params
            }
            if len(verbs) == 1 and len(parsed_params) == 1:
                model_param = parsed_params.pop()
                path_params = [p for p in params if p not in {"self", model_param}]
                # The path parameter is the one interpolated into the request.
                interpolated = {
                    ast.unparse(part.value)
                    for node in ast.walk(func)
                    if _tray_request_verb(node) is not None
                    and getattr(node, "args", None)
                    and isinstance(node.args[0], ast.JoinedStr)
                    for part in node.args[0].values
                    if isinstance(part, ast.FormattedValue)
                }
                path_param = next(
                    (p for p in path_params if p in interpolated), None
                )
                if path_param is not None:
                    helpers[func.name] = (
                        next(iter(verbs)),
                        params.index(path_param),
                        params.index(model_param),
                    )

        # Rule 1: each parse belongs to the request most recently issued.
        events.sort(key=lambda event: (event[0], event[1]))
        current: tuple[str, str] | None = None
        for _lineno, _col, kind, payload in events:
            if kind == 0:
                current = payload  # type: ignore[assignment]
                requests.add(current)
            elif current is not None and isinstance(payload, str):
                parses.setdefault(current, set()).add(payload)

    # Resolve each helper's call sites: path and model are arguments there.
    for func, _module in _tray_functions():
        for node in ast.walk(func):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            spec = helpers.get(node.func.attr)
            if spec is None:
                continue
            verb, path_index, model_index = spec
            args = node.args
            # ``self`` is bound by the attribute access, so positional
            # arguments are offset by one.
            path_at, model_at = path_index - 1, model_index - 1
            if not (0 <= path_at < len(args) and 0 <= model_at < len(args)):
                continue
            path = _tray_literal_path(args[path_at])
            model = args[model_at]
            if path and isinstance(model, ast.Name):
                pair = (verb, path)
                requests.add(pair)
                parses.setdefault(pair, set()).add(model.id)

    return TrayConsumption(
        requests=frozenset(requests),
        parses={pair: frozenset(names) for pair, names in parses.items()},
        indirect_helpers=frozenset(helpers),
    )
