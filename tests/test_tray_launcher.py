"""The tray has one launcher, and it is the one in git.

Estate message ``633d1a86`` (dotfiles, 2026-09-30) found
``~/.config/systemd/user/sysadmin-tray.service`` matching no file in any
repository, while this one versioned ``systemd/sysadmin-tray.desktop`` and
``scripts/setup-systemd.sh`` installed only that.  Measured 2026-10-01: the
unit alone launched the tray — one process, inside the unit's cgroup, and no
autostart entry in ``~/.config/autostart`` or ``/etc/xdg/autostart``.  The
unit had been hand-written on 2026-08-11 and never committed; the
``.desktop`` file had been in git since 2026-02-07 and never installed.

Two launchers are worse than a stale one: the tray has no single-instance
guard, Plasma turns an XDG autostart entry into its own
``app-…@autostart.service``, and two trays announce every alert twice.  So
the repository half is always checked and the box half skips where nothing
is installed (CI).

The same drift check covers the system units in ``/etc/systemd/system``.
Until Session 306 it read only the user unit directory. That is how the
installed ``sysadmin.service`` kept ``After=… ollama.service`` from
2026-09-02, when ``3f5af0d`` dropped it from git, until the owner redeployed
it on 2026-10-01.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
UNIT_DIR = REPO / "systemd"
SETUP_SCRIPT = REPO / "scripts" / "setup-systemd.sh"
TRAY_UNIT = UNIT_DIR / "sysadmin-tray.service"

USER_UNIT_DIR = Path.home() / ".config/systemd/user"
SYSTEM_UNIT_DIR = Path("/etc/systemd/system")
AUTOSTART_DIRS = (Path.home() / ".config/autostart", Path("/etc/xdg/autostart"))

#: Every ``$PROJECT_DIR/systemd/<file>`` the setup script copies from.
SCRIPT_SOURCE_RE = re.compile(r"\$PROJECT_DIR/systemd/([\w.@-]+)")


def _launches_tray(desktop: Path) -> bool:
    """Whether an XDG ``.desktop`` entry's ``Exec=`` runs ``sysadmin-tray``."""
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read_string(desktop.read_text(encoding="utf-8", errors="replace"))
    except (OSError, configparser.Error):
        return False
    exec_line = parser.get("Desktop Entry", "Exec", fallback="")
    return any(Path(word).name == "sysadmin-tray" for word in exec_line.split())


def _installed_sysadmin_units(directory: Path) -> list[Path]:
    """Every ``sysadmin*`` regular file in a unit directory.

    ``is_file()`` leaves out a ``sysadmin.service.d/`` drop-in directory and
    a mask, which is a symlink to ``/dev/null``.
    """
    try:
        return sorted(
            p for p in directory.iterdir() if p.name.startswith("sysadmin") and p.is_file()
        )
    except OSError:
        return []


def _drifted(installed: list[Path]) -> list[str]:
    """Installed units that match no file in ``systemd/``, or whose bytes differ from it."""
    return [
        unit.name
        for unit in installed
        if not (UNIT_DIR / unit.name).is_file()
        or (UNIT_DIR / unit.name).read_bytes() != unit.read_bytes()
    ]


class TestTheRepositoryShipsOneLauncher:
    def test_the_tray_unit_is_tracked(self):
        assert TRAY_UNIT.is_file()

    def test_no_tracked_desktop_entry_launches_the_tray(self):
        # may-not-turn: Session 304 deleted the last tracked .desktop file, so the glob
        # finds nothing on a healthy tree; test_the_detector_sees_an_autostart_entry
        # proves the filter fires
        offenders = [
            p.name
            for p in REPO.rglob("*.desktop")
            if ".venv" not in p.parts and _launches_tray(p)
        ]
        assert offenders == [], f"a second tray launcher is tracked: {offenders}"

    def test_the_detector_sees_an_autostart_entry(self, tmp_path):
        """Negative control: the retired file's own ``Exec=`` line is read as a launcher."""
        entry = tmp_path / "sysadmin-tray.desktop"
        entry.write_text(
            "[Desktop Entry]\nType=Application\n"
            "Exec=/home/gaddi/projects/sysadmin_assistant/.venv/bin/sysadmin-tray\n"
        )
        assert _launches_tray(entry)

    def test_every_file_the_setup_script_copies_exists(self):
        sources = SCRIPT_SOURCE_RE.findall(SETUP_SCRIPT.read_text(encoding="utf-8"))
        assert "sysadmin-tray.service" in sources
        missing = [name for name in sources if not (UNIT_DIR / name).is_file()]
        assert missing == []

    def test_the_drift_check_sees_a_lagging_and_an_untracked_unit(self, tmp_path):
        """Negative control, runnable in CI: one stale copy, one copy matching git, one stray."""
        tracked = (UNIT_DIR / "sysadmin.service").read_bytes()
        (tmp_path / "sysadmin.service").write_bytes(tracked + b"After=ollama.service\n")
        (tmp_path / "sysadmin-tray.service").write_bytes(
            (UNIT_DIR / "sysadmin-tray.service").read_bytes()
        )
        (tmp_path / "sysadmin-hand-written.service").write_text("[Unit]\n")
        assert _drifted(_installed_sysadmin_units(tmp_path)) == [
            "sysadmin-hand-written.service",
            "sysadmin.service",
        ]


@pytest.mark.skipif(
    not _installed_sysadmin_units(USER_UNIT_DIR),
    reason="no sysadmin user unit is installed here (CI)",
)
class TestTheBoxRunsWhatGitHolds:
    def test_every_installed_user_unit_is_the_tracked_one(self):
        drifted = _drifted(_installed_sysadmin_units(USER_UNIT_DIR))
        assert drifted == [], (
            f"installed user units in no file of systemd/, or differing from it: {drifted}"
        )

    def test_no_autostart_entry_launches_the_tray(self):
        entries = [
            str(p)
            for directory in AUTOSTART_DIRS
            if directory.is_dir()
            for p in directory.glob("*.desktop")
            if _launches_tray(p)
        ]
        assert entries == [], f"the tray would start twice at login: {entries}"


@pytest.mark.skipif(
    not _installed_sysadmin_units(SYSTEM_UNIT_DIR),
    reason="no sysadmin system unit is installed here (CI)",
)
class TestTheSystemRunsWhatGitHolds:
    def test_every_installed_system_unit_is_the_tracked_one(self):
        drifted = _drifted(_installed_sysadmin_units(SYSTEM_UNIT_DIR))
        assert drifted == [], (
            f"installed system units in no file of systemd/, or differing from it: {drifted}"
            " — redeploy with `sudo ./scripts/setup-systemd.sh`"
        )
