"""Tests for the systemd subprocess helpers.

SNAG-SYSD-001: ``systemctl --user`` needs ``XDG_RUNTIME_DIR`` to find the
session bus.  A systemd service unit is started with a near-empty
environment, so every user-scope check made by the daemon failed — and the
old code read the resulting empty output as "the unit is inactive",
reporting a live timer as ``critical``.  It passed verification because an
interactive shell always has ``XDG_RUNTIME_DIR`` set.

Everything here mocks ``asyncio.create_subprocess_exec``: these tests must
assert what environment we *hand to* systemctl, and must not depend on a
live session bus (there is none in CI).
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.utils import systemd
from sysadmin.utils.systemd import (
    SystemdQueryError,
    UserBusUnavailableError,
    build_env,
    get_unit_status,
    is_active,
    restart_unit,
    user_runtime_dir,
)

_SPAWN = "sysadmin.utils.systemd.asyncio.create_subprocess_exec"

#: The exact message systemd emits when it cannot find the session bus.
BUS_FAILURE_STDERR = (
    "Failed to connect to user scope bus via local transport: "
    "$DBUS_SESSION_BUS_ADDRESS and $XDG_RUNTIME_DIR not defined"
)

SHOW_ACTIVE_STDOUT = (
    "ActiveState=active\nSubState=waiting\nMainPID=0\n"
    "MemoryCurrent=[not set]\nCPUUsageNSec=[not set]\nLoadState=loaded\n"
)


def _proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """A stand-in for the object create_subprocess_exec awaits to."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    return proc


@pytest.fixture
def runtime_dir(tmp_path, monkeypatch):
    """A runtime directory that exists, exported as XDG_RUNTIME_DIR."""
    path = tmp_path / "run-user"
    path.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(path))
    return str(path)


# ---------------------------------------------------------------------------
# Environment construction
# ---------------------------------------------------------------------------


class TestBuildEnv:
    def test_system_scope_inherits_the_environment(self):
        """System units need nothing injected — None means "inherit"."""
        assert build_env(user=False) is None

    def test_user_scope_keeps_an_existing_runtime_dir(self, runtime_dir):
        env = build_env(user=True)
        assert env is not None
        assert env["XDG_RUNTIME_DIR"] == runtime_dir

    def test_user_scope_derives_a_missing_runtime_dir_from_the_uid(self, monkeypatch):
        """The daemon's environment has only PATH — we supply the default."""
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)

        with patch("sysadmin.utils.systemd.os.path.isdir", return_value=True):
            env = build_env(user=True)

        assert env is not None
        assert env["XDG_RUNTIME_DIR"] == f"/run/user/{os.getuid()}"

    def test_dbus_address_is_not_synthesised(self, runtime_dir, monkeypatch):
        """Verified against the live bus: XDG_RUNTIME_DIR alone is enough.

        systemctl composes ``$XDG_RUNTIME_DIR/bus`` itself, so inventing a
        DBUS_SESSION_BUS_ADDRESS would only add a second thing that can be
        wrong.
        """
        monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)

        env = build_env(user=True)

        assert env is not None
        assert "DBUS_SESSION_BUS_ADDRESS" not in env

    def test_existing_dbus_address_is_passed_through(self, runtime_dir, monkeypatch):
        monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/custom/bus")

        env = build_env(user=True)

        assert env is not None
        assert env["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/custom/bus"

    def test_missing_runtime_dir_raises(self, tmp_path, monkeypatch):
        """No login session → there is genuinely no bus to talk to."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "absent"))

        with pytest.raises(UserBusUnavailableError, match="does not exist"):
            build_env(user=True)

    def test_user_runtime_dir_default(self, monkeypatch):
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        assert user_runtime_dir() == f"/run/user/{os.getuid()}"


# ---------------------------------------------------------------------------
# What actually reaches the subprocess
# ---------------------------------------------------------------------------


class TestSubprocessEnvironment:
    @pytest.mark.asyncio
    async def test_user_scope_passes_xdg_runtime_dir(self, runtime_dir):
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(stdout=SHOW_ACTIVE_STDOUT)
            await get_unit_status("alfred-evaluate.timer", user=True)

        args, kwargs = spawn.call_args
        assert args[:2] == ("systemctl", "--user")
        assert kwargs["env"]["XDG_RUNTIME_DIR"] == runtime_dir

    @pytest.mark.asyncio
    async def test_system_scope_passes_no_explicit_env(self, runtime_dir):
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(stdout=SHOW_ACTIVE_STDOUT)
            await get_unit_status("sysadmin.service", user=False)

        args, kwargs = spawn.call_args
        assert args[:2] == ("systemctl", "show")
        assert kwargs["env"] is None

    @pytest.mark.asyncio
    async def test_control_actions_get_the_user_environment_too(self, runtime_dir):
        """start/stop/restart are as broken as the status check without it."""
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(returncode=0)
            success, message = await restart_unit("alfred-evaluate.timer", user=True)

        assert (success, message) == (True, "ok")
        assert spawn.call_args.kwargs["env"]["XDG_RUNTIME_DIR"] == runtime_dir

    @pytest.mark.asyncio
    async def test_missing_runtime_dir_never_spawns_systemctl(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "absent"))

        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            with pytest.raises(UserBusUnavailableError):
                await get_unit_status("alfred-evaluate.timer", user=True)

        spawn.assert_not_called()


# ---------------------------------------------------------------------------
# An unanswerable query must not look like a dead unit
# ---------------------------------------------------------------------------


class TestGetUnitStatus:
    @pytest.mark.asyncio
    async def test_active_unit_parses(self, runtime_dir):
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(stdout=SHOW_ACTIVE_STDOUT)
            status = await get_unit_status("alfred-evaluate.timer", user=True)

        assert status["is_active"] is True
        assert status["ActiveState"] == "active"
        assert status["SubState"] == "waiting"
        assert status["unit"] == "alfred-evaluate.timer"

    @pytest.mark.asyncio
    async def test_genuinely_inactive_unit_is_still_inactive(self, runtime_dir):
        """The fix must not paper over units that really are down."""
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(
                stdout="ActiveState=inactive\nSubState=dead\nLoadState=loaded\n"
            )
            status = await get_unit_status("redis.service", user=True)

        assert status["is_active"] is False

    @pytest.mark.asyncio
    async def test_bus_failure_raises_instead_of_reporting_inactive(self, runtime_dir):
        """The whole bug in one assertion: no bus → no verdict."""
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(returncode=1, stderr=BUS_FAILURE_STDERR)

            with pytest.raises(UserBusUnavailableError, match="systemd bus"):
                await get_unit_status("alfred-evaluate.timer", user=True)

    @pytest.mark.asyncio
    async def test_non_zero_exit_raises(self, runtime_dir):
        """``systemctl show`` exits 0 even for unknown units, so rc != 0
        means the query itself failed."""
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(returncode=4, stderr="boom")

            with pytest.raises(SystemdQueryError, match="code 4"):
                await get_unit_status("whatever.service")

    @pytest.mark.asyncio
    async def test_empty_output_raises_rather_than_defaulting_to_inactive(
        self, runtime_dir
    ):
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(stdout="")

            with pytest.raises(SystemdQueryError, match="no ActiveState"):
                await get_unit_status("alfred-evaluate.timer", user=True)


class TestIsActive:
    @pytest.mark.asyncio
    async def test_active(self, runtime_dir):
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(stdout="active\n")
            assert await is_active("alfred-evaluate.timer", user=True) is True

    @pytest.mark.asyncio
    async def test_inactive_returns_false(self, runtime_dir):
        # is-active exits 3 for an inactive unit — a normal answer.
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(returncode=3, stdout="inactive\n")
            assert await is_active("redis.service", user=True) is False

    @pytest.mark.asyncio
    async def test_bus_failure_raises_not_false(self, runtime_dir):
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(returncode=1, stderr=BUS_FAILURE_STDERR)

            with pytest.raises(UserBusUnavailableError):
                await is_active("alfred-evaluate.timer", user=True)


class TestControlUnit:
    @pytest.mark.asyncio
    async def test_missing_runtime_dir_reports_a_clear_failure(
        self, tmp_path, monkeypatch
    ):
        """Actions return (success, message) rather than raising."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "absent"))

        success, message = await restart_unit("alfred-evaluate.timer", user=True)

        assert success is False
        assert "user bus unreachable" in message

    @pytest.mark.asyncio
    async def test_failure_surfaces_stderr(self, runtime_dir):
        with patch(_SPAWN, new_callable=AsyncMock) as spawn:
            spawn.return_value = _proc(returncode=1, stderr="Unit not found.")
            success, message = await systemd._control_unit(
                "start", "ghost.service", user=True
            )

        assert success is False
        assert message == "Unit not found."
