"""Failures the registry raises at load time rather than at use time.

Every error here carries *all* instances of its kind, not the first one
found.  A registry that fails once per broken manifest turns a tidy-up
into a dozen edit-run cycles; one error listing twelve paths is one
editing session.
"""

from collections.abc import Iterable
from pathlib import Path


class RegistryError(Exception):
    """Base class for every registry failure."""


class ManifestError(RegistryError):
    """One or more ``.project.yaml`` files are unreadable or invalid."""

    def __init__(self, problems: Iterable[tuple[Path, str]]) -> None:
        self.problems = list(problems)
        detail = "\n".join(f"  {path}: {reason}" for path, reason in self.problems)
        super().__init__(
            f"{len(self.problems)} invalid project manifest(s):\n{detail}"
        )


class DuplicateProjectIdError(RegistryError):
    """Two or more declared manifests claim the same project id."""

    def __init__(self, collisions: dict[str, list[Path]]) -> None:
        self.collisions = collisions
        detail = "\n".join(
            f"  {project_id}: " + ", ".join(str(p) for p in sorted(paths))
            for project_id, paths in sorted(collisions.items())
        )
        super().__init__(
            f"{len(collisions)} project id(s) claimed more than once:\n{detail}"
        )


class UnknownProjectError(RegistryError):
    """Something referenced a project id the registry does not know.

    ``referenced_by`` names the file or field that made the reference, so
    the message says where to go and edit rather than only what is wrong.
    """

    def __init__(
        self,
        unknown: Iterable[str],
        referenced_by: str,
        known: Iterable[str] = (),
    ) -> None:
        self.unknown = sorted(set(unknown))
        self.referenced_by = referenced_by
        self.known = sorted(set(known))
        detail = ", ".join(self.unknown)
        suffix = f"\nKnown ids: {', '.join(self.known)}" if self.known else ""
        super().__init__(
            f"{referenced_by} references unknown project id(s): {detail}{suffix}"
        )
