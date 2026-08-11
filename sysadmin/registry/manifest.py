"""The ``.project.yaml`` manifest — a project's declaration of itself.

The manifest lives at the root of the repository it describes, so a move
or a rename cannot orphan it and filesystem case sensitivity stops
mattering.  Identity travels with the directory instead of being asserted
about it from a central file.

``extra="forbid"`` is deliberate.  A registry whose whole purpose is to
stop declarations rotting silently must not accept ``statuss: dormant``
and carry on as though nothing was declared.
"""

import re
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

MANIFEST_NAME = ".project.yaml"

SCHEMA_VERSION = 1

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

Status = Literal["active", "dormant", "archived", "undeclared"]

STATUSES: tuple[str, ...] = ("active", "dormant", "archived", "undeclared")


class Decision(BaseModel):
    """One recorded change of intent, with the reasoning that drove it.

    This is where the reasoning currently held in projects.yaml comments
    lands.  ``note`` carries the consequence that is not obvious from the
    change itself — "endpoints stay monitored" is the sort of thing that
    is lost when a comment is replaced by a field.
    """

    model_config = ConfigDict(extra="forbid")

    date: date
    change: str
    reason: str
    note: str | None = None


class ProjectManifest(BaseModel):
    """A validated ``.project.yaml``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: int = Field(alias="schema")
    id: str
    name: str
    category: str | None = None
    status: Status = "undeclared"
    summary: str | None = None
    supersedes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    alert_threshold: int | None = None
    #: Days this project's stated next action may stand before it nudges
    #: (Session 31).  ``None`` takes the global default from config.yaml.
    #: Deliberately a *separate* knob from ``alert_threshold``: that one
    #: governs a health score, this one governs a commitment, and a repo
    #: with a long release cycle wants the second relaxed without also
    #: going unwatched for the first.
    idle_nudge_days: int | None = None
    decisions: list[Decision] = Field(default_factory=list)

    @field_validator("idle_nudge_days")
    @classmethod
    def _positive_nudge_days(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError(
                "idle_nudge_days must be at least 1; to switch nudges off for "
                "this project set a large number rather than 0, so the "
                "intention stays readable"
            )
        return value

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: int) -> int:
        if value != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema {value}, this registry reads schema {SCHEMA_VERSION}"
            )
        return value

    @field_validator("id")
    @classmethod
    def _kebab_id(cls, value: str) -> str:
        if not ID_PATTERN.match(value):
            raise ValueError(
                f"id {value!r} must be lowercase kebab-case (a-z, 0-9, single hyphens)"
            )
        return value

    @field_validator("supersedes")
    @classmethod
    def _kebab_supersedes(cls, value: list[str]) -> list[str]:
        bad = [item for item in value if not ID_PATTERN.match(item)]
        if bad:
            raise ValueError(
                "supersedes must contain project ids in lowercase kebab-case; "
                f"invalid: {', '.join(repr(b) for b in bad)}"
            )
        return value


def manifest_path(repository: Path) -> Path:
    """Where the manifest for ``repository`` lives."""
    return repository / MANIFEST_NAME


def has_manifest(repository: Path) -> bool:
    """Whether ``repository`` declares itself."""
    return manifest_path(repository).is_file()


def parse_manifest(raw: Any) -> ProjectManifest:
    """Validate an already-decoded manifest mapping."""
    if not isinstance(raw, dict):
        raise ValueError("manifest must be a YAML mapping")
    return ProjectManifest.model_validate(raw)


def read_manifest(repository: Path) -> ProjectManifest | None:
    """Read and validate ``repository``'s manifest, or None if it has none.

    Raises ``ValueError`` (including pydantic's ``ValidationError``) on a
    manifest that exists but does not parse.  Callers that sweep a whole
    estate collect these rather than failing on the first.
    """
    path = manifest_path(repository)
    if not path.is_file():
        return None

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"unreadable YAML: {exc}") from exc

    return parse_manifest(raw)


def describe_error(exc: Exception) -> str:
    """A one-line reason suitable for a collected error report."""
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg']}"
            for err in exc.errors()
        )
    return str(exc)
