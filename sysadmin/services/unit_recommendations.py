"""Turn unit findings into ranked advice with ready-to-paste config.

Tier 2 of Session 26, and the sibling of
:mod:`sysadmin.services.recommendations` (health-score points) and
:mod:`sysadmin.services.file_recommendations` (reclaimable megabytes).

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

**Never auto-edit the config.**  Both YAML files are hand-curated and
their comments carry the reasoning — projects.yaml explains *why*
``user: true`` is mandatory, config.yaml explains *why* a oneshot's timer
is monitored instead of the service.  A writer that rewrote either would
destroy that and the next reader would rediscover both lessons the hard
way.  Advice only: the snippet is text for a human to paste.

Which file the snippet targets is decided by what will actually work,
not by which is tidier:

- A ``Type=oneshot`` service is monitored via its **timer**, and
  projects.yaml models only ``backend``/``frontend`` — so timers go to
  config.yaml ``services:``.
- A long-running service goes to config.yaml too **unless its project is
  already in projects.yaml**, because a projects.yaml endpoint without a
  ``url`` is inert: ``ManagedProject.to_monitored_services`` skips it, so
  the entry looks wired and checks nothing.  Ports are Session 26b's job,
  and until then ``type: systemd`` in config.yaml is the form that
  actually checks something.

Pure module: no DB, no FastAPI.  Give it findings, get advice.
"""

from __future__ import annotations

from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from typing import Any

from sysadmin.contracts import UnitRecommendationInfo
from sysadmin.services.units import HOST, ORPHANED, UNMONITORED, UnitFinding

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
    projects_config: Any = None,
) -> list[UnitRecommendationInfo]:
    """Ranked advice for one unit sweep.

    ``projects_config`` is consulted only to decide *where* a snippet
    should go — whether the finding's project already has a projects.yaml
    entry to extend.  It is never written to.
    """
    known = _projects_with_entries(projects_config)
    # Computed here, once, so every snippet for a two-scope unit agrees
    # on the disambiguated name.
    duplicates = duplicate_units(findings)

    recs = [_recommend(finding, known, duplicates) for finding in findings]
    recs.sort(key=lambda r: (KIND_ORDER.index(r.kind), r.scope, r.unit))
    return recs


def _projects_with_entries(projects_config: Any) -> set[str]:
    """Names of projects that already appear in projects.yaml."""
    projects = getattr(projects_config, "projects", None) or []
    known: set[str] = set()
    for project in projects:
        name = getattr(project, "name", None)
        if name:
            known.add(str(name))
        path = getattr(project, "path", None)
        if path:
            known.add(str(path).rstrip("/").rsplit("/", 1)[-1])
    return known


def _recommend(
    finding: UnitFinding, known: set[str], duplicates: set[str]
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
    finding: UnitFinding, known: set[str], duplicates: set[str]
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
    finding: UnitFinding, known: set[str], duplicates: set[str]
) -> UnitRecommendationInfo:
    """Advice for a live project's unwatched unit."""
    target, snippet = _snippet_for(finding, known, duplicates)
    where = "projects.yaml" if target == "projects.yaml" else "config.yaml"

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
    finding: UnitFinding, known: set[str], duplicates: set[str]
) -> UnitRecommendationInfo:
    """Advice for hand-written infrastructure with no project."""
    target, snippet = _snippet_for(finding, known, duplicates)

    detail = (
        f"{finding.description or finding.unit} is a hand-written unit under "
        f"{_scope_dir(finding.scope)} that maps to no project in "
        "~/projects, so no projects.yaml entry can cover it."
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
        action="Paste the snippet below into config.yaml under agents.sysadmin.services",
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
    finding: UnitFinding, known: set[str], duplicates: set[str]
) -> tuple[str | None, str]:
    """``(target_file, snippet)`` for a finding worth wiring up.

    A oneshot's timer and any unit with no project both go to config.yaml
    — projects.yaml models only ``backend``/``frontend``, and neither is
    a backend or a frontend.  A long-running unit whose project is
    already in projects.yaml gets a projects.yaml fragment instead, since
    that is where its sibling endpoints already live.
    """
    if finding.manual:
        # Nothing to wire: a hand-started oneshot has no steady state to
        # check, so a monitor would report it dead almost always.
        return None, ""

    is_timer = finding.monitor_unit != finding.unit
    if not is_timer and finding.project and finding.project in known:
        return "projects.yaml", _projects_yaml_snippet(finding)
    return "config.yaml", _config_yaml_snippet(finding, duplicates)


def _config_yaml_snippet(finding: UnitFinding, duplicates: set[str]) -> str:
    """A ``agents.sysadmin.services`` entry.

    ``type: systemd`` rather than ``http``: this scan does not know the
    unit's port (that is Session 26b), and a systemd check needs no URL.
    ``controllable: false`` on a timer because start/stop from the tray
    would arm or disarm a schedule, which is not what the button reads as.
    """
    lines = [
        f"      # {finding.description}" if finding.description else None,
        f"      - name: {_service_name(finding, duplicates)}",
        "        type: systemd",
        f"        systemd_unit: {finding.monitor_unit}",
    ]
    if finding.scope == "user":
        lines.append("        user: true  # systemd *user* unit")
    if finding.monitor_unit.endswith(".timer"):
        lines.append(
            "        controllable: false  # start/stop would arm/disarm the schedule"
        )
    return "\n".join(line for line in lines if line)


def _projects_yaml_snippet(finding: UnitFinding) -> str:
    """A ``backend:`` fragment for a project already in projects.yaml.

    ``url`` is present but commented, not omitted and not invented.
    ``to_monitored_services`` skips an endpoint with no ``url``, so an
    uncommented entry without one would look wired and check nothing —
    the exact failure mode the SportsAnalyser entry's own comment records
    from 2026-08-04.  The reader has to supply the port; the scan does
    not know it yet.
    """
    role = "frontend" if "frontend" in finding.unit else "backend"
    lines = [
        f"    # {finding.description}" if finding.description else None,
        f"    {role}:",
        "      # url: http://localhost:PORT/api/health   # required — a",
        "      #   systemd_unit with no url is skipped by the health check",
        f"      systemd_unit: {finding.monitor_unit}",
    ]
    if finding.scope == "user":
        lines.append("      user: true  # systemd *user* unit")
    lines.extend(
        [
            "      log:",
            "        type: journalctl",
            f"        unit: {finding.monitor_unit}",
            "        severity_filter: warning",
        ]
    )
    return "\n".join(line for line in lines if line)


def _service_name(finding: UnitFinding, duplicates: AbstractSet[str] = frozenset()) -> str:
    """A config.yaml ``name:`` for the unit.

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
