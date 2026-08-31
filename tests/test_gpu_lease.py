"""The weekly reviews' GPU lease — the budget, the degradations, the release.

``SNAG-SCHED-003``.  Three reviews that read the card once and gave up
now park in the estate's queue.  What is asserted here is the half this
repository owns: how long each dispatch is allowed to wait, what happens
to each of the three typed refusals, and that a review is written either
way.  The wire mechanics are :mod:`estate.queue`'s and are not re-tested.

Every test drives the real :func:`~sysadmin.core.gpu_lease.acquire_review_lease`
against a stand-in for the *library*, never a stand-in for the function
under test.
"""

import pathlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from estate import queue as estate_queue

from sysadmin.core import gpu_lease
from sysadmin.core.config import AppConfig
from sysadmin.core.gpu_lease import (
    HOLD_TIMEOUT_MULTIPLE,
    REVIEW_PROFILE,
    acquire_review_lease,
    hold_seconds,
    release_review_lease,
    wait_budget_seconds,
)

LOCAL = timezone(timedelta(hours=1))


def _at(hour, minute=0, second=0):
    return datetime(2026, 8, 31, hour, minute, second, tzinfo=LOCAL)


def _config(**overrides):
    config = AppConfig()
    for path, value in overrides.items():
        obj = config
        *parents, leaf = path.split(".")
        for part in parents:
            obj = getattr(obj, part)
        setattr(obj, leaf, value)
    return config


class TestTheBudgetIsOneDeadlineDerivedThreeTimes:
    """One number, three budgets — and the derivation is the claim.

    Three independent leaves were the obvious implementation and say the
    wrong thing about the mechanism: the arbiter grants one lease at a
    time FIFO across every profile, so all three reviews are waiting for
    a single instant from three starting points.
    """

    @pytest.mark.parametrize(
        "dispatch,expected_minutes",
        [(_at(5, 0), 55), (_at(5, 15), 40), (_at(5, 45), 10)],
    )
    def test_each_slot_derives_its_own_distance_to_the_deadline(self, dispatch, expected_minutes):
        assert wait_budget_seconds(dispatch, _config()) == expected_minutes * 60

    def test_moving_the_briefing_moves_every_budget_with_it(self):
        """Provenance, not a value.

        Asserting 3300 against the shipped config passes just as well
        over a hard-coded number while the briefing happens to be 06:00
        — the trap this repository has been caught by three times.  So
        the *briefing* moves and the budget has to move with it.
        """
        later = _config(**{"schedules.briefing_hour": 7})
        assert wait_budget_seconds(_at(5, 0), later) == 115 * 60

    def test_widening_the_margin_narrows_every_budget(self):
        wider = _config(**{"schedules.review_lease_margin_minutes": 20})
        assert wait_budget_seconds(_at(5, 0), wider) == 40 * 60

    def test_past_the_deadline_there_is_no_budget_rather_than_a_zero(self):
        """``None``, never ``0``.

        A zero-second waiter is a row in the estate's table for its next
        tick to drop — charged to another repository's queue depth, which
        is a gauge this repository itself judges.
        """
        assert wait_budget_seconds(_at(5, 56), _config()) is None

    def test_the_deadline_itself_is_not_a_budget(self):
        """The boundary case, because ``> 0`` and ``>= 0`` differ here."""
        assert wait_budget_seconds(_at(5, 55), _config()) is None
        assert wait_budget_seconds(_at(5, 54, 59), _config()) == 1


class TestTheBudgetSurvivesTheMeasuredRelease:
    """The correction estate-manager sent back, driven rather than believed.

    Closing message ``dcae132c``: ``Arbiter._drop_overdue_waiters()`` runs
    **first** in every tick, before the grant, so a waiter past its
    ``wait_deadline`` is dropped even if the card frees a second later.
    Verified in their source.  Their warning is that copying their
    ``REVIEW_WAIT_SECONDS`` of 1800 drops the 05:00 job at 05:30 —
    fifteen minutes before the card frees — and the 05:15 job by 22-72 s,
    which is the nasty one because it fails by a margin small enough to
    read as a fluke.

    **It does not bite this design, and the reason is the shape of the
    number rather than its size**: a deadline is not a duration.  Every
    budget here ends at 05:55 whatever slot it was derived from, which is
    past the whole measured release band.  Pinned so that a future edit
    trading the deadline back for a copied duration is named.

    **One of the three below is a recorded counterfactual and not a
    guard, and it says so rather than being counted as one.**
    ``test_a_copied_duration_would_have_dropped_two_of_the_three``
    is arithmetic over two constants: no change to
    :mod:`sysadmin.core.gpu_lease` can break it, and driving the thirteen
    mutations of this fix left it green throughout.  It is here because
    the shape of the fix is only legible beside the shape it refused, and
    it *would* fail if ``MEASURED_RELEASES`` were edited — which is the
    one thing that could make the argument stale.  The other two do
    witness the code: the margin read as hours, or the deadline stopping
    its derivation from the briefing, turn them red.
    """

    #: Every release of ``venture-enrich-nightly`` recorded on this box
    #: since its timer moved to 00:00 on 2026-08-25 — five from
    #: ``SNAG-SCHED-003``'s symptom bullet, one from 2026-08-31.  The
    #: worst is 05:47:18.
    MEASURED_RELEASES = (
        (5, 45, 15),
        (5, 45, 22),
        (5, 45, 26),
        (5, 46, 11),
        (5, 46, 58),
        (5, 47, 18),
    )

    @pytest.mark.parametrize("dispatch", [_at(5, 0), _at(5, 15), _at(5, 45)])
    def test_no_slot_is_dropped_before_the_worst_recorded_release(self, dispatch):
        budget = wait_budget_seconds(dispatch, _config())
        assert budget is not None
        deadline = dispatch + timedelta(seconds=budget)
        worst = _at(*self.MEASURED_RELEASES[-1])
        assert deadline > worst, (
            f"a request at {dispatch:%H:%M} is dropped at {deadline:%H:%M:%S}, "
            f"before the worst recorded release at {worst:%H:%M:%S}"
        )

    def test_a_copied_duration_would_have_dropped_two_of_the_three(self):
        """The counterfactual, because the fix is only legible beside it.

        1800 s is estate-manager's number for estate-manager's slot, and
        it is correct there: 05:30 + 1800 s is 06:00, past every release
        below.  Transplanted to 05:00 and 05:15 it lands at 05:30 and
        05:45:00, and 05:45:00 is *before* every recorded release but the
        first — the failure their note calls a fluke-sized margin.
        """
        estate_copy = 1800
        worst = _at(*self.MEASURED_RELEASES[-1])
        dropped = [
            slot
            for slot in (_at(5, 0), _at(5, 15))
            if slot + timedelta(seconds=estate_copy) <= worst
        ]
        assert len(dropped) == 2
        assert _at(5, 30) + timedelta(seconds=estate_copy) > worst

    def test_the_earliest_release_still_does_not_rescue_a_copied_duration(self):
        """Driven at the *best* case as well as the worst, or the test
        above is satisfied by an outlier."""
        earliest = _at(*self.MEASURED_RELEASES[0])
        assert _at(5, 0) + timedelta(seconds=1800) < earliest
        assert wait_budget_seconds(_at(5, 0), _config()) is not None
        assert _at(5, 0) + timedelta(seconds=wait_budget_seconds(_at(5, 0), _config())) > earliest


class TestTheHoldIsDerivedFromTheInferenceTimeout:
    def test_it_is_a_multiple_of_the_llm_timeout(self):
        assert hold_seconds(_config()) == int(120 * HOLD_TIMEOUT_MULTIPLE)

    def test_raising_the_inference_timeout_raises_the_hold(self):
        """Provenance again: two statements of one duration is
        ``SNAG-DB-003``'s shape at the size of a constant."""
        slower = _config(**{"llm.timeout_seconds": 300.0})
        assert hold_seconds(slower) == int(300 * HOLD_TIMEOUT_MULTIPLE)


class TestEveryRefusalDegradesToTheGateThatWasThereBefore:
    """The thing arbitrating the card must never stop inference.

    Each returns ``None``, which the caller passes on as
    ``gpu_lease_held=False`` — the digest path that was there before.
    """

    @staticmethod
    def _raising(exc):
        return patch.object(estate_queue, "acquire", AsyncMock(side_effect=exc))

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exc",
        [
            estate_queue.QueueUnavailable("no :8400"),
            estate_queue.AcquireDropped("lease 1 dropped"),
            estate_queue.AcquireTimeout("lease 1 not granted"),
        ],
    )
    async def test_a_typed_refusal_returns_none(self, exc):
        with self._raising(exc):
            assert (
                await acquire_review_lease(
                    AsyncMock(), "health_review", now=_at(5, 0), config=_config()
                )
                is None
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exc,event",
        [
            (estate_queue.QueueUnavailable("x"), "review_queue_unavailable"),
            (estate_queue.AcquireDropped("x"), "review_lease_dropped"),
            (estate_queue.AcquireTimeout("x"), "review_lease_timeout"),
        ],
    )
    async def test_the_three_are_logged_apart_though_they_degrade_alike(self, exc, event, caplog):
        """``SNAG-SCHED-003``'s quieter half.

        Nothing on ``health_reviews``, ``log_reviews`` or ``disk_reviews``
        distinguishes *skipped for contention* from *llama-server was
        down*, and this repository served three digests for a reason no
        log line recorded.  A stored column would be a second statement
        of a fact the journal can carry, so the journal is made able to
        carry it.
        """
        with self._raising(exc), caplog.at_level("WARNING"):
            await acquire_review_lease(AsyncMock(), "log_review", now=_at(5, 0), config=_config())
        assert [r.message for r in caplog.records] == [event]

    @pytest.mark.asyncio
    async def test_an_untyped_error_is_not_swallowed(self):
        """Only the library's three degrade.

        A ``TypeError`` out of this module is a defect here, and
        catching everything would make it a Monday of quiet digests —
        which is the failure this whole entry is about, wearing the fix's
        clothes.
        """
        with self._raising(RuntimeError("bug")), pytest.raises(RuntimeError):
            await acquire_review_lease(AsyncMock(), "disk_review", now=_at(5, 0), config=_config())


class TestPastTheDeadlineNoLeaseIsAskedFor:
    @pytest.mark.asyncio
    async def test_it_does_not_reach_the_queue_at_all(self):
        acquire = AsyncMock()
        with patch.object(estate_queue, "acquire", acquire):
            result = await acquire_review_lease(
                AsyncMock(), "disk_review", now=_at(5, 56), config=_config()
            )
        assert result is None
        acquire.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_it_says_so_rather_than_going_quiet(self, caplog):
        with patch.object(estate_queue, "acquire", AsyncMock()), caplog.at_level("WARNING"):
            await acquire_review_lease(AsyncMock(), "disk_review", now=_at(5, 56), config=_config())
        assert [r.message for r in caplog.records] == ["review_lease_past_deadline"]


class TestAGrantIsPassedOnAsTheHoldItIs:
    @pytest.mark.asyncio
    async def test_it_returns_the_lease_id(self):
        granted = estate_queue.Lease(id=41, state="granted", profile=REVIEW_PROFILE)
        with patch.object(estate_queue, "acquire", AsyncMock(return_value=granted)):
            assert (
                await acquire_review_lease(
                    AsyncMock(), "health_review", now=_at(5, 0), config=_config()
                )
                == 41
            )

    @pytest.mark.asyncio
    async def test_it_asks_for_the_derived_budget_and_hold(self):
        granted = estate_queue.Lease(id=7, state="granted", profile=REVIEW_PROFILE)
        acquire = AsyncMock(return_value=granted)
        with patch.object(estate_queue, "acquire", acquire):
            await acquire_review_lease(AsyncMock(), "log_review", now=_at(5, 15), config=_config())
        kwargs = acquire.await_args.kwargs
        assert kwargs["wait_seconds"] == 40 * 60
        assert kwargs["max_hold_seconds"] == 600
        assert kwargs["profile"] == REVIEW_PROFILE

    @pytest.mark.asyncio
    async def test_it_is_addressed_from_config_not_the_librarys_default(self):
        """:mod:`estate.queue` defaults ``base_url`` to its own
        ``127.0.0.1:8400``, so passing nothing is a second spelling of the
        estate's address inside this process — right on this box today
        and free to drift from the address the judging uses.

        Asserted as provenance: the config is *moved* and the request has
        to move with it, which a comparison against the shipped value
        would pass over a hard-coded default.
        """
        granted = estate_queue.Lease(id=7, state="granted", profile=REVIEW_PROFILE)
        acquire = AsyncMock(return_value=granted)
        elsewhere = _config(**{"agents.estate_judge.base_url": "http://box:9999/"})
        with patch.object(estate_queue, "acquire", acquire):
            await acquire_review_lease(AsyncMock(), "log_review", now=_at(5, 15), config=elsewhere)
        assert acquire.await_args.kwargs["base_url"] == "http://box:9999"

    @pytest.mark.asyncio
    async def test_the_release_is_addressed_the_same_way(self):
        release = AsyncMock()
        elsewhere = _config(**{"agents.estate_judge.base_url": "http://box:9999"})
        with patch.object(estate_queue, "release", release):
            await release_review_lease(AsyncMock(), 41, "log_review", config=elsewhere)
        assert release.await_args.kwargs["base_url"] == "http://box:9999"

    @pytest.mark.asyncio
    async def test_the_requester_names_the_review_not_the_service(self):
        """Three simultaneous waiters in one FIFO queue are unreadable
        under one name, and the estate's ``gpu_leases`` rows are read by
        a human deciding which is which."""
        granted = estate_queue.Lease(id=7, state="granted", profile=REVIEW_PROFILE)
        acquire = AsyncMock(return_value=granted)
        with patch.object(estate_queue, "acquire", acquire):
            await acquire_review_lease(AsyncMock(), "disk_review", now=_at(5, 45), config=_config())
        assert acquire.await_args.kwargs["requester"] == "disk_review"


class TestTheReleaseIsBestEffort:
    @pytest.mark.asyncio
    async def test_it_passes_best_effort_through(self):
        """A release that raised would turn a stored review into a failed
        unit, and the arbiter's hold deadline restores the baseline
        anyway."""
        release = AsyncMock()
        with patch.object(estate_queue, "release", release):
            await release_review_lease(AsyncMock(), 41, "health_review")
        assert release.await_args.kwargs["best_effort"] is True
        assert release.await_args.kwargs["lease_id"] == 41


class TestTheProfileIsThisRepositorysOwn:
    def test_it_does_not_name_the_estates_review_profile(self):
        """Their ``estate-review`` is a no-swap profile of the same shape
        and its own comment names their timer and their job.  Requested
        as ours 2026-08-31, message ``dcae132c``."""
        assert REVIEW_PROFILE == "sysadmin-review"
        assert REVIEW_PROFILE != "estate-review"

    def test_this_module_cannot_write_a_file_at_all(self):
        """The estate rule this repository is bound by: shared
        infrastructure gets an owner that is not an application, and the
        estate's founding exception — writing code into another
        repository — closed on 2026-08-13.

        Asserted as a **capability** rather than as the absence of one
        path.  Refusing the string ``profiles.yaml`` would be satisfied
        by a module that built the path from two halves; a module with no
        write in it cannot edit that file or any other, so the profile
        can only ever arrive by their hand.
        """
        import ast

        tree = ast.parse(pathlib.Path(gpu_lease.__file__).read_text(encoding="utf-8"))
        writers = {"open", "write_text", "write_bytes", "dump", "dump_all", "mkdir"}
        found = sorted(
            {
                node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, (ast.Name, ast.Attribute))
                and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr) in writers
            }
        )
        assert found == []


class TestTheGateIsSkippedOnlyWithALeaseInHand:
    """``gpu_lease_held`` is the absence of a gate, not a third sampler."""

    @pytest.mark.asyncio
    async def test_a_holder_does_not_read_the_counter(self):
        import httpx

        from sysadmin.core.llm_client import LLMClient

        client = LLMClient(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200, json={"choices": [{"message": {"content": "hi"}}]}
                )
            )
        )
        busy = SimpleNamespace(called=False)

        def _gate(*_args, **_kwargs):
            busy.called = True

        with patch("sysadmin.core.llm_client.ensure_gpu_idle", _gate):
            await client.startup()
            try:
                assert await client.generate("p", gpu_lease_held=True) == "hi"
            finally:
                await client.shutdown()
        assert not busy.called

    @pytest.mark.asyncio
    async def test_without_a_lease_the_counter_is_still_the_gate(self):
        """The default is today's behaviour, so a caller that forgets the
        flag fails in the direction that costs prose rather than the one
        that claims a hold nobody has."""
        from estate.gpu import GpuBusy

        from sysadmin.core.llm_client import LLMClient

        client = LLMClient()

        def _busy(*_args, **_kwargs):
            raise GpuBusy("dGPU 99% busy", busy_percent=99, threshold=25)

        with patch("sysadmin.core.llm_client.ensure_gpu_idle", _busy):
            await client.startup()
            try:
                assert await client.generate("p") is None
            finally:
                await client.shutdown()
