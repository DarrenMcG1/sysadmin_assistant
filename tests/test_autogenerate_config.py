"""One copy of the autogenerate comparison rules, enforced (`SNAG-DB-003`).

``sysadmin/metadata.py`` owns what autogenerate compares: the frozen-table
exclusions, the schema filter and the comparison flags. ``alembic/env.py``
and ``tests/test_schema_drift.py`` splat ``COMPARISON_OPTS`` and configure
nothing of their own.

This is a guard against the copy coming *back*, which is a live risk
rather than a hypothetical one: the natural way to add a table to the
exclusion list is to edit the file you are looking at, and the two files
fail in opposite directions. An exclusion added only to ``env.py`` makes
the drift guard fail loudly. One added only to the guard is silent — the
guard stays green while the next ``alembic revision --autogenerate``
writes ``op.drop_table('project_snapshots')`` into an unrelated
migration, against 3,739 live rows.

The check is textual, over the AST, because ``alembic/env.py`` cannot be
imported — it runs the migrations at module scope. Session 43 considered
and rejected asserting the two function *bodies* were identical: that
pins the copy rather than removing it, and is brittle against
formatting. This asserts the opposite thing — that there is no second
body to compare.

Two of the four tests exist because a detector that cannot fail proves
nothing (the vacuity lesson of `SNAG-TRAY-006`): one runs the walker at
the owner, which it must flag, and one feeds it the code this session
deleted.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / "sysadmin" / "metadata.py"
CALLERS = (ROOT / "alembic" / "env.py", ROOT / "tests" / "test_schema_drift.py")

SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "data", "logs",
             "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache"}

#: Every option that decides what autogenerate compares. Passing one by
#: hand — as a keyword or as a key in an ``opts`` dict — is a second
#: statement of the comparison, whether or not it happens to agree today.
OWNED_KEYS = frozenset({
    "target_metadata",
    "version_table_schema",
    "include_schemas",
    "include_object",
    "include_name",
    "compare_type",
})
OWNED_FUNCTIONS = ("include_object", "include_name")
OWNED_CONSTANTS = frozenset({"FROZEN_TABLES"})


def python_files():
    """Every module in the repository, owner excluded."""
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path == OWNER:
            continue
        yield path


def offenders_in(source: str, label: str) -> list[str]:
    """Places that state a comparison rule instead of importing one."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.endswith(OWNED_FUNCTIONS):
                found.append(f"{label}:{node.lineno}: defines {node.name}()")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in OWNED_CONSTANTS:
                    found.append(f"{label}:{node.lineno}: assigns {target.id}")
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in OWNED_CONSTANTS:
                found.append(f"{label}:{node.lineno}: assigns {node.target.id}")
        elif isinstance(node, ast.keyword):
            if node.arg in OWNED_KEYS:
                found.append(f"{label}:{node.lineno}: passes {node.arg}=")
        elif isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value in OWNED_KEYS:
                    found.append(f"{label}:{node.lineno}: dict key {key.value!r}")
    return found


def test_no_module_states_the_comparison_rules_for_itself():
    offenders = []
    for path in python_files():
        offenders += offenders_in(
            path.read_text(encoding="utf-8"), str(path.relative_to(ROOT))
        )
    assert not offenders, (
        "sysadmin/metadata.py owns what autogenerate compares — import "
        "COMPARISON_OPTS instead of restating it:\n" + "\n".join(offenders)
    )


def test_both_callers_import_the_shared_options():
    """A file that configures nothing at all would pass the test above.

    The drift guard certifying a comparison it never applied, and env.py
    running autogenerate with alembic's defaults, are both silent — the
    same direction of failure this snag is about.
    """
    for path in CALLERS:
        assert path.exists(), f"{path} not found — adjust CALLERS"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "sysadmin.metadata"
            for alias in node.names
        }
        assert "COMPARISON_OPTS" in imported, (
            f"{path.relative_to(ROOT)} must take the comparison from "
            "sysadmin.metadata.COMPARISON_OPTS"
        )


def test_the_walker_flags_the_owner():
    """Guard against a green run that only means the walker found nothing.

    The owner is the one file that *should* trip every rule, so running
    the detector at it proves the detector is looking at real code and
    that the exclusion of one path is what makes the sweep pass.
    """
    offenders = offenders_in(OWNER.read_text(encoding="utf-8"), "metadata.py")
    kinds = {entry.split(": ", 1)[1].split()[0] for entry in offenders}
    assert kinds >= {"defines", "assigns", "dict"}, offenders


def test_the_walker_flags_a_recopied_guard():
    """The code deleted in this session, fed back in."""
    recopied = '''
FROZEN_TABLES = {"project_snapshots", "project_reviews"}


def _include_object(object, name, type_, reflected, compare_to):
    """Mirror alembic/env.py."""
    return name not in FROZEN_TABLES


context = MigrationContext.configure(conn, opts={"include_object": _include_object})
'''
    offenders = offenders_in(recopied, "recopied")
    assert len(offenders) == 3, offenders


def test_the_walker_sees_the_repository():
    files = list(python_files())
    assert len(files) > 50, f"only {len(files)} modules walked — check ROOT/SKIP_DIRS"
    for caller in CALLERS:
        assert caller in files, f"{caller} not walked"
