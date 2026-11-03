"""The pre-push gate's non-``box`` half really cannot see the box.

``scripts/pytest-without-the-box.sh`` runs ``-m "not box"`` the way
GitHub's runner meets it, so a test that reads the box without the mark
fails at push rather than in CI. That is only true for what the script
hides, and until ``SNAG-TEST-020`` it hid the network alone: the Claude
settings, the unit files, ``systemctl --user`` and the journal were all
still the box's, and a probe reading each passed inside the blind.

So this drives the real script at a probe file whose every test asserts
an absence, one per thing the ``box`` mark names in ``pyproject.toml``.
The premise runs first and outside the blind: each probe is worth
something only if the thing it says is absent is present out here.
Remove a mount from the script and the probe for it passes outside and
fails inside, which is the red this file exists to give.
"""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "pytest-without-the-box.sh"
HOME = Path.home()

SETTINGS = HOME / ".claude" / "settings.json"
UNIT_DIRS = (HOME / ".config" / "systemd" / "user", Path("/etc/systemd/system"))
DATABASE = ("127.0.0.1", 5432)


def _database_answers() -> bool:
    try:
        with socket.create_connection(DATABASE, timeout=2):
            return True
    except OSError:
        return False


def _systemctl_user_answers() -> bool:
    result = subprocess.run(
        ["systemctl", "--user", "show", "-p", "Version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


def _journal_lines(*scope: str) -> str:
    result = subprocess.run(
        ["journalctl", *scope, "-q", "-n", "1", "--no-pager"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


# Each test is an absence the blind must produce. The probe imports
# nothing from this repository, so it runs whatever the suite's state.
PROBE = f'''
import socket
import subprocess
from pathlib import Path


def test_the_database_refuses():
    try:
        socket.create_connection({DATABASE!r}, timeout=2).close()
    except OSError:
        return
    raise AssertionError("the database answered inside the blind")


def test_the_claude_settings_are_absent():
    assert not Path({str(SETTINGS)!r}).exists()


def test_the_user_unit_files_are_absent():
    assert not list(Path({str(UNIT_DIRS[0])!r}).iterdir())


def test_the_system_unit_files_are_absent():
    assert not list(Path({str(UNIT_DIRS[1])!r}).iterdir())


def test_systemctl_user_cannot_connect():
    result = subprocess.run(
        ["systemctl", "--user", "show", "-p", "Version"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0, result.stdout


def test_the_system_journal_is_empty():
    result = subprocess.run(
        ["journalctl", "-q", "-n", "1", "--no-pager"],
        capture_output=True, text=True, timeout=10,
    )
    assert not result.stdout.strip(), result.stdout


def test_the_user_journal_is_empty():
    result = subprocess.run(
        ["journalctl", "--user", "-q", "-n", "1", "--no-pager"],
        capture_output=True, text=True, timeout=10,
    )
    assert not result.stdout.strip(), result.stdout
'''

PROBE_COUNT = PROBE.count("\ndef test_")


@pytest.mark.box
@pytest.mark.premise
class TestTheBoxIsVisibleOutsideTheBlind:
    """Without these, an absence inside the blind proves nothing."""

    def test_the_database_answers(self):
        assert _database_answers(), f"nothing listens on {DATABASE}"

    def test_the_claude_settings_exist(self):
        assert SETTINGS.is_file(), SETTINGS

    @pytest.mark.parametrize("directory", UNIT_DIRS, ids=lambda p: str(p))
    def test_the_unit_directory_holds_units(self, directory: Path):
        assert list(directory.iterdir()), f"{directory} is empty"

    def test_systemctl_user_answers(self):
        assert _systemctl_user_answers()

    @pytest.mark.parametrize("scope", [(), ("--user",)], ids=["system", "user"])
    def test_the_journal_has_records(self, scope: tuple[str, ...]):
        assert _journal_lines(*scope), f"journalctl {' '.join(scope)} read nothing"


@pytest.mark.box
class TestTheBlindHidesEachOne:
    def test_every_probe_meets_an_absence(self, tmp_path: Path):
        probe = tmp_path / "test_probe.py"
        probe.write_text(PROBE)
        result = subprocess.run(
            [str(SCRIPT), "-p", "no:cacheprovider", "-rf", str(probe)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        # Seven passed and none deselected: a probe the script's `-m` had
        # filtered out would pass this vacuously.
        assert f"{PROBE_COUNT} passed" in output, output
        assert "deselected" not in output, output

    def test_the_probe_counts_every_absence(self):
        assert PROBE_COUNT == 7
