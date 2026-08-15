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
   Within the tier, **armed orphans come first**: one systemd will start
   is failing on every trigger, where a disabled one is only debt.  That
   is the SNAG-ESTATE-001 distinction, and it is the sole sub-ordering
   here — a measured fact, not a score.
2. ``restart`` (SNAG-UNITS-002) — the unit restarts, and its start limit
   is unreachable at its own restart cadence, so a crash loop never
   reaches ``failed`` and no ``OnFailure=`` can fire.  Severity
   ``advice``: nothing here is broken *now*.  It ranks above
   ``unmonitored`` because the two are competing safety nets and this is
   the stronger one — a wedged unit is seen as ``unreachable`` only if
   something polls it, whereas a reachable start limit makes systemd
   itself say so, to a hook, whether or not this service is running.
3. ``unmonitored`` — a live project's unit that nothing watches.
4. ``host`` — hand-written infrastructure with no project.  Last not
   because it matters least (``pgbackrest-backup`` is the estate's only
   database backup) but because it is a documentation gap rather than a
   defect: the unit is running fine, nobody is watching.

**Never auto-edit the config.**  services.yaml is hand-curated and its
comments carry reasoning a writer would flatten.  Advice only: the
snippet is text for a human to paste.

Snippets have **two** destinations, and the second one is new in the
restart tier: services.yaml for anything being wired up, and *the unit
file itself* for a start limit.  That is the first time this module has
emitted text for a file another repository owns, which is why the
recommendation names the owning project in its ``detail`` and stops at
text — the estate rule is that writes into another repository are
documents and pointers, and a paste-ready line served over a GET is a
pointer.  ``snippet_target`` is the absolute unit path in that case
rather than a filename, so the two are never confused.

Otherwise one destination.  There used to be two and a rule for choosing
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
from sysadmin.units.scan import (
    DEFAULT_RESTART_SEC,
    DEFAULT_START_LIMIT_BURST,
    HOST,
    ORPHANED,
    RESTART_UNBOUNDED,
    UNMONITORED,
    UnitFinding,
)

#: Rank order.  Index into this is the sort key, so the list *is* the
#: policy — there is no second place stating it differently.
KIND_ORDER = ("orphan", "restart", "unmonitored", "host")

_KIND_FOR_CATEGORY = {
    ORPHANED: "orphan",
    RESTART_UNBOUNDED: "restart",
    UNMONITORED: "unmonitored",
    HOST: "host",
}

#: Windows to suggest for ``StartLimitIntervalSec=``, smallest first.
#: Round numbers a human would have written by hand — the two units on
#: this box that get this right chose 600 and 60.
_START_LIMIT_LADDER = (60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0)

#: How much wider than the burst span the suggested window must be.
#: **The margin cuts the opposite way from the intuition**: a *longer*
#: ``StartLimitIntervalSec`` is a *stricter* limiter, because more starts
#: fit inside it.  So this is not slack for safety — it is the smallest
#: value that still leaves the arithmetic true if someone later nudges
#: ``RestartSec`` up a little, and going much beyond it starts failing
#: units for unrelated restarts spread over an hour.
START_LIMIT_MARGIN = 1.5


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

    paired = [(f, _recommend(f, known, duplicates)) for f in findings]
    # Armed orphans first *within* the orphan tier.  This is a
    # sub-ordering on a measured fact, not the invented currency the
    # module docstring refuses: an orphan systemd starts is failing
    # right now, and one that is disabled is filing debt.  Nothing about
    # it makes two host units comparable to one orphan, which is the
    # ranking this tier still declines to invent.
    paired.sort(
        key=lambda pair: (
            KIND_ORDER.index(pair[1].kind),
            not pair[0].armed,
            pair[1].scope,
            pair[1].unit,
        )
    )
    return [rec for _, rec in paired]


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
        "restart": _restart_recommendation,
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
        action=removal_command(finding),
        snippet="",
        snippet_target=None,
    )


def suggested_start_limit_interval(
    restart_sec: float | None, burst: int | None
) -> float | None:
    """A ``StartLimitIntervalSec=`` that would make this unit's loop terminal.

    The burst-th start lands ``restart_sec * (burst - 1)`` after the
    first, so any window wider than that span trips the limiter.  This
    returns the smallest value on :data:`_START_LIMIT_LADDER` clearing
    the span by :data:`START_LIMIT_MARGIN`.

    ``None`` when no window would work — a unit whose ``RestartSec`` is
    wider than an hour, or ``infinity``.  **The advice for those is the
    other lever**, and saying nothing is better than naming a number that
    does not fix it: the reader would paste it, watch the loop continue,
    and stop trusting the family.

    Note the direction, because it is counter-intuitive and the caller's
    wording depends on getting it right: a *bigger* interval is a
    *stricter* limiter.  Widening the window lets more starts fall inside
    it, which is why raising ``StartLimitIntervalSec`` is the fix and
    lowering it would make things worse.
    """
    cadence = DEFAULT_RESTART_SEC if restart_sec is None else restart_sec
    limit = DEFAULT_START_LIMIT_BURST if burst is None else burst
    if limit <= 1:
        # One start allowed: the second trips it whenever it happens, so
        # the window is irrelevant and there is nothing to suggest.
        return None
    span = cadence * (limit - 1)
    if span == float("inf"):
        return None
    wanted = span * START_LIMIT_MARGIN
    for candidate in _START_LIMIT_LADDER:
        if candidate > span and candidate >= wanted:
            return candidate
    return None


def _restart_recommendation(
    finding: UnitFinding, known: dict[str, str], duplicates: set[str]
) -> UnitRecommendationInfo:
    """Advice for a unit whose crash loop can never reach ``failed``.

    Severity ``advice``, not ``risk``, and the distinction is the one the
    orphan builder draws: ``risk`` describes something broken *now*.
    Nothing here is failing — these are healthy services whose *failure*
    would be silent.  Calling that a risk would put thirteen units on
    this box at the same severity as four dead ones, which is the
    flattening SNAG-ESTATE-001 spent itself undoing.

    Ranked second all the same, above ``unmonitored``, because
    monitoring is the weaker of the two safety nets: a wedged unit shows
    up as ``unreachable`` only if something polls it, whereas a start
    limit it can reach makes systemd itself say so.
    """
    burst = finding.start_limit_burst or DEFAULT_START_LIMIT_BURST
    interval = suggested_start_limit_interval(finding.restart_sec, burst)

    # Scope is part of a unit's identity, and this is the family where
    # that finally bites: ``deadlock-api-ingest.service`` is installed in
    # both scopes running two different binaries, and both are unbounded
    # today.  Two rows headed "Bound the restart loop in
    # deadlock-api-ingest.service" read as one item listed twice.  The
    # orphan builder gets away with a bare name only because no orphan
    # on this box is currently duplicated.
    label = finding.unit
    if finding.unit in duplicates:
        label = f"{finding.unit} ({finding.scope})"

    detail = f"{label} {finding.reason}."
    if finding.start_limit_interval is None and finding.start_limit_burst is None:
        detail += (
            " It declares no start limit at all, so systemd's defaults apply "
            f"({_seconds(DEFAULT_START_LIMIT_INTERVAL_DISPLAY)}, "
            f"{DEFAULT_START_LIMIT_BURST} starts) — a limit does exist, it is "
            "simply unreachable at this restart cadence."
        )
    if finding.project:
        detail += (
            f" The unit belongs to {finding.project}, so the edit is that "
            "repository's to make."
        )

    if interval is None:
        # No window on the ladder helps.  Say what would, rather than
        # emitting a snippet that looks like a fix and is not.
        detail += (
            " No StartLimitIntervalSec= would help at this RestartSec — "
            "lower RestartSec first, then set a window wider than "
            "RestartSec x (StartLimitBurst - 1)."
        )
        snippet = ""
        target: str | None = None
        action = f"Lower RestartSec= in {finding.path}, then re-run the sweep"
    else:
        detail += (
            f" Setting StartLimitIntervalSec={_seconds(interval)} makes {burst} "
            f"failed starts inside {_seconds(interval)} terminal, so the unit "
            "reaches `failed` and an OnFailure= hook can fire."
        )
        snippet = _start_limit_snippet(finding, interval, burst)
        target = finding.path
        action = (
            f"Add the lines below to the [Unit] section of {finding.path}, "
            f"then {_reload_command(finding.scope)}"
        )

    return UnitRecommendationInfo(
        kind="restart",
        severity="advice",
        unit=finding.unit,
        scope=finding.scope,
        project=finding.project,
        monitor_unit=finding.monitor_unit or finding.unit,
        title=f"Bound the restart loop in {label}",
        detail=detail,
        action=action,
        snippet=snippet,
        snippet_target=target,
    )


#: systemd's default window, restated here only for the human-readable
#: sentence.  The arithmetic reads it from
#: :mod:`sysadmin.units.scan`; this is presentation.
DEFAULT_START_LIMIT_INTERVAL_DISPLAY = 10.0


def _seconds(value: float) -> str:
    """A systemd time span, always in seconds.

    ``600s`` rather than ``10min`` even though systemd accepts both.  The
    snippet's comment states the burst span in seconds and the window
    beside it, and a sentence mixing ``40s`` with ``1min`` makes the
    reader do the conversion before they can check the arithmetic they
    are being asked to trust — which is the one thing this family cannot
    afford, since the naive version of the rule is wrong.
    """
    return f"{int(value)}s" if value == int(value) else f"{value}s"


def _ordinal(n: int) -> str:
    """``5`` -> ``5th``.  Only ever sees a StartLimitBurst, so 1-20 is ample."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _reload_command(scope: str) -> str:
    if scope == "user":
        return "systemctl --user daemon-reload"
    return "sudo systemctl daemon-reload"


def _start_limit_snippet(finding: UnitFinding, interval: float, burst: int) -> str:
    """The two lines to paste, in ``[Unit]``.

    ``[Unit]`` rather than ``[Service]``: systemd moved these keys there
    in v229.  The old placement is still accepted — :class:`UnitFile`
    reads both, because a unit written before the move would otherwise
    look like it declares no limit — but advice should emit the current
    form, and the two units on this box that get it right both use
    ``[Unit]``.

    ``StartLimitBurst=`` is emitted even when it is already the default.
    The pair is what makes the arithmetic legible: a lone
    ``StartLimitIntervalSec=600`` next to ``RestartSec=10`` requires the
    reader to remember that the burst is 5 before the line means
    anything, and Session 39's comment on ``sysadmin.service`` had to
    spell it out for exactly that reason.
    """
    lines = [
        f"# {finding.description}" if finding.description else None,
        "[Unit]",
        f"# Restart={finding.restart} with RestartSec="
        f"{_seconds(finding.restart_sec or 0)} puts the {_ordinal(burst)} start "
        f"{_seconds((finding.restart_sec or 0) * (burst - 1))} after the first; "
        "the window must be wider than that or the limit is unreachable.",
        f"StartLimitIntervalSec={_seconds(interval)}",
        f"StartLimitBurst={burst}",
    ]
    return "\n".join(line for line in lines if line)


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


def removal_command(finding: UnitFinding) -> str:
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
