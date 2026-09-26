"""Whether ``~/.claude/settings.json`` still parses — read here, not pulled.

Every other question this package asks is answered by the estate and
judged here (``ADR-0005``'s swap).  This one is asked here, and the
reason is that on 2026-09-08 it stopped being answerable anywhere else
honestly.

**The check this replaces half of compares two statements.**
estate-manager's check 11 (their ``audit/checks/wiring.py``) asks whether
each hook script's ``estate-hook-event:`` declaration matches
``~/.claude/settings.json``.  Until 2026-09-08 the estate wrote the first
operand and the owner the second, so agreement between them was two
parties agreeing.  Their ADR-0132 gave the estate the file's ``hooks``
key, and ADR-0067's justification for the check — *"the only check whose
subject the estate can neither write nor repair"* — became false.

**Moving the whole check here would have restored nothing**, which is
``docs/adr/0008-the-file-half-of-the-wiring-check.md`` §2: a move
relocates the *comparator* and leaves both *operands* the estate's, so a
green result would mean exactly what it meant before.  What the split
turns on is that the check's four codes do not take the same inputs:

===========================  ==================================  =========
code                         inputs                              owner
===========================  ==================================  =========
``hook_not_wired``           declarations **+** ``settings.json``  estate
``hook_wired_undeclared``    declarations **+** ``settings.json``  estate
``settings_unparseable``     ``settings.json`` alone               here
``settings_not_an_object``   ``settings.json`` alone               here
===========================  ==================================  =========

The bottom two need no statement of the estate's at all, so an
independent party genuinely can hold them — and they are the two
carrying the consequence the check was built for: a file that does not
parse takes *every* hook on this box down, the blocking ``Stop`` one
included, and no hook can report it because they fail open.

Four rules, three of them the opposite of the obvious implementation:

1. **It asks one question and refuses the neighbouring one.**  Whether
   the ``hooks`` key wires what the scripts declare stays with the
   estate, because answering it here would mean parsing
   ``estate-hook-event:`` — a format estate-manager owns and has already
   changed once (``aspect``, and ``none`` as a legitimate value).  That
   is ``SNAG-ESTATE-002``'s rule: splitting a producer's format is this
   repository parsing something the estate owns.

2. **"Cannot look" is not "looked and it is fine", and the distinction
   is the surface's** — :attr:`~sysadmin.estate.client.SurfaceResult.read`,
   which the agent gates *both* raising and resolving on.  A missing or
   unreadable file yields ``error`` and the sweep leaves any standing row
   alone; a file that is present and broken yields a *payload* saying so,
   because that is a fact about the box rather than about this reader's
   reach.  The estate's own check draws the same line for the same
   reason (their ADR-0016 §3), and reusing it is what lets a local read
   slot into a contract built for HTTP with no second vocabulary.

3. **The contract type is imported, never restated.**  This returns
   :class:`~sysadmin.estate.client.SurfaceResult` although nothing here
   is HTTP: those three fields *are* the agent's read/unread contract,
   and a second dataclass carrying the same three would be two
   statements of one contract free to drift — ``SNAG-DB-003``'s shape.
   The module it lives in is named for the surfaces it pulls; the type
   is not.

4. **The path is a constant and the function takes one.**  There is no
   config leaf, because a knob with exactly one legal value is
   ``SNAG-CFG-001`` at the size of a setting — the harness decides where
   this file lives and nobody may point the monitor elsewhere.  Taking
   the path as an argument is what makes it testable without one, which
   is ``journal.since_timestamp``'s argument for taking a ``datetime``:
   the type is what makes the wrong call impossible rather than merely
   discouraged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sysadmin.estate.client import SurfaceResult

__all__ = [
    "AGREEMENT_SURFACE",
    "SETTINGS_PATH",
    "SURFACE",
    "KIND_NOT_AN_OBJECT",
    "KIND_UNPARSEABLE",
    "compare_settings_paths",
    "read_settings",
]

#: This module's surface id, in the vocabulary
#: :data:`sysadmin.estate.client.SURFACE_PATHS` establishes.
#:
#: A sixth surface, and ``docs/adr/0006-wiring-joins-ports.md`` §7
#: refused one — *"it arrives in the same payload from the same HTTP
#: call, so it is one surface"*.  That ground does not survive the split:
#: this half no longer arrives in that payload at all, it is a read of a
#: different thing that fails for different reasons, and folding it into
#: ``audit_findings`` would let a successful pull of 8400 resolve a row
#: raised from the local filesystem — the exact "resolving on unknown"
#: the per-surface scoping exists to prevent.  The rejection is
#: superseded by its own stated reason.
SURFACE = "hook_wiring"

#: The **derived** surface: this module's read and the estate's audit,
#: compared on which file each of them read (``SNAG-CFG-007``).
#:
#: A surface of its own because its row rests on **two** reads, and the
#: sweep is scoped per surface: tagged ``hook_wiring``, a run in which
#: 8400 did not answer would resolve a standing disagreement on the
#: strength of one half of it — the "resolving on unknown" the per-surface
#: scoping exists to prevent.  See :func:`compare_settings_paths`.
AGREEMENT_SURFACE = "settings_path"

#: Where the harness reads its settings from.
#:
#: **Not resolved at import.**  ``expanduser`` at module scope freezes
#: one process's ``$HOME`` into a constant, and the resolved *target*
#: moved under this path on 2026-09-06 without the path itself changing
#: — which is precisely the kind of fact a reader wants measured at the
#: moment of the read rather than remembered.
SETTINGS_PATH = Path("~/.claude/settings.json")

#: The file is present, readable, and not JSON.
KIND_UNPARSEABLE = "unparseable"

#: The file is present, readable, valid JSON, and not an object — so it
#: declares no hooks at all, whatever else it contains.
KIND_NOT_AN_OBJECT = "not_an_object"


def _where(path: Path) -> dict[str, Any]:
    """The path as declared and as it actually lands.

    Both, because they stopped being the same file on 2026-09-06:
    ``~/.claude/settings.json`` is a symlink into ``~/projects/dotfiles``
    (estate ADR-0132 registered that tree ``status: active`` on
    2026-09-08).  A row naming only the symlink sends a reader to edit a
    file whose changes are tracked somewhere they were not told about;
    ``monitor/collation.py`` rule 4's *"the remedy's trap is carried in
    the alert"*, applied to a trap that is one day old.

    Resolution failure is reported as absence rather than raised: this
    runs to *describe* a fault and must never become one.

    **``RuntimeError`` is the one that can actually occur, and the guard
    said ``OSError`` until 2026-09-08** (estate message ``f5e450cb``,
    measured there after their identical line survived a mutation and
    re-measured here before this was widened).  ``resolve(strict=False)``
    swallows almost every hostile input — an over-long name, a descent
    through a file, an unsearchable parent and a sixty-link chain all
    return a path — and the only class that raises is a **loop**, whose
    errno-40 ``OSError`` :func:`pathlib.check_eloop` re-raises as a
    ``RuntimeError``.  That is not an ``OSError`` subclass, so the
    original guard was aimed at an exception this call cannot produce.
    Reachable rather than theoretical: ``~/.claude/settings.json`` is a
    symlink into ``~/projects/dotfiles``, which is what makes a loop
    constructible with one mistyped ``ln -s``, and ``_where`` runs
    *before* the file is opened — so uncaught it took down the surface
    whose whole job is to say every hook on this box is down.

    The loop still reaches :func:`read_settings`'s own ``except
    OSError``, because ``open()`` raises ELOOP without pathlib's
    conversion — so a loop reads as ``error`` (nothing looked), never as
    a payload.  Rule 2's line, arrived at from the filesystem's side.
    """
    where: dict[str, Any] = {"path": str(path)}
    try:
        target = path.resolve()
    except (OSError, RuntimeError):
        return where
    if target != path:
        where["resolves_to"] = str(target)
    return where


def read_settings(path: Path = SETTINGS_PATH) -> SurfaceResult:
    """Read the file and say whether it presents a JSON object.

    Rule 2 decides the three returns: an unreadable file is ``error``
    (unknown, so nothing is raised and nothing is swept), and a readable
    one is a payload — ``fault: None`` when it parses to an object, and a
    described fault when it does not.
    """
    path = path.expanduser()
    where = _where(path)

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        # Including "it does not exist". The estate's check calls this a
        # check error for the reason this repository calls it unread: an
        # auditor that cannot look must not file as though it had, and a
        # tree deployed somewhere without this file is not an owner who
        # deleted their hook wiring.
        return SurfaceResult(
            surface=SURFACE,
            error=f"{exc.__class__.__name__}: {where['path']} could not be read ({exc})",
        )

    try:
        settings = json.loads(raw)
    except json.JSONDecodeError as exc:
        # `str(exc)` and not `f"{exc.msg} at line {exc.lineno}"`, which
        # the live drive caught reading *"Unterminated string starting
        # at at line 671"*: several of json's messages already end in
        # "at" because theposition is meant to follow them, and the exception's
        # own `__str__` is the sentence that composes correctly for all
        # of them. Recomposing it by hand is a second statement of the
        # producer's format — `SNAG-DB-003`'s shape at the size of a
        # sentence — and no fixture would have shown it, because the
        # doubling only appears on the messages that carry a position.
        return SurfaceResult(
            surface=SURFACE,
            payload={
                **where,
                "kind": KIND_UNPARSEABLE,
                "fault": str(exc),
            },
        )

    if not isinstance(settings, dict):
        return SurfaceResult(
            surface=SURFACE,
            payload={
                **where,
                "kind": KIND_NOT_AN_OBJECT,
                "fault": f"the top level is {type(settings).__name__}, not an object",
            },
        )

    return SurfaceResult(surface=SURFACE, payload={**where, "kind": None, "fault": None})


def _target(where: dict[str, Any]) -> str | None:
    """The file a ``{path, resolves_to?}`` pair names.

    Both parties publish that pair by one rule — ``resolves_to`` present
    only when resolution moved the path (:func:`_where` here, their
    ``audit.finding.input_source``) — so an absent ``resolves_to`` means
    ``path`` *is* the file and the comparison is two strings, with no
    re-resolution of the estate's path on this side.  Re-resolving it
    would be a second derivation of a fact the producer already
    published, ``judge_queue_invariants``' *"the mask is read, never
    recomputed"*.
    """
    target = where.get("resolves_to")
    if isinstance(target, str) and target.strip():
        return target
    path = where.get("path")
    if isinstance(path, str) and path.strip():
        return path
    return None


def compare_settings_paths(
    audit: SurfaceResult | None, local: SurfaceResult | None
) -> SurfaceResult:
    """Whether the estate's wiring check and this read opened one file.

    ``SNAG-CFG-007``.  Since ADR-0008 two readers answer questions about
    ``~/.claude/settings.json`` — this module from a constant, the
    estate's check 11 from a *configured* ``WiringConfig.settings_file``
    — and if those ever name different files both report cleanly about
    their own and neither surface says which it used.  The estate began
    publishing its answer on 2026-09-11 (their message ``999f4432``):
    every check summary on ``GET /api/audit/invariants`` carries
    ``inputs``, and ``wiring``'s holds ``settings_file``.

    Three rules, two of them the opposite of the obvious implementation:

    1. **It returns a surface, not a verdict.**  The comparison rests on
       two reads, so it is *read* only when both were — an
       :class:`~sysadmin.estate.client.SurfaceResult` whose ``error``
       names the half that is missing otherwise.  That is what lets the
       agent's existing rules reach it without a branch: an unread
       surface raises nothing and sweeps nothing.

    2. **A summary that publishes no path is unread, never agreement.**
       ``payload.get(...)`` answers ``None`` both for a producer that
       read nothing and for one that has stopped saying, and collapsing
       either into "same file" would close a standing row on the day the
       estate rolls back — ``ports_checked``'s rule at the size of a
       dict key.  Every step down the payload that can be absent is
       named in the error, so ``unread_surfaces`` says *which* step.

    3. **Neither side is named as the wrong one.**  The constant says
       where the harness reads its settings, and the estate's value is
       configurable; the obvious sentence blames the configurable side.
       But the harness's own location can move too, and the day it does
       the *constant* is the stale half.  The payload carries both
       targets and the judge says they differ, which is what is known.
    """
    if audit is None or not audit.read:
        return SurfaceResult(
            surface=AGREEMENT_SURFACE,
            error="not compared: audit_invariants was not read",
        )
    if local is None or not local.read:
        return SurfaceResult(
            surface=AGREEMENT_SURFACE,
            error=f"not compared: {SURFACE} was not read",
        )

    last = (audit.payload or {}).get("last_audit")
    checks = last.get("checks") if isinstance(last, dict) else None
    wiring = checks.get("wiring") if isinstance(checks, dict) else None
    inputs = wiring.get("inputs") if isinstance(wiring, dict) else None
    theirs = inputs.get("settings_file") if isinstance(inputs, dict) else None
    theirs_target = _target(theirs) if isinstance(theirs, dict) else None
    if theirs_target is None:
        # The first step that is absent, or the path itself when every
        # step is present and the pair names no file.
        steps = (
            ("last_audit", last),
            ("last_audit.checks", checks),
            ("checks.wiring", wiring),
            ("wiring.inputs", inputs),
            ("inputs.settings_file", theirs),
        )
        missing = next(
            (step for step, value in steps if not isinstance(value, dict)),
            "inputs.settings_file.path",
        )
        return SurfaceResult(
            surface=AGREEMENT_SURFACE,
            error=f"not compared: the estate's audit summary publishes no {missing}",
        )

    # Narrowed for the reader and the type checker alike: a target was
    # found, so every step above it was a mapping.
    assert isinstance(last, dict) and isinstance(theirs, dict)

    ours = local.payload or {}
    ours_target = _target(ours)
    if ours_target is None:
        # Unreachable while `read_settings` is the producer — every
        # payload it returns carries `path` — and kept for rule 2's
        # reason: a missing operand is never an agreement.
        return SurfaceResult(
            surface=AGREEMENT_SURFACE,
            error=f"not compared: {SURFACE} published no path",
        )

    return SurfaceResult(
        surface=AGREEMENT_SURFACE,
        payload={
            "ours": {k: ours[k] for k in ("path", "resolves_to") if k in ours},
            "theirs": {k: theirs[k] for k in ("path", "resolves_to") if k in theirs},
            "ours_target": ours_target,
            "theirs_target": theirs_target,
            "same_file": ours_target == theirs_target,
            "audit_finished_at": last.get("finished_at"),
        },
    )
