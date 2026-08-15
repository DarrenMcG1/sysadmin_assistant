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
4. ``host`` — hand-written infrastructure with no project.  Last of the
   unit kinds not because it matters least (``pgbackrest-backup`` is the
   estate's only database backup) but because it is a documentation gap
   rather than a defect: the unit is running fine, nobody is watching.
5. ``port`` (Session 26c) — the estate's port registry disagrees with
   the box: one port claimed by two rows, or a row attributing a port to
   a project that does not own the unit holding it.  **Last, and it is
   the only kind where nothing on this box is broken or unwatched** —
   the document is wrong and the box is right.  It is reported here
   because estate-manager's audit is *structurally* unable to see
   either case (it folds the table into a ``set`` and runs ``ss``
   without ``-p``), not because it outranks a unit nobody is watching.
   The live half of that check does not appear here at all: a port held
   by the wrong unit is a fault in progress and gets its own alert row.

**Never auto-edit the config.**  services.yaml is hand-curated and its
comments carry reasoning a writer would flatten.  Advice only: the
snippet is text for a human to paste.

**Advice must be executable, and Session 48 was the first sitting to
check.**  Sessions 46, 47 and 26c made the diagnosis speak; nobody had
carried out what it says.  Two defects surfaced within the hour, both
the same root cause — this module under-reading a finding the sweep had
already filled in:

* **A snippet is offered only for a unit something starts.**  ``kind:
  systemd`` asserts the unit is *active* and ``kind: timer`` that the
  schedule is armed, so wiring up a disabled unit declares a check that
  fails on every poll for ever.  Measured: pasting the two suppressed
  snippets would have written **two ``critical`` rows every 300 s**, the
  pile-up shape Sessions 41-45 spent themselves deleting, arriving
  through this module's own remediation text.  The gate is "nothing
  enables it" rather than "it is not running", because ``enabled`` is an
  enablement symlink the sweep already walks and staying pure matters
  more than the sharper test.  ``manual`` is a subset — no ``[Install]``
  means it cannot be enabled — so it is tested first and keeps its
  wording.
* **A folded oneshot's timer is removed with its service.**
  ``monitor_unit`` names the timer, and the timer is the half carrying
  ``[Install]``; removing only the service leaves a ``Requires=``
  pointing at nothing, which the next sweep cannot see because a timer
  with no service is not a finding shape this module has.

And the rule both of them imply: **an advice row that offers no snippet
must not say "paste the snippet below"**.  ``sysadmin-failed.service``
shipped exactly that, which is an item an execution sitting cannot
close, so it returns on every sweep for ever — the roll-up defect
wearing a single unit's name.  Every no-snippet row now names its real
next step, and for a disabled unit that step is a fork: enable it and
the next sweep emits a snippet, or remove it.

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

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from pathlib import Path
from typing import Any

from sysadmin.core.contracts import UnitRecommendationInfo
from sysadmin.units.ports import DUPLICATE_CLAIM
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
KIND_ORDER = ("orphan", "restart", "unmonitored", "host", "port")

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
    ports: Mapping[str, Any] | None = None,
) -> list[UnitRecommendationInfo]:
    """Ranked advice for one unit sweep.

    ``registry`` is consulted only to decide *where* a snippet
    should go — whether the finding's project already has a manifest
    entry to extend.  It is never written to.

    ``ports`` is the stored ``findings['ports']`` blob and does two
    unrelated jobs, both of which need a port and neither of which the
    sweep could do before Session 26c: it upgrades a wired-up snippet
    from the liveness-only ``kind: systemd`` to a real ``kind: http``
    (SNAG-UNITS-001), and it contributes the registry-disagreement
    advice.  ``None`` — a sweep stored before 26c, or one whose ``ss``
    call failed — degrades to exactly the behaviour that shipped
    before, which is why every read of it is defensive.
    """
    known = _project_ids(registry)
    # Computed here, once, so every snippet for a two-scope unit agrees
    # on the disambiguated name.
    duplicates = duplicate_units(findings)
    held = _held_ports(ports)

    paired = [(f, _recommend(f, known, duplicates, held)) for f in findings]
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
    ranked = [rec for _, rec in paired]
    # Appended rather than sorted in: ``port`` is last in ``KIND_ORDER``
    # and has no unit to tie-break on, so the sort key above does not
    # describe it.  Its own order is the one ``judge_ports`` already
    # applied — worst kind, then port ascending.
    ranked.extend(_port_recommendations(ports))
    return ranked


def _held_ports(ports: Mapping[str, Any] | None) -> dict[str, list[int]]:
    """``"scope:unit"`` → the audited ports it holds, from the stored blob."""
    if not ports:
        return {}
    raw = ports.get("unit_audited_ports") or {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): [int(p) for p in value]
        for key, value in raw.items()
        if isinstance(value, list)
    }


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
    finding: UnitFinding,
    known: dict[str, str],
    duplicates: set[str],
    held: Mapping[str, Sequence[int]] = (),  # type: ignore[assignment]
) -> UnitRecommendationInfo:
    kind = _KIND_FOR_CATEGORY.get(finding.category, "host")
    builder = {
        "orphan": _orphan_recommendation,
        "restart": _restart_recommendation,
        "unmonitored": _unmonitored_recommendation,
        "host": _host_recommendation,
    }[kind]
    return builder(finding, known, duplicates, held)


# --------------------------------------------------------------------------
# Per-kind advice
# --------------------------------------------------------------------------


def _orphan_recommendation(
    finding: UnitFinding,
    known: dict[str, str],
    duplicates: set[str],
    held: Mapping[str, Sequence[int]] = (),  # type: ignore[assignment]
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
    finding: UnitFinding,
    known: dict[str, str],
    duplicates: set[str],
    held: Mapping[str, Sequence[int]] = (),  # type: ignore[assignment]
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


def _enable_command(finding: UnitFinding) -> str:
    """``systemctl enable --now`` for the unit that actually starts it.

    ``monitor_unit`` rather than ``unit``: enabling a folded oneshot's
    *service* arms nothing, because a oneshot with a timer is started by
    the timer.  Same field, same reason, as :func:`removal_command`.
    """
    if finding.scope == "user":
        return f"systemctl --user enable --now {finding.monitor_unit}"
    return f"sudo systemctl enable --now {finding.monitor_unit}"


def _no_snippet_action(finding: UnitFinding) -> str:
    """What to do about a finding this module declines to wire up.

    An advice row carrying an empty snippet under the text "paste the
    snippet below" is the thing an execution sitting cannot close: it
    reads as actionable, is not, and returns on every sweep for ever.
    Both no-snippet cases have a real next step, so they say it.
    """
    if finding.manual:
        return (
            "Nothing to wire — a hand-started unit has no steady state to "
            "check. Leave it, or remove it if it is no longer wanted."
        )
    return (
        f"Decide whether it should run: {_enable_command(finding)} and the "
        "next sweep will emit a snippet, or remove the unit if it is no "
        "longer wanted. Do not wire up a disabled unit — the check would "
        "fail on every poll."
    )


def _unmonitored_recommendation(
    finding: UnitFinding,
    known: dict[str, str],
    duplicates: set[str],
    held: Mapping[str, Sequence[int]] = (),  # type: ignore[assignment]
) -> UnitRecommendationInfo:
    """Advice for a live project's unwatched unit."""
    target, snippet = _snippet_for(finding, known, duplicates, held)
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
    elif not finding.enabled:
        detail += (
            f" Nothing enables {finding.monitor_unit}, so no snippet is "
            "offered: a check on a unit the box never starts would report "
            "it unhealthy on every poll."
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
        action=(
            f"Paste the snippet below into {where}, then restart sysadmin.service"
            if snippet
            else _no_snippet_action(finding)
        ),
        snippet=snippet,
        snippet_target=target,
    )


def _host_recommendation(
    finding: UnitFinding,
    known: dict[str, str],
    duplicates: set[str],
    held: Mapping[str, Sequence[int]] = (),  # type: ignore[assignment]
) -> UnitRecommendationInfo:
    """Advice for hand-written infrastructure with no project."""
    target, snippet = _snippet_for(finding, known, duplicates, held)

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
    elif not finding.enabled:
        detail += (
            f" Nothing enables {finding.monitor_unit}, so no snippet is "
            "offered: a check on a unit the box never starts would report "
            "it unhealthy on every poll."
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
        action=(
            "Paste the snippet below into services.yaml under services:"
            if snippet
            else _no_snippet_action(finding)
        ),
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

    **A folded oneshot's timer is removed too**, and leaving it out was
    the defect: ``classify_units`` already folds a oneshot under the
    timer that starts it, so ``monitor_unit`` names the timer — and the
    timer, not the service, is the half carrying ``[Install]`` and the
    enablement symlink.  Removing only the service leaves a timer whose
    ``Requires=`` points at a unit that no longer exists, which systemd
    reports on every ``daemon-reload`` and which the next sweep cannot
    see, because a timer with no service is not a finding shape this
    module has.  Measured on this box 2026-08-15:
    ``ticktick-sync.service`` is an orphan whose ``ticktick-sync.timer``
    the emitted command silently left behind.

    The timer's path is its sibling in the same directory rather than a
    field, because a unit and the timer that starts it are installed
    together — the sweep walks one directory per scope.
    """
    targets = [finding.unit]
    paths = [str(finding.path)]
    if finding.monitor_unit and finding.monitor_unit != finding.unit:
        # Timer first: disabling the timer disarms the schedule before
        # the service it triggers goes away.
        targets.insert(0, finding.monitor_unit)
        paths.insert(0, str(Path(finding.path).parent / finding.monitor_unit))

    units = " ".join(targets)
    files = " ".join(paths)
    if finding.scope == "user":
        return (
            f"systemctl --user disable --now {units} "
            f"&& rm {files} "
            "&& systemctl --user daemon-reload"
        )
    return (
        f"sudo systemctl disable --now {units} "
        f"&& sudo rm {files} "
        "&& sudo systemctl daemon-reload"
    )


def _snippet_for(
    finding: UnitFinding,
    known: dict[str, str],
    duplicates: set[str],
    held: Mapping[str, Sequence[int]] = (),  # type: ignore[assignment]
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

    if not finding.enabled:
        # Same argument as ``manual``, one step more general, and the
        # reason this gate exists at all: a unit nothing enables has no
        # steady state either.  ``kind: systemd`` asserts the unit is
        # active and ``kind: timer`` that the schedule is armed, so
        # wiring up a disabled unit declares a check that fails on every
        # poll for ever — the pile-up shape Sessions 41-45 spent
        # themselves deleting, re-created by this module's own advice.
        #
        # Measured 2026-08-15: of five ``host`` findings on this box the
        # two with ``enabled=False`` (``deadlock-api-ingest.service``
        # system, and its updater timer) were both ``inactive``, and the
        # three with ``enabled=True`` were all ``active``.
        #
        # ``manual`` is a *subset* of this — no ``[Install]`` section
        # means the unit cannot be enabled — so it is tested first and
        # keeps its more specific wording.
        #
        # Purity is preserved: ``enabled`` is an enablement symlink the
        # sweep already walks, and :func:`classify_units` folds a
        # oneshot's timer enablement into it, so a live schedule is
        # never read as dormant.  The sweep still cannot see *active*
        # state without a subprocess, which is why the gate is
        # "nothing starts it" rather than "it is not running".
        return None, ""

    return "services.yaml", _services_yaml_snippet(finding, known, duplicates, held)


def _services_yaml_snippet(
    finding: UnitFinding,
    known: dict[str, str],
    duplicates: set[str],
    held: Mapping[str, Sequence[int]] = (),  # type: ignore[assignment]
) -> str:
    """A services.yaml entry for one unwired unit.

    **``kind: http`` when the port is known, ``kind: systemd`` when it
    is not** (SNAG-UNITS-001, fixed in Session 26c).  A ``systemd``
    check asserts only that the unit is *active*, and a backend that is
    running while every request 500s is active, healthy by that check,
    and broken — the failure an HTTP service is most likely to have and
    the only one a unit check structurally cannot see.  The snag's own
    proposed fix was a comment saying so, on the grounds that *"this
    scan does not know the unit's port"*.  That sentence was true of
    the sweep and is no longer true of the sweep's siblings:
    :mod:`sysadmin.units.ports` reads ``/proc/<pid>/cgroup`` for every
    listener, and on this box all twelve attributed units hold exactly
    one port in the registry's range.

    Three rules, because the upgrade is only an improvement if it is
    narrow:

    1. **Exactly one audited port, or no upgrade.**  Two ports means
       guessing which one is the service, and a url pointing at the
       wrong one produces a check that alerts about something real
       happening somewhere else.
    2. **The health path is the contract's, and the snippet says so
       twice.**  The sweep observes a *port*; it never fetches, so
       ``/api/health`` is what
       ``docs/guides/monitorable-project.md`` requires rather than what
       this unit was seen to answer.  Measured on 2026-08-15, that
       default is **right for 4 of the 11 services declared here and
       wrong for 7** — three llama-servers on ``/health``,
       ``sports_analyser`` on ``/api/v1/health``, ``sysadmin`` itself on
       ``/health``, and two frontends with no path at all.  Kept anyway,
       and the reason is this repository's own standing preference:
       a wrong url fails *loudly* within one poll of pasting it, where
       ``kind: systemd`` under-monitors silently for ever, which is
       SNAG-UNITS-001 itself.  The comment names the two other shapes in
       use so the fix is one edit rather than an investigation.  Filed
       as ``SNAG-UNITS-003`` with the candidate fix (probe once when the
       snippet is generated) and the reason it was not taken here.
    3. **The comment survives the downgrade.**  Where no port is known
       the entry still says a url would buy a real check, because the
       reader pasting it is the person who knows what the unit serves.

    A timer gets ``kind: timer``, which is the declaration that stops
    its oneshot service being checked, and ``controllable: false``,
    because start and stop from the tray would arm or disarm a schedule
    rather than restart something.  Timers are never upgraded: a timer
    holds no socket, and the oneshot behind it is not running when the
    check would look.

    ``project:`` is emitted only when the project is *declared* — an id
    no manifest claims fails at load, so guessing one would turn advice
    into an outage.
    """
    is_timer = finding.monitor_unit.endswith(".timer")
    # Keyed on the unit that holds the socket, which is ``unit`` and not
    # ``monitor_unit``: for a folded oneshot those differ, and the timer
    # never listens.  ``is_timer`` short-circuits it anyway; the lookup
    # is written this way so it stays right if that ever changes.
    port = _sole_port(held, finding.scope, finding.unit) if not is_timer else None
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
    if is_timer:
        lines.append("    kind: timer")
    elif port is not None:
        lines.append("    kind: http")
        lines.append(
            f"    url: http://localhost:{port}/api/health"
            "   # observed port; path is the contract's default"
        )
        lines.append(
            "    # check it answers — /health and /api/v1/health are both in use here"
        )
        lines.append(f"    port: {port}")
    else:
        lines.append("    kind: systemd")
        lines.append(
            "    # no listening port attributed to this unit — if it serves HTTP, "
            "use kind: http with a url; kind: systemd only asserts the unit is active"
        )
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


def _port_recommendations(
    ports: Mapping[str, Any] | None,
) -> list[UnitRecommendationInfo]:
    """Advice for the registry disagreements — the half that does not alert.

    Only the non-collision kinds reach here.  ``wrong_unit`` and
    ``port_shared`` describe the box disagreeing with itself now and get
    an alert row each; ``duplicate_claim`` and ``wrong_project``
    describe a document that is wrong while the box is right, which is
    debt and belongs beside the orphan and restart tiers.  The split is
    read off :data:`~sysadmin.units.ports.COLLISION_KINDS` rather than
    restated, so the alert family and this list cannot come to disagree
    about which findings are faults.

    **No snippet, deliberately**, and this is the one advice kind with
    none.  The fix is a row in another repository's markdown table and
    the correct row needs the prose in its role column — inventing that
    would be this service writing an estate document rather than
    pointing at one, and the estate rule about writes into another
    repository is the one boundary this tier has stayed inside while
    happily emitting text for other projects' unit files.  ``action``
    names the document and the line instead.
    """
    if not ports:
        return []
    raw = ports.get("findings")
    if not isinstance(raw, list):
        return []
    document = ports.get("registry_document") or "the port registry"

    recs: list[UnitRecommendationInfo] = []
    for item in raw:
        if not isinstance(item, dict) or item.get("collision"):
            continue
        raw_detail = item.get("detail")
        detail: dict[str, Any] = raw_detail if isinstance(raw_detail, dict) else {}
        port = item.get("port")
        kind = item.get("kind")
        if kind == DUPLICATE_CLAIM:
            lines = detail.get("rows") or []
            where = ", ".join(
                f"line {row.get('line')} ({row.get('project')})"
                for row in lines
                if isinstance(row, dict)
            )
            action = (
                f"Two rows of {document} claim port {port} — {where}. "
                "Decide which is current and delete or renumber the other; "
                "the estate's audit folds the table into a set and cannot "
                "report this."
            )
            title = f"Port {port} is claimed twice in the registry"
        else:
            action = (
                f"{document} line {detail.get('registry_line')} gives port "
                f"{port} to {detail.get('registry_project')}; the unit holding "
                f"it ({detail.get('holding_unit')}) belongs to "
                f"{detail.get('actual_project')}. Correct the row, or move the "
                "service to the port its own row claims."
            )
            title = f"Port {port} is attributed to the wrong project"

        # ``holding_unit`` is the sweep's ``"<scope>:<unit>"`` key, and
        # the contract splits the two — scope is part of a unit's
        # identity here, not decoration.  A duplicate registry row has
        # no holder at all, which is why both sides default rather than
        # being parsed out of an empty string.
        holder = str(detail.get("holding_unit") or "")
        unit_scope, _, unit_name = holder.partition(":") if ":" in holder else ("user", "", "")

        recs.append(
            UnitRecommendationInfo(
                kind="port",
                severity="advice",
                unit=unit_name,
                scope=unit_scope,
                project=detail.get("actual_project"),
                monitor_unit="",
                title=title,
                detail=str(item.get("summary") or ""),
                action=action,
                snippet="",
                snippet_target=None,
            )
        )
    return recs


def _sole_port(
    held: Mapping[str, Sequence[int]], scope: str, unit: str
) -> int | None:
    """The one audited port this unit holds, or ``None``.

    ``None`` for zero ports (nothing listening, or a root-owned socket
    ``ss`` would not attribute) and for two or more (which one is the
    service is a guess).  Both collapse to "make no claim" for the
    reason :func:`~sysadmin.units.scan.parse_timespan` returns ``None``
    rather than zero: advice built on a guess costs more than no advice.
    """
    if not held:
        return None
    ports = held.get(f"{scope}:{unit}") or ()
    return int(ports[0]) if len(ports) == 1 else None


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
