"""Which games are running, read from ``/proc`` (ADR-0016 §2).

Pure apart from :func:`read_processes` and :func:`steam_app_name`, which
read files; everything between them takes plain values so a test can
hand it a recorded process table.

Three rules, two of them not what ADR-0016 §2 literally says:

1. **A Steam game is keyed on its AppId, not on one process.**  §2 says
   the span lasts as long as the reaper lives.  Steam's own
   ``gameprocess_log`` for Deadlock on 2026-10-14 shows *two* processes
   whose argv carry ``SteamLaunch AppId=1422450``: the
   ``steam-launch-wrapper`` (which has the reaper's whole command line
   as its arguments) and the reaper itself.  Keyed on a PID, one game
   would open two spans.  Keyed on the AppId it opens one, and it lasts
   while any process carrying that AppId lives.
2. **``SteamLaunch`` and ``AppId=<n>`` are two argv entries.**
   ``/proc/<pid>/cmdline`` is NUL-separated, so the pair is matched as
   adjacent arguments rather than as a substring of a joined line.  The
   Proton and Steam Linux Runtime paths appear later in the same argv
   and never in that position, which is why they need no exclusion.
3. **A listed executable inside a Steam launch is that launch's game.**
   If the owner lists ``deadlock.exe`` and Steam launched it, the Steam
   span already covers it; a second span for the same minutes would be
   counted twice by anything that sums them.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

STEAM_LAUNCH = "SteamLaunch"
_APPID = re.compile(r"AppId=(\d+)\Z")

MATCHED_BY_STEAM = "steam_appid"
MATCHED_BY_EXECUTABLE = "executable"

#: Names an AppId.  Injected so a test needs no Steam library.
_NameLookup = Callable[[int], str]


@dataclass(frozen=True)
class Process:
    """One ``/proc`` entry, as much of it as detection reads."""

    pid: int
    ppid: int
    comm: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class Sighting:
    """One game seen on one poll."""

    game: str
    matched_by: str
    appid: int | None
    executable: str | None
    #: The outermost matching process — the one whose parent does not match.
    pid: int
    #: Every process in the game's trees: the matching processes and all
    #: their descendants.  The focus check asks whether the active
    #: window's PID is in here, because Proton runs the game as a child of
    #: the reaper (ADR-0016 §3).
    pids: frozenset[int]

    @property
    def key(self) -> tuple[str, int | None, str | None]:
        """What makes two polls' sightings the same game."""
        return (self.matched_by, self.appid, self.executable)


def steam_appid(argv: Sequence[str]) -> int | None:
    """The AppId when ``argv`` holds ``SteamLaunch`` then ``AppId=<n>``."""
    for i, arg in enumerate(argv[:-1]):
        if arg == STEAM_LAUNCH:
            match = _APPID.match(argv[i + 1])
            if match:
                return int(match.group(1))
    return None


def executable_name(process: Process) -> str:
    """The basename of argv[0], split on both separators (Wine passes ``Z:\\…``)."""
    if not process.argv or not process.argv[0]:
        return process.comm
    return re.split(r"[/\\]", process.argv[0])[-1]


def _descendants(roots: Iterable[int], children: Mapping[int, list[int]]) -> set[int]:
    seen: set[int] = set()
    stack = list(roots)
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stack.extend(children.get(pid, ()))
    return seen


def detect_games(
    processes: Sequence[Process],
    games: Mapping[str, str],
    steam_name: _NameLookup,
) -> list[Sighting]:
    """Every game in ``processes``, one sighting per game.

    ``games`` is the owner's list, executable name to game name.
    ``steam_name`` names an AppId, and is only called for AppIds seen.
    """
    children: dict[int, list[int]] = {}
    for proc in processes:
        children.setdefault(proc.ppid, []).append(proc.pid)

    steam: dict[int, list[Process]] = {}
    for proc in processes:
        appid = steam_appid(proc.argv)
        if appid is not None:
            steam.setdefault(appid, []).append(proc)

    sightings: list[Sighting] = []
    steam_trees: set[int] = set()
    for appid, matched in sorted(steam.items()):
        tree = _descendants((p.pid for p in matched), children)
        steam_trees |= tree
        sightings.append(
            Sighting(
                game=steam_name(appid),
                matched_by=MATCHED_BY_STEAM,
                appid=appid,
                executable=None,
                pid=_outermost(matched),
                pids=frozenset(tree),
            )
        )

    listed: dict[str, list[Process]] = {}
    for proc in processes:
        if proc.pid in steam_trees:
            continue
        for name in {executable_name(proc), proc.comm}:
            if name in games:
                listed.setdefault(name, []).append(proc)
                break
    for name, matched in sorted(listed.items()):
        sightings.append(
            Sighting(
                game=games[name],
                matched_by=MATCHED_BY_EXECUTABLE,
                appid=None,
                executable=name,
                pid=_outermost(matched),
                pids=frozenset(_descendants((p.pid for p in matched), children)),
            )
        )
    return sightings


def _outermost(matched: Sequence[Process]) -> int:
    pids = {p.pid for p in matched}
    roots = [p.pid for p in matched if p.ppid not in pids]
    return min(roots or pids)


# --- The two reads ---


def read_processes(proc_root: Path = Path("/proc")) -> list[Process]:
    """Every process this user can read.  A process that exits mid-read is skipped."""
    processes: list[Process] = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        # comm is parenthesised and may itself hold spaces or ')'.
        open_at, close_at = stat.find("("), stat.rfind(")")
        if open_at < 0 or close_at < 0:
            continue
        fields = stat[close_at + 2 :].split()
        if len(fields) < 2:
            continue
        argv = tuple(
            part.decode(errors="replace") for part in raw.split(b"\0") if part
        )
        processes.append(
            Process(
                pid=int(entry.name),
                ppid=int(fields[1]),
                comm=stat[open_at + 1 : close_at],
                argv=argv,
            )
        )
    return processes


_VDF_PATH = re.compile(r'"path"\s+"((?:[^"\\]|\\.)*)"')
_VDF_NAME = re.compile(r'"name"\s+"((?:[^"\\]|\\.)*)"')


def _vdf_unescape(value: str) -> str:
    return re.sub(r"\\(.)", r"\1", value)


def steam_libraries(steam_root: Path) -> list[Path]:
    """The libraries ``libraryfolders.vdf`` lists, or the root alone without it."""
    try:
        text = (steam_root / "steamapps" / "libraryfolders.vdf").read_text(
            errors="replace"
        )
    except OSError:
        return [steam_root]
    libraries = [Path(_vdf_unescape(m)) for m in _VDF_PATH.findall(text)]
    return libraries or [steam_root]


def steam_app_name(appid: int, libraries: Sequence[Path]) -> str:
    """``"name"`` from the app's manifest, or ``steam:<n>`` — never dropped."""
    for library in libraries:
        try:
            text = (library / "steamapps" / f"appmanifest_{appid}.acf").read_text(
                errors="replace"
            )
        except OSError:
            continue
        match = _VDF_NAME.search(text)
        if match:
            return _vdf_unescape(match.group(1))
    return f"steam:{appid}"


def scan(steam_root: Path, games: Mapping[str, str]) -> list[Sighting]:
    """One poll's reads: the process table, then names for what it found."""
    processes = read_processes()
    libraries: list[Path] | None = None

    def name(appid: int) -> str:
        nonlocal libraries
        if libraries is None:
            libraries = steam_libraries(steam_root)
        return steam_app_name(appid, libraries)

    return detect_games(processes, games, name)
