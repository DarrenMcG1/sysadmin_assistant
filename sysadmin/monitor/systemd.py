"""Systemd unit status helpers via subprocess.

All helpers accept ``user=True`` to target *user* units
(``systemctl --user ...``) instead of system units.

The user session bus
--------------------
``systemctl --user`` talks to the per-user session bus, which it locates
through ``XDG_RUNTIME_DIR`` (it composes ``$XDG_RUNTIME_DIR/bus`` itself)
or an explicit ``DBUS_SESSION_BUS_ADDRESS``.  A systemd *service* unit is
started with a near-empty environment — ``sysadmin.service`` has only
``PATH`` — so neither variable is set and every ``--user`` call fails with
"Failed to connect to user scope bus".  The old code read that empty
output as "the unit is not active" and reported a perfectly healthy timer
as ``critical`` (SNAG-SYSD-001).  It never reproduced interactively,
because an interactive shell always has ``XDG_RUNTIME_DIR``.

We therefore inject ``XDG_RUNTIME_DIR`` into the subprocess environment
for user-scope calls, defaulting to ``/run/user/<uid>``.
``DBUS_SESSION_BUS_ADDRESS`` is deliberately **not** derived: it was
verified against the live session bus that ``XDG_RUNTIME_DIR`` alone is
sufficient, and inventing a second address only creates a second thing
that can be wrong.

When the runtime directory does not exist at all (no login session, no
lingering), the bus is genuinely unreachable — that raises
:class:`UserBusUnavailableError` so callers can report "cannot determine"
instead of inventing a failure for a unit they never managed to query.

``journalctl --user`` is unaffected: it reads journal files directly and
needs no bus, so log aggregation deliberately keeps inheriting the
environment untouched.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

#: systemd's wording when it cannot reach a bus, in any of its variants
#: ("Failed to connect to user scope bus via local transport: ...",
#: "Failed to connect to bus: ...").
_BUS_FAILURE_MARKER = "failed to connect to"


class SystemdQueryError(RuntimeError):
    """systemctl could not answer the question.

    Distinct from "the unit is down" — the query itself did not succeed,
    so nothing may be concluded about the unit's state.
    """


class UserBusUnavailableError(SystemdQueryError):
    """The systemd *user* bus could not be reached from this process."""


def _base_cmd(user: bool) -> list[str]:
    """Build the systemctl command prefix for system or user scope."""
    return ["systemctl", "--user"] if user else ["systemctl"]


def user_runtime_dir() -> str:
    """The XDG runtime directory for this process's user."""
    return os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"


def build_env(user: bool) -> dict[str, str] | None:
    """Environment for a systemctl subprocess.

    Returns ``None`` for system scope — inherit the parent environment
    unchanged.  For user scope, returns a copy of the environment with
    ``XDG_RUNTIME_DIR`` guaranteed present so ``systemctl --user`` can
    find the session bus.

    Raises:
        UserBusUnavailableError: the runtime directory does not exist, so
            there is no user bus to connect to.
    """
    if not user:
        return None

    runtime_dir = user_runtime_dir()
    if not os.path.isdir(runtime_dir):
        raise UserBusUnavailableError(
            f"systemd user bus unreachable: XDG_RUNTIME_DIR {runtime_dir!r} "
            "does not exist (no login session, and lingering is not enabled)"
        )

    env = dict(os.environ)
    env["XDG_RUNTIME_DIR"] = runtime_dir
    return env


async def _run(args: list[str], user: bool) -> tuple[int, str, str]:
    """Run ``systemctl [--user] <args>``. Returns (returncode, stdout, stderr)."""
    env = build_env(user)
    proc = await asyncio.create_subprocess_exec(
        *_base_cmd(user), *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(), stderr.decode()


def _raise_on_bus_failure(stderr: str, description: str, user: bool) -> None:
    """Turn systemd's "cannot reach the bus" message into an exception."""
    if _BUS_FAILURE_MARKER not in stderr.lower():
        return
    message = f"{description} could not reach the systemd bus: {stderr.strip()}"
    if user:
        raise UserBusUnavailableError(message)
    raise SystemdQueryError(message)


async def is_active(unit: str, user: bool = False) -> bool:
    """Check if a systemd unit is active.

    Raises:
        SystemdQueryError: systemctl could not be queried at all — an
            inactive unit returns ``False``, an unanswerable question does
            not silently look the same.
    """
    # is-active exits non-zero for an inactive unit, so the return code
    # carries no signal here — the stderr message is what distinguishes a
    # failed query from a down unit.
    _, stdout, stderr = await _run(["is-active", unit], user)
    _raise_on_bus_failure(stderr, f"is-active {unit}", user)
    return stdout.strip() == "active"


async def get_unit_status(unit: str, user: bool = False) -> dict:
    """Get detailed status of a systemd unit.

    Raises:
        SystemdQueryError: systemctl could not be queried, or answered
            without an ``ActiveState``.  ``systemctl show`` exits 0 even
            for a unit that does not exist (``LoadState=not-found``), so a
            non-zero exit really does mean the query failed.
    """
    # The timer properties are requested for every unit, not just timers:
    # systemctl omits the ones that do not apply, so asking costs nothing
    # and a second call to fetch them would double the subprocess count
    # for the estate's six timers.  ``Result`` is meaningful for services
    # too — it is how a oneshot reports the outcome of its last run.
    #
    # ``Unit`` is a *timer* property naming the unit the timer starts.
    # It is asked for here rather than derived by stripping ``.timer``
    # and appending ``.service`` because that derivation is a second
    # statement of a fact systemd already publishes, and systemd does not
    # require the two names to correspond — ``Unit=`` may name anything.
    # SNAG-SYSD-005.
    props = [
        "ActiveState", "SubState", "MainPID",
        "MemoryCurrent", "CPUUsageNSec", "LoadState",
        "LastTriggerUSec", "NextElapseUSecRealtime", "Result",
        "Unit", "ExecMainStatus",
    ]
    prop_args = ",".join(props)

    returncode, stdout, stderr = await _run(
        ["show", unit, f"--property={prop_args}"], user
    )
    _raise_on_bus_failure(stderr, f"show {unit}", user)
    if returncode != 0:
        raise SystemdQueryError(
            f"systemctl show {unit} exited with code {returncode}: "
            f"{stderr.strip() or 'no output'}"
        )

    result: dict = {"unit": unit}
    for line in stdout.strip().split("\n"):
        if "=" in line:
            key, _, value = line.partition("=")
            result[key] = value

    if "ActiveState" not in result:
        raise SystemdQueryError(
            f"systemctl show {unit} returned no ActiveState — cannot "
            "determine whether the unit is running"
        )

    result["is_active"] = result.get("ActiveState") == "active"
    return result


async def _control_unit(action: str, unit: str, user: bool = False) -> tuple[bool, str]:
    """Run ``systemctl [--user] <action> <unit>`` and return (success, message)."""
    try:
        returncode, _, stderr = await _run([action, unit], user)
    except SystemdQueryError as e:
        logger.warning("systemctl %s %s failed: %s", action, unit, e)
        return False, str(e)

    if returncode == 0:
        return True, "ok"
    msg = stderr.strip() or f"systemctl {action} exited with code {returncode}"
    logger.warning("systemctl %s %s failed: %s", action, unit, msg)
    return False, msg


async def restart_unit(unit: str, user: bool = False) -> tuple[bool, str]:
    """Restart a systemd unit.  Returns (success, message)."""
    return await _control_unit("restart", unit, user)


async def start_unit(unit: str, user: bool = False) -> tuple[bool, str]:
    """Start a systemd unit.  Returns (success, message)."""
    return await _control_unit("start", unit, user)


async def stop_unit(unit: str, user: bool = False) -> tuple[bool, str]:
    """Stop a systemd unit.  Returns (success, message)."""
    return await _control_unit("stop", unit, user)
