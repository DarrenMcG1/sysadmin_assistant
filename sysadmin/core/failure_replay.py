"""Say at login what nobody was there to hear at boot.

``SNAG-SYSD-005``, Session 126. The third half of the lifecycle
:mod:`sysadmin.core.unit_failure` owns: the handler writes the row while
the application is dead, the lifespan closes it when the application
returns, and this speaks the gap between them to the first human who
arrives.

**The entry that asked for this priced its own benefit at the gap to the
next login, and the alert table prices it at the life of the row.** Four
of the five firings this handler has ever had came at a boot with nobody
logged in, and the entry measured the wait to the next ``class=user``
session at 24 min at best and 6.1 h at worst. But the one firing that
produced a row and was not immediately fixed left it open for **37.73
hours** (``1 day 13:43:31``, 2026-08-22 18:10:22 → 2026-08-24 07:53:54),
of which the login gap was 24 minutes. So what is recovered here is not
24 minutes of lateness. It is 37.3 hours of silence, because nothing
after the login spoke either.

**The room was not even empty for most of it, which is the part the entry
had the wrong way round.** Reconstructed from the journal: the daemon hit
``start-limit-hit`` at 18:11:15, the user logged in at 18:34:41, and the
tray started five seconds later, polled 8500, got nothing and went to
``IconState.DISCONNECTED`` — where it sat, silently, for **22.2 of the
37.7 hours** across two sessions. So the loss is not principally that the
toast fired into an empty room; it is that *nothing on this box
interrupts about a dead daemon, occupied or not*. Login is simply the
cheapest moment to catch it. The tray's own two silences are a separate
fault with a separate owner and are filed as ``SNAG-TRAY-009``.

**Why this cannot live anywhere that already exists.** The tray polls
``GET /api/sysadmin/alerts``, which the dead daemon serves.
:mod:`sysadmin.monitor.desktop`, its ``desktop_notifications`` store and
``sweep_reminders`` are all *inside* that daemon. The one component able
to speak is the one that has died — so the speaker has to be a process
that starts when the session does and reads the database directly, which
is :mod:`sysadmin.core.unit_failure`'s operating condition exactly, one
trigger over.

**The wait is permitted here and was refused in the announcer, and the
number is what changed rather than the principle.** ``SNAG-SYSD-004``
rejected waiting because notify-send's own activation window is 60.08 s
against a gap to the next login of 24 minutes — nought of four firings
could ever have been delivered. At login the missing precondition is
about to become true in *seconds*: measured at the 2026-08-23 session,
``plasma-plasmashell.service`` went active at 14:44:55, the target this
unit is wanted by was reached at 14:44:57, and plasmashell was still
initialising at 14:44:58. So a unit started by ``graphical-session.target``
can genuinely find the name unclaimed, and for a second or two rather
than for hours.

:data:`WAIT_BUDGET_SECONDS` is therefore **derived rather than invented**:
it is notify-send's own measured 60.08 s activation bound, rounded down.
The replay waits exactly as long as a single blocked ``notify-send``
would have — the same patience, spent on a mechanism that can be observed
and that starts no ``plasma_waitforname``. Nothing here waits longer than
the thing that was rejected there, and unlike there, no 30-second systemd
job budget sits above it.

**The question is asked by the script that already owns it.**
``scripts/notification-server-present.sh`` is the one statement of "can
this box put a notification on a screen right now", with three verdicts
and three exit statuses. Re-implementing ``NameHasOwner`` in Python here
would be a second statement of a fact one module already owns —
``max_priority_for`` against ``PRIORITY_MAP``'s rule — and the two would
be free to disagree about the day ``busctl`` changes its output.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from sysadmin.core.escalation import humanise_hours
from sysadmin.core.unit_failure import PendingFailure, pending_unit_failures

logger = logging.getLogger(__name__)

#: How long to wait for a notification server to claim the name before
#: giving up. **Derived, not chosen**: notify-send blocks for a measured
#: 60.08 s on an unserved bus before failing, so this is the same patience
#: it would have spent anyway — see the module docstring. Rounded down so
#: the replay can never outlast the call it replaces.
WAIT_BUDGET_SECONDS = 60.0

#: How often to re-ask while waiting. The guard costs a measured 3.1–3.8 ms,
#: so a one-second poll spends about 0.4 % of the wait asking and the rest
#: of it idle — cheap enough that shortening it would buy nothing a human
#: could perceive.
POLL_INTERVAL_SECONDS = 1.0

#: Rows spoken individually before the run collapses to one notification.
#: **The population is one today**, and measurably so: a row is written per
#: *unit*, deduplicated on an open row, and exactly one unit on this box
#: carries an ``OnFailure=`` pointing at this application. The cap is a
#: guard against a shape that cannot currently occur, kept because Session
#: 46's rule is that a roll-up cannot name anything and the moment to
#: decide that is before there are six of them, not after.
MAX_SPOKEN = 3

#: The guard, addressed by path rather than by name so that a test can point
#: this at a copy without touching the box's own.
GUARD_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "notification-server-present.sh"
)

#: What the guard's exit statuses mean, ``check-migrations.sh``'s three and
#: for its reason. Only ``0`` is a "yes"; ``1`` and ``2`` are different
#: kinds of "could not", and they are reported apart because a session that
#: has not finished starting and a bus that is broken need different next
#: steps — ``ports_checked``'s rule at the size of an exit status.
SERVER_PRESENT = 0
NOBODY_LISTENING = 1
COULD_NOT_ASK = 2


def ask_notification_server(
    guard: Path = GUARD_SCRIPT,
    *,
    bus_path: str | None = None,
) -> tuple[int, str]:
    """Ask the guard whether anything can be told, right now.

    Returns its verdict and its sentence. **Every way of not-knowing is
    :data:`COULD_NOT_ASK` and never a "no"** — a missing script, a
    non-executable one, a guard that itself hung — because reading "I
    could not find out" as "there is nobody there" is how a notification
    is silenced by a decision nothing recorded.
    """
    if not guard.is_file():
        return COULD_NOT_ASK, f"no notification guard at {guard}"

    argv = [str(guard)]
    if bus_path is not None:
        argv.append(bus_path)

    try:
        # The guard bounds its own D-Bus call at 5 s; this bounds the guard.
        # A wrapper that can hang around a thing that cannot is not a bound.
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return COULD_NOT_ASK, f"could not run {guard}: {exc}"

    said = (done.stdout or done.stderr or "").strip()
    if done.returncode not in (SERVER_PRESENT, NOBODY_LISTENING, COULD_NOT_ASK):
        # An unrecognised status is not a "no" either, for the reason the
        # guard itself refuses to read an unrecognised `busctl` answer as one.
        return COULD_NOT_ASK, f"unrecognised verdict {done.returncode} from {guard}: {said}"
    return done.returncode, said


def wait_for_notification_server(
    guard: Path = GUARD_SCRIPT,
    *,
    budget: float = WAIT_BUDGET_SECONDS,
    poll: float = POLL_INTERVAL_SECONDS,
    bus_path: str | None = None,
    sleep=time.sleep,
    now=time.monotonic,
) -> tuple[bool, str]:
    """Wait, bounded, for something to own the notification name.

    **It asks before it waits**, so the common case — a session that is
    already up, which is every login after the first second — costs one
    3 ms call and no sleeping at all.

    ``now`` is :func:`time.monotonic` and not the wall clock: this
    measures an elapsed budget inside one short-lived process, and a
    wall clock can step under it. That is the opposite reading from
    ``DesktopNotifier``'s, which went to a wall clock deliberately because
    a reminder interval is about elapsed *human* time and must survive a
    suspend. Different question, different clock.
    """
    deadline = now() + budget
    verdict, said = ask_notification_server(guard, bus_path=bus_path)
    while verdict != SERVER_PRESENT and now() < deadline:
        sleep(poll)
        verdict, said = ask_notification_server(guard, bus_path=bus_path)
    return verdict == SERVER_PRESENT, said


def compose(pending: PendingFailure, *, at: datetime | None = None) -> tuple[str, str]:
    """The summary and body for one standing failure.

    **The row's own ``message`` is carried verbatim rather than rebuilt.**
    It already holds what ``SNAG-DB-005`` put there — the schema verdict
    and, on a mismatch, the one command that fixes it — so composing a
    fresh sentence here would be a second author of the same claim, free
    to fall behind ``_schema_diagnosis`` the day it learns a new cause.

    What is added is the **age**, which is the figure this row has always
    carried in ``created_at`` and which no destination has ever rendered.
    A person who has just sat down needs to know whether this happened
    four minutes ago or the day before yesterday, and that difference is
    the entire reason this module exists.
    """
    moment = at or datetime.now(UTC)
    created = pending.created_at
    if created.tzinfo is None:
        # Defensive only: the column is `timestamp with time zone`. Reading
        # a naive value as local is precisely the defect `SNAG-LOG-009`
        # removed, so it is read as UTC and never as the reader's clock.
        created = created.replace(tzinfo=UTC)
    hours = max(0.0, (moment - created).total_seconds() / 3600.0)

    summary = f"STILL FAILED: {pending.unit}"
    body = (
        f"{pending.message}\n"
        f"Failed {humanise_hours(hours)} ago and has not come back.\n"
        f"  systemctl status {pending.unit}\n"
        f"  journalctl -u {pending.unit} -n 50 --no-pager"
    )
    return summary, body


def compose_rollup(pending: list[PendingFailure]) -> tuple[str, str]:
    """One notification for more failures than are worth listing singly.

    **It names every unit it swallows** — ``SNAG-ESTATE-001``'s rule.
    A roll-up that reports a count is the defect this repository spent
    Session 46 removing: ``Unmonitored systemd units: 17 findings`` was
    open, accurate and unread for eight days.
    """
    units = ", ".join(p.unit for p in pending)
    summary = f"STILL FAILED: {len(pending)} units"
    body = (
        f"{units}\n"
        "None has come back since it failed. Monitoring is down.\n"
        "  systemctl --failed"
    )
    return summary, body


def speak(summary: str, body: str, *, runner=subprocess.run) -> bool:
    """Put one notification on the screen. Returns whether it landed.

    ``--expire-time=0`` and ``--urgency=critical`` for Session 39's reason,
    which this module is the second instance of: the failure the whole
    family exists to fix was a transient toast nobody was in the room to
    see, and an expiring notification about a dead monitor is that miss
    with extra steps.
    """
    try:
        done = runner(
            [
                "notify-send",
                "--app-name=sysadmin",
                "--urgency=critical",
                "--expire-time=0",
                "--icon=dialog-error",
                summary,
                body,
            ],
            capture_output=True,
            text=True,
            # notify-send's own GDBus bound against a server that exists is
            # 25 s; this is above it, so a timeout here means something
            # stranger than a slow server.
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("could not run notify-send: %s", exc)
        return False
    if done.returncode != 0:
        logger.error("notify-send failed (%d): %s", done.returncode, (done.stderr or "").strip())
        return False
    return True


def replay(
    *,
    guard: Path = GUARD_SCRIPT,
    budget: float = WAIT_BUDGET_SECONDS,
    bus_path: str | None = None,
    read=pending_unit_failures,
    announce=speak,
    sleep=time.sleep,
) -> int:
    """Announce every unit failure that is still open. Returns an exit status.

    **The read comes first and the wait only happens if there is something
    to say.** A clean box — which is the overwhelmingly common login —
    costs one database query and exits, never touching D-Bus and never
    sleeping. Waiting 60 s at every login to discover there was nothing to
    announce would be a cost paid by the healthy case for the benefit of
    the broken one.

    Three statuses, and they are ``check-migrations.sh``'s three once more:

    ``0``
        Nothing to say, or everything was said.
    ``1``
        There was something to say and nobody to say it to.
    ``2``
        There was something to say and the attempt failed.

    ``1`` is kept apart from ``2`` because a session where the notification
    server never appeared is a different fault from one where ``notify-send``
    itself broke, and ``systemctl --user status`` is where an operator will
    read the difference.
    """
    pending = read()
    if not pending:
        logger.info("no standing unit failures to replay")
        return 0

    logger.warning(
        "%d standing unit failure(s) to announce: %s",
        len(pending),
        ", ".join(p.unit for p in pending),
    )

    listening, said = wait_for_notification_server(
        guard, budget=budget, bus_path=bus_path, sleep=sleep
    )
    if not listening:
        # The row is not lost — it is in the table, and it is why this ran.
        # What is lost is the interruption, and that is what this status
        # records, exactly as the announcer's does.
        logger.error("not notifying: %s", said)
        return 1

    if len(pending) > MAX_SPOKEN:
        summary, body = compose_rollup(pending)
        return 0 if announce(summary, body) else 2

    landed = 0
    for row in pending:
        summary, body = compose(row)
        if announce(summary, body):
            landed += 1
    if landed != len(pending):
        logger.error("announced %d of %d standing failures", landed, len(pending))
        return 2
    return 0


def main() -> int:
    """``sysadmin-replay-failures`` — entry point for the login-time unit."""
    parser = argparse.ArgumentParser(description="Announce unit failures still open.")
    parser.add_argument(
        "--bus-path",
        default=None,
        help="session bus to ask about (default: the guard's own)",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=WAIT_BUDGET_SECONDS,
        help="how long to wait for a notification server",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return replay(budget=args.wait_seconds, bus_path=args.bus_path)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
