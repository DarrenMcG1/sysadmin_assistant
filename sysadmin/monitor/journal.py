"""Journalctl log reading helpers."""

import asyncio
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sysadmin.monitor.log_signature import signature

logger = logging.getLogger(__name__)

#: Entries parsed from one read.  A ceiling is unavoidable — the kernel
#: journal on this box has sustained 8.5 messages a second for days — so
#: the question is only whether hitting it is visible.  It was not:
#: ``-n 500`` was passed with no report, and ``findings_count`` sat at
#: exactly 200 on every single run while nobody read it as a symptom
#: (``SNAG-AGENT-005``).
DEFAULT_READ_LIMIT = 500


@dataclass(frozen=True)
class JournalRead:
    """One read of a journal, with the two facts a poller needs back.

    ``read_journal`` used to return a bare list, which could express
    neither "where to resume" nor "there was more than this".
    """

    entries: list[dict[str, Any]]
    #: Opaque journalctl cursor of the newest entry seen, or ``None`` when
    #: the read was empty.  Taken **before** the severity filter — see
    #: :func:`read_journal`.
    cursor: str | None = None
    #: The read hit ``limit``, so older unread entries were skipped.
    truncated: bool = False

# journalctl priority mapping (RFC 5424)
PRIORITY_MAP = {
    "0": "critical",  # emerg
    "1": "critical",  # alert
    "2": "critical",  # crit
    "3": "error",
    "4": "warning",
    "5": "info",      # notice
    "6": "info",
    "7": "debug",
}

SEVERITY_ORDER = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}


def max_priority_for(severity_filter: str) -> int:
    """The journalctl ``-p`` ceiling that admits exactly ``severity_filter``.

    **Derived from :data:`PRIORITY_MAP`, never written down beside it.**
    A second table mapping severity to a priority number is two statements
    of one fact that can disagree — the shape ``chk_alert_agent`` against
    ``AGENT_NAMES`` has, and the reason ``syslog_priority`` is pinned to
    this same map by a round-trip test rather than asserted on each side.

    ``journalctl -p N`` admits priorities ``0..N`` inclusive, which is the
    same "this rung and every louder one" that :data:`SEVERITY_ORDER`
    expresses in the other direction, so the two compose without a
    conversion rule anybody has to remember.
    """
    floor = SEVERITY_ORDER.get(severity_filter, 0)
    admitted = [
        int(code)
        for code, name in PRIORITY_MAP.items()
        if SEVERITY_ORDER.get(name, 0) >= floor
    ]
    # An unknown filter admits everything, matching the Python filter's own
    # ``.get(severity_filter, 0)`` above rather than failing differently.
    return max(admitted) if admitted else max(int(c) for c in PRIORITY_MAP)


def read_ceiling(
    severity_filter: str, declared: Mapping[str, str] | None = None
) -> int:
    """The ``-p`` ceiling wide enough for the filter *and* every declaration.

    **Derived, so a declaration cannot be made invisible by a config
    edit** (``SNAG-CFG-006``).  ``arrives_at`` used to be *asserted*
    against the shipped ``config.yaml`` by a test, and
    :mod:`sysadmin.reload` re-reads that file on ``SIGHUP`` — so
    narrowing the kernel source back to ``error`` disarmed the
    declaration on the running daemon with the suite still green.  A
    relation that is derived cannot be broken by an edit, which is why
    this is a computation rather than a second verdict in ``reload.py``:
    ``max_priority_for`` against ``PRIORITY_MAP``'s rule, one level up.

    ``journalctl -p N`` admits ``0..N``, so *wider* is a **larger**
    number and the composition is a ``max``.  Note the wording that
    reads backwards: the declaration needing the widest read is the
    **quietest** one, because a quiet rung sits at a high priority
    number.

    ``declared`` maps a normalised signature to the rung its producer
    stamps it with.  Empty or ``None`` returns ``max_priority_for``
    unchanged, so a source that declares nothing reads exactly as it did
    before this existed — :func:`read_journal`'s ``log_format``
    precedent.
    """
    ceiling = max_priority_for(severity_filter)
    for rung in (declared or {}).values():
        ceiling = max(ceiling, max_priority_for(rung))
    return ceiling


def admits(
    severity: str,
    severity_filter: str,
    message: str,
    declared: Mapping[str, str] | None = None,
) -> bool:
    """Is this line stored — by its rung, or by a declaration below it?

    **The reader has two gates and widening one alone is inert.**
    ``SNAG-CFG-006`` named only the ``-p`` ceiling; measured against the
    live kernel journal with ``severity_filter`` at ``error``, forcing
    ``-p 6`` returns the same 32 entries and the same **zero** ``VRAM is
    lost due to GPU reset!`` lines, because this filter — which
    :func:`read_journal` calls the authority on what is stored — drops
    them one loop later.  So both gates move together, and they move from
    one argument so they cannot drift apart.

    **Widened per signature, never wholesale.**  Lowering the floor to
    the declaration's rung would store all 1,823 info-level kernel lines
    a boot while ``config.yaml`` said ``error`` — a config edit that does
    nothing, which is worse than the gap it closes.  A line below the
    floor is admitted only when its own signature is declared, so an
    operator's narrowing still governs everything nobody has spoken for.

    **The signature is computed only when the rung gate has already
    failed and something is declared.**  :meth:`LogAggregatorAgent._execute`
    already had to make this move one layer up — *"a declared signature
    is precisely one whose rung does not admit it, so the gate cannot be
    asked before the key exists"* — and the same argument arrives here.
    The cost is a regex pass over lines that were about to be discarded,
    bounded by the read limit; with nothing declared it is not paid at
    all.

    ``severity_filter`` is read through ``.get(..., 0)`` so an unknown
    filter admits everything, which is what :func:`max_priority_for`
    already does with the same value on the other side of the same
    read.
    """
    if SEVERITY_ORDER.get(severity, 0) >= SEVERITY_ORDER.get(severity_filter, 0):
        return True
    if not declared:
        return False
    return signature(message) in declared


def message_text(value: Any) -> str:
    """``MESSAGE`` as text, whatever shape journald handed it back in.

    Three shapes reach here and only the first is the common case.

    A **string** is an ordinary record.  A **list of integers** is a field
    holding bytes that are not valid UTF-8, which ``-a`` renders as an
    array of byte values rather than as a string — the one new shape ``-a``
    introduces, since without it such a field is simply ``null``.  And
    **absent or null** is what remains: a field journald did not return.

    The fallback is ``""`` rather than ``None`` because a caller slicing
    the result is the whole of ``SNAG-LOG-004``.  It is deliberately not a
    raise: one unreadable record must not cost the other 499 in the read,
    which is ``collation.py``'s fail-open posture rather than
    ``schema_guard``'s — nothing is served against a wrong schema here, a
    single line is simply blank and the entry still carries its severity,
    timestamp and ``raw_line``.

    Measured before being written: 205,298 kernel records over seven days
    returned ``str`` for every one, with and without ``-a``.  So the list
    branch has an empty population on this box and exists because the
    shape is journalctl's to choose, not because it has been seen.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        try:
            return bytes(value).decode("utf-8", errors="replace")
        except (TypeError, ValueError):
            return ""
    return ""


def unwrap_json_message(text: str) -> tuple[str, dict[str, str]]:
    """Lift the human-readable part out of a record declared ``format: json``.

    Returns the message and whatever metadata the envelope gave up for
    free.  Applied **only where a source declares it** — the reader is
    honouring a statement, not recognising an application
    (``SNAG-LOG-003``).

    Four rules, three of them the opposite of the obvious implementation:

    1. **It fails open at every step.**  A line that is not JSON, is not
       an object, or carries no ``message`` string is returned unchanged.
       This is not defensive habit: systemd writes its **own** plain-text
       lines into a unit's journal at error level — ``Failed to start
       SportsAnalyser - Frontend (Next.js).`` appears 668 times in the
       live journal, and nine distinct such messages exist — so a
       declaration that discarded non-JSON would silence exactly the line
       saying the service died.  A declaration describes what the
       *application* writes; it can never describe everything in the
       journal it writes to.
    2. **Severity is not taken from the envelope.**  ``"level": "ERROR"``
       sits right beside the message and is deliberately ignored: since
       :class:`~sysadmin.core.logging_config.JournalLevelPrefixFormatter`
       the record's ``PRIORITY`` already carries it, and two statements of
       one fact that can disagree is the defect
       :func:`max_priority_for` exists to avoid.  The prefix is also the
       half that works for ``journalctl -p err`` and ``OnFailure=``,
       which a reader-side parse never reaches.
    3. **The envelope is not lost.**  ``raw_line`` still holds the
       journalctl record verbatim, so ``exc_info`` and every other field
       stays one query away.  The unwrap changes what the *identity* is
       built from, not what is kept.
    4. **``logger`` is carried into metadata and not into the title.**
       Measured over the 723 real ``ERROR`` lines this daemon has
       written: the title goes from 6 distinct values of 242–253
       characters of JSON to **5** of 46–151 readable characters.  The
       one merge is ``sysadmin.core.scheduler`` and
       ``sysadmin.services.scheduler`` both emitting
       ``scheduler_job_error`` — one fault under a renamed module, which
       the old key forked only because the module path happened to fall
       inside the 252 characters that survived truncation.  Putting
       ``logger`` back in the title would restore that fork by design.

    The limit this leaves is stated rather than implied: ``agent_run_failed``
    is written by all five agents, so five different failures share one
    signature.  That is **not a regression** — the truncated JSON title cut
    at ``"servic`` and never reached the ``agent`` field either — and
    closing it means choosing which further envelope fields join the
    identity, which is recognising this application again.
    """
    if not text.startswith("{"):
        return text, {}
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text, {}
    if not isinstance(payload, dict):
        return text, {}
    message = payload.get("message")
    if not isinstance(message, str) or not message:
        return text, {}
    logger_name = payload.get("logger")
    return message, {"logger": logger_name} if isinstance(logger_name, str) else {}


def since_timestamp(moment: datetime) -> str:
    """Format ``moment`` as a journalctl ``--since`` argument.

    ``@<epoch seconds>`` rather than a formatted datetime, because
    journalctl reads a bare ``YYYY-MM-DD HH:MM:SS`` in **local** time while
    everything stored here is UTC — a one-hour window silently shifted by
    the BST offset is the kind of gap that only shows up in winter.

    **A naive ``moment`` is refused rather than converted**
    (``SNAG-LOG-009``).  ``datetime.timestamp()`` reads a naive value as
    *local*, which is the very reading this function exists to avoid — so
    accepting one would rebuild the defect inside its own fix, silently
    and with the right-looking type.  Every caller reads
    ``log_entries.logged_at``, a ``timestamp with time zone``, so the
    guard has an empty population by construction and exists to keep it
    that way.  Loud beats silent: ``SNAG-UNITS-003``'s trade.
    """
    if moment.tzinfo is None:
        raise ValueError(
            "since_timestamp needs an aware datetime: a naive one is read "
            "as local time, which is the ambiguity this function removes"
        )
    return f"@{int(moment.timestamp())}"


async def read_journal(
    unit: str,
    since: str = "5m ago",
    severity_filter: str = "warning",
    user: bool = False,
    after_cursor: str | None = None,
    limit: int = DEFAULT_READ_LIMIT,
    log_format: str = "text",
    declared: Mapping[str, str] | None = None,
) -> JournalRead:
    """Read journal entries for a systemd unit.

    **Resume from ``after_cursor``, not from a time window.** The caller
    used to pass ``since="2m ago"`` on a 60-second poll, so every entry was
    ingested exactly twice — confirmed at two copies for all 18
    ``venture-assistant-backend`` and all 15 ``sportsanalyser-frontend``
    events (``SNAG-AGENT-005``). Narrowing the window instead would trade
    the duplicate for a gap whenever a run ran long, which is the worse
    failure for a monitor: a cursor overlaps safely because journalctl,
    not a clock, decides what has already been read.

    ``since`` is still the **first** read of a source and the fallback when
    a cursor no longer resolves — the journal is vacuumed and rotated, so a
    cursor from before a rotation is simply gone, and treating that as a
    hard failure would stop a source for good.

    Args:
        unit: systemd unit name (e.g. 'postgresql.service'), or 'kernel'.
        since: time specification used only when there is no usable cursor.
        severity_filter: minimum severity to include.
        user: read a *user* unit's journal (journalctl --user).
        after_cursor: resume position from the previous read.
        limit: maximum entries to take from one read.
        log_format: the source's declared encoding — ``json`` unwraps each
            record through :func:`unwrap_json_message`. Defaults to
            ``text``, so a source that declares nothing is read exactly as
            it was before the field existed.
        declared: signatures this source speaks for below its own floor,
            mapped to the rung their producer stamps them with — the
            :data:`~sysadmin.monitor.log_aggregator.CRITICAL_SIGNATURES`
            entries for this source, keyed the way ``log_entries.source``
            is keyed. It widens **both** gates together
            (:func:`read_ceiling` and :func:`admits`), because widening
            either alone is measurably inert. ``None`` is ``log_format``'s
            default read again: a source that declares nothing is read
            exactly as it was before this existed.

    Returns:
        A :class:`JournalRead`.
    """
    base = [
        "journalctl",
        "-o", "json",
        "--no-pager",
        # ``-a`` is load-bearing and its absence was a crash, not a
        # cosmetic loss.  ``-o json`` replaces any field over ~4096 bytes
        # with ``null`` unless it is passed, so ``MESSAGE`` came back
        # ``None`` and ``entry["message"][:5000]`` in the aggregator raised
        # ``TypeError`` — taking the whole run down, every source in it,
        # once a minute for ever, because the failure it logs is itself a
        # 12.8 kB line that reproduces the read (``SNAG-LOG-004``).
        #
        # Reachable only for a source that puts a long record on **one**
        # line, which on this box is this daemon alone: a Python traceback
        # from any other service arrives as many short journal entries,
        # while ``JsonFormatter`` folds ``exc_info`` into a single
        # ``MESSAGE``.  Measured: all 215 historic ``agent_run_failed``
        # lines are 12,837–12,845 bytes and every one exceeds the cap.
        # It could not fire before 2026-08-17 because those lines were
        # stamped ``PRIORITY=6`` and ``-p`` excluded them; Session 61's
        # level prefix is what armed it.
        #
        # Note this is a property of the **JSON serialiser**, not of
        # journalctl's reading: the same records print in full under the
        # default text output, which is why ``journal_command`` — the
        # invocation a recommendation hands a human — needed no change.
        "-a",
        "-n", str(limit),
        # The severity filter is applied **server-side as well**, because
        # ``limit`` bounds the lines journalctl returns and the Python
        # filter below runs after they have already been counted against
        # it.  Measured on the 2026-08-12 kernel storm: 107,353 raw lines
        # over four hours of which 42,298 (39 %) survive kernel's
        # ``severity_filter: error``, so a 500-line budget was carrying
        # ~195 usable entries.  Per minute that is a median of 510 raw
        # against a ceiling of 500 — 208 of 210 storm minutes truncated,
        # and 100 instrumented storm minutes produced 103 truncated reads,
        # one per poll.  With ``-p`` the same window peaks at 206.
        #
        # This does **not** replace the Python filter.  ``-p`` exists to
        # make the ceiling count the entries that matter; the filter below
        # stays the authority on what is stored, so the two cannot
        # disagree about a record journalctl admits and this module would
        # not.
        #
        # The ceiling is :func:`read_ceiling` rather than
        # ``max_priority_for`` alone, so a signature this family has
        # declared cannot be filtered out by a ``severity_filter`` edit
        # that a ``SIGHUP`` installs (``SNAG-CFG-006``).  It is half the
        # fix: journalctl handing the line over is worth nothing while
        # the Python gate below still drops it, which is what
        # :func:`admits` is for, and measuring that is what refuted the
        # entry's own named remedy.
        "-p", str(read_ceiling(severity_filter, declared)),
    ]
    # Kernel messages use -k/--dmesg rather than -u
    if unit == "kernel":
        base.insert(1, "-k")
    else:
        base[1:1] = ["-u", unit]
        if user:
            base.insert(1, "--user")

    stdout = None
    if after_cursor:
        stdout = await _run([*base, "--after-cursor", after_cursor], unit)
        if stdout is None:
            # A cursor the journal no longer holds. Start again from the
            # window rather than leaving this source permanently unread.
            logger.warning("journal_cursor_stale", extra={"unit": unit})
    if stdout is None:
        stdout = await _run([*base, "--since", since], unit)
    if stdout is None:
        return JournalRead(entries=[])

    lines = [ln for ln in stdout.strip().split("\n") if ln]
    entries = []
    cursor = None

    for line in lines:
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        # The cursor advances over **every** entry read, not only the ones
        # that survive the severity filter. Advancing only past kept
        # entries would leave the resume point behind a run of info-level
        # noise, and the next read would parse it all again — the
        # duplicate-ingest defect rebuilt one layer down.
        #
        # ``-p`` made the two sets coincide for a source that declares
        # nothing, and ``SNAG-CFG-006`` has pulled them apart again: a
        # source with a ``declared`` mapping reads at the declaration's
        # rung and stores at its own, so journalctl now returns lines
        # ``admits`` drops.  The rule was kept as written while it was
        # merely defensive and is load-bearing once more — it is about
        # what was **read**, and the pre-filter is an optimisation on the
        # ceiling rather than a second statement of what is stored.
        cursor = data.get("__CURSOR") or cursor

        try:
            priority = data.get("PRIORITY", "6")
            severity = PRIORITY_MAP.get(str(priority), "info")

            # The message is composed **before** the rung gate now, where
            # it used to be composed after it.  It has to be: a declared
            # signature is precisely one whose rung does not admit it, so
            # the gate cannot be asked before the key exists — the same
            # reordering ``LogAggregatorAgent._execute`` already had to
            # make one layer up, arriving here for the same reason.  The
            # cost is a compose plus a regex over lines that were about
            # to be discarded, bounded by ``limit``, and ``admits``
            # short-circuits it away entirely when nothing is declared.
            message = message_text(data.get("MESSAGE"))
            envelope: dict[str, str] = {}
            if log_format == "json":
                message, envelope = unwrap_json_message(message)

            if not admits(severity, severity_filter, message, declared):
                continue

            # Parse timestamp
            usec = data.get("__REALTIME_TIMESTAMP")
            if usec:
                ts = datetime.fromtimestamp(int(usec) / 1_000_000, tz=UTC)
            else:
                ts = datetime.now(UTC)

            entries.append({
                "source": unit,
                "severity": severity,
                "message": message,
                "logged_at": ts,
                # The journalctl record verbatim, envelope and all — so the
                # unwrap above changes what the identity is built from and
                # never what is retained.
                "raw_line": line[:2000],
                "metadata": {
                    "pid": data.get("_PID"),
                    "hostname": data.get("_HOSTNAME"),
                    "syslog_identifier": data.get("SYSLOG_IDENTIFIER"),
                    **envelope,
                },
            })
        except (json.JSONDecodeError, ValueError):
            continue

    return JournalRead(
        entries=entries,
        cursor=cursor,
        # ``-n`` returns the *newest* ``limit`` entries, so hitting the cap
        # means older unread ones were skipped and the cursor has jumped
        # past them. Staying current matters more than completeness for a
        # monitor, but the skip must be reported rather than inferred from
        # a findings count that never moves.
        #
        # Since ``-p`` was added this counts entries **at or above the
        # filter severity**, so it now means relevant data was lost rather
        # than "the read was busy" — the weaker reading it carried while
        # 61 % of the budget went on lines that were about to be
        # discarded.  What it still cannot express is a *catch-up* read:
        # ``_resume_floor()`` sets the window to how long the daemon was
        # down, so one restart behind a backlog truncates however high the
        # ceiling is, and that is inherent rather than a ceiling to tune.
        truncated=len(lines) >= limit,
    )


async def _run(cmd: list[str], unit: str) -> str | None:
    """Run a journalctl command, returning stdout or ``None`` on failure.

    Return code 1 means "no entries", which is not a failure.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except TimeoutError:
        logger.warning("journalctl_timeout", extra={"unit": unit})
        return None
    except FileNotFoundError:
        logger.warning("journalctl_not_found")
        return None

    if proc.returncode not in (0, 1):
        logger.warning(
            "journalctl_error",
            extra={"unit": unit, "stderr": stderr.decode()[:200]},
        )
        return None

    return stdout.decode()
