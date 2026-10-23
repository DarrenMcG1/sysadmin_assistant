"""Session 414 — the journal's window and the core-dump loops that shorten it.

Measured 2026-10-23 21:50: both scopes' oldest records were 2026-10-20
12:16 (system) and 12:21 (user), a window of 3.4 days, after baloo's
loop wrote about 207k dumps into the shared 4G cap.  The flood's worst
hour held 11,963 dumps from ``/usr/lib/kf6/baloo_file_extractor``; the
24 hours to the measurement held three, from three executables.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.core.config import JournalHorizonConfig
from sysadmin.monitor import journal_horizon
from sysadmin.monitor.agent import RESOLVABLE_TITLE_PATTERNS, SysAdminAgent
from sysadmin.monitor.journal_horizon import (
    COREDUMP_DETAIL_KEY,
    HORIZON_DETAIL_KEY,
    WINDOW_SUBJECT,
    WINDOW_TITLE,
    Window,
    is_short,
    loop_title,
    loops_from,
)

NOW = datetime(2026, 10, 23, 20, 50, tzinfo=UTC)
BALOO = "/usr/lib/kf6/baloo_file_extractor"


def _like(pattern: str, value: str) -> bool:
    return re.fullmatch(re.escape(pattern).replace("%", ".*"), value) is not None


def _window(days: float | None, user_days: float | None = None) -> Window:
    def head(d):
        return None if d is None else NOW - timedelta(days=d)
    return Window(system_head=head(days), user_head=head(user_days),
                  measured_at=NOW)


# ── Rule 3: the family owns its lifecycle ────────────────────────────


class TestTitlesAreNotSweptByTheServiceResolve:
    @pytest.mark.parametrize("title", [
        WINDOW_TITLE,
        loop_title(BALOO),
        loop_title("/opt/chrome/chrome"),
        loop_title("/tmp/.mount_x/usr/lib/webkit2gtk-4.1/WebKitWebProcess"),
    ])
    def test_no_resolvable_pattern_matches(self, title):
        matched = [p for p in RESOLVABLE_TITLE_PATTERNS if _like(p, title)]
        assert matched == []

    def test_the_loop_title_names_the_basename(self):
        assert loop_title(BALOO) == "Core dump loop in baloo_file_extractor"


# ── Rule 1: the window is the shorter scope ──────────────────────────


class TestWindow:
    def test_the_newer_head_decides(self):
        window = _window(10.0, user_days=3.4)
        assert window.days == pytest.approx(3.4)

    def test_one_failed_scope_leaves_the_other(self):
        assert _window(None, user_days=3.4).days == pytest.approx(3.4)

    def test_both_failed_is_unknown_not_zero(self):
        assert _window(None).days is None
        assert is_short(_window(None), 7.0) is None

    def test_the_live_window_is_short_at_the_default_floor(self):
        assert is_short(_window(3.42, user_days=3.42), 7.0) is True

    def test_a_recovered_window_is_not_short(self):
        assert is_short(_window(15.0, user_days=15.0), 7.0) is False

    def test_the_message_states_both_instants_and_the_floor(self):
        message = journal_horizon.window_message(_window(3.4), 7.0)
        assert "3.4 days" in message
        assert "7-day floor" in message


# ── Rule 4: per executable ───────────────────────────────────────────


class TestLoops:
    def test_the_live_day_holds_no_loop(self):
        counts = {"/opt/chrome/chrome": 1, "/tmp/a/WebKitWebProcess": 1,
                  "/tmp/b/WebKitWebProcess": 1}
        assert loops_from(counts, 10, 60) == []

    def test_the_flood_hour_is_a_loop(self):
        [loop] = loops_from({BALOO: 11_963, "/opt/chrome/chrome": 1}, 10, 60)
        assert loop.exe == BALOO
        assert loop.details == {COREDUMP_DETAIL_KEY: BALOO, "dumps": 11_963,
                                "window_minutes": 60}

    def test_the_threshold_is_inclusive(self):
        assert [lp.count for lp in loops_from({BALOO: 10}, 10, 60)] == [10]

    def test_unrelated_dumps_are_not_summed(self):
        counts = {f"/bin/p{i}": 2 for i in range(20)}
        assert loops_from(counts, 10, 60) == []


# ── The reads ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestReads:
    async def test_head_parses_the_realtime_field(self, monkeypatch):
        micros = int(NOW.timestamp() * 1_000_000)
        run = AsyncMock(return_value=json.dumps(
            {"__REALTIME_TIMESTAMP": str(micros)}) + "\n")
        monkeypatch.setattr(journal_horizon, "_run", run)

        assert await journal_horizon.read_head(user=True) == NOW
        cmd = run.await_args.args[0]
        assert cmd[:2] == ["journalctl", "--user"]
        assert cmd[cmd.index("-n") + 1] == "+1"

    @pytest.mark.parametrize("stdout", [None, "", "not json\n", "{}\n"])
    async def test_an_unreadable_head_is_none(self, monkeypatch, stdout):
        monkeypatch.setattr(journal_horizon, "_run", AsyncMock(return_value=stdout))
        assert await journal_horizon.read_head(user=False) is None

    async def test_dumps_are_counted_per_executable(self, monkeypatch):
        lines = [{"COREDUMP_EXE": BALOO}] * 3 + [{"COREDUMP_EXE": "/bin/x"}, {}]
        run = AsyncMock(return_value="\n".join(json.dumps(x) for x in lines))
        monkeypatch.setattr(journal_horizon, "_run", run)

        counts = await journal_horizon.read_dump_counts(60, now=NOW)

        assert counts == {BALOO: 3, "/bin/x": 1}
        cmd = run.await_args.args[0]
        assert f"MESSAGE_ID={journal_horizon.COREDUMP_MESSAGE_ID}" in cmd
        assert cmd[cmd.index("--since") + 1] == f"@{int(NOW.timestamp()) - 3600}"

    async def test_a_failed_dump_read_is_none_not_empty(self, monkeypatch):
        monkeypatch.setattr(journal_horizon, "_run", AsyncMock(return_value=None))
        assert await journal_horizon.read_dump_counts(60) is None


# ── The agent method ─────────────────────────────────────────────────


def _agent_config(**overrides):
    cfg = MagicMock()
    cfg.journal_horizon = JournalHorizonConfig(**overrides)
    return cfg


def _open(details, alert_id):
    row = MagicMock()
    row.details = details
    row.id = alert_id
    return row


def _agent(monkeypatch, window: Window, dumps, open_rows=()):
    monkeypatch.setattr(journal_horizon, "read_window", AsyncMock(return_value=window))
    monkeypatch.setattr(journal_horizon, "read_dump_counts",
                        AsyncMock(return_value=dumps))
    agent = SysAdminAgent()
    agent.raise_alert = AsyncMock()
    agent._resolve_alert_ids = AsyncMock()
    agent._active_alerts = AsyncMock(return_value=list(open_rows))
    return agent


WINDOW_ROW = {HORIZON_DETAIL_KEY: WINDOW_SUBJECT}


@pytest.mark.asyncio
class TestCheckJournalHorizon:
    async def test_the_live_state_raises_the_window_row(self, monkeypatch):
        agent = _agent(monkeypatch, _window(3.4, 3.4), {})
        session = MagicMock()

        raised = await agent._check_journal_horizon(session, _agent_config())

        assert raised == 1
        call = agent.raise_alert.await_args
        assert call.kwargs["title"] == WINDOW_TITLE
        assert call.kwargs["severity"] == "warning"
        assert call.kwargs["details"][HORIZON_DETAIL_KEY] == WINDOW_SUBJECT
        assert agent._journal_horizon_counts == {
            "window_days": 3.4, "loops": 0, "raised": 1, "resolved": 0,
        }

    async def test_an_open_window_row_is_held(self, monkeypatch):
        agent = _agent(monkeypatch, _window(3.4), {}, [_open(WINDOW_ROW, "w")])
        session = MagicMock()

        assert await agent._check_journal_horizon(session, _agent_config()) == 0
        agent.raise_alert.assert_not_awaited()
        agent._resolve_alert_ids.assert_awaited_once_with(session, [])

    async def test_a_recovered_window_resolves_its_row(self, monkeypatch):
        agent = _agent(monkeypatch, _window(15.0), {}, [_open(WINDOW_ROW, "w")])
        session = MagicMock()

        await agent._check_journal_horizon(session, _agent_config())

        agent._resolve_alert_ids.assert_awaited_once_with(session, ["w"])

    async def test_unknown_holds_every_open_row(self, monkeypatch):
        """Rule 2: a failed read resolves nothing."""
        rows = [_open(WINDOW_ROW, "w"), _open({COREDUMP_DETAIL_KEY: BALOO}, "b")]
        agent = _agent(monkeypatch, _window(None), None, rows)
        session = MagicMock()

        raised = await agent._check_journal_horizon(session, _agent_config())

        assert raised == 0
        agent._resolve_alert_ids.assert_awaited_once_with(session, [])
        assert agent._journal_horizon_counts["window_days"] is None

    async def test_a_loop_is_raised_once_and_resolved_when_it_stops(
        self, monkeypatch
    ):
        agent = _agent(monkeypatch, _window(15.0), {BALOO: 11_963})
        assert await agent._check_journal_horizon(MagicMock(), _agent_config()) == 1
        assert agent.raise_alert.await_args.kwargs["title"] == loop_title(BALOO)

        held = _agent(monkeypatch, _window(15.0), {BALOO: 4_000},
                      [_open({COREDUMP_DETAIL_KEY: BALOO}, "b")])
        assert await held._check_journal_horizon(MagicMock(), _agent_config()) == 0

        session = MagicMock()
        stopped = _agent(monkeypatch, _window(15.0), {BALOO: 3},
                         [_open({COREDUMP_DETAIL_KEY: BALOO}, "b")])
        await stopped._check_journal_horizon(session, _agent_config())
        stopped._resolve_alert_ids.assert_awaited_once_with(session, ["b"])

    async def test_other_families_rows_are_ignored(self, monkeypatch):
        rows = [_open({"collation_database": "projects"}, "c")]
        agent = _agent(monkeypatch, _window(15.0), {}, rows)
        session = MagicMock()

        await agent._check_journal_horizon(session, _agent_config())

        agent._resolve_alert_ids.assert_awaited_once_with(session, [])

    async def test_disabled_reads_nothing(self, monkeypatch):
        agent = _agent(monkeypatch, _window(3.4), {BALOO: 99})

        raised = await agent._check_journal_horizon(
            MagicMock(), _agent_config(enabled=False))

        assert raised == 0
        journal_horizon.read_window.assert_not_awaited()
        assert agent._journal_horizon_counts["window_days"] is None


# ── The box ──────────────────────────────────────────────────────────


@pytest.mark.box
@pytest.mark.asyncio
async def test_this_box_answers_both_heads():
    """Both scopes and the dump read answer as the daemon's user."""
    window = await journal_horizon.read_window()
    assert window.system_head is not None
    assert window.user_head is not None
    assert window.days is not None and window.days > 0
    assert await journal_horizon.read_dump_counts(60) is not None
