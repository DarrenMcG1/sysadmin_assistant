"""The game detector: what it sees in ``/proc`` and how polls become spans (ADR-0016)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.core.config import AppConfig
from sysadmin.core.jobs import plan_jobs
from sysadmin.games import focus as focus_module
from sysadmin.games.agent import (
    FOCUSED,
    UNKNOWN,
    GameDetectorAgent,
    apply_poll,
    focus_state,
)
from sysadmin.games.detect import (
    MATCHED_BY_EXECUTABLE,
    MATCHED_BY_STEAM,
    Process,
    Sighting,
    detect_games,
    read_processes,
    steam_app_name,
    steam_appid,
    steam_libraries,
)
from sysadmin.games.focus import (
    NO_WINDOW,
    PLUGIN_NAME,
    kwin_focus_probe,
    parse_line,
    parse_load_id,
    script_text,
)
from sysadmin.games.models import GameFocus, GameSpan

STEAM = "/home/gaddi/.local/share/Steam"

#: The reaper's argv for Deadlock, from Steam's ``console_log.txt`` on
#: 2026-10-14 ("Game process added : AppID 1422450 …"), split where
#: ``/proc/<pid>/cmdline`` puts its NULs.  The Proton and Steam Linux
#: Runtime paths are in it, after the ``AppId=`` this matches on.
REAPER_ARGV = (
    f"{STEAM}/ubuntu12_32/reaper",
    "SteamLaunch",
    "AppId=1422450",
    "--",
    f"{STEAM}/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point",
    "--verb=waitforexitandrun",
    "--",
    f"{STEAM}/steamapps/common/Proton - Experimental/proton",
    "waitforexitandrun",
    f"{STEAM}/steamapps/common/Deadlock/game/bin/win64/deadlock.exe",
    "-steam",
    "-console",
)
#: The wrapper carries the reaper's whole line as its arguments — which
#: is why a span is keyed on the AppId and not on a process.
WRAPPER_ARGV = (f"{STEAM}/ubuntu12_32/steam-launch-wrapper", "--", *REAPER_ARGV)


def _proc(pid, ppid, argv, comm=None):
    return Process(pid=pid, ppid=ppid, comm=comm or argv[0].rsplit("/", 1)[-1][:15], argv=argv)


def _deadlock_tree():
    """steam → wrapper → reaper → runtime → proton → the game."""
    return [
        _proc(100, 1, (f"{STEAM}/ubuntu12_32/steam",)),
        _proc(200, 100, WRAPPER_ARGV),
        _proc(201, 200, REAPER_ARGV),
        _proc(202, 201, (f"{STEAM}/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point",)),
        _proc(203, 202, ("python3", "proton", "waitforexitandrun")),
        _proc(204, 203, ("Z:\\home\\gaddi\\Deadlock\\deadlock.exe",), comm="deadlock.exe"),
        _proc(300, 1, ("/usr/bin/Discord",)),
    ]


def _names(appid):
    return {1422450: "Deadlock"}.get(appid, f"steam:{appid}")


class TestSteamDetection:
    def test_the_recorded_reaper_and_wrapper_both_carry_the_appid(self):
        assert steam_appid(REAPER_ARGV) == 1422450
        assert steam_appid(WRAPPER_ARGV) == 1422450

    def test_the_runtimes_never_carry_steamlaunch_themselves(self):
        """ADR-0016 §2: Proton and the Runtime need no exclusion."""
        for argv in (
            (
                f"{STEAM}/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point",
                "--verb=waitforexitandrun",
            ),
            (f"{STEAM}/steamapps/common/Proton - Experimental/proton", "waitforexitandrun"),
        ):
            assert steam_appid(argv) is None

    def test_a_substring_is_not_a_launch(self):
        assert steam_appid(("grep", "SteamLaunch AppId=570")) is None
        assert steam_appid(("SteamLaunch",)) is None

    def test_one_game_is_one_sighting_from_the_outermost_process(self):
        [sighting] = detect_games(_deadlock_tree(), {}, _names)
        assert sighting.game == "Deadlock"
        assert sighting.matched_by == MATCHED_BY_STEAM
        assert sighting.appid == 1422450
        assert sighting.executable is None
        assert sighting.pid == 200
        # The window belongs to the game, three levels below the reaper.
        assert {200, 201, 202, 203, 204} == set(sighting.pids)
        assert 300 not in sighting.pids

    def test_discord_and_steam_itself_are_never_games(self):
        assert detect_games(_deadlock_tree()[:1] + _deadlock_tree()[-1:], {}, _names) == []


class TestTheOwnersList:
    def test_a_listed_executable_is_a_game(self):
        procs = [
            _proc(10, 1, ("/opt/factorio/bin/x64/factorio",)),
            _proc(11, 10, ("factorio-worker",)),
        ]
        [sighting] = detect_games(procs, {"factorio": "Factorio"}, _names)
        assert sighting.matched_by == MATCHED_BY_EXECUTABLE
        assert sighting.game == "Factorio"
        assert (sighting.executable, sighting.appid) == ("factorio", None)
        assert sighting.pids == frozenset({10, 11})

    def test_a_wine_path_is_matched_by_its_basename(self):
        procs = [_proc(10, 1, ("C:\\Games\\Thing\\thing.exe",), comm="thing.exe")]
        [sighting] = detect_games(procs, {"thing.exe": "Thing"}, _names)
        assert sighting.executable == "thing.exe"

    def test_a_listed_executable_inside_a_steam_launch_is_not_counted_twice(self):
        [sighting] = detect_games(_deadlock_tree(), {"deadlock.exe": "Deadlock"}, _names)
        assert sighting.matched_by == MATCHED_BY_STEAM


class TestTheReads:
    def test_proc_entries_are_parsed_and_unreadable_ones_skipped(self, tmp_path):
        game = tmp_path / "4242"
        game.mkdir()
        # comm may hold spaces and a ')' — the split is at the last one.
        (game / "stat").write_text("4242 (Game) (x) S 17 4242 4242 0 -1\n")
        (game / "cmdline").write_bytes(b"SteamLaunch\0AppId=570\0")
        (tmp_path / "self").mkdir()
        (tmp_path / "99").mkdir()  # exited between listing and reading
        [proc] = read_processes(tmp_path)
        assert (proc.pid, proc.ppid, proc.comm) == (4242, 17, "Game) (x")
        assert proc.argv == ("SteamLaunch", "AppId=570")

    def test_names_come_from_whichever_library_holds_the_manifest(self, tmp_path):
        root, other = tmp_path / "Steam", tmp_path / "games"
        (root / "steamapps").mkdir(parents=True)
        (other / "steamapps").mkdir(parents=True)
        (root / "steamapps" / "libraryfolders.vdf").write_text(
            f'"libraryfolders"\n{{\n\t"0"\n\t{{\n\t\t"path"\t\t"{root}"\n\t}}\n'
            f'\t"1"\n\t{{\n\t\t"path"\t\t"{other}"\n\t}}\n}}\n'
        )
        (other / "steamapps" / "appmanifest_1245620.acf").write_text(
            '"AppState"\n{\n\t"appid"\t\t"1245620"\n\t"name"\t\t"ELDEN RING \\"NIGHTREIGN\\""\n}\n'
        )
        libraries = steam_libraries(root)
        assert libraries == [root, other]
        assert steam_app_name(1245620, libraries) == 'ELDEN RING "NIGHTREIGN"'

    def test_an_appid_with_no_manifest_is_named_not_dropped(self, tmp_path):
        assert steam_libraries(tmp_path) == [tmp_path]
        assert steam_app_name(570, [tmp_path]) == "steam:570"


# --- Polls into spans ---

T0 = datetime(2026, 10, 15, 20, 0, tzinfo=UTC)
GAP = timedelta(seconds=180)


def _sighting(pids=frozenset({200, 204})):
    return Sighting(
        game="Deadlock",
        matched_by=MATCHED_BY_STEAM,
        appid=1422450,
        executable=None,
        pid=200,
        pids=pids,
    )


def _apply(spans, focus, sightings, now, *, window_pid):
    return apply_poll(spans, focus, sightings, now, window_pid=window_pid, max_gap=GAP)


def _span(last_seen, started=None):
    return GameSpan(
        id=uuid.uuid4(),
        game="Deadlock",
        matched_by=MATCHED_BY_STEAM,
        appid=1422450,
        executable=None,
        pid=200,
        started_at=started or last_seen,
        last_seen_at=last_seen,
        ended_at=None,
    )


def _stretch(span, state, last_seen):
    return GameFocus(
        id=uuid.uuid4(),
        span_id=span.id,
        state=state,
        started_at=last_seen,
        last_seen_at=last_seen,
        ended_at=None,
    )


class TestPollsIntoSpans:
    def test_a_first_sighting_opens_a_span_and_a_focus_stretch(self):
        new = _apply([], [], [_sighting()], T0, window_pid=204)
        span, stretch = new
        assert isinstance(span, GameSpan) and isinstance(stretch, GameFocus)
        assert (span.started_at, span.last_seen_at, span.ended_at) == (T0, T0, None)
        assert (stretch.span_id, stretch.state) == (span.id, FOCUSED)

    def test_the_next_poll_extends_rather_than_inserts(self):
        span = _span(T0)
        stretch = _stretch(span, FOCUSED, T0)
        later = T0 + timedelta(seconds=60)
        assert _apply([span], [stretch], [_sighting()], later, window_pid=204) == []
        assert (span.last_seen_at, stretch.last_seen_at) == (later, later)

    def test_a_span_ends_at_its_last_sighting_not_at_the_poll_that_noticed(self):
        span = _span(T0, started=T0 - timedelta(hours=1))
        stretch = _stretch(span, FOCUSED, T0)
        later = T0 + timedelta(seconds=60)
        assert _apply([span], [stretch], [], later, window_pid=None) == []
        assert span.ended_at == T0
        assert stretch.ended_at == T0

    def test_a_gap_breaks_the_run_though_the_game_is_still_there(self):
        """A suspended box resumes with the game open; the night is not play."""
        span = _span(T0)
        morning = T0 + timedelta(hours=8)
        [fresh, _] = _apply([span], [], [_sighting()], morning, window_pid=None)
        assert span.ended_at == T0
        assert fresh.started_at == morning and fresh.id != span.id

    def test_a_late_poll_inside_the_gap_does_not_split(self):
        span = _span(T0)
        [stretch] = _apply([span], [], [_sighting()], T0 + GAP, window_pid=None)
        assert stretch.state == UNKNOWN
        assert span.ended_at is None and span.last_seen_at == T0 + GAP

    def test_no_answer_from_the_probe_is_unknown_never_unfocused(self):
        [_, stretch] = _apply([], [], [_sighting()], T0, window_pid=None)
        assert stretch.state == UNKNOWN

    def test_another_window_closes_the_stretch_and_opens_none(self):
        span = _span(T0)
        stretch = _stretch(span, FOCUSED, T0)
        later = T0 + timedelta(seconds=60)
        assert _apply([span], [stretch], [_sighting()], later, window_pid=999) == []
        assert stretch.ended_at == T0
        assert span.ended_at is None and span.last_seen_at == later

    def test_a_change_of_state_starts_a_new_stretch(self):
        span = _span(T0)
        stretch = _stretch(span, UNKNOWN, T0)
        later = T0 + timedelta(seconds=60)
        [fresh] = _apply([span], [stretch], [_sighting()], later, window_pid=204)
        assert stretch.ended_at == T0
        assert (fresh.state, fresh.started_at) == (FOCUSED, later)


class TestTheAgent:
    @pytest.mark.asyncio
    async def test_the_probe_runs_only_on_a_poll_that_found_a_game(self, monkeypatch):
        """ADR-0016 §3: probing every poll writes 1,440 journal lines a day."""
        probe = AsyncMock(return_value=None)
        agent = GameDetectorAgent(focus_probe=probe)
        monkeypatch.setattr("sysadmin.games.agent.scan", lambda root, games: [])
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock())
        result = await agent._execute(session)
        probe.assert_not_called()
        assert result.findings_count == 0

    def test_the_kwin_probe_is_the_default(self):
        assert GameDetectorAgent().focus_probe is kwin_focus_probe

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("window_pid", "said"), [(None, UNKNOWN), (204, "known")])
    async def test_the_run_says_whether_the_probe_answered(self, monkeypatch, window_pid, said):
        """A probe that has stopped working shows in ``agent_runs.details``."""
        agent = GameDetectorAgent(focus_probe=AsyncMock(return_value=window_pid))
        monkeypatch.setattr("sysadmin.games.agent.scan", lambda root, games: [_sighting()])
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock())
        result = await agent._execute(session)
        assert result.details["focus"] == said

    def test_it_is_planned_every_sixty_seconds_and_wired(self):
        from sysadmin.main import JOB_TARGETS, game_detector_agent

        [spec] = [s for s in plan_jobs(AppConfig()) if s.job_id == "game_detector_poll"]
        assert spec.enabled and spec.trigger_kwargs == {"seconds": 60}
        assert JOB_TARGETS["game_detector_poll"] == game_detector_agent.run
        assert game_detector_agent.name == "game_detector"


class TestTheFocusProbe:
    """The one-shot KWin script (ADR-0016 §3), with ``gdbus`` and the journal faked.

    Driven live on 2026-10-15 under the daemon's own stripped environment:
    it answered firefox's PID in 0.011 s, unloaded, and left no file.
    """

    def test_the_line_is_picked_by_this_calls_token(self):
        out = (
            "sysadmin-focus-probe token=other pid=11\n"
            "sysadmin-focus-probe token=mine pid=71447\n"
        )
        assert parse_line(out, "mine") == 71447
        assert parse_line(out, "absent") is None

    def test_no_active_window_is_an_answer_not_unknown(self):
        """Rule 4: ``pid=0`` is unfocused; only a missing line is unknown."""
        assert parse_line("sysadmin-focus-probe token=t pid=0", "t") == NO_WINDOW
        assert focus_state(_sighting(), NO_WINDOW) is None
        assert focus_state(_sighting(), None) == UNKNOWN

    def test_the_script_prints_the_token(self):
        assert "token=abc" in script_text("abc")
        assert "workspace.activeWindow" in script_text("abc")

    @pytest.mark.parametrize(("out", "want"), [("(0,)\n", 0), ("(-1,)", -1), ("()", None)])
    def test_the_load_id_is_read_from_gdbus(self, out, want):
        assert parse_load_id(out) == want

    @staticmethod
    def _fake(monkeypatch, tmp_path, answers):
        """Fake ``_run`` answering by verb; return the calls it saw."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        calls: list[list[str]] = []
        loads = iter(answers["loadScript"])

        async def fake_run(args, env):
            calls.append(args)
            assert env["XDG_RUNTIME_DIR"] == str(tmp_path)
            if args[0] == "journalctl":
                token = (tmp_path / next(tmp_path.glob("*.js")).name).read_text()
                token = token.split("token=")[1].split(" ")[0]
                return answers["journal"].replace("TOKEN", token)
            verb = args[args.index("--method") + 1].rsplit(".", 1)[-1]
            if verb == "loadScript":
                return next(loads)
            if verb == "run" and "run_fails" in answers:
                raise focus_module.ProbeFailedError("run refused")
            return "(true,)" if verb == "unloadScript" else "()"

        monkeypatch.setattr("sysadmin.games.focus._run", fake_run)
        monkeypatch.setattr("sysadmin.games.focus.JOURNAL_RETRY_SECONDS", 0)
        return calls

    @staticmethod
    def _verbs(calls):
        return [
            c[c.index("--method") + 1].rsplit(".", 1)[-1] if c[0] == "gdbus" else c[0]
            for c in calls
        ]

    @pytest.mark.asyncio
    async def test_it_loads_runs_unloads_then_reads(self, monkeypatch, tmp_path):
        calls = self._fake(
            monkeypatch,
            tmp_path,
            {"loadScript": ["(3,)"], "journal": "sysadmin-focus-probe token=TOKEN pid=204\n"},
        )
        assert await kwin_focus_probe() == 204
        assert self._verbs(calls) == ["loadScript", "run", "unloadScript", "journalctl"]
        assert "/Scripting/Script3" in calls[1]
        assert PLUGIN_NAME in calls[2]
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.asyncio
    async def test_a_leftover_load_is_cleared_and_loaded_again(self, monkeypatch, tmp_path):
        """Rule 3: ``loadScript`` answers -1 for a name a killed probe left loaded."""
        calls = self._fake(
            monkeypatch,
            tmp_path,
            {
                "loadScript": ["(-1,)", "(0,)"],
                "journal": "sysadmin-focus-probe token=TOKEN pid=7\n",
            },
        )
        assert await kwin_focus_probe() == 7
        assert self._verbs(calls)[:4] == ["loadScript", "unloadScript", "loadScript", "run"]

    @pytest.mark.asyncio
    async def test_a_failed_run_still_unloads_and_answers_unknown(self, monkeypatch, tmp_path):
        calls = self._fake(
            monkeypatch,
            tmp_path,
            {"loadScript": ["(0,)"], "journal": "", "run_fails": True},
        )
        assert await kwin_focus_probe() is None
        assert self._verbs(calls) == ["loadScript", "run", "unloadScript"]
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.asyncio
    async def test_a_missing_line_is_unknown_after_every_attempt(self, monkeypatch, tmp_path):
        calls = self._fake(monkeypatch, tmp_path, {"loadScript": ["(0,)"], "journal": "noise\n"})
        assert await kwin_focus_probe() is None
        assert self._verbs(calls).count("journalctl") == focus_module.JOURNAL_ATTEMPTS

    @pytest.mark.asyncio
    async def test_no_runtime_directory_is_unknown(self, monkeypatch, tmp_path):
        """No login session and no lingering: no bus to ask."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "absent"))
        assert await kwin_focus_probe() is None
