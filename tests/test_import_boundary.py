"""The module boundary, enforced.

``sysadmin/monitor`` must not import ``sysadmin.projects``. Monitoring is
the half that has to keep working when the organiser is stopped (Phase 6
gives it its own timer), and an import is how that independence rots
without anyone noticing.

The check is textual and direct: it does not follow transitive imports.
An indirect route through ``sysadmin.core`` would pass here, so the phase
report lists those separately rather than relying on this test alone.
"""

import ast
from pathlib import Path

FORBIDDEN = "sysadmin.projects"
PACKAGE = Path(__file__).resolve().parents[1] / "sysadmin" / "monitor"


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_monitor_does_not_import_projects():
    offenders = []
    for path in PACKAGE.rglob("*.py"):
        for module in imported_modules(path):
            if module == FORBIDDEN or module.startswith(f"{FORBIDDEN}."):
                offenders.append(f"{path}: {module}")
    assert not offenders, "monitor must not import projects:\n" + "\n".join(offenders)


def test_package_under_test_exists():
    """Guard against the boundary test passing because the path is wrong."""
    assert PACKAGE.is_dir(), f"{PACKAGE} not found — adjust parents[1]"
    assert list(PACKAGE.rglob("*.py")), f"no modules found under {PACKAGE}"


def test_core_and_registry_do_not_import_domains():
    """The shared layers are depended on, never depending.

    Not asked for by the brief, but a ``core`` that imports a domain
    turns every boundary above it into a fiction: monitor would reach
    projects through core while the test above stayed green.
    """
    # `sysadmin.estate` joined this tuple on 2026-08-31 (SNAG-AGENT-011).
    # It was missing from the day the package was created: it is a domain
    # by its own module docstring's argument — *"a package rather than a
    # module in monitor/ because it is a domain"* — and `core` importing
    # it would have gone unremarked. Nothing had ever done so, so this
    # adds a guard rather than fixing a breach; it is added now because
    # that sitting gave `monitor` its first import edge into `estate`,
    # and a boundary is easiest to state while somebody is looking at it.
    domains = ("sysadmin.monitor", "sysadmin.projects", "sysadmin.files",
               "sysadmin.units", "sysadmin.briefing", "sysadmin.estate")
    root = PACKAGE.parent
    offenders = []
    for layer in ("core", "registry"):
        for path in (root / layer).rglob("*.py"):
            for module in imported_modules(path):
                if any(module == d or module.startswith(f"{d}.") for d in domains):
                    offenders.append(f"{path}: {module}")
    assert not offenders, "core/registry must not import a domain:\n" + "\n".join(offenders)


def test_no_domain_imports_a_composition_root():
    """The five composition roots are imported by nothing below them.

    ``main``, ``metadata``, ``reload``, ``ops_claims`` and ``snag_claims``.

    ``sysadmin/metadata.py`` states the rule — *"both are composition
    roots: they are allowed to import every domain, and no domain imports
    them"* — and until ``sysadmin/reload.py`` joined them nothing checked
    it. It is what keeps the composition roots free to import across every
    boundary the two tests above defend: the moment a domain imports one,
    it has a transitive route to every other domain and both of those
    tests stay green while meaning nothing.

    It is also load-bearing for the reload path specifically. ``reload``
    composes ``core.config`` with ``monitor.services``, so a router that
    imported it would give ``monitor`` an import edge to every domain
    ``reload`` may grow. ``ops_claims`` joined them for the same reason
    read the other way: it counts the routes ``create_app`` declares, so
    it imports every domain transitively and belongs nowhere below.
    ``snag_claims`` joined them on 2026-08-25 for a third reason again: it
    *drives* a domain to reproduce a claim — ``units.scan.discover_units``,
    over a synthetic unit tree — and the next check written will drive
    another, so it would break this rule the first time anyone extended it
    from ``core``.
    """
    roots = (
        "sysadmin.main",
        "sysadmin.metadata",
        "sysadmin.reload",
        "sysadmin.ops_claims",
        "sysadmin.snag_claims",
    )
    package = PACKAGE.parent
    offenders = []
    for path in package.rglob("*.py"):
        if path.parent == package and path.stem in {
            "main", "metadata", "reload", "ops_claims", "snag_claims", "__init__"
        }:
            continue
        for module in imported_modules(path):
            if module in roots or any(module.startswith(f"{r}.") for r in roots):
                offenders.append(f"{path.relative_to(package.parent)}: {module}")
    assert not offenders, (
        "a composition root must be imported by nothing below it:\n"
        + "\n".join(offenders)
    )


def test_monitor_may_read_the_estate_client_but_never_its_judge():
    """The service family consults a fact; it does not borrow a verdict.

    ``SNAG-AGENT-011`` gave :mod:`sysadmin.monitor.agent` an import edge
    into :mod:`sysadmin.estate`, so that a service measured unreachable
    can ask whether the estate's arbiter stopped it on purpose.  The
    entry names, as the first of three things the fix must not do, that
    this must be *the service family consulting a fact* and never *the
    estate judge acquiring a say in a service's rung* —
    ``sysadmin/estate/judgements.py`` rule 3 read in reverse, that rule
    having declined to judge estate unreachability precisely because the
    service family owns it.

    The edge is legal and has a mirror precedent:
    :mod:`sysadmin.estate.agent` imports :mod:`sysadmin.units.ports` so
    the judge reads the unit sweep's attribution rather than running
    ``ss`` itself.  What makes it *safe* is which module is reached.
    ``client`` is transport — it returns a reading and knows nothing
    about severities.  ``judgements`` is the verdict half, and a
    ``monitor`` module importing it is how the two would come to share a
    ladder without anyone deciding to.

    Stated as a rule rather than as an observation about today's one
    import, because the failure mode is silent: nothing about
    ``from sysadmin.estate import judgements`` in a monitor module would
    look wrong in review.
    """
    allowed = {"sysadmin.estate", "sysadmin.estate.client"}
    offenders = []
    for path in PACKAGE.rglob("*.py"):
        for module in imported_modules(path):
            if not (module == "sysadmin.estate"
                    or module.startswith("sysadmin.estate.")):
                continue
            if module not in allowed:
                offenders.append(f"{path.relative_to(PACKAGE.parent.parent)}: {module}")
    assert not offenders, (
        "monitor may import sysadmin.estate.client (transport) and nothing "
        "else from that domain — a verdict is not a fact:\n"
        + "\n".join(offenders)
    )


def test_the_quietening_rung_is_not_borrowed_from_the_judge():
    """``ARBITRATED_STOP_SEVERITY`` is derived, and equals the judge's floor.

    Two halves, and they are different claims.  **Provenance**: the
    constant is built from
    :data:`~sysadmin.core.escalation.QUIETEST_SEVERITY`, a ``core``
    symbol both domains may import, rather than from
    :data:`~sysadmin.estate.judgements.TRANSIENT_HOLDER_SEVERITY` — the
    test above is what enforces that, since it is the import that would
    have to appear.  **Value**: the two must nonetheless name the same
    rung, because they are one fact — *the quietest rung there is, which
    is the only one below* ``tray.notify_min_severity`` *on this box* —
    and two families quietening to different floors would be that fact
    stated twice and free to drift.

    Asserting the value here and the provenance there is deliberate: a
    value assertion cannot see provenance, which this repository has now
    recorded three times as the shape a falsification passes against
    broken code.
    """
    from sysadmin.core.escalation import QUIETEST_SEVERITY
    from sysadmin.estate.judgements import TRANSIENT_HOLDER_SEVERITY
    from sysadmin.monitor.agent import ARBITRATED_STOP_SEVERITY

    assert ARBITRATED_STOP_SEVERITY == QUIETEST_SEVERITY
    assert ARBITRATED_STOP_SEVERITY == TRANSIENT_HOLDER_SEVERITY
