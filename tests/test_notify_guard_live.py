"""The announcer's guard, driven against real buses.

SNAG-SYSD-004, Session 125. The entry named the shape of this drive before
it existed: *"point ``DBUS_SESSION_BUS_ADDRESS`` at a bus this repository
started with nothing owning ``org.freedesktop.Notifications``, run the
script's final call under a bound, and assert it does not return — with the
witness being the same call against the live bus, which does"*.

**Why it cannot be a fixture.** The mechanism is a D-Bus activation:
``/usr/share/dbus-1/services/org.kde.plasma.Notifications.service`` declares
``Exec=/usr/bin/plasma_waitforname``, so a method call to an unowned name
starts a program whose whole job is to block until the name appears. Nothing
in that sentence is visible from the script text, and a probe run on a
working desktop returns in milliseconds — which is why four killed firings
looked like a puzzle rather than a mechanism for six days.

**Two tests composing, not one doing both.** ``TestTheHazardIsReal`` shows
that speaking to an unserved bus blocks and that speaking to the live one
does not; ``TestTheGuardSeparatesThem`` shows the guard tells those two
apart, quickly, and without triggering the activation itself. The first is
the discriminating witness for the second — without it, a guard returning 1
on a private bus is just a guard returning 1, and nothing says the refusal
was warranted.

**What each half skips on, and why a skip is honest here.** The private-bus
half needs ``dbus-daemon`` and ``notify-send``; the live half needs a
notification server actually running, which no CI box has. A test asserting
two observations agree has nothing to assert when one is unobtainable —
so it skips, and says which observation was missing.

**The live half cleans up after itself, and that is not tidiness.** The
announcer's flags include ``--expire-time=0``, which the freedesktop
specification defines as *never expire*, and ``--urgency=critical``, which
Plasma never auto-dismisses either. So every full suite run parked one more
toast on the owner's screen that only a human could clear — reported as
spam on 2026-08-31, after two days and an unknown number of runs. Three
shapes were available and two were refused:

* **Soften the flags on the live half.** The cheapest, and it breaks the
  only thing that makes this pair evidence: the two observations must
  differ in *one* thing, whether a server owns the name. Different flags
  on the two sides is a second difference, and ``--expire-time=0`` is
  named in :func:`_notify_send` as the suspect that was cleared only by
  measurement — so it is precisely the flag that must not vary.
* **Drop the live call.** It is the discriminating witness; without it a
  guard that refuses everything passes every other test in this file.
  ``_live_server_present``'s own docstring refuses that trade one
  function down.
* **Send the identical call, then close the notification by id.** What
  ships. ``--print-id`` is added to *both* halves, so the flags stay
  uniform and the D-Bus ``Notify`` call is byte-for-byte the announcer's;
  the live half then calls ``CloseNotification`` on what came back. The
  toast still lands — the happy path is still exercised — and it lands
  for milliseconds rather than for ever.

**Two operations used to escape this fixture's bus, and they were a
cause of red rather than untidiness** (``SNAG-TEST-004``). The teardown
killed waiters with a global ``pkill`` and
:meth:`test_asking_does_not_start_the_waiter_that_calling_starts` counted
them with a global ``pgrep``, so both asked a question about *the box*
and reported it as a question about this fixture. Four tests take the
fixture — counted by an ``ast`` walk when the entry was filed, because two
of the four have multi-line signatures and a ``def``-line grep sees only
two — and a body-level ``pytest.skip`` runs *after* fixture setup, so all
four teardowns fire on any box with ``dbus-daemon``. Four global kills,
against a threshold of three.

**That count is not pinned by anything, and deliberately is not.** Both
the entry and an earlier draft of this docstring said it was; nothing in
the repository ever walked this file for it. It is left unpinned rather
than built, because the number stopped deciding anything the moment the
kills were scoped: four scoped kills reach four processes this fixture
started, and forty would. Pinning it now would be pinning an arithmetic
whose threshold no longer exists. What *is* pinned is the property that
replaced it — ``tests/test_live_drive_scoping.py`` refuses a box-wide
process selector in any live drive, which is the thing a future edit can
break and whose failure mode is silent: a reintroduced global ``pkill``
leaves this file green in isolation and turns a **peer's** run red.

The threshold is the mechanism, and one kill is not a small version of
three. Measured 2026-08-31 against a private bus with a real blocked
``notify-send``:

===========  ==========================================================
kills        outcome
===========  ==========================================================
0            blocked, rc=124, 8001 ms
1            blocked, rc=124, 8001 ms
3            **returned**, rc=1, 3082 ms
4            **returned**, rc=1, 3082 ms
===========  ==========================================================

At one kill the bus simply **re-activates** the waiter mid-call — PID
tracked, 1750881 killed and 1750920 in its place within a second — so
the call stays blocked and the operation looks harmless. At three the bus
stops re-activating, the activation fails
(``StartServiceByName ... exited with status 255``), and the pending call
is errored, so ``notify-send`` returns and ``assert not returned`` fails.

**The interference needs an *offset*, which is why it was intermittent
and is worth stating.** Two file runs started together are synchronised:
both sit in the blocking test for the same eight seconds and both fire
their teardown burst afterwards, so the burst never lands inside anybody's
block. Measured — two simultaneous runs are green, twice. Offset so one
run's teardowns land inside the other's block, the same code is red
**3 for 3** at delays of 5 s, 6 s and 7 s, and always on exactly
``test_notify_send_does_not_return_on_a_bus_with_nothing_listening``
(the run returning in 1.76–3.73 s instead of 8.7 s). Scoped, the same
three offsets are green **6 for 6** with both runs taking the full
8.67 s, and no waiter is left on the box. A green pair proves nothing
without the red pair first — the sequence is the evidence, not the green.

**A red on the blocking half now says which of two things happened**
(``SNAG-TEST-003``). Its assertion read *"the D-Bus activation that causes
SNAG-SYSD-004 is gone from this box and the guard's urgency should be
re-derived"*, so any red at all — from any cause — reported good news, and
the honest response to good news is to relax the control. The entry
survived two refutations of its own evidence because it never rested on
one: the claim was about the sentence.

The separator is a **precondition rather than a differential**, which is
what the entry named as the cheapest form once ``SNAG-TEST-004`` had
removed the one measured cause. ``notify-send`` returning is common to both
readings; the *activation* is not, so the probe watches for
``plasma_waitforname`` under this fixture's own bus while the call runs and
:meth:`TestTheHazardIsReal.test_notify_send_does_not_return_on_a_bus_with_nothing_listening`
asserts that first. Three states, measured 2026-09-02 rather than reasoned
about:

===============================  =========  ========  =======  ===========
state                            activated  returned  elapsed  notify-send
===============================  =========  ========  =======  ===========
hazard intact (the control)      yes        no        8.03 s   —
reading disturbed (3 kills)      **yes**    yes       3.06 s   ``status 255``
hazard gone (no .service files)  **no**     yes       0.03 s   ``ServiceUnknown``
===============================  =========  ========  =======  ===========

**Sampled during the call, and that is forced rather than tidy.** Row 2's
waiter is dead by the time the call returns — killing it is what errored
the call — so a single check *afterwards* reports ``activated=False`` for
rows 2 and 3 alike and reproduces the collapse being removed. Polling is
therefore the cheapest thing that discriminates at all, and it is why
:func:`_notify_send` is a :class:`subprocess.Popen` rather than the
``subprocess.run(timeout=...)`` it was: that call hands back only what the
process ended with.

**The budget was not raised**, which the entry named as the thing that must
not happen: a larger :data:`BLOCK_PROBE_SECONDS` makes the red rarer
without changing what it means. Nor is ``stderr`` what decides anything.
The two shapes do carry distinct messages and both are quoted into the
failure, but keying on them would be a second implementation of a
judgement ``activated`` already states — the reader gets the evidence, the
assertion gets the fact.

The close is **asserted on Plasma's answer, and what that answer covers
is narrower than it looks.** Measured against Plasma 6.7.4 on 2026-08-31:
``CloseNotification`` answers ``rc=0`` for an id that was never issued
(999999) and even emits a ``NotificationClosed`` signal for it, reason 3.
So neither the exit status nor the signal is evidence that a popup left the
screen. No discriminating witness for that exists over D-Bus, because the
server reports the same thing either way.

Until 2026-09-28 the assertion was ``busctl``'s exit status, and
``SNAG-TEST-014`` is what that missed: a green run under fullscreen Dota 2
left its popup on the owner's screen. The exit status says only that the
bus delivered the call. ``NotificationClosed`` for this call's own id says
Plasma handled it, and Plasma's source removes the popup's row in the same
step. So the test now waits for the signal, sends one more close only if it
does not come, and appends which happened to :data:`PROBE_RECORD`. A
recurrence then tells two failures apart that looked identical before:
**no signal** means Plasma lost the close, and **a signal with the popup
still on screen** means the display side, Plasma or KWin, failed to update.
Only the owner can see the second, and the record is what they match it
against.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
GUARD = SCRIPTS / "notification-server-present.sh"
LIVE_BUS = Path("/run/user/1000/bus")

# Comfortably above the ~4 ms the guard measures and far below the 60.08 s
# notify-send spends inside the activation. A guard slower than this is not
# failing fast, whatever its exit status says.
GUARD_BUDGET_SECONDS = 2.0

# Long enough that returning inside it cannot be the activation timeout
# (60 s) or the bus's own service_start_timeout (120 s), short enough to
# keep the suite usable. A call still running at this bound is blocked.
BLOCK_PROBE_SECONDS = 8.0

_MISSING_DBUS = "dbus-daemon is not installed — cannot start a bus with nothing on it"
_MISSING_NOTIFY = "notify-send is not installed — the hazard cannot be reproduced"
_NO_LIVE_SERVER = (
    "no notification server owns org.freedesktop.Notifications on this box — "
    "the live witness is unobtainable, so nothing here can be compared against it"
)


#: The activation helper the unowned name starts. Matched against a full
#: ``ps`` argument list rather than ``comm``, which truncates it to
#: ``plasma_waitforn`` at fifteen characters.
WAITER = "plasma_waitforname"


def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


@dataclasses.dataclass(frozen=True)
class UnservedBus:
    """A private bus, and the pid that scopes every question asked about it.

    The pid is carried beside the path because ``SNAG-TEST-004`` was two
    operations that asked a question about *the box* while believing they
    had asked it about this fixture. A path alone cannot scope either of
    them, so the fixture hands out both and the call sites read which one
    they meant.
    """

    path: str
    pid: str


def _waiters_under(root_pid: str) -> list[str]:
    """The waiters this bus started — and no others.

    **A descendant walk rather than ``pgrep -P``, and that is measured
    rather than tidy.** ``dbus-daemon --fork --print-pid`` prints a pid
    that is not the serving daemon: it forks once more, and the activation
    helper hangs off the *child*. Observed 2026-08-31 — printed 1756159,
    which parents a second ``dbus-daemon`` 1756174, which parents
    ``plasma_waitforname`` 1756175. So the obvious scoping would find
    nothing, report zero waiters, and make
    :meth:`test_asking_does_not_start_the_waiter_that_calling_starts` pass
    without looking — ``ports_checked``'s rule, zero-because-blind served
    as zero-because-clean.

    Callers must ask **before** killing the bus. Once the daemon dies its
    children are reparented and the ppid chain that identifies them as
    this fixture's is gone.
    """
    listing = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True, check=False
    ).stdout
    children: dict[str, list[tuple[str, str]]] = {}
    for line in listing.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            pid, ppid, args = parts
            children.setdefault(ppid, []).append((pid, args))

    found: list[str] = []
    stack = [root_pid]
    while stack:
        for pid, args in children.get(stack.pop(), []):
            stack.append(pid)
            if WAITER in args:
                found.append(pid)
    return found


@pytest.fixture
def unserved_bus(tmp_path: Path):
    """A private session bus with nothing owning the notification name.

    This is the state a lingering box is in at every boot before login, and
    it is reproduced rather than simulated: the same ``dbus-daemon``, the
    same system-wide activation files, the same everything except that no
    Plasma session has claimed the name.
    """
    if not _have("dbus-daemon"):
        pytest.skip(_MISSING_DBUS)

    proc = subprocess.run(
        ["dbus-daemon", "--session", "--fork", "--print-address=1", "--print-pid=1"],
        capture_output=True,
        text=True,
        check=True,
    )
    address, pid = proc.stdout.strip().splitlines()[:2]
    bus_path = address.removeprefix("unix:path=").split(",", 1)[0]
    try:
        yield UnservedBus(path=bus_path, pid=pid)
    finally:
        # The activation the hazard triggers outlives its caller — it is
        # started by the bus, not by notify-send — so it is cleaned up
        # explicitly rather than left for the next run to miscount.
        #
        # **Scoped to this bus's own descendants** (``SNAG-TEST-004``). This
        # was a global ``pkill -f plasma_waitforname``, which reached every
        # waiter on the box including a concurrent run's, and that is not a
        # tidiness point: measured 2026-08-31, one kill leaves the call
        # blocked because the bus re-activates the waiter mid-call, but at
        # **three** the bus stops re-activating, the activation fails
        # (``StartServiceByName ... exited with status 255``) and the pending
        # call is errored — so ``notify-send`` returns and
        # ``test_notify_send_does_not_return_on_a_bus_with_nothing_listening``
        # goes red. **Four** tests take this fixture, so one file run fired
        # four global kills against a threshold of three, and two sessions
        # sharing this box turned each other red.
        #
        # Asked before the bus is killed, because killing it reparents the
        # children this identifies them by.
        for waiter in _waiters_under(pid):
            subprocess.run(["kill", waiter], capture_output=True, check=False)
        subprocess.run(["kill", pid], capture_output=True, check=False)


def _live_server_present() -> bool:
    """Is a notification server running — asked *without* the guard.

    This decides whether the live-witness tests run at all, so it must not
    route through the script under test. Driven at a guard mutated to
    refuse everything, the first version of this helper made
    ``test_it_admits_the_live_bus`` **skip** rather than fail: a broken
    guard reported no server, the test that would have caught it removed
    itself, and the mutation came back green. A control a fix can switch
    off is not a control.

    ``busctl`` is the same binary the guard uses and that is fine — what
    must not be shared is the *decision*, which is the script's.
    """
    if not LIVE_BUS.is_socket() or not _have("busctl"):
        return False
    result = subprocess.run(
        [
            "busctl",
            "--user",
            "call",
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "NameHasOwner",
            "s",
            "org.freedesktop.Notifications",
        ],
        capture_output=True,
        text=True,
        env=dict(os.environ, DBUS_SESSION_BUS_ADDRESS=f"unix:path={LIVE_BUS}"),
        timeout=10,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "b true"


def _run_guard(bus_path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(GUARD), bus_path], capture_output=True, text=True, check=False
    )


#: How often the blocking probe asks whether the activation has started.
#: Derived from the latency rather than picked: measured 2026-09-02 against
#: this fixture's own bus, ``plasma_waitforname`` appears **48-50 ms** after
#: the call, four trials for four, and then persists for the whole block
#: (124 consecutive sightings across one 8 s probe). At 20 ms the first
#: sighting lands on the second or third poll.
#:
#: What the interval bounds is the one thing this observation can get wrong,
#: and it is worth naming because it fails in the *unsafe* direction: a
#: waiter both started and reaped inside a single poll reads as no
#: activation at all, which is precisely the reading
#: :class:`TestTheHazardIsReal`'s precondition exists to refuse. Two orders
#: of magnitude between the interval and the observed lifetime is what makes
#: that unreachable here rather than merely unlikely.
_ACTIVATION_POLL_SECONDS = 0.02


@dataclasses.dataclass(frozen=True)
class NotifySendOutcome:
    """What one probe call saw — including whether the hazard actually fired.

    ``activated`` is why this is a record and not the tuple it replaced.
    ``SNAG-TEST-003``: ``returned`` alone cannot tell *the hazard is gone*
    from *this reading was disturbed*, because both shapes return. The
    activation can, and it is carried beside the outcome because the two are
    only meaningful together — the same argument :class:`UnservedBus` makes
    one field over.

    ``activated`` is ``None`` when no ``watch_pid`` was given, never
    ``False``. Nobody looked and nothing was there are different facts and a
    caller must not be able to read the first as the second —
    ``ports_checked``'s rule. The live half passes no pid because a bus with
    a server on the name activates nothing, so the question does not arise
    there.

    ``stderr`` is evidence for a reader triaging a red and decides nothing.
    The two failing shapes are separated by ``activated``; that they *also*
    carry distinct messages (``exited with status 255`` against
    ``ServiceUnknown``) is a convenience, and keying on it would be a second
    implementation of a judgement this record already states.
    """

    returned: bool
    elapsed: float
    notification_id: str | None
    activated: bool | None
    stderr: str


def _notify_send(
    bus_path: str, timeout: float, watch_pid: str | None = None
) -> NotifySendOutcome:
    """Send the announcer's own notification, watching for the activation.

    The flags are the announcer's own, because the question is whether *its*
    call blocks, and libnotify's behaviour on an unowned name is not
    obviously independent of them — ``--expire-time=0`` in particular was
    the first suspect and was cleared only by measurement.

    ``--print-id`` is the one addition, and it is made **here** rather than
    at the live call site so that both halves send the same thing. It
    changes no D-Bus traffic: libnotify issues the identical ``Notify``
    method call either way and ``-p`` only prints the id the server
    returned, so the blocking half blocks in the same place for the same
    reason. What it buys is the live half's ability to take its own toast
    back off the screen — see the module docstring.

    The id is ``None`` whenever there is nothing to close: a call that was
    killed at *timeout* never reached a server, and a server that answered
    with something unparseable is a state this helper reports rather than
    guesses at.

    **``watch_pid`` is sampled while the call runs, and that is forced
    rather than convenient** (``SNAG-TEST-003``). In the disturbed shape the
    waiter is killed and the pending call is errored, so by the time
    ``notify-send`` returns there is nothing left to see: a single check
    after the call reports *no activation* for both a box where the hazard
    is gone and a box where it fired and was interrupted, which is the
    reading being separated. Polling is therefore the cheapest form that
    discriminates at all, not a refinement of a post-hoc check.

    ``subprocess.run(timeout=...)`` cannot do it — it hands back only what
    the call ended with — so the probe is a :class:`subprocess.Popen` and
    the timeout is this loop's. The cost is that *elapsed* is quantised by
    :data:`_ACTIVATION_POLL_SECONDS`, which is 20 ms against a 2 s budget on
    the live half and an 8 s bound on this one.
    """
    env = dict(os.environ, DBUS_SESSION_BUS_ADDRESS=f"unix:path={bus_path}")
    activated: bool | None = None if watch_pid is None else False
    started = time.monotonic()
    call = subprocess.Popen(
        [
            "notify-send",
            "--print-id",
            "--app-name=sysadmin-test",
            "--urgency=critical",
            "--expire-time=0",
            "--icon=dialog-error",
            "SNAG-SYSD-004 probe",
            "if you are reading this on screen, the live witness worked",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        while call.poll() is None and time.monotonic() - started < timeout:
            if watch_pid is not None and not activated and _waiters_under(watch_pid):
                activated = True
            time.sleep(_ACTIVATION_POLL_SECONDS)
        returned = call.poll() is not None
        elapsed = time.monotonic() - started
    finally:
        if call.poll() is None:
            call.kill()
    stdout, stderr = call.communicate()

    printed = stdout.strip()
    return NotifySendOutcome(
        returned=returned,
        elapsed=elapsed,
        notification_id=printed if (returned and printed.isdigit()) else None,
        activated=activated,
        stderr=stderr.strip(),
    )


#: How long Plasma is given to answer a close with ``NotificationClosed``.
#: Measured: 18-29 ms after every close in Session 274's three drives, and
#: 52 ms in Session 276's, so two orders of magnitude of margin for a box
#: under load. The happy path returns on the signal and never waits this out.
CLOSE_ACK_SECONDS = 3.0

#: How long ``dbus-monitor`` is given to become a monitor. Measured at about
#: 1 ms on this box.
MONITOR_ATTACH_SECONDS = 2.0

#: Where every live close is recorded, one JSON line per run. The popup is
#: seen on the owner's screen and the pytest output is not kept, so a
#: recurrence needs a record that outlives the run and can be matched to the
#: popup by time (``SNAG-TEST-014``). It sits outside the checkout so a run
#: leaves the tree clean, and outside the journal because the log aggregator
#: reads the journal, so a test writing there writes into what this service
#: monitors. A line is about 400 bytes and the file is never trimmed.
PROBE_RECORD = (
    Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    / "sysadmin_assistant"
    / "notify-probe.jsonl"
)

_CLOSED_MATCH = (
    "type='signal',interface='org.freedesktop.Notifications',"
    "member='NotificationClosed'"
)


@dataclasses.dataclass(frozen=True)
class ClosedSignal:
    """One ``NotificationClosed`` as ``dbus-monitor`` printed it."""

    at: float
    notification_id: int
    reason: int


class _ClosedSignalParser:
    """Read ``NotificationClosed`` out of ``dbus-monitor``'s text, a line at a time.

    A signal is three lines: a header carrying ``time=`` and
    ``member=NotificationClosed``, then ``uint32 <id>`` and
    ``uint32 <reason>``. The header's ``time=`` is when the monitor received
    the signal, so it is on the same wall clock as :class:`CloseAttempt`'s
    ``sent_at``.
    """

    def __init__(self) -> None:
        self._at: float | None = None
        self._values: list[int] = []

    def feed(self, line: str) -> ClosedSignal | None:
        text = line.strip()
        if text.startswith(("signal ", "method ", "error ")):
            self._at = None
            self._values = []
            if "member=NotificationClosed" in text:
                stamp = text.split("time=", 1)[1].split(" ", 1)[0]
                self._at = float(stamp)
            return None
        if self._at is None or not text.startswith("uint32 "):
            return None
        self._values.append(int(text.split()[1]))
        if len(self._values) < 2:
            return None
        signal = ClosedSignal(self._at, self._values[0], self._values[1])
        self._at = None
        self._values = []
        return signal


class ClosedSignalWatch:
    """``dbus-monitor`` on the live bus, filtered to ``NotificationClosed``.

    **A monitor, not a subscription.** ``dbus-monitor`` calls
    ``BecomeMonitor``, which sees a signal whatever its destination. An
    ``AddMatch`` client such as ``gdbus monitor`` sees only broadcasts, and a
    server that answered its client directly would read as a lost close.

    **Attachment is observed, not assumed.** Becoming a monitor makes the bus
    take the connection's unique name away, and ``dbus-monitor`` prints that
    ``NameLost``. Until it does, a missing signal says nothing about Plasma,
    so ``attached`` is the premise every "no signal" reading rests on.

    Started **before** the send, so the monitor's start-up does not add to
    the time the probe stays on screen.
    """

    def __init__(self, bus_path: Path) -> None:
        self._bus_path = bus_path
        self._lines: queue.Queue[str] = queue.Queue()
        self._parser = _ClosedSignalParser()
        self._seen: list[ClosedSignal] = []
        self._process: subprocess.Popen[str] | None = None
        self._pump_thread: threading.Thread | None = None
        self.attached = False

    def __enter__(self) -> ClosedSignalWatch:
        if not _have("dbus-monitor"):
            return self
        self._process = subprocess.Popen(
            ["dbus-monitor", "--session", _CLOSED_MATCH],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=dict(
                os.environ, DBUS_SESSION_BUS_ADDRESS=f"unix:path={self._bus_path}"
            ),
        )
        self._pump_thread = threading.Thread(target=self._pump, daemon=True)
        self._pump_thread.start()
        deadline = time.monotonic() + MONITOR_ATTACH_SECONDS
        while not self.attached and (remaining := deadline - time.monotonic()) > 0:
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty:
                break
            self.attached = "member=NameLost" in line
        return self

    def __exit__(self, *exc: object) -> None:
        if self._process is None:
            return
        self._process.terminate()
        self._process.wait(timeout=5)
        # The pump ends at the pipe's EOF; the pipe is closed once it has.
        if self._pump_thread is not None:
            self._pump_thread.join(timeout=5)
        if self._process.stdout is not None:
            self._process.stdout.close()

    def _pump(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        for line in self._process.stdout:
            self._lines.put(line)

    def wait_for(self, notification_id: str, timeout: float) -> ClosedSignal | None:
        """The ``NotificationClosed`` for *notification_id*, or ``None`` at *timeout*.

        Matched by id because Plasma closes other applications'
        notifications on the same bus, and answers a close for an id it
        never issued as well (the module docstring's 999999).
        """
        wanted = int(notification_id)
        deadline = time.monotonic() + timeout
        while True:
            for signal in self._seen:
                if signal.notification_id == wanted:
                    return signal
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty:
                return None
            if (parsed := self._parser.feed(line)) is not None:
                self._seen.append(parsed)


@dataclasses.dataclass(frozen=True)
class CloseAttempt:
    """One ``CloseNotification`` and what Plasma said back.

    ``busctl_rc`` is ``None`` when the call timed out. It is recorded and
    decides nothing: ``SNAG-TEST-014`` was a green ``rc=0`` with the popup
    still on screen.
    """

    sent_at: float
    busctl_rc: int | None
    answer: ClosedSignal | None


#: The readings :attr:`CloseOutcome.reading` gives, and what each means.
CLOSE_READINGS = {
    "closed": "Plasma answered the first close with NotificationClosed",
    "closed on the second call": (
        "Plasma did not answer the first close within the bound and answered "
        "the second. This is the lost-close case SNAG-TEST-014 is waiting for"
    ),
    "never acknowledged": (
        "Plasma answered neither close, so it has lost the close and the popup "
        "is almost certainly still on screen"
    ),
    "monitor not attached": (
        "dbus-monitor never became a monitor on the live bus, so a missing "
        "signal says nothing about Plasma. One close was sent and not checked"
    ),
    "no id": (
        "notify-send printed no id, so there was nothing to close and the "
        "popup is still on screen"
    ),
}


@dataclasses.dataclass(frozen=True)
class CloseOutcome:
    """The live half's cleanup, read from Plasma's answer rather than an exit status."""

    notification_id: str | None
    monitor_attached: bool
    attempts: tuple[CloseAttempt, ...]

    @property
    def reading(self) -> str:
        if self.notification_id is None:
            return "no id"
        if not self.monitor_attached:
            return "monitor not attached"
        answered = [attempt.answer is not None for attempt in self.attempts]
        if answered[:1] == [True]:
            return "closed"
        if answered[1:2] == [True]:
            return "closed on the second call"
        return "never acknowledged"

    @property
    def acknowledged(self) -> bool:
        return self.reading in ("closed", "closed on the second call")


def _send_close(notification_id: str) -> int | None:
    """Call ``CloseNotification`` on the live bus; ``None`` if it timed out.

    ``CloseNotification`` is mandatory in the freedesktop specification and
    goes to the notification name itself. That is safe *here* and would not
    be in the guard, because this is only ever called on the live bus after
    a server has been observed answering. On an unowned name it would
    trigger the very activation ``test_asking_does_not_start_the_waiter``
    exists to keep out of the guard's path.
    """
    try:
        done = subprocess.run(
            [
                "busctl",
                "--user",
                "call",
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications",
                "CloseNotification",
                "u",
                notification_id,
            ],
            capture_output=True,
            text=True,
            env=dict(os.environ, DBUS_SESSION_BUS_ADDRESS=f"unix:path={LIVE_BUS}"),
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    return done.returncode


def _close_notification(
    notification_id: str | None, watch: ClosedSignalWatch
) -> CloseOutcome:
    """Take the live half's own popup back off the screen, and hear Plasma say so.

    One close, then a wait for ``NotificationClosed``. **A second close is
    sent only when the first went unanswered**: by Plasma's source it does
    nothing when the first worked, and sent blindly it would hide the one
    fault this is waiting to see. With no monitor attached a second close
    would be blind in the same way, so only one is sent.
    """
    if notification_id is None:
        return CloseOutcome(None, watch.attached, ())
    attempts: list[CloseAttempt] = []
    for _ in range(2 if watch.attached else 1):
        sent_at = time.time()
        rc = _send_close(notification_id)
        answer = watch.wait_for(notification_id, CLOSE_ACK_SECONDS) if watch.attached else None
        attempts.append(CloseAttempt(sent_at, rc, answer))
        if answer is not None:
            break
    return CloseOutcome(notification_id, watch.attached, tuple(attempts))


def _record_close(
    outcome: NotifySendOutcome, close: CloseOutcome, path: Path = PROBE_RECORD
) -> None:
    """Append one live run to :data:`PROBE_RECORD`.

    Every run is recorded, not only the failures, because the case this
    exists to catch reads ``closed`` from here: Plasma answered and the popup
    stayed anyway. Only the owner sees that, and the record is what they
    match it against by time.
    """
    row = {
        "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "pid": os.getpid(),
        "notification_id": close.notification_id,
        "notify_elapsed_ms": round(outcome.elapsed * 1000, 1),
        "reading": close.reading,
        "monitor_attached": close.monitor_attached,
        "attempts": [
            {
                "sent_at": attempt.sent_at,
                "busctl_rc": attempt.busctl_rc,
                "answered_at": attempt.answer.at if attempt.answer else None,
                "reason": attempt.answer.reason if attempt.answer else None,
                "latency_ms": (
                    round((attempt.answer.at - attempt.sent_at) * 1000, 1)
                    if attempt.answer
                    else None
                ),
            }
            for attempt in close.attempts
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as record:
        record.write(json.dumps(row) + "\n")


@pytest.mark.premise
class TestTheHazardIsReal:
    """Speaking to an unserved bus blocks; speaking to a served one does not.

    This pair is the reason the guard is worth having. Without it the guard's
    refusal is unmotivated — a constant observation is not evidence unless
    something in the population would have forced a different one.
    """

    def test_notify_send_does_not_return_on_a_bus_with_nothing_listening(
        self, unserved_bus: UnservedBus
    ):
        if not _have("notify-send"):
            pytest.skip(_MISSING_NOTIFY)

        outcome = _notify_send(
            unserved_bus.path, BLOCK_PROBE_SECONDS, watch_pid=unserved_bus.pid
        )

        assert outcome.activated, (
            f"nothing started {WAITER} under this fixture's own bus in "
            f"{outcome.elapsed:.2f}s, so the call was answered without the "
            "D-Bus activation SNAG-SYSD-004 turns on ever running. Read this "
            "as the hazard being gone from this box — the guard's urgency "
            "should be re-derived rather than assumed — unless the waiter "
            f"lived and died inside one {_ACTIVATION_POLL_SECONDS}s poll, "
            "which the measured 48-50ms start and whole-block lifetime make "
            f"unreachable here. notify-send said: {outcome.stderr or 'nothing'}"
        )
        assert not outcome.returned, (
            f"notify-send returned after {outcome.elapsed:.2f}s on a bus with "
            f"no notification server — but a {WAITER} was started under this "
            "fixture's own bus first, so the activation is intact and "
            "something errored the pending call. That is this reading being "
            "disturbed, not the hazard being fixed: SNAG-TEST-004's shape is "
            "three kills landing inside this window, after which the bus "
            "stops re-activating and the call comes back with "
            f"'exited with status 255'. notify-send said: {outcome.stderr or 'nothing'}"
        )

    def test_notify_send_returns_at_once_on_the_live_bus(self):
        """The witness. Same flags, same binary, a server on the other end.

        It puts a real notification on screen, which is the point: the
        happy path is asserted by exercising it, not by trusting that the
        unhappy one implies it. It then takes it off again, because the
        announcer's ``--expire-time=0`` means the server would otherwise
        hold it there until a human dismissed it — one more every time
        anybody ran the suite.

        The close runs **before** the assertions rather than in a
        ``finally``, so the screen is cleared on the failing path too
        without a failed cleanup being able to mask the real verdict:
        ``returned`` is asserted first and names the actual fault, and the
        cleanup's own assertions come last.

        **The cleanup is asserted on Plasma's answer** (``SNAG-TEST-014``).
        The monitor's attachment is asserted before the answer for the
        reason ``SNAG-TEST-003`` ordered the blocking half's assertions:
        without it, "Plasma answered neither close" is a claim about a bus
        nobody was listening to. A close answered only the second time
        passes, because the popup is gone, and warns, because that is the
        lost close the entry is waiting to see. Either way the run is in
        :data:`PROBE_RECORD`.
        """
        if not _have("notify-send"):
            pytest.skip(_MISSING_NOTIFY)
        if not _live_server_present():
            pytest.skip(_NO_LIVE_SERVER)

        with ClosedSignalWatch(LIVE_BUS) as watch:
            outcome = _notify_send(str(LIVE_BUS), BLOCK_PROBE_SECONDS)
            close = _close_notification(outcome.notification_id, watch)
        _record_close(outcome, close)

        assert outcome.returned, "notify-send blocked against a bus that has a server"
        assert outcome.elapsed < GUARD_BUDGET_SECONDS
        assert close.notification_id is not None, CLOSE_READINGS["no id"]
        assert close.monitor_attached, CLOSE_READINGS["monitor not attached"]
        assert close.acknowledged, (
            f"the probe notification (id {close.notification_id}) was never "
            f"closed: {CLOSE_READINGS[close.reading]}. The announcer's flags "
            "make it persistent, so it stays until a human dismisses it. "
            f"This run is the last line of {PROBE_RECORD}"
        )
        if close.reading == "closed on the second call":
            warnings.warn(
                f"{CLOSE_READINGS[close.reading]}. Recorded in {PROBE_RECORD}",
                stacklevel=1,
            )


class TestTheGuardSeparatesThem:
    def test_it_refuses_a_bus_with_nothing_listening(self, unserved_bus: UnservedBus):
        """Exit 1 — the state this box is in at every boot before login."""
        result = _run_guard(unserved_bus.path)

        assert result.returncode == 1, result.stdout + result.stderr
        assert "nothing owning" in result.stdout

    def test_it_refuses_quickly_enough_to_matter(self, unserved_bus: UnservedBus):
        """A refusal that takes 30 s is the bug wearing the fix's clothes."""
        started = time.monotonic()
        _run_guard(unserved_bus.path)
        elapsed = time.monotonic() - started

        assert elapsed < GUARD_BUDGET_SECONDS, (
            f"the guard took {elapsed:.2f}s; the announcer's whole budget is "
            "30s and the point of asking is to leave it unspent"
        )

    def test_asking_does_not_start_the_waiter_that_calling_starts(
        self, unserved_bus: UnservedBus
    ):
        """The mechanism, asserted directly rather than inferred from speed.

        ``NameHasOwner`` goes to ``org.freedesktop.DBus`` and is answered by
        the bus; ``Notify`` goes to an unowned name and activates
        ``plasma_waitforname``. Measured by hand at five guard calls → zero
        waiters, one notify-send → one waiter.

        **Counted over this fixture's own bus, never over the box**
        (``SNAG-TEST-004``). The count was a global ``pgrep -c -f``, which
        asks a question about the machine and reports it as a question
        about this bus: a concurrent run entering its blocking half inside
        the five guard calls and the 0.5 s sleep raises the count and turns
        this red, and one dying inside the same window lowers it and hides
        a real regression. Scoping is what makes the observation belong to
        the thing under test — and it strengthens the assertion, because
        this bus starts with **no** waiter, so ``before`` is an empty set
        rather than whatever the desktop happened to be doing.

        Skipped where no activation file for the name exists at all, since
        then there is nothing to avoid starting and a pass would mean
        nothing.
        """
        services = Path("/usr/share/dbus-1/services")
        activatable = services.is_dir() and any(
            "org.freedesktop.Notifications" in f.read_text(errors="ignore")
            for f in services.glob("*.service")
        )
        if not activatable:
            pytest.skip("nothing on this box activates org.freedesktop.Notifications")

        before = _waiters_under(unserved_bus.pid)

        for _ in range(5):
            _run_guard(unserved_bus.path)
        time.sleep(0.5)

        after = _waiters_under(unserved_bus.pid)

        assert after == before, (
            f"asking the guard's question started a waiter ({before} → {after}) "
            "under this fixture's own bus; the question is being addressed to "
            "the notification name rather than to the bus daemon"
        )

    def test_it_reports_a_missing_socket_as_not_knowing_rather_than_as_no(
        self, tmp_path: Path
    ):
        """Exit 2. A box with no user manager and a box with no server are
        different faults, and only the second is ordinary."""
        result = _run_guard(str(tmp_path / "no-such-bus"))

        assert result.returncode == 2, result.stdout + result.stderr
        assert "no session bus" in result.stdout

    def test_it_admits_the_live_bus(self):
        """The other half of the pair: the guard must not refuse everything.

        A guard that always says no would pass every test above and silence
        the handler permanently — the failure mode with no symptom, since
        the thing it suppresses is itself a notification nobody receives.
        """
        if not LIVE_BUS.is_socket():
            pytest.skip("no session bus on this box")
        if not _live_server_present():
            pytest.skip(_NO_LIVE_SERVER)

        result = _run_guard(str(LIVE_BUS))

        assert result.returncode == 0, result.stdout + result.stderr
        assert "owns org.freedesktop.Notifications" in result.stdout


class TestTheRedSaysWhichReadingItIs:
    """The precondition is asserted first, or the block assertion's message lies.

    ``SNAG-TEST-003``, closed 2026-09-02. The entry's claim was never about
    a mechanism — both of its candidate causes were refuted while it stood —
    but about the assertion's *wording*: a red on
    :meth:`TestTheHazardIsReal.test_notify_send_does_not_return_on_a_bus_with_nothing_listening`
    said the D-Bus activation *"is gone from this box"*, so **any** red there
    read as good news and the honest response to good news is to relax the
    control.

    Two assertions separate the readings now, and the order is what makes
    the second one true. The block assertion's message states that a waiter
    *was* started; it can only state that because the precondition has
    already run. Swap them and, on a box where the activation is genuinely
    gone, the block assertion fires first and asserts something false about
    a box nobody looked at — the original defect wearing the fix's clothes.

    **Only the assert's ``test`` is read, never its message**, and that is
    the whole reason this pin says anything. Both messages quote
    ``outcome.elapsed`` and ``outcome.stderr``, so a walk over the whole
    :class:`ast.Assert` node would find every field in both and report
    agreement whatever the order was — ``test_live_drive_scoping.py``'s
    prose problem arriving one node deeper, where the confusable thing is an
    f-string rather than a docstring.

    No snag check accompanies this. One would have to reproduce an
    intermittent fault on demand, and the entry is closed by the wording
    changing rather than by an observation. The two readings were driven by
    hand instead — a bus with no ``.service`` files at all gives
    ``activated=False`` and ``ServiceUnknown`` in 0.03 s, and three kills
    landing inside the window give ``activated=True`` with
    ``exited with status 255`` at 3.06 s — and each lands on its own
    assertion. This pin is what survives them: ``FROZEN_TABLES``' rule, the
    detector outliving the finding.
    """

    #: The two readings, in the order that keeps the second one honest.
    EXPECTED_ORDER = [["activated"], ["returned"]]

    @staticmethod
    def _outcome_fields(expression: ast.expr) -> list[str]:
        return [
            node.attr
            for node in ast.walk(expression)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "outcome"
        ]

    def _asserts(self) -> list[ast.Assert]:
        tree = ast.parse(Path(__file__).resolve().read_text())
        wanted = "test_notify_send_does_not_return_on_a_bus_with_nothing_listening"
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == wanted:
                return [s for s in node.body if isinstance(s, ast.Assert)]
        raise AssertionError(f"{wanted} is gone; this pin has nothing to guard")

    def test_the_precondition_is_asserted_before_the_block(self):
        order = [self._outcome_fields(a.test) for a in self._asserts()]

        assert order == self.EXPECTED_ORDER, (
            f"the blocking probe asserts {order} where it must assert "
            f"{self.EXPECTED_ORDER}. The activation is the precondition: "
            "without it first, a red cannot say whether the hazard is gone "
            "or whether this reading was disturbed, which is SNAG-TEST-003"
        )


#: ``dbus-monitor``'s own output, captured 2026-09-28 on this box with
#: :data:`_CLOSED_MATCH` while closing the never-issued id 999999. The first
#: four lines are the monitor attaching; the last three are Plasma's answer.
_RECORDED_MONITOR_TEXT = """\
signal time=1790588565.883901 sender=org.freedesktop.DBus -> destination=:1.7020 serial=4294967295 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=NameAcquired
   string ":1.7020"
signal time=1790588565.883910 sender=org.freedesktop.DBus -> destination=:1.7020 serial=4294967295 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=NameLost
   string ":1.7020"
signal time=1790588565.935774 sender=:1.4830 -> destination=(null destination) serial=27143 path=/org/freedesktop/Notifications; interface=org.freedesktop.Notifications; member=NotificationClosed
   uint32 999999
   uint32 3
"""  # noqa: E501


class _ScriptedWatch:
    """A :class:`ClosedSignalWatch` that answers the Nth wait and no other."""

    def __init__(self, attached: bool, answers_on: int | None) -> None:
        self.attached = attached
        self._answers_on = answers_on
        self.waits = 0

    def wait_for(self, notification_id: str, timeout: float) -> ClosedSignal | None:
        self.waits += 1
        if self.waits == self._answers_on:
            return ClosedSignal(time.time(), int(notification_id), 3)
        return None


def _patch_send_close(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stand in for the live ``CloseNotification``; the list is every id closed."""
    sent: list[str] = []

    def send(notification_id: str) -> int:
        sent.append(notification_id)
        return 0

    monkeypatch.setattr(f"{__name__}._send_close", send)
    return sent


class TestTheCloseIsReadFromPlasmasAnswer:
    """``SNAG-TEST-014``'s cleanup, driven without a live bus.

    The live test can only reach the reading the box gives it that day,
    which is ``closed`` on every run measured. The other readings are what a
    recurrence would produce, so they are driven here or never.
    """

    def test_the_recorded_signal_is_parsed(self):
        parser = _ClosedSignalParser()
        found = [
            signal
            for line in _RECORDED_MONITOR_TEXT.splitlines()
            if (signal := parser.feed(line)) is not None
        ]

        assert found == [ClosedSignal(1790588565.935774, 999999, 3)]

    def test_a_new_header_discards_a_half_read_close(self):
        """Without the reset, the id below would pair with the next member's value."""
        parser = _ClosedSignalParser()
        lines = [
            "signal time=0.5 sender=:1.1 -> destination=(null destination) "
            "serial=0 path=/org/freedesktop/Notifications; "
            "interface=org.freedesktop.Notifications; member=NotificationClosed",
            "   uint32 41",
            "signal time=1.0 sender=:1.1 -> destination=(null destination) "
            "serial=1 path=/org/freedesktop/Notifications; "
            "interface=org.freedesktop.Notifications; member=ActionInvoked",
            "   uint32 42",
            "   uint32 7",
        ]

        assert [parser.feed(line) for line in lines] == [None] * 5

    @pytest.mark.parametrize(
        ("attached", "answers_on", "reading", "closes"),
        [
            (True, 1, "closed", 1),
            (True, 2, "closed on the second call", 2),
            (True, None, "never acknowledged", 2),
            (False, None, "monitor not attached", 1),
        ],
    )
    def test_a_second_close_is_sent_only_when_the_first_goes_unanswered(
        self,
        monkeypatch: pytest.MonkeyPatch,
        attached: bool,
        answers_on: int | None,
        reading: str,
        closes: int,
    ):
        sent = _patch_send_close(monkeypatch)
        watch = _ScriptedWatch(attached, answers_on)

        close = _close_notification("41", watch)  # type: ignore[arg-type]

        assert (close.reading, len(sent)) == (reading, closes)
        assert close.acknowledged is (reading in ("closed", "closed on the second call"))

    def test_no_id_sends_nothing(self, monkeypatch: pytest.MonkeyPatch):
        sent = _patch_send_close(monkeypatch)

        close = _close_notification(None, _ScriptedWatch(True, 1))  # type: ignore[arg-type]

        assert (close.reading, sent) == ("no id", [])

    def test_every_reading_has_an_explanation(self):
        readings = {
            CloseOutcome(None, True, ()).reading,
            CloseOutcome("1", False, ()).reading,
            CloseOutcome("1", True, ()).reading,
        }

        assert readings <= CLOSE_READINGS.keys()

    def test_a_run_is_appended_as_one_json_line(self, tmp_path: Path):
        record = tmp_path / "state" / "notify-probe.jsonl"
        outcome = NotifySendOutcome(True, 0.05, "41", None, "")
        answer = ClosedSignal(100.025, 41, 3)
        close = CloseOutcome("41", True, (CloseAttempt(100.0, 0, answer),))

        _record_close(outcome, close, record)
        _record_close(outcome, close, record)

        rows = [json.loads(line) for line in record.read_text().splitlines()]
        assert len(rows) == 2
        assert rows[0]["reading"] == "closed"
        assert rows[0]["attempts"] == [
            {
                "sent_at": 100.0,
                "busctl_rc": 0,
                "answered_at": 100.025,
                "reason": 3,
                "latency_ms": 25.0,
            }
        ]
