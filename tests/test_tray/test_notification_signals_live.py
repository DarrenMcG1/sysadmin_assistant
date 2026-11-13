"""The toast's buttons reach the tray: D-Bus signals delivered over a real bus.

Finding H4 of ``docs/review/bug-review.md``. The freedesktop notification
signals carry unsigned ids, ``ActionInvoked(us)`` and
``NotificationClosed(uu)``, and QtDBus matches a slot to a signal by its
D-Bus signature. Slots declared ``@pyqtSlot(int, str)`` and
``@pyqtSlot(int, int)`` have the signatures ``(is)`` and ``(ii)``, so they
were never called: ``connect()`` returned true, nothing was logged, and the
Restart and Snooze buttons on every toast did nothing.

**Why this file exists beside ``test_notifications.py``.** The tests there
call ``_on_action_invoked`` directly, which skips the one step that was
broken, the signature match. Only a signal delivered over a bus exercises
it, so this test starts a private ``dbus-daemon``, puts a stand-in
notification server on it, and has the stand-in send the two signals with
``uint`` arguments, as Plasma does.

**The stand-in is a process of its own, as Plasma is.** ``DbusNotifier``
builds a ``QDBusInterface``, which makes a blocking introspection call.
With the stand-in in the tray's process, on the main thread or on a
``QThread`` of its own, that call waited out the 25 s D-Bus timeout
(measured 2026-11-13: 25.3 s to construct the notifier). In a second
process it answers at once.

**Falsified 2026-11-13:** with the slots put back to ``int``, the tray
reports no restart, no snooze and the closed id still pending, and this
test fails on the first verdict.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from tests.test_notify_guard_live import UnservedBus, unserved_bus  # noqa: F401

#: Both roles in one source, run as two processes: ``server`` owns the
#: notification name and sends the signals when ``Fire`` is called;
#: ``tray`` builds the real ``DbusNotifier`` and reports what reached it.
#: Subprocesses as well because ``QDBusConnection.sessionBus()`` is fixed
#: per process at first use, and this pytest process may hold one on the
#: real session bus.
_SOURCE = '''
import json, os, sys, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtCore import QMetaType, QObject, QVariant, pyqtClassInfo, pyqtSlot
from PyQt6.QtDBus import (
    QDBusAbstractAdaptor, QDBusArgument, QDBusConnection, QDBusMessage,
)

PATH, IFACE = "/org/freedesktop/Notifications", "org.freedesktop.Notifications"


def uint(n):
    arg = QDBusArgument()
    arg.add(n, QMetaType.Type.UInt.value)
    return QVariant(arg)


@pyqtClassInfo("D-Bus Interface", IFACE)
class Server(QDBusAbstractAdaptor):
    @pyqtSlot(result="QStringList")
    def GetCapabilities(self):
        return ["actions"]

    @pyqtSlot()
    def Fire(self):
        bus = QDBusConnection.sessionBus()
        for name, args in (
            ("ActionInvoked", [uint(7), "restart"]),
            ("ActionInvoked", [uint(8), "snooze"]),
            ("NotificationClosed", [uint(9), uint(2)]),
        ):
            msg = QDBusMessage.createSignal(PATH, IFACE, name)
            msg.setArguments(args)
            bus.send(msg)


def serve():
    from PyQt6.QtCore import QCoreApplication
    app = QCoreApplication([])
    bus = QDBusConnection.sessionBus()
    holder = QObject()
    Server(holder)
    claimed = bus.registerObject(PATH, holder) and bus.registerService(IFACE)
    print(json.dumps({"claimed": bool(claimed)}), flush=True)
    app.exec()


def tray():
    from PyQt6.QtWidgets import QApplication
    from sysadmin_tray.notifications import DbusNotifier

    app = QApplication([])
    notifier = DbusNotifier()
    got = {"restart": [], "snooze": []}
    notifier.restart_requested.connect(got["restart"].append)
    notifier.snooze_requested.connect(got["snooze"].append)
    notifier._pending_actions[7] = "redis"
    notifier._pending_snoozes[8] = "service:redis"
    notifier._pending_actions[9] = "postgres"

    QDBusConnection.sessionBus().send(
        QDBusMessage.createMethodCall(IFACE, PATH, IFACE, "Fire")
    )

    def done():
        return got["restart"] and got["snooze"] and 9 not in notifier._pending_actions

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and not done():
        app.processEvents()
        time.sleep(0.01)

    print(json.dumps({
        "available": notifier.available,
        "restart": got["restart"],
        "snooze": got["snooze"],
        "closed_cleared": 9 not in notifier._pending_actions,
    }), flush=True)


serve() if sys.argv[1] == "server" else tray()
'''

#: The server prints its claim after importing PyQt6 and taking the name,
#: which takes well under a second here; this bounds a slow interpreter.
_CLAIM_SECONDS = 15


def _drive(bus: UnservedBus, tmp_path: Path) -> tuple[bool, dict]:
    """Start the stand-in, run the tray against it, return both reports."""
    source = tmp_path / "signals.py"
    source.write_text(_SOURCE, encoding="utf-8")
    env = dict(os.environ, DBUS_SESSION_BUS_ADDRESS=f"unix:path={bus.path}")

    server = subprocess.Popen(
        [sys.executable, str(source), "server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert server.stdout is not None
        deadline = time.monotonic() + _CLAIM_SECONDS
        claim_line = server.stdout.readline()
        assert time.monotonic() < deadline, "the stand-in took too long to claim"
        claimed = bool(claim_line) and json.loads(claim_line)["claimed"]

        result = subprocess.run(
            [sys.executable, str(source), "tray"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover
            server.kill()

    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    assert result.returncode == 0 and lines, (
        f"the tray did not report (exit {result.returncode}): {result.stderr[-2000:]}"
    )
    return claimed, json.loads(lines[-1])


def test_signals_from_the_notification_server_reach_the_slots(
    unserved_bus: UnservedBus,  # noqa: F811
    tmp_path: Path,
) -> None:
    claimed, report = _drive(unserved_bus, tmp_path)

    # Premise: without these, every verdict below is about the harness.
    assert claimed, "the stand-in never owned the notification name"
    assert report["available"], "DbusNotifier fell back, so it subscribed to nothing"

    assert report["restart"] == ["redis"], (
        "ActionInvoked(u, 'restart') did not reach _on_action_invoked; "
        "is its slot declared with \"uint\"?"
    )
    assert report["snooze"] == ["service:redis"], (
        "ActionInvoked(u, 'snooze') did not reach _on_action_invoked"
    )
    assert report["closed_cleared"], (
        "NotificationClosed(u, u) did not reach _on_notification_closed; "
        "is its slot declared with (\"uint\", \"uint\")?"
    )
