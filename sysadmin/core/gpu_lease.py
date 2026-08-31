"""The weekly reviews' GPU lease: exclusion against a holder, and a place to wait.

**A guard asks "is the card busy now?" and, told yes, has no memory, no
ordering and no eventual grant.  A lease is a row: it parks.**  That
sentence is estate-manager's (``SNAG-ESTATE-093``, their ADR-0076) and
this module exists because this repository met the identical fault and
paid it three times over.

Measured on 2026-08-31, the first morning the two designs were observed
side by side under one holder (``SNAG-SCHED-003``).  All three weekly
reviews here dispatched inside ``venture-enrich-nightly``'s hold —
``health_reviews`` 05:00:03.92, ``log_reviews`` 05:15:00.06,
``disk_reviews`` 05:45:00.43 — each preceded by ``llm_gpu_busy`` at
``busy_percent`` 99, 97 and 98 against a threshold of 25, and each
followed by its own ``*_llm_unavailable_used_fallback``.
``alfred-inference.service`` was ``active`` throughout with no start,
stop or failure in the window, so "llama-server was down" is refuted
rather than assumed away.  The same morning
``estate-manager-review.service`` took lease 38, polled it for 16 m 21 s,
was granted at **05:46:20** — nine seconds after the drain released — and
kept its narrative.  Same card, same drain, same hour.

The client is :mod:`estate.queue` (ADR-0004 permits it; the wire
mechanics are the estate's by their ADR-0006).  What is this
repository's own convention, and lives here:

1. **Every refusal degrades to the gate that was there before.**  A
   review that cannot reach :8400 must still write a digest — the
   thing arbitrating the card must never be the thing that stops
   inference.  :class:`~estate.queue.QueueUnavailable`,
   :class:`~estate.queue.AcquireDropped` and
   :class:`~estate.queue.AcquireTimeout` all return ``None``, and the
   caller falls back to ``ensure_gpu_idle`` exactly as it did before.

2. **The three are logged apart even though they degrade alike.**  This
   is the whole of ``SNAG-SCHED-003``'s quieter half: nothing on
   ``health_reviews``, ``log_reviews`` or ``disk_reviews`` distinguishes
   *skipped for contention* from *llama-server was down*, and this
   repository served three digests for a reason no log line recorded.
   The stored ``llm_used`` flag is unchanged — a column would be a
   second statement of a fact the journal already carries — but the
   journal can now answer *why*.

3. **The budget is one deadline and three derivations of it.**  See
   :func:`wait_budget_seconds`.

4. **A non-positive budget takes no lease at all.**  Requesting with
   ``wait_seconds=0`` puts a row in the estate's table for
   ``_drop_overdue_waiters`` to reap on its next tick — a waiter that
   was never going to wait, charged to another repository's database and
   its queue-depth invariant, which this repository judges.  Past the
   deadline the digest is the right answer, so the lease is simply not
   asked for.
"""

import logging
from datetime import datetime, timedelta

import httpx
from estate import queue as estate_queue

from sysadmin.core.config import AppConfig, get_config

logger = logging.getLogger(__name__)

#: The estate's no-swap profile for this repository's weekly reviews.
#:
#: A **constant pinned live**, not a config leaf and not a copy that
#: nothing checks.  The profile is defined in estate-manager's
#: ``service/profiles.yaml``, which is theirs by the estate rule that
#: shared infrastructure gets an owner that is not an application, so
#: either spelling here is a name this repository does not own.  A
#: setting would add a second place for the two to disagree without
#: making the agreement checkable; ``tests/test_gpu_lease_live.py`` reads
#: ``GET :8400/api/health``, which publishes ``profiles``, and asserts
#: this string is among them — import where you can, pin where you
#: cannot.
#:
#: Requested from estate-manager 2026-08-31 as message ``dcae132c``.
#: Naming their ``estate-review`` instead was considered and refused:
#: that profile's own comment names their timer and their job.  Until
#: they add it, ``POST /api/queue/acquire`` answers ``404`` and rule 1
#: above carries every review to the digest it already served.
REVIEW_PROFILE = "sysadmin-review"

#: How many times the LLM's own timeout the arbiter should let a crashed
#: review hold the card before ``_expire_if_overdue`` takes it back.
#:
#: A **leak bound, not a budget** — nothing waits for it.  Derived from
#: ``llm.timeout_seconds`` rather than written beside it, so raising the
#: inference timeout raises the hold with it; the alternative is two
#: statements of one duration, free to drift, which is ``SNAG-DB-003``'s
#: shape at the size of a constant.  At the shipped 120 s this yields
#: **600 s**, which is the number estate-manager's ``REVIEW_MAX_HOLD_SECONDS``
#: reaches from the same timeout by the same reasoning — an agreement
#: arrived at by arithmetic rather than by transcription, which is why it
#: is not imported from them: their constant describes their review's
#: worst run, not ours.
HOLD_TIMEOUT_MULTIPLE = 5.0


def arbiter_url(config: AppConfig | None = None) -> str:
    """Where the arbiter is, read from the address this repository already uses.

    :mod:`estate.queue` defaults ``base_url`` to its own
    ``http://127.0.0.1:8400``, and **taking that default would be a second
    spelling of the estate's address inside this process** — the shape
    ``SNAG-DB-003`` is about, at the size of a hostname.  This repository
    already reaches :8400 through ``agents.estate_judge.base_url``
    (itself a deliberate duplicate of ``services.yaml``, pinned by a
    test), so the lease goes to the same place the judging does or the
    two could disagree about which estate they are talking to.

    Found by writing the live drive rather than by reading the call: the
    module was passing no ``base_url`` at all and worked, because the
    library's default happens to be right on this box today.
    """
    return (config or get_config()).agents.estate_judge.base_url.rstrip("/")


def hold_seconds(config: AppConfig | None = None) -> int:
    """The lease's hold deadline, derived from the inference timeout."""
    config = config or get_config()
    return int(config.llm.timeout_seconds * HOLD_TIMEOUT_MULTIPLE)


def wait_budget_seconds(
    now: datetime,
    config: AppConfig | None = None,
) -> int | None:
    """Seconds this dispatch may wait for a grant; ``None`` past the deadline.

    **One deadline, three budgets.**  The deadline is the briefing less
    ``schedules.review_lease_margin_minutes``; each review subtracts its
    own dispatch instant from it, so the 05:00, 05:15 and 05:45 slots get
    55, 40 and 10 minutes from one configured number.

    Three independent budgets were the obvious implementation and say
    the wrong thing about the mechanism.  The arbiter grants **one lease
    at a time, FIFO on ``requested_at``, across every profile**
    (``Arbiter.tick`` returns early while any lease is ``granted``), so
    the three reviews are not waiting three different lengths — they are
    waiting for **one instant**, the holder's release, from three
    different starting points.  A single deadline states that; three
    leaves would be three spellings of one boundary, free to drift apart
    and to be edited one at a time when the briefing moves.

    The subtraction is a **wall-clock** one, and that is the reading that
    agrees with what is being measured rather than an oversight.  Both
    ends are cron jobs in local time — the review slots and the briefing
    — so a daylight-saving transition moves both, and a wall-clock
    distance is what stays true across it.  An instant-difference would
    be an hour wrong on exactly the morning APScheduler had already
    corrected for.  (Contrast ``journal.since_timestamp``, where the
    consumer is ``journalctl`` reading an absolute moment and the local
    clock is the ambiguity being removed — ``SNAG-LOG-009``.)

    Returns ``None`` rather than ``0`` past the deadline, and the caller
    takes no lease: a zero-second waiter is a row in the estate's table
    for its next tick to drop, charged to another repository's queue
    depth — the gauge this repository itself judges in
    ``estate/judgements.py``.
    """
    config = config or get_config()
    schedules = config.schedules
    deadline = now.replace(
        hour=schedules.briefing_hour,
        minute=schedules.briefing_minute,
        second=0,
        microsecond=0,
    ) - timedelta(minutes=schedules.review_lease_margin_minutes)
    budget = int((deadline - now).total_seconds())
    return budget if budget > 0 else None


async def acquire_review_lease(
    client: httpx.AsyncClient,
    requester: str,
    *,
    now: datetime | None = None,
    config: AppConfig | None = None,
) -> int | None:
    """Take the review lease for this run; ``None`` to degrade to the gate.

    ``requester`` names the review (``health_review``, ``log_review``,
    ``disk_review``) rather than this service, because the estate's
    ``gpu_leases`` rows and its queue log are read by a human deciding
    which of three simultaneous waiters is which — one name for all
    three would make the FIFO order it grants them in unreadable.

    Every ``None`` is a degradation, never a failure: the caller writes
    its digest.  ``None`` is also what a caller **must** pass on to
    :meth:`~sysadmin.core.llm_client.LLMClient.generate` as
    ``gpu_lease_held=False``, which is that parameter's default, so
    forgetting is safe in the direction that preserves today's
    behaviour.
    """
    config = config or get_config()
    base_url = arbiter_url(config)
    budget = wait_budget_seconds(now or datetime.now().astimezone(), config)
    if budget is None:
        logger.warning(
            "review_lease_past_deadline",
            extra={"requester": requester, "profile": REVIEW_PROFILE},
        )
        return None

    hold = hold_seconds(config)
    try:
        lease = await estate_queue.acquire(
            client,
            profile=REVIEW_PROFILE,
            requester=requester,
            max_hold_seconds=hold,
            wait_seconds=budget,
            base_url=base_url,
        )
    except estate_queue.QueueUnavailable as exc:
        logger.warning(
            "review_queue_unavailable",
            extra={"requester": requester, "error": str(exc)},
        )
        return None
    except estate_queue.AcquireDropped as exc:
        logger.warning(
            "review_lease_dropped",
            extra={"requester": requester, "error": str(exc)},
        )
        return None
    except estate_queue.AcquireTimeout as exc:
        logger.warning(
            "review_lease_timeout",
            extra={
                "requester": requester,
                "wait_seconds": budget,
                "error": str(exc),
            },
        )
        return None

    logger.info(
        "review_lease_granted",
        extra={
            "requester": requester,
            "lease_id": lease.id,
            "profile": lease.profile,
            "wait_seconds": budget,
            "max_hold_seconds": hold,
        },
    )
    return lease.id


async def release_review_lease(
    client: httpx.AsyncClient,
    lease_id: int,
    requester: str,
    *,
    config: AppConfig | None = None,
) -> None:
    """End the lease, best-effort — as the estate's own review does.

    A release that raised here would turn a stored review into a failed
    unit, and the arbiter's hold deadline restores the baseline anyway
    (``_expire_if_overdue``).  The failure is logged by the library.
    """
    await estate_queue.release(
        client,
        lease_id=lease_id,
        base_url=arbiter_url(config or get_config()),
        best_effort=True,
    )
    logger.info(
        "review_lease_released",
        extra={"requester": requester, "lease_id": lease_id},
    )
