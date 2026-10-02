"""The ``sd_notify`` sender (``sysadmin/core/sd_notify.py``).

The sends are received on a real ``AF_UNIX`` datagram socket rather than
a patched ``socket``, because the address spelling (a path, or ``@`` for
the abstract namespace) is the part most likely to be wrong and a mock
would accept either.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import os
import socket
import textwrap
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from sysadmin.core import sd_notify


@pytest.fixture(autouse=True)
def _no_inherited_systemd(monkeypatch: pytest.MonkeyPatch) -> None:
    """A suite run from inside a notify unit must not ping that unit."""
    for name in (
        sd_notify.SOCKET_ENV,
        sd_notify.WATCHDOG_USEC_ENV,
        sd_notify.WATCHDOG_PID_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def path_socket(tmp_path: Path) -> Iterator[tuple[str, socket.socket]]:
    path = str(tmp_path / "notify")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(path)
    sock.settimeout(2)
    yield path, sock
    sock.close()


def _received(sock: socket.socket) -> bytes:
    return sock.recv(4096)


class TestNotify:
    def test_no_socket_is_a_silent_no_op(self, caplog: pytest.LogCaptureFixture):
        """The rollback's premise: under ``Type=simple`` nothing happens."""
        assert sd_notify.notify("READY=1") is False
        assert caplog.records == []

    def test_a_path_socket_receives_the_state(self, monkeypatch, path_socket):
        path, sock = path_socket
        monkeypatch.setenv(sd_notify.SOCKET_ENV, path)
        assert sd_notify.notify("READY=1") is True
        assert _received(sock) == b"READY=1"

    def test_an_abstract_socket_is_spelled_with_a_nul(self, monkeypatch):
        """``@name`` is how systemd writes it; the kernel wants ``\\0name``."""
        name = f"sysadmin-test-{uuid.uuid4().hex}"
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.bind(b"\0" + name.encode())
            sock.settimeout(2)
            monkeypatch.setenv(sd_notify.SOCKET_ENV, "@" + name)
            assert sd_notify.notify("WATCHDOG=1") is True
            assert _received(sock) == b"WATCHDOG=1"

    def test_a_missing_socket_is_logged_and_not_raised(
        self, monkeypatch, tmp_path, caplog
    ):
        monkeypatch.setenv(sd_notify.SOCKET_ENV, str(tmp_path / "absent"))
        assert sd_notify.notify("WATCHDOG=1") is False
        assert [r.message for r in caplog.records] == ["sd_notify_failed"]

    def test_an_address_systemd_would_not_hand_out_is_refused(
        self, monkeypatch, caplog
    ):
        monkeypatch.setenv(sd_notify.SOCKET_ENV, "vsock:2:1234")
        assert sd_notify.notify("READY=1") is False
        assert [r.message for r in caplog.records] == [
            "sd_notify_unsupported_socket"
        ]


class TestWatchdogInterval:
    def test_unarmed_is_none(self):
        assert sd_notify.watchdog_interval() is None

    def test_half_the_period(self, monkeypatch):
        monkeypatch.setenv(sd_notify.WATCHDOG_USEC_ENV, "30000000")
        assert sd_notify.watchdog_interval() == 15.0

    def test_our_pid_is_armed(self, monkeypatch):
        monkeypatch.setenv(sd_notify.WATCHDOG_USEC_ENV, "30000000")
        monkeypatch.setenv(sd_notify.WATCHDOG_PID_ENV, str(os.getpid()))
        assert sd_notify.watchdog_interval() == 15.0

    def test_another_pid_is_not(self, monkeypatch):
        """A child that inherited the environment must not ping for us."""
        monkeypatch.setenv(sd_notify.WATCHDOG_USEC_ENV, "30000000")
        monkeypatch.setenv(sd_notify.WATCHDOG_PID_ENV, str(os.getpid() + 1))
        assert sd_notify.watchdog_interval() is None

    @pytest.mark.parametrize("raw", ["0", "-5", "thirty"])
    def test_a_period_that_arms_nothing_is_none(self, monkeypatch, raw):
        monkeypatch.setenv(sd_notify.WATCHDOG_USEC_ENV, raw)
        assert sd_notify.watchdog_interval() is None


class TestPinging:
    def test_unarmed_starts_no_task(self):
        async def drive():
            return sd_notify.start_watchdog()

        assert asyncio.run(drive()) is None

    def test_armed_pings_repeatedly_until_cancelled(self, monkeypatch):
        monkeypatch.setenv(sd_notify.WATCHDOG_USEC_ENV, "20000")  # 10 ms apart
        sent: list[str] = []

        def record(state: str) -> bool:
            sent.append(state)
            return True

        async def drive() -> None:
            task = sd_notify.start_watchdog(record)
            assert task is not None
            await asyncio.sleep(0.1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(drive())
        assert len(sent) >= 3
        assert set(sent) == {"WATCHDOG=1"}

    def test_the_default_sender_reaches_the_socket(self, monkeypatch, path_socket):
        path, sock = path_socket
        monkeypatch.setenv(sd_notify.SOCKET_ENV, path)
        monkeypatch.setenv(sd_notify.WATCHDOG_USEC_ENV, "20000")

        async def drive() -> None:
            task = sd_notify.start_watchdog()
            assert task is not None
            await asyncio.sleep(0.05)
            task.cancel()

        asyncio.run(drive())
        assert _received(sock) == b"WATCHDOG=1"


class TestLifespanWiring:
    """Where ``main.lifespan`` sends, read off its source.

    The real lifespan needs the database, so the order is checked on the
    syntax tree: ready is the last thing startup does, and stopping the
    first thing shutdown does.
    """

    @staticmethod
    def _around_yield() -> tuple[list[str], list[str]]:
        from sysadmin import main

        tree = ast.parse(textwrap.dedent(inspect.getsource(main.lifespan)))
        body = tree.body[0].body  # type: ignore[attr-defined]
        index = next(
            i
            for i, stmt in enumerate(body)
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Yield)
        )
        return (
            [ast.unparse(s) for s in body[:index]],
            [ast.unparse(s) for s in body[index + 1 :]],
        )

    def test_ready_then_the_watchdog_immediately_before_yield(self):
        before, _ = self._around_yield()
        assert before[-2:] == ["notify('READY=1')", "watchdog = start_watchdog()"]

    def test_stopping_is_the_first_thing_shutdown_says(self):
        _, after = self._around_yield()
        assert after[0] == "notify('STOPPING=1')"

    def test_the_watchdog_is_cancelled_on_shutdown(self):
        _, after = self._around_yield()
        assert "if watchdog is not None:\n    watchdog.cancel()" in after
