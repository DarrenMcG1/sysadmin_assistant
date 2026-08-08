"""Turn unit findings into ranked advice with ready-to-paste config.

Tier 2 of Session 26, and the sibling of
:mod:`sysadmin.projects.recommendations` (health-score points) and
:mod:`sysadmin.files.recommendations` (reclaimable megabytes).

**This tier has no currency, deliberately.**  Both siblings rank by a
directly measurable quantity.  There is no equivalent here: nothing makes
fixing two host units meaningfully "twice" the win of fixing one orphan,
and a made-up score would be a number the reader cannot check.  So
recommendations rank by severity tier only, and the model carries no
points field — the same reasoning Session 24 used to refuse to overload
``RecommendationInfo.points`` with a second unit.

Ranked, worst first:

1. ``orphan`` (severity ``risk``) — the unit is already broken.  A dead
   ``WorkingDirectory`` makes systemd fail the start job outright, so
   this is not a monitoring gap, it is a thing that does not work.
2. ``unmonitored`` — a live project's unit that nothing watches.
3. ``host`` — hand-written infrastructure with no project.  Last not
   because it matters least (``pgbackrest-backup`` is the estate's only
   database backup) but because it is a documentation gap rather than a
   defect: the unit is running fine, nobody is watching.

**Never auto-edit the config.**  services.yaml is hand-curated and its
comments carry reasoning a writer would flatten.  Advice only: the
snippet is text for a human to paste.

Every snippet targets services.yaml, which is the whole simplification.
There used to be two possible destinations and a rule for choosing
between them, because projects.yaml modelled only ``backend`` and
``frontend`` and a third unit had nowhere to go.  What remains of that
rule is narrower and still load-bearing: ``project:`` is emitted only
when a manifest declares the id, since an id nothing claims fails at
load, and a ``Type=oneshot`` service is still wired as its ``kind:
timer`` — which is now a declaration the checker reads rather than a
convention a comment explained.

Pure module: no DB, no FastAPI.  Give it findings, get advice.
"""

from __future__ import annotations

from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from typing import Any

from sysadmin.core.contracts import UnitRecommendationInfo
from sysadmin.units.scan import HOST, ORPHANED, UNMONITORED, UnitFinding

#: Rank order.  Index into this is the sort key, so the list *is* the
#: policy — there is no second place stating it differently.
KIND_ORDER = ("orphan", "unmonitored", "host")

_KIND_FOR_CATEGORY = {
    ORPHANED: "orphan",
    UNMONITORED: "unmonitored",
    HOST: "host",
}


def recommendations_for_scan(
    findings: Sequence[UnitFinding],
    registry: Any = None,
) -> list[UnitRecommendationInfo]:
    """Ranked advice for one unit sweep.

    ``registry`` is consulted only to decide *where* a snippet
    should go — whether the finding's project already has a manifest
    entry to extend.  It is never written to.
    """
    known = _project_ids(registry)
    # Computed here, once, so every snippet for a two-scope unit agrees
    # on the disambiguated name.
    duplicates = duplicate_units(findings)

    recs = [_recommend(finding, known, duplicates) for finding in findings]
    recs.sort(key=lambda r: (KIND_ORDER.index(r.kind), r.scope, r.unit))
    return recs


def _project_ids(registry: Any) -> dict[str, str]:
    """Every name a declared project answers to, mapped to its id.

    The sweep matches units against the *directory* name it found on
    disk, while services.yaml references the *manifest id*, and they
    differ often enough to matter — ``SportsAnalyser`` against
    ``sports-analyser``. Emitting the name the sweep happened to use
    would produce a snippet that fails to load, which is a worse outcome
    than no snippet.
    """
    ids: dict[str, str] = {}
    for entry in getattr(registry, "declared", ()) or ():
        ids[str(entry.id)] = str(entry.id)
        ids[entry.path.name] = str(entry.id)
    return ids


def _recommend(
    finding: UnitFinding, known: dict[str, str], duplicates: set[str]
) -> UnitRecommendationInfo:
    kind = _KIND_FOR_CATEGORY.get(finding.category, "host")
    builder = {
        "orphan": _orphan_recommendation,
        "unmonitored": _unmonitored_recommendation,
        "host": _host_recommendation,
    }[kind]
    return builder(finding, known, duplicates)


# --------------------------------------------------------------------------
# Per-kind advice
# --------------------------------------------------------------------------


def _orphan_recommendation(
    finding: UnitFinding, known: dict[str, str], duplicates: set[str]
) -> UnitRecommendationInfo:
    """Advice for a unit whose project is gone.

    Severity ``risk`` rather than ``advice``: the other two kinds
    describe something unwatched, this one describes something broken.
    A unit with a dead ``WorkingDirectory`` has been failing every start
    since the directory moved, and because nothing monitors it, silently.
    """
    if finding.dead_path:
        detail = (
            f"{finding.reason}. Nothing has monitored it, so the failures "
            "have been silent."
        )
    else:
        detail = finding.reason + "."

    if finding.project:
        detail += (
            f" Confirm {finding.project} is genuinely retired before "
            "removing anything."
        )

    return UnitRecommendationInfo(
        kind="orphan",
        severity="risk",
        unit=finding.unit,
        scope=finding.scope,
        project=finding.project,
        title=f"Remove the dead unit {finding.unit}",
        detail=detail,
        action=_removal_command(finding),
        snippet="",
        snippet_target=None,
    )


def _unmonitored_recommendation(
    finding: UnitFinding, known: dict[str, str], duplicates: set[str]
) -> UnitRecommendationInfo:
    """Advice for a live project's unwatched unit."""
    target, snippet = _snippet_for(finding, known, duplicates)
    where = target or "services.yaml"

    detail = f"{finding.reason}."
    if finding.monitor_unit != finding.unit:
        detail += (
            f" It is Type=oneshot, so monitor {finding.monitor_unit} instead — "
            "a oneshot service is inactive between runs by design and would "
            "alert continuously."
        )
    if finding.manual:
        detail += (
            " It has no [Install] section and no timer, so it is started by "
            "hand; monitoring it would report it dead whenever it is simply "
            "not running."
        )

    return UnitRecommendationInfo(
        kind="unmonitored",
        severity="advice",
        unit=finding.unit,
        scope=finding.scope,
        project=finding.project,
        monitor_unit=finding.monitor_unit,
        title=f"Monitor {finding.monitor_unit} ({finding.project})",
        detail=detail,
        action=f"Paste the snippet below into {where}, then restart sysadmin.service",
        snippet=snippet,
        snippet_target=target,
    )


def _host_recommendation(
    finding: UnitFinding, known: dict[str, str], duplicates: set[str]
) -> UnitRecommendationInfo:
    """Advice for hand-written infrastructure with no project."""
    target, snippet = _snippet_for(finding, known, duplicates)

    detail = (
        f"{finding.description or finding.unit} is a hand-written unit under "
        f"{_scope_dir(finding.scope)} that maps to no project in "
        "~/projects, so its services.yaml entry carries no `project:`."
    )
    if finding.monitor_unit != finding.unit:
        detail += (
            f" It is Type=oneshot, so monitor {finding.monitor_unit} — the "
            "timer stays active while armed, the service does not."
        )
    if finding.manual:
        detail += (
            " It is oneshot with no timer, so it only runs when invoked; "
            "there is no schedule to go quiet."
        )

    return UnitRecommendationInfo(
        kind="host",
        severity="advice",
        unit=finding.unit,
        scope=finding.scope,
        project=None,
        monitor_unit=finding.monitor_unit,
        title=f"Monitor the host unit {finding.monitor_unit}",
        detail=detail,
        action="Paste the snippet below into services.yaml under services:",
        snippet=snippet,
        snippet_target=target,
    )


# --------------------------------------------------------------------------
# Snippet generation
# --------------------------------------------------------------------------


def _scope_dir(scope: str) -> str:
    return (
        "~/.config/systemd/user" if scope == "user" else "/etc/systemd/system"
    )


def _removal_command(finding: UnitFinding) -> str:
    """The exact command to retire an orphan, scope-correct.

    ``disable --now`` before ``rm`` because deleting the unit file first
    leaves the enablement symlink in ``*.wants/`` behind, and systemd
    then warns about a dangling link on every ``daemon-reload``.
    """
    if finding.scope == "user":
        return (
            f"systemctl --user disable --now {finding.unit} "
            f"&& rm {finding.path} "
            "&& systemctl --user daemon-reload"
        )
    return (
        f"sudo systemctl disable --now {finding.unit} "
        f"&& sudo rm {finding.path} "
        "&& sudo systemctl daemon-reload"
    )


def _snippet_for(
    finding: UnitFinding, known: dict[str, str], duplicates: set[str]
) -> tuple[str | None, str]:
    """``(target_file, snippet)`` for a finding worth wiring up.

    One target now. Every unit on this host is declared in services.yaml,
    whether it belongs to a project or to the machine — the old split,
    where a third unit could not be expressed beside its siblings and had
    to be filed under "sysadmin" with a comment, is what services.yaml
    removed.
    """
    if finding.manual:
        # Nothing to wire: a hand-started oneshot has no steady state to
        # check, so a monitor would report it dead almost always.
        return None, ""

    return "services.yaml", _services_yaml_snippet(finding, known, duplicates)


def _services_yaml_snippet(
    finding: UnitFinding, known: dict[str, str], duplicates: set[str]
) -> str:
    """A services.yaml entry for one unwired unit.

    ``kind: systemd`` rather than ``http``: this scan does not know the
    unit's port, and a systemd check needs no url. A timer gets
    ``kind: timer``, which is the declaration that stops its oneshot
    service being checked, and ``controllable: false``, because start and
    stop from the tray would arm or disarm a schedule rather than restart
    something.

    ``project:`` is emitted only when the project is *declared* — an id
    no manifest claims fails at load, so guessing one would turn advice
    into an outage.
    """
    is_timer = finding.monitor_unit.endswith(".timer")
    lines = [
        f"  # {finding.description}" if finding.description else None,
    ]
    project_id = known.get(finding.project) if finding.project else None
    if project_id:
        lines.append(f"  - project: {project_id}")
        lines.append(f"    name: {_service_name(finding, duplicates)}")
    else:
        lines.append(f"  - name: {_service_name(finding, duplicates)}")
        if finding.project:
            lines.append(
                f"    # {finding.project} has no .project.yaml manifest, so it "
                "has no id to reference yet"
            )
    lines.append(f"    kind: {'timer' if is_timer else 'systemd'}")
    lines.append(
        f"    systemd: {{ unit: {finding.monitor_unit}, scope: {finding.scope} }}"
    )
    if is_timer:
        lines.append(
            "    controllable: false  # start/stop would arm/disarm the schedule"
        )
    else:
        lines.append("    log: { type: journalctl, severity_filter: warning }")
    return "\n".join(line for line in lines if line)


def _service_name(finding: UnitFinding, duplicates: AbstractSet[str] = frozenset()) -> str:
    """A services.yaml ``name:`` for the unit.

    Unit stem with the suffix dropped, plus ``-timer`` when the thing
    monitored is a timer — the convention config.yaml already uses for
    ``alfred-evaluate-timer``.

    Scope is appended when the *same unit name* exists in both scopes.
    ``deadlock-api-ingest.service`` is installed twice on this box,
    running ``~/.local/share/...`` as a user unit and ``/opt/...`` as a
    system one.  Without the suffix both snippets say
    ``name: deadlock-api-ingest``, and config.yaml ``name`` is what the
    tray labels a tile with — two tiles, one label, no way to tell which
    binary went down.
    """
    stem = finding.monitor_unit.rsplit(".", 1)[0]
    if finding.monitor_unit.endswith(".timer"):
        stem = f"{stem}-timer"
    if finding.unit in duplicates:
        return f"{stem}-{finding.scope}"
    return stem


def duplicate_units(findings: Sequence[UnitFinding]) -> set[str]:
    """Unit names installed in *both* scopes.

    Worth naming explicitly: ``deadlock-api-ingest.service`` exists as a
    user unit running ``~/.local/share/...`` and a system unit running
    ``/opt/...``.  Two units, one name, two different binaries — advice
    that did not say so would read as a single item reported twice.
    """
    seen: dict[str, set[str]] = {}
    for finding in findings:
        seen.setdefault(finding.unit, set()).add(finding.scope)
    return {unit for unit, scopes in seen.items() if len(scopes) > 1}
