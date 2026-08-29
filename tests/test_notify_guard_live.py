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
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
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


def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


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
        yield bus_path
    finally:
        # The activation the hazard triggers outlives its caller — it is
        # started by the bus, not by notify-send — so it is cleaned up
        # explicitly rather than left for the next run to miscount.
        subprocess.run(
            ["pkill", "-f", "plasma_wait[f]orname"], capture_output=True, check=False
        )
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


def _notify_send(bus_path: str, timeout: float) -> tuple[bool, float]:
    """Return (returned_within_timeout, elapsed).

    The flags are the announcer's own, because the question is whether *its*
    call blocks, and libnotify's behaviour on an unowned name is not
    obviously independent of them — ``--expire-time=0`` in particular was
    the first suspect and was cleared only by measurement.
    """
    env = dict(os.environ, DBUS_SESSION_BUS_ADDRESS=f"unix:path={bus_path}")
    started = time.monotonic()
    try:
        subprocess.run(
            [
                "notify-send",
                "--app-name=sysadmin-test",
                "--urgency=critical",
                "--expire-time=0",
                "--icon=dialog-error",
                "SNAG-SYSD-004 probe",
                "if you are reading this on screen, the live witness worked",
            ],
            capture_output=True,
            env=env,
            timeout=timeout,
            check=False,
        )
        return True, time.monotonic() - started
    except subprocess.TimeoutExpired:
        return False, time.monotonic() - started


class TestTheHazardIsReal:
    """Speaking to an unserved bus blocks; speaking to a served one does not.

    This pair is the reason the guard is worth having. Without it the guard's
    refusal is unmotivated — a constant observation is not evidence unless
    something in the population would have forced a different one.
    """

    def test_notify_send_does_not_return_on_a_bus_with_nothing_listening(
        self, unserved_bus: str
    ):
        if not _have("notify-send"):
            pytest.skip(_MISSING_NOTIFY)

        returned, elapsed = _notify_send(unserved_bus, BLOCK_PROBE_SECONDS)

        assert not returned, (
            f"notify-send returned after {elapsed:.2f}s on a bus with no "
            "notification server. If this fails, the D-Bus activation that "
            "causes SNAG-SYSD-004 is gone from this box and the guard's "
            "urgency should be re-derived rather than assumed"
        )

    def test_notify_send_returns_at_once_on_the_live_bus(self):
        """The witness. Same flags, same binary, a server on the other end.

        It puts a real notification on screen, which is the point: the
        happy path is asserted by exercising it, not by trusting that the
        unhappy one implies it.
        """
        if not _have("notify-send"):
            pytest.skip(_MISSING_NOTIFY)
        if not _live_server_present():
            pytest.skip(_NO_LIVE_SERVER)

        returned, elapsed = _notify_send(str(LIVE_BUS), BLOCK_PROBE_SECONDS)

        assert returned, "notify-send blocked against a bus that has a server"
        assert elapsed < GUARD_BUDGET_SECONDS


class TestTheGuardSeparatesThem:
    def test_it_refuses_a_bus_with_nothing_listening(self, unserved_bus: str):
        """Exit 1 — the state this box is in at every boot before login."""
        result = _run_guard(unserved_bus)

        assert result.returncode == 1, result.stdout + result.stderr
        assert "nothing owning" in result.stdout

    def test_it_refuses_quickly_enough_to_matter(self, unserved_bus: str):
        """A refusal that takes 30 s is the bug wearing the fix's clothes."""
        started = time.monotonic()
        _run_guard(unserved_bus)
        elapsed = time.monotonic() - started

        assert elapsed < GUARD_BUDGET_SECONDS, (
            f"the guard took {elapsed:.2f}s; the announcer's whole budget is "
            "30s and the point of asking is to leave it unspent"
        )

    def test_asking_does_not_start_the_waiter_that_calling_starts(
        self, unserved_bus: str
    ):
        """The mechanism, asserted directly rather than inferred from speed.

        ``NameHasOwner`` goes to ``org.freedesktop.DBus`` and is answered by
        the bus; ``Notify`` goes to an unowned name and activates
        ``plasma_waitforname``. Measured by hand at five guard calls → zero
        waiters, one notify-send → one waiter.

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

        before = subprocess.run(
            ["pgrep", "-c", "-f", "plasma_wait[f]orname"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        for _ in range(5):
            _run_guard(unserved_bus)
        time.sleep(0.5)

        after = subprocess.run(
            ["pgrep", "-c", "-f", "plasma_wait[f]orname"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        assert after == before, (
            f"asking the guard's question started a waiter ({before} → {after}); "
            "the question is being addressed to the notification name rather "
            "than to the bus daemon"
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
