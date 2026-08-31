"""The lease seam driven against the estate's real arbiter on :8400.

``SNAG-SCHED-003``'s two checks retired with the entry on 2026-08-31 —
every member of ``snag_claims.CHECKS`` names an *open* one — and the
guard did not go with them (``FROZEN_TABLES``' rule).  It moved here and
into ``tests/test_gpu_gate_invocations.py``, and it is **stronger than
what it replaces**: those checks asked whether anything under
``sysadmin/`` mentioned an arbitrating name, which a docstring nearly
satisfied once.  These ask the two questions that decide whether a
Monday narrative survives.

1. **The profile is still published.**  ``POST /api/queue/acquire``
   answers ``404 unknown profile`` for a name the estate has not
   registered, and this repository's degradation is *silent by design* —
   every review writes its digest and the box looks healthy.  So a
   profile removed at the other end costs three narratives a week and
   raises nothing.  Nothing else on this box would notice.
2. **An unreachable arbiter degrades rather than raising.**  The estate
   being down must cost the swap and never resident inference (their
   ADR-0007 decision 1, this module's rule 1).

**The roster is the arbiter's own answer, not a proxy for it.**
``GET /api/health`` returns ``sorted(app.state.profiles)`` and
``Arbiter`` is constructed with that same dict — the one ``submit``
raises ``UnknownProfile`` from — verified in ``estate_service/api.py``
at lines 79, 103-105 and 215.  So "would an acquire from here 404" is
answered *exactly* by a read, which is why no grant round-trip is driven
here: an acquire writes a row into another repository's ``gpu_leases``,
and its ``dropped_total`` is evidence this repository's own
``judge_queue_invariants`` reads back.  A test that dirtied the gauge it
judges is the second-owner defect wearing a probe's clothes.

The seam was driven by hand on the day it landed rather than left to the
suite: lease 39 was requested at 06:39:30 with ``wait 3300s, hold 600s``,
the arbiter logged ``lease 39 waits: GPU floor 26% over threshold 25%``
and parked it — which is the whole fix in one line, since the old gate
raised ``GpuBusy`` at that same 26 % and served a digest — and
``wait_deadline`` came back ``07:34:30``, request plus exactly the
derived 3300 s.
"""

import httpx
import pytest

from sysadmin.core.config import get_config
from sysadmin.core.gpu_lease import (
    REVIEW_PROFILE,
    acquire_review_lease,
    arbiter_url,
    wait_budget_seconds,
)

PROBE_TIMEOUT = 5.0


def _roster() -> list[str] | None:
    """The arbiter's registered profiles, or ``None`` if it will not say."""
    try:
        response = httpx.get(f"{arbiter_url()}/api/health", timeout=PROBE_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None
    profiles = payload.get("profiles") if isinstance(payload, dict) else None
    return profiles if isinstance(profiles, list) else None


@pytest.mark.premise
def test_the_arbiter_answers_and_publishes_a_roster():
    """Everything below reads the estate's profile roster.

    Held as its own test rather than as a skip predicate inside each
    drive: a premise checked by the subject's own helper is a control the
    subject can switch off.  This one shares no code with
    :mod:`sysadmin.core.gpu_lease` beyond the address.
    """
    roster = _roster()
    if roster is None:
        pytest.skip("estate-manager on :8400 is not answering /api/health")
    assert isinstance(roster, list)
    assert roster, "the arbiter published an empty roster — no profile can be granted"


class TestTheProfileIsStillRegistered:
    """The half nothing else on this box would notice.

    Landed by estate-manager 2026-08-31 in answer to message
    ``dcae132c``.  If it is ever removed, every review here degrades
    silently to the digest it served before — which is the entry this
    file is the residue of, arriving without a symptom anybody sees.
    """

    def test_the_arbiter_still_publishes_our_profile(self):
        roster = _roster()
        if roster is None:
            pytest.skip("estate-manager on :8400 is not answering /api/health")
        assert REVIEW_PROFILE in roster, (
            f"{REVIEW_PROFILE!r} is not in the arbiter's roster {sorted(roster)} — "
            "every weekly review here now degrades to a digest, silently, and "
            "SNAG-SCHED-003 is back with no surface saying so"
        )

    def test_it_is_ours_rather_than_the_estates(self):
        """Their ``estate-review`` is a no-swap profile of the same shape
        and its own comment names their timer and their job; a shared
        entry would make one comment lie (their close note, ``dcae132c``).
        """
        assert REVIEW_PROFILE == "sysadmin-review"
        roster = _roster()
        if roster is None:
            pytest.skip("estate-manager on :8400 is not answering /api/health")
        assert "estate-review" in roster, "the premise for the distinction is gone"


class TestTheDegradationIsWhatTheReviewsSee:
    """A 404 or a dead socket must reach the caller as ``None``.

    A review that raised here would fail its unit and write no digest at
    all — strictly worse than the Monday the entry was about.
    """

    @pytest.mark.asyncio
    async def test_an_unreachable_arbiter_degrades_rather_than_raising(self):
        """Driven against a genuinely dead port, not against a stand-in.

        A mocked ``QueueUnavailable`` proves the ``except`` clause; a
        closed socket proves the whole path from :mod:`httpx` through the
        library's typed error to this module's ``None``.
        """
        dead = get_config().model_copy(deep=True)
        dead.agents.estate_judge.base_url = "http://127.0.0.1:1"
        async with httpx.AsyncClient(timeout=1.0) as client:
            assert await acquire_review_lease(client, "disk_review", config=dead) is None

    def test_the_lease_is_addressed_where_the_judging_is(self):
        """Not :mod:`estate.queue`'s own default.

        That library defaults ``base_url`` to ``127.0.0.1:8400``; taking
        the default is a second spelling of the estate's address inside
        this process — right on this box today and free to drift from the
        address the judging uses.  Found by writing the drive above,
        which is what a live test is for.
        """
        assert arbiter_url() == get_config().agents.estate_judge.base_url.rstrip("/")


class TestTheBudgetReachesTheArbiterUnchanged:
    """The wait deadline is the estate's arithmetic over our number.

    ``Arbiter._drop_overdue_waiters()`` runs first in every tick, so a
    budget that arrives wrong is a review dropped before the card frees —
    the failure estate-manager's close note warned about for a *copied*
    duration, and the one this design avoids by deriving a deadline.
    """

    def test_the_slots_derive_budgets_that_clear_the_recorded_releases(self):
        from datetime import timedelta

        config = get_config()
        worst_release_seconds = 5 * 3600 + 47 * 60 + 18  # 05:47:18, 2026-08-27
        for hour, minute in (
            (config.schedules.health_review_hour, config.schedules.health_review_minute),
            (config.schedules.log_review_hour, config.schedules.log_review_minute),
            (config.schedules.disk_review_hour, config.schedules.disk_review_minute),
        ):
            import datetime as _dt

            at = (
                _dt.datetime.now()
                .astimezone()
                .replace(hour=hour, minute=minute, second=0, microsecond=0)
            )
            budget = wait_budget_seconds(at, config)
            assert budget is not None, f"{hour:02d}:{minute:02d} derives no budget"
            deadline = at + timedelta(seconds=budget)
            deadline_seconds = deadline.hour * 3600 + deadline.minute * 60 + deadline.second
            assert deadline_seconds > worst_release_seconds
