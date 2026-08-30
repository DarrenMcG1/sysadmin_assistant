"""The login replay driven against a real bus, a real guard, a real toast.

``SNAG-SYSD-005``, Session 126. ``tests/test_failure_replay.py`` decides
the orderings against stand-ins; this decides the one claim a stand-in
cannot settle — **that waiting here delivers what failing fast would have
lost.**

``SNAG-SYSD-004`` refused to wait in the announcer and was right to: the
window is notify-send's own 60.08 s and the gap to the next login was 24
minutes at best. At *login* the same wait covers a gap of seconds —
measured at the 2026-08-23 session, ``plasma-plasmashell.service`` went
active at 14:44:55, ``graphical-session.target`` was reached at 14:44:57
and plasmashell was still initialising at 14:44:58. So the principle did
not change; the number did, and only a live bus can show it.

**The premise is asserted before any negative is believed**, which is not
ceremony. Writing this, a stand-in notification server printed
``claimed`` and owned nothing a millisecond later — ``dbus.service.BusName``
held only in a local is garbage-collected the moment the function returns —
and the wait duly reported ``False`` after a full budget. That reads as a
verdict about the code under test and was a verdict about the harness. So
every test here that expects "nobody listening" first proves the server
was not there, and every test that expects delivery first proves it was.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from sysadmin.core.failure_replay import (
    NOBODY_LISTENING,
    SERVER_PRESENT,
    ask_notification_server,
    wait_for_notification_server,
)

GUARD = Path(__file__).resolve().parents[1] / "scripts" / "notification-server-present.sh"

#: Well under notify-send's 60.08 s activation bound and the bus's 120 s
#: ``service_start_timeout``, so a test that fails does so quickly rather
#: than by holding the suite.
TEST_BUDGET = 15.0

#: When the stand-in server claims the name, in seconds. Above the guard's
#: measured 3.8 ms by three orders of magnitude, so the "not there yet, then
#: there" transition is unambiguous rather than a race with the first poll.
CLAIM_AFTER = 2.0

_MISSING_DBUS = "dbus-daemon is not installed — cannot start a bus with nothing on it"
_MISSING_BINDINGS = (
    "the system python has no dbus/gi bindings — cannot own a name on a private bus"
)

#: A notification server that claims the name after a delay and records what
#: it is told. Run under the *system* interpreter: the project venv has no
#: D-Bus bindings and must not gain them for a test.
_SERVER_SOURCE = '''
import json, sys
import dbus, dbus.mainloop.glib, dbus.service
from gi.repository import GLib

ADDRESS, DELAY = sys.argv[1], float(sys.argv[2])

class Server(dbus.service.Object):
    @dbus.service.method("org.freedesktop.Notifications",
                         in_signature="susssasa{sv}i", out_signature="u")
    def Notify(self, app, replaces, icon, summary, body, actions, hints, timeout):
        print(json.dumps({"summary": str(summary), "body": str(body),
                          "urgency": int(hints.get("urgency", -1)),
                          "expire_timeout": int(timeout)}), flush=True)
        return 1

    @dbus.service.method("org.freedesktop.Notifications",
                         in_signature="", out_signature="as")
    def GetCapabilities(self):
        return ["body"]

    @dbus.service.method("org.freedesktop.Notifications",
                         in_signature="", out_signature="ssss")
    def GetServerInformation(self):
        return ("probe", "sysadmin", "1.0", "1.2")

# Held at module scope deliberately. As locals these are collected when
# claim() returns, which releases the name: the server prints "claimed" and
# owns nothing. That is the harness defect this file's docstring records.
HELD = {}

def claim():
    bus = dbus.bus.BusConnection(ADDRESS)
    HELD["bus"] = bus
    HELD["name"] = dbus.service.BusName("org.freedesktop.Notifications", bus)
    HELD["obj"] = Server(bus, "/org/freedesktop/Notifications")
    print(json.dumps({"event": "claimed"}), flush=True)
    return False

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
GLib.timeout_add(max(1, int(DELAY * 1000)), claim)
GLib.MainLoop().run()
'''


def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


def _name_is_owned(bus_path: str | None = None) -> bool:
    """Does anything own the notification name — asked *without* the guard.

    The premise check behind every verdict in this file, and it exists in
    this shape because the weaker version was not enough. Driving the
    harness mutation that drops the name to the garbage collector, an
    earlier premise — "the stand-in printed ``claimed``" — passed, and the
    failure landed on the verdict instead: a fact about the harness
    reported as a fact about the module. Printing that a name was claimed
    and holding it are different claims, and only the bus can settle the
    second.

    It must not route through ``notification-server-present.sh``, for
    ``test_notify_guard_live.py``'s reason: a control the subject can
    answer is a control the subject can switch off.
    """
    env = {"PATH": "/usr/bin:/bin"}
    if bus_path is not None:
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus_path}"
    else:  # pragma: no cover — the live-bus path, exercised on a desktop
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{__import__('os').getuid()}/bus"
    probe = subprocess.run(
        [
            "busctl", "--user", "call",
            "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "NameHasOwner", "s",
            "org.freedesktop.Notifications",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0 and probe.stdout.strip() == "b true"


def _system_python_has_bindings() -> bool:
    probe = subprocess.run(
        ["/usr/bin/python3", "-c", "import dbus, dbus.service, gi"],
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


@pytest.fixture
def unserved_bus(tmp_path: Path):
    """A private session bus with nothing owning the notification name."""
    if not _have("dbus-daemon"):
        pytest.skip(_MISSING_DBUS)

    started = subprocess.run(
        ["dbus-daemon", "--session", "--fork", "--print-address=1", "--print-pid=1"],
        capture_output=True,
        text=True,
        check=True,
    )
    address, pid = started.stdout.strip().splitlines()[:2]
    bus_path = address.removeprefix("unix:path=").split(",", 1)[0]
    try:
        yield bus_path
    finally:
        subprocess.run(["kill", pid], capture_output=True, check=False)


@pytest.fixture
def claim_name(tmp_path: Path):
    """Start a notification server that claims the name after a delay.

    Yields a callable returning every JSON line the server has printed, so
    a test can assert both that it claimed and what it was told.
    """
    if not _system_python_has_bindings():
        pytest.skip(_MISSING_BINDINGS)

    source = tmp_path / "notif_server.py"
    source.write_text(_SERVER_SOURCE, encoding="utf-8")
    log = tmp_path / "server.jsonl"
    started: list[subprocess.Popen] = []

    def start(bus_path: str, delay: float = CLAIM_AFTER):
        handle = log.open("w", encoding="utf-8")
        proc = subprocess.Popen(
            ["/usr/bin/python3", str(source), f"unix:path={bus_path}", str(delay)],
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
        started.append(proc)

        def said() -> list[dict]:
            handle.flush()
            if not log.exists():
                return []
            return [
                json.loads(line)
                for line in log.read_text(encoding="utf-8").splitlines()
                if line.strip().startswith("{")
            ]

        return said

    try:
        yield start
    finally:
        for proc in started:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover
                proc.kill()


class TestTheWaitGivesUpWhenNothingArrives:
    @pytest.mark.premise
    def test_a_bus_with_nothing_on_it_is_refused_within_the_budget(
        self, unserved_bus: str
    ):
        """Bounded, and bounded by *this* module rather than by a unit timeout.

        ``SNAG-SYSD-004``'s defect was that the only bound was systemd's, so
        the only symptom was a killed unit. Here the wait ends itself.
        """
        # Premise: nothing owns the name, so a negative below is about the
        # wait rather than about a server that failed to start.
        verdict, _ = ask_notification_server(GUARD, bus_path=unserved_bus)
        assert verdict == NOBODY_LISTENING

        began = time.monotonic()
        landed, said = wait_for_notification_server(
            GUARD, budget=3.0, poll=0.5, bus_path=unserved_bus
        )
        elapsed = time.monotonic() - began

        assert landed is False
        assert "nothing owning" in said
        assert elapsed < 10.0, f"the wait overran its own budget: {elapsed:.2f}s"


class TestTheWaitCatchesAServerThatArrivesLate:
    @pytest.mark.premise
    def test_a_name_claimed_mid_wait_is_seen(self, unserved_bus: str, claim_name):
        """The claim that justifies waiting here at all.

        Fail-fast would return "nobody listening" at t=0 and lose a
        notification that becomes deliverable two seconds later — which is
        the whole shape of a login.
        """
        assert ask_notification_server(GUARD, bus_path=unserved_bus)[0] == NOBODY_LISTENING

        said = claim_name(unserved_bus, delay=CLAIM_AFTER)
        began = time.monotonic()
        landed, message = wait_for_notification_server(
            GUARD, budget=TEST_BUDGET, poll=0.5, bus_path=unserved_bus
        )
        elapsed = time.monotonic() - began

        # Premise before verdict, in two steps because the first is not
        # enough. Reaching the claim is what the log proves; *holding* the
        # name is what the bus proves, and a stand-in can do the first and
        # not the second — see `_name_is_owned`.
        assert {"event": "claimed"} in said(), "the stand-in never reached its claim"
        assert _name_is_owned(unserved_bus), (
            "the stand-in printed 'claimed' and does not own the name — the "
            "harness is broken, so nothing below is evidence about the wait"
        )
        assert landed is True, message
        assert elapsed >= CLAIM_AFTER, "it cannot have seen a name claimed later than this"
        assert elapsed < TEST_BUDGET

    @pytest.mark.premise
    def test_what_arrives_is_the_notification_that_was_sent(
        self, unserved_bus: str, claim_name
    ):
        """Delivered intact, not merely accepted.

        ``notify-send`` returning 0 is evidence about the call; the server's
        own record is evidence about the message — and Session 39's two
        flags are the half most easily lost in transit.
        """
        if not _have("notify-send"):
            pytest.skip("notify-send is not installed")

        said = claim_name(unserved_bus, delay=CLAIM_AFTER)
        landed, _ = wait_for_notification_server(
            GUARD, budget=TEST_BUDGET, poll=0.5, bus_path=unserved_bus
        )
        assert _name_is_owned(unserved_bus), "the harness never owned the name"
        assert landed is True

        sent = subprocess.run(
            [
                "notify-send",
                "--app-name=sysadmin",
                "--urgency=critical",
                "--expire-time=0",
                "STILL FAILED: sysadmin.service",
                "Failed 38 hours ago and has not come back.",
            ],
            env={"DBUS_SESSION_BUS_ADDRESS": f"unix:path={unserved_bus}", "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert sent.returncode == 0, sent.stderr

        deadline = time.monotonic() + 5
        received: list[dict] = []
        while time.monotonic() < deadline and not received:
            received = [row for row in said() if "summary" in row]
            if not received:
                time.sleep(0.1)

        assert received, "the server claimed the name and recorded no notification"
        got = received[0]
        assert got["summary"] == "STILL FAILED: sysadmin.service"
        assert "38 hours ago" in got["body"]
        # Session 39's two flags: critical, and never expiring.
        assert got["urgency"] == 2
        assert got["expire_timeout"] == 0


class TestTheGuardIsTheOneOnDisk:
    def test_it_exists_and_is_executable(self):
        """Every test above is meaningless if this path is wrong."""
        assert GUARD.is_file()
        assert GUARD.stat().st_mode & 0o111

    def test_the_live_bus_is_admitted(self):
        """The discriminating witness for the negatives above.

        A guard that refused *everything* would pass every "nobody
        listening" test in this file. Asked without routing through the
        thing under test, exactly as ``test_notify_guard_live.py`` had to
        be repaired to do.
        """
        probe = subprocess.run(
            [
                "busctl", "--user", "call",
                "org.freedesktop.DBus", "/org/freedesktop/DBus",
                "org.freedesktop.DBus", "NameHasOwner", "s",
                "org.freedesktop.Notifications",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode != 0 or probe.stdout.strip() != "b true":
            pytest.skip("no notification server on this box to be admitted")

        verdict, said = ask_notification_server(GUARD)
        assert verdict == SERVER_PRESENT, said
