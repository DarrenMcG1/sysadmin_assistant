"""The unit files, and the pairs inside them that must not drift apart.

Session 39. ``OnFailure=`` and ``StartLimitBurst=`` are two halves of one
change: with ``Restart=always`` and no burst limit the unit sits in
``activating (auto-restart)`` for ever and **never enters ``failed``**, so
the failure hook is installed, correct, and unreachable. That is the same
silence-reads-as-health shape the escalation ladder was built to fix, and
it is the kind of half-change this repository has shipped before — a
retention row with no ``TABLE_TIMESTAMP_MAP`` entry, an agent name absent
from ``AGENT_NAMES``.

**What these tests cannot see.** They read the files in ``systemd/``, which
is the source deployment copies *from*; nothing here can tell whether
``/etc/systemd/system`` actually matches, because CI has no such directory
and the installed copy needs root to change. Drift between the two is
caught by ``GET /api/units/status``, not by this file.
"""

from pathlib import Path

import pytest

UNITS = Path(__file__).resolve().parents[1] / "systemd"
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _directives(unit: str) -> dict[str, str]:
    """Parse a unit file into directive → value, ignoring section headers.

    Comments are stripped, which is most of these files by volume: the
    reasoning lives in them precisely because a directive cannot carry it.
    """
    values: dict[str, str] = {}
    for raw in (UNITS / unit).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "[")):
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _script_lines(name: str) -> list[str]:
    return (SCRIPTS / name).read_text(encoding="utf-8").splitlines()


def _script_code(name: str) -> str:
    """A script with its comment lines removed.

    These scripts are mostly comments by volume, and every one of them
    names the commands below it. Asserting on the raw text therefore
    matches the explanation as readily as the code.
    """
    return "\n".join(
        line for line in _script_lines(name) if not line.lstrip().startswith("#")
    )


def test_the_unit_directory_is_where_this_thinks_it_is():
    """Guard against every test below passing because the path is wrong."""
    assert UNITS.is_dir(), f"{UNITS} not found — adjust parents[1]"
    assert (UNITS / "sysadmin.service").is_file()


class TestFailureIsReportable:
    def test_restart_always_is_paired_with_a_burst_limit(self):
        """Without the limit, `failed` is unreachable and no hook can fire."""
        directives = _directives("sysadmin.service")
        assert directives.get("Restart") == "always"
        assert "StartLimitBurst" in directives, (
            "Restart=always with no StartLimitBurst never reaches `failed`, "
            "so OnFailure= and every `systemctl is-failed` check are dead code"
        )
        assert int(directives["StartLimitBurst"]) > 0

    def test_the_burst_window_outlasts_the_restart_delay(self):
        """A window shorter than the delays it counts can never be tripped.

        With RestartSec=10 and a burst of 5, roughly 50 seconds of loop is
        needed; a StartLimitIntervalSec below that measures nothing and the
        unit would restart for ever while looking limited.
        """
        directives = _directives("sysadmin.service")
        window = int(directives["StartLimitIntervalSec"])
        burst = int(directives["StartLimitBurst"])
        delay = int(directives["RestartSec"])
        assert window > burst * delay, (
            f"{burst} restarts {delay}s apart need more than {burst * delay}s, "
            f"but the window is {window}s — the limit can never trip"
        )

    def test_onfailure_names_a_unit_that_exists_here(self):
        """A hook pointing at a missing unit fails silently at the worst moment."""
        target = _directives("sysadmin.service")["OnFailure"]
        assert (UNITS / target).is_file(), f"OnFailure={target} has no unit file"

    def test_the_handler_has_no_failure_handler_of_its_own(self):
        """A failure handler with a failure handler is a loop."""
        assert "OnFailure" not in _directives("sysadmin-failed.service")

    def test_the_handler_is_a_oneshot_that_cannot_hang(self):
        """A handler that blocks holds a job open while the fault goes unsaid."""
        directives = _directives("sysadmin-failed.service")
        assert directives["Type"] == "oneshot"
        assert 0 < int(directives["TimeoutStartSec"]) <= 60

    def test_the_handler_runs_a_script_that_exists_and_is_executable(self):
        exec_start = _directives("sysadmin-failed.service")["ExecStart"]
        script = Path(exec_start.split()[0])
        assert script.is_file(), f"ExecStart script missing: {script}"
        assert script.stat().st_mode & 0o111, f"not executable: {script}"

    @pytest.mark.parametrize(
        "flag", ["--urgency=critical", "--expire-time=0"]
    )
    def test_the_notification_persists_rather_than_expiring(self, flag):
        """The whole point of the session, in two flags.

        The reported failure was a transient toast nobody was in the room
        to see. ``--expire-time=0`` is what makes the notification still be
        there on return; without it this handler reproduces the miss.
        """
        assert flag in _script_code("notify-unit-failed.sh")

    def test_the_broker_credential_arrives_by_loadcredential_not_env(self):
        """ADR-0003: the MQTT password reaches this service as a systemd
        credential, never as configuration.

        ``config.yaml`` is tracked in git and has never held a secret, and
        this repository reads no environment variables — so the only door
        left is ``LoadCredential=``, which delivers the password into
        ``$CREDENTIALS_DIRECTORY`` without touching git, the environment,
        or the process list. The id must stay ``mqtt``: the publisher code
        will read ``$CREDENTIALS_DIRECTORY/mqtt`` by that name.
        """
        directives = _directives("sysadmin.service")
        credential = directives.get("LoadCredential", "")
        cred_id, _, source = credential.partition(":")
        assert cred_id == "mqtt", f"LoadCredential id must be 'mqtt', got {credential!r}"
        assert source.startswith("/"), "credential source must be an absolute path"
        assert "EnvironmentFile" not in directives, (
            "an EnvironmentFile= would reintroduce the env-var door this "
            "repository's conventions keep closed"
        )

    def test_the_handler_writes_to_the_journal_before_the_session_bus(self):
        """Journald is the destination that does not need anyone logged in.

        If the notification is attempted first and the script exits on
        failure, a failure that happens while nobody is logged in is
        recorded nowhere at all.

        Comment lines are stripped first. The script explains both
        commands in prose above the code, so an ordering assertion over
        the raw text compares where they are *discussed* rather than where
        they run — which is how this test failed on its first outing while
        the script was correct.
        """
        code = _script_code("notify-unit-failed.sh")
        assert code.index("systemd-cat") < code.index("notify-send")
