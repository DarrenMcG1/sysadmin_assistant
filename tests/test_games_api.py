"""``GET /api/games/spans`` — what is served and what is refused (ADR-0016 §5).

The overlap query is PostgreSQL's to decide and is tested against the
scratch database in ``test_game_spans_db.py``; this file holds what needs
no database.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from sysadmin.core.contracts import GameSpansResponse
from sysadmin.games.agent import FOCUSED, UNKNOWN
from sysadmin.games.detect import MATCHED_BY_STEAM
from sysadmin.games.models import GameFocus, GameSpan
from sysadmin.games.router import retained_from, span_payload

T0 = datetime(2026, 10, 15, 20, 0, tzinfo=UTC)


def _span(ended_at=None):
    return GameSpan(
        id=uuid.uuid4(),
        game="Deadlock",
        matched_by=MATCHED_BY_STEAM,
        appid=1422450,
        executable=None,
        pid=200,
        started_at=T0,
        last_seen_at=T0 + timedelta(minutes=30),
        ended_at=ended_at,
    )


def _stretch(span, state, minute):
    return GameFocus(
        span_id=span.id,
        state=state,
        started_at=T0 + timedelta(minutes=minute),
        last_seen_at=T0 + timedelta(minutes=minute + 5),
        ended_at=T0 + timedelta(minutes=minute + 5),
    )


class TestTheServedSpan:
    def test_stretches_are_served_oldest_first_and_parse_as_the_contract(self):
        span = _span()
        payload = span_payload(span, [_stretch(span, FOCUSED, 20), _stretch(span, FOCUSED, 0)])
        assert [f["started_at"] for f in payload["focus"]] == [
            T0.isoformat(),
            (T0 + timedelta(minutes=20)).isoformat(),
        ]
        parsed = GameSpansResponse.from_dict({"spans": [payload]})
        assert parsed.spans[0].ended_at is None
        assert parsed.spans[0].focus_known is True

    def test_one_unknown_stretch_makes_the_span_focus_unknown(self):
        """ADR-0016 §3: a reader ignoring ``focus`` can still fall back to presence."""
        span = _span()
        payload = span_payload(span, [_stretch(span, FOCUSED, 0), _stretch(span, UNKNOWN, 10)])
        assert payload["focus_known"] is False
        assert [f["state"] for f in payload["focus"]] == [FOCUSED, UNKNOWN]

    def test_a_span_never_focused_has_known_focus_and_no_stretches(self):
        """Unfocused minutes have no row, so an empty list is a known answer."""
        payload = span_payload(_span(T0 + timedelta(minutes=30)), [])
        assert (payload["focus"], payload["focus_known"]) == ([], True)


class TestRetainedFrom:
    def test_nobody_has_looked(self):
        assert retained_from(None, 30, T0) is None

    def test_the_detectors_first_run_when_it_is_younger_than_retention(self):
        assert retained_from(T0 - timedelta(days=2), 30, T0) == T0 - timedelta(days=2)

    def test_the_purge_cutoff_when_runs_outlive_spans(self):
        """Rule 3: ``agent_runs`` kept longer must not claim purged minutes."""
        assert retained_from(T0 - timedelta(days=90), 30, T0) == T0 - timedelta(days=30)


class TestTheRefusals:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "params",
        [
            {"start": "2026-10-15T00:00:00", "end": "2026-10-16T00:00:00+01:00"},
            {"start": "2026-10-15T00:00:00+01:00", "end": "2026-10-16T00:00:00"},
        ],
    )
    async def test_a_timestamp_without_an_offset_is_refused(self, test_client, params):
        """Rule 2: a naive value on a BST box is an hour's guess."""
        response = await test_client.get("/api/games/spans", params=params)
        assert response.status_code == 422
        assert "offset" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_an_offset_is_accepted_when_its_plus_is_encoded(
        self, test_client, mock_session
    ):
        """An unencoded ``+`` arrives as a space and fails to parse — hence ``Z``.

        With no rows and no detector run, the answer is "nobody looked".
        """
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        response = await test_client.get(
            "/api/games/spans",
            params={"start": "2026-10-15T00:00:00+01:00", "end": "2026-10-16T00:00:00Z"},
        )
        assert response.status_code == 200
        assert response.json() == {"poll_seconds": 60, "retained_from": None, "spans": []}

    @pytest.mark.asyncio
    async def test_an_empty_or_backwards_range_is_refused(self, test_client):
        response = await test_client.get(
            "/api/games/spans?start=2026-10-15T00:00:00Z&end=2026-10-15T00:00:00Z"
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_both_ends_are_required(self, test_client):
        response = await test_client.get("/api/games/spans?start=2026-10-15T00:00:00Z")
        assert response.status_code == 422
