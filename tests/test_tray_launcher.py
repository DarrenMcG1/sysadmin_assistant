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


def _installed_sysadmin_user_units() -> list[Path]:
    try:
        return sorted(
            p for p in USER_UNIT_DIR.iterdir() if p.name.startswith("sysadmin") and p.is_file()
        )
    except OSError:
        return []


class TestTheRepositoryShipsOneLauncher:
    def test_the_tray_unit_is_tracked(self):
        assert TRAY_UNIT.is_file()

    def test_no_tracked_desktop_entry_launches_the_tray(self):
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


@pytest.mark.skipif(
    not _installed_sysadmin_user_units(),
    reason="no sysadmin user unit is installed here (CI)",
)
class TestTheBoxRunsWhatGitHolds:
    def test_every_installed_user_unit_is_the_tracked_one(self):
        drifted = [
            unit.name
            for unit in _installed_sysadmin_user_units()
            if not (UNIT_DIR / unit.name).is_file()
            or (UNIT_DIR / unit.name).read_bytes() != unit.read_bytes()
        ]
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
