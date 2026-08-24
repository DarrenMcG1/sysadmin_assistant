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
    domains = ("sysadmin.monitor", "sysadmin.projects", "sysadmin.files",
               "sysadmin.units", "sysadmin.briefing")
    root = PACKAGE.parent
    offenders = []
    for layer in ("core", "registry"):
        for path in (root / layer).rglob("*.py"):
            for module in imported_modules(path):
                if any(module == d or module.startswith(f"{d}.") for d in domains):
                    offenders.append(f"{path}: {module}")
    assert not offenders, "core/registry must not import a domain:\n" + "\n".join(offenders)


def test_no_domain_imports_a_composition_root():
    """``main``, ``metadata``, ``reload`` and ``ops_claims`` are imported by nothing below them.

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
    """
    roots = (
        "sysadmin.main",
        "sysadmin.metadata",
        "sysadmin.reload",
        "sysadmin.ops_claims",
    )
    package = PACKAGE.parent
    offenders = []
    for path in package.rglob("*.py"):
        if path.parent == package and path.stem in {
            "main", "metadata", "reload", "ops_claims", "__init__"
        }:
            continue
        for module in imported_modules(path):
            if module in roots or any(module.startswith(f"{r}.") for r in roots):
                offenders.append(f"{path.relative_to(package.parent)}: {module}")
    assert not offenders, (
        "a composition root must be imported by nothing below it:\n"
        + "\n".join(offenders)
    )
