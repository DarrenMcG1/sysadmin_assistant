#!/usr/bin/env python3
"""Migrate projects.yaml onto per-repository ``.project.yaml`` manifests.

Reads the existing projects.yaml and writes one manifest into each project
directory that exists on disk, then reports what it could not account for:
entries pointing at nothing, and repositories nobody ever declared.

Two things it deliberately does **not** do:

*Comments.* projects.yaml's comments carry the reasoning behind several
decisions and this script never reads them — ``yaml.safe_load`` discards
them before the script sees anything. Every manifest is written with an
empty ``decisions:`` history, and transferring the reasoning is a manual
job, one project at a time, after the move.

*Overwrite.* An existing manifest is left alone unless ``--force`` says
otherwise, so the script is safe to run repeatedly. It also defaults to a
dry run: writing requires ``--apply``.

Usage::

    scripts/migrate_registry.py                 # dry run, the default
    scripts/migrate_registry.py --apply
    scripts/migrate_registry.py --apply --force
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sysadmin.registry import (  # noqa: E402
    MANIFEST_NAME,
    SCHEMA_VERSION,
    derive_category,
    derive_id,
    discover_repositories,
    has_manifest,
)

DEFAULT_PROJECTS_YAML = REPO_ROOT / "projects.yaml"
DEFAULT_ROOT = Path("~/projects")


@dataclass
class Plan:
    """What the migration would do, before it does any of it."""

    write: list[tuple[Path, dict]] = field(default_factory=list)
    skip_existing: list[Path] = field(default_factory=list)
    dead_paths: list[tuple[str, str]] = field(default_factory=list)
    undeclared: list[Path] = field(default_factory=list)
    id_collisions: dict[str, list[str]] = field(default_factory=dict)


def kebab(value: str) -> str:
    """The project id for a projects.yaml ``name``."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def manifest_for(entry: dict, path: Path, root: Path) -> dict:
    """The manifest body for one projects.yaml entry.

    ``id`` comes from the entry's ``name`` because that is what the user
    chose to call the project; ``name`` comes from the directory, which is
    what they called it on disk. They differ often enough to be worth
    keeping both — ``sports_analyser`` in projects.yaml is
    ``apps/SportsAnalyser`` on disk and becomes id ``sports-analyser``.

    ``status`` defaults to ``undeclared`` rather than ``active``: an entry
    that never said what it was is not evidence that it is being worked on.
    """
    body: dict = {
        "schema": SCHEMA_VERSION,
        "id": kebab(entry["name"]),
        "name": path.name,
        "category": derive_category(path, root),
        "status": entry.get("status") or "undeclared",
    }
    if entry.get("alert_threshold") is not None:
        body["alert_threshold"] = entry["alert_threshold"]
    body["decisions"] = []
    return body


def build_plan(projects_yaml: Path, root: Path, depth: int, force: bool) -> Plan:
    """Work out every action without touching the filesystem."""
    plan = Plan()
    raw = yaml.safe_load(projects_yaml.read_text(encoding="utf-8")) or {}
    entries = raw.get("projects") or []

    declared_paths: set[Path] = set()
    ids: dict[str, list[str]] = {}

    for entry in entries:
        declared = entry.get("path")
        if not declared:
            plan.dead_paths.append((entry["name"], "<no path>"))
            continue

        path = Path(declared).expanduser()
        if not path.is_dir():
            plan.dead_paths.append((entry["name"], declared))
            continue

        declared_paths.add(path.resolve())
        body = manifest_for(entry, path, root)
        ids.setdefault(body["id"], []).append(str(path))

        if has_manifest(path) and not force:
            plan.skip_existing.append(path)
            continue
        plan.write.append((path, body))

    plan.id_collisions = {
        project_id: paths for project_id, paths in ids.items() if len(paths) > 1
    }

    for repository in discover_repositories(root, depth):
        if repository.resolve() not in declared_paths:
            plan.undeclared.append(repository)

    return plan


def render(body: dict) -> str:
    """The manifest as it will be written."""
    return yaml.safe_dump(body, sort_keys=False, allow_unicode=True)


def report(plan: Plan, root: Path, applied: bool) -> None:
    verb = "Wrote" if applied else "Would write"
    print(f"\n{verb} {len(plan.write)} manifest(s):")
    for path, body in plan.write:
        print(f"  {path.relative_to(root) if path.is_relative_to(root) else path}"
              f"  ->  id: {body['id']}, status: {body['status']}")

    if plan.skip_existing:
        print(f"\nLeft alone, manifest already present ({len(plan.skip_existing)}) "
              "— use --force to overwrite:")
        for path in plan.skip_existing:
            print(f"  {path}")

    if plan.id_collisions:
        print(f"\nID COLLISIONS ({len(plan.id_collisions)}) — the registry will "
              "refuse to load until these are resolved:")
        for project_id, paths in sorted(plan.id_collisions.items()):
            print(f"  {project_id}: " + ", ".join(paths))

    print(f"\nprojects.yaml entries whose path does not exist ({len(plan.dead_paths)}):")
    for name, declared in plan.dead_paths:
        print(f"  {name}  ->  {declared}")
    if not plan.dead_paths:
        print("  (none)")

    print(f"\nRepositories under {root} with no manifest, never in projects.yaml "
          f"({len(plan.undeclared)}):")
    for path in plan.undeclared:
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        print(f"  {rel}  (would report as undeclared, provisional id "
              f"{derive_id(path.name)!r})")
    if not plan.undeclared:
        print("  (none)")


def apply(plan: Plan) -> None:
    for path, body in plan.write:
        (path / MANIFEST_NAME).write_text(render(body), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects-yaml", type=Path, default=DEFAULT_PROJECTS_YAML)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--apply", action="store_true",
                        help="write the manifests (default is a dry run)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite manifests that already exist")
    args = parser.parse_args(argv)

    root = args.root.expanduser().resolve()
    if not args.projects_yaml.is_file():
        parser.error(f"not found: {args.projects_yaml}")

    plan = build_plan(args.projects_yaml, root, args.depth, args.force)

    if args.apply and plan.id_collisions:
        report(plan, root, applied=False)
        print("\nRefusing to write: resolve the id collisions above first.")
        return 1

    if args.apply:
        apply(plan)
    report(plan, root, applied=args.apply)

    if not args.apply:
        print("\nDry run — nothing was written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
