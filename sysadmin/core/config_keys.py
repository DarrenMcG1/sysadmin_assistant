"""Keys in config.yaml that no model declares — reported, never refused.

``SNAG-CFG-004``. ``services.yaml``'s four models set ``extra="forbid"``,
so a typo there raises a ``ValidationError`` naming the line. The 37
models in :mod:`sysadmin.core.config` inherit pydantic's
``extra="ignore"``, so the same typo is accepted, dropped, and silent:
``briefing_hourr: 9`` parses cleanly and the briefing stays at 6. The
operator has moved the morning briefing and the briefing has not moved.

**The obvious remedy does not boot.** Walking the shipped ``config.yaml``
against ``AppConfig``'s field tree finds **ten** keys the backend does
not declare, every one of them legitimate: the top-level ``tray:``
section and nine leaves under ``notifications.tray:``, all owned by
``sysadmin_tray/config.py``, which parses the same file for itself.
``TrayNotificationsConfig`` says so in its own docstring — those keys are
*"deliberately absent here and ignored on load"*. So ``extra="forbid"``
across the models is not a trade-off to weigh; it is a daemon that will
not start on this box.

That is also why the two files legitimately answer differently, which the
entry read as an inconsistency. ``services.yaml`` can forbid because
every key in it belongs to the process holding the models.
``config.yaml`` cannot, because it carries a region this process does not
own. The asymmetry is structural, and the boundary has to be *declared*
before anything can be judged — :data:`sysadmin.core.config.FOREIGN_KEYS`
is that declaration.

Five rules, three of them the opposite of the obvious implementation:

1. **It reports; it cannot refuse.** A walker returns a list, so there is
   no path by which it fails a boot or a reload — the strictness question
   is settled by the shape of the mechanism rather than by a flag someone
   could flip. ``schema_guard`` refuses because serving against the wrong
   schema is worse than not serving; serving with an ignored config key
   is *not* worse than not serving, and has been the daemon's behaviour
   for its whole life at a cost of one briefing at the wrong hour. Same
   posture, opposite answer, because the cost side differs.
2. **It derives from ``model_fields`` rather than restating the schema.**
   Pydantic has already parsed the annotations and the aliases; this
   walks what pydantic built. A second hand-written list of valid keys is
   ``SNAG-DB-003``'s shape — two statements of one fact, free to
   disagree — and the whole entry is about a key nobody declared.
3. **A shape it cannot classify is reported, never skipped.** A field
   whose annotation holds a model and whose value is neither a mapping
   nor a sequence of them is ``unwalkable``: the subtree beneath it was
   not examined, so its zero unknown keys are zero-because-blind.
   Serving that as zero-because-clean is ``ports_checked``'s rule, and a
   silent skip is the exact defect this module exists to end, one level
   down.
4. **Foreign keys are exempted by leaf, never by subtree — with one
   deliberate exception.** ``notifications.tray.mute_services`` is read
   *here* (reliability waives deductions for an expected-down service),
   so exempting the whole ``notifications.tray:`` subtree would make
   ``mute_servicess`` silent — rebuilding the defect inside its own fix,
   on the one leaf under that key the backend genuinely depends on. The
   top-level ``tray:`` section is exempt whole, because the backend reads
   nothing under it and judging another parser's section is the
   second-owner defect this repository has now found at seven scales.
5. **It reads the file itself and its failure is contained.** The
   annotation must never be able to break what it annotates
   (``unit_failure._schema_diagnosis``'s rule), so it never shares
   ``parse_config``'s parsed object and a caller wraps it. The cost is a
   second read: a file edited between the two produces a stale warning,
   which is the failure direction this module is allowed to have.

The one thing it deliberately cannot see is a typo *inside* ``tray:``.
That belongs to the tray, which parses the section with ``.get()`` walks
and could report on it there; judging it from here would require this
process to hold a model of a surface it does not own.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KeyReport:
    """What a walk of one raw config found, and what it could not reach.

    ``unknown`` and ``unwalkable`` are separate because the remedies are
    opposites: an unknown key is the operator's line to fix, an
    unwalkable one is this module's traversal failing to keep up with an
    annotation somebody added. Collapsing them would report a defect in
    the walker as a defect in the file.
    """

    unknown: list[str] = field(default_factory=list)
    unwalkable: list[str] = field(default_factory=list)
    #: False when the file could not be read or parsed at all. A walk that
    #: never happened must not serve its empty ``unknown`` as a clean bill
    #: — ``ports_checked``'s rule at the size of a boolean.
    walked: bool = True

    @property
    def clean(self) -> bool:
        """Every key was declared, and every subtree was actually read."""
        return self.walked and not self.unknown and not self.unwalkable

    def as_payload(self) -> dict[str, Any]:
        """The wire shape, for ``ReloadResponse``."""
        return {
            "unknown": list(self.unknown),
            "unwalkable": list(self.unwalkable),
            "walked": self.walked,
        }


def model_in(annotation: Any) -> type[BaseModel] | None:
    """The ``BaseModel`` inside an annotation, unwrapping containers.

    ``Thresholds`` → itself; ``list[LogSource]`` → ``LogSource``;
    ``str | None`` → ``None``. Recursive rather than a fixed set of
    origins, because the question is only ever "is there a model in here
    to descend into", and a new container shape should widen the answer
    rather than silently narrow it.
    """
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for arg in get_args(annotation):
        found = model_in(arg)
        if found is not None:
            return found
    return None


def _accepted_names(model: type[BaseModel]) -> dict[str, Any]:
    """Every spelling ``model`` accepts, mapped to its field.

    Both the field name and its alias, because ``DatabaseConfig`` sets
    ``populate_by_name`` and declares ``schema_`` with ``alias="schema"``
    — the shipped file writes ``schema:``, and a walker reading only
    field names would report the one key in this tree that is spelled
    deliberately.
    """
    names: dict[str, Any] = {}
    for name, info in model.model_fields.items():
        names[name] = info
        if info.alias:
            names[info.alias] = info
    return names


def walk(
    raw: Any,
    model: type[BaseModel],
    *,
    foreign: Iterable[str] = (),
    prefix: str = "",
) -> KeyReport:
    """Every key in ``raw`` that ``model``'s tree does not declare.

    ``foreign`` is a set of dotted paths owned by another parser. A path
    that matches is neither reported nor descended into — see rule 4 for
    why the match is exact rather than a prefix.
    """
    foreign_set = frozenset(foreign)
    report = KeyReport()
    _walk_into(raw, model, foreign_set, prefix, report)
    return report


def _walk_into(
    raw: Any,
    model: type[BaseModel],
    foreign: frozenset[str],
    prefix: str,
    report: KeyReport,
) -> None:
    if raw is None:
        # ``notifications:`` with nothing under it. Pydantic accepted the
        # file, so there is no key here to be wrong about.
        return
    if not isinstance(raw, dict):
        report.unwalkable.append(prefix or "<root>")
        return

    accepted = _accepted_names(model)
    for key, value in raw.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if path in foreign:
            continue
        info = accepted.get(key)
        if info is None:
            report.unknown.append(path)
            continue
        submodel = model_in(info.annotation)
        if submodel is None:
            # A leaf, or a container of leaves. Pydantic validated its
            # type; there are no further keys to declare.
            continue
        if isinstance(value, dict):
            _walk_into(value, submodel, foreign, path, report)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                _walk_into(item, submodel, foreign, f"{path}[{index}]", report)
        elif value is None:
            continue
        else:
            # Rule 3: the annotation says a model lives here and the value
            # is neither a mapping nor a sequence of them, so this subtree
            # went unread. Say so rather than counting it clean.
            report.unwalkable.append(path)


def report_for_file(
    path: Path,
    model: type[BaseModel],
    *,
    foreign: Iterable[str] = (),
) -> KeyReport:
    """Walk the YAML at ``path``, reading it independently of the parse.

    Rule 5: this never shares ``parse_config``'s object, so nothing it
    does can change what gets installed. An unreadable file yields
    ``walked=False`` rather than an empty ``unknown`` — the caller has
    already parsed it successfully, so a failure here is this module's,
    and reporting it as "no unknown keys" would be a clean bill issued by
    the component that fell over.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning(
            "config_key_walk_unavailable",
            extra={"path": str(path), "error": str(exc)},
        )
        return KeyReport(walked=False)
    return walk(raw, model, foreign=foreign)
