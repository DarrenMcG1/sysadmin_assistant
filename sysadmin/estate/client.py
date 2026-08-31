"""Pulling the estate's five published surfaces.

One HTTP round trip each, all four concurrently, and **a result per
surface** rather than one result for the pull.  That shape is the whole
point of this module: the surfaces are served by one process but they
answer different questions, and a 500 from ``/api/projects/attention``
must not stop this run from judging the scan's invariants — nor, more
importantly, let it *resolve* them.  See
:meth:`sysadmin.estate.agent.EstateJudgeAgent._execute` for why the
second half is the dangerous one.

**Unreachability is not judged here, and not judged at all.**
``estate-manager-api`` is already an ``http`` entry in ``services.yaml``
polled every 300 s by the sysadmin agent, and both estate timers are
``kind: timer`` entries beside it.  A second owner of that lifecycle is
the defect ``_resolve_recovered``'s docstring names three times over —
one side closes a row while the other still holds it true.  So an
unreachable 8400 costs a log line and a field in
``agent_runs.details``, and the alert about it comes from the service
check that owns it.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

#: Surface id → path on the estate's 8400 service.
#:
#: The ids are the vocabulary of the whole package: they key the
#: judgement functions, they key ``agent_runs.details``, and they select
#: which title patterns a run is allowed to sweep.  Paths are relative so
#: the base URL stays in one place (config), and the ids are stable even
#: if a path moves.
SURFACE_PATHS: dict[str, str] = {
    "projects_invariants": "/api/projects/invariants",
    "projects_attention": "/api/projects/attention",
    "audit_invariants": "/api/audit/invariants",
    "audit_findings": "/api/audit/findings",
    "queue_invariants": "/api/queue/invariants",
}

#: Every surface id, in the order a reader would want them reported.
SURFACES: tuple[str, ...] = tuple(SURFACE_PATHS)


@dataclass(frozen=True)
class SurfaceResult:
    """One surface's answer, or the reason there is not one.

    ``payload`` and ``error`` are mutually exclusive and one is always
    set — a result carrying neither would be a third state ("read, but
    empty") that no caller wants to distinguish, since an empty
    ``attention`` payload is a legitimate and common answer meaning
    nothing needs attention.
    """

    surface: str
    payload: dict[str, Any] | None = None
    error: str | None = None

    @property
    def read(self) -> bool:
        """Whether this surface was read successfully.

        The agent gates *both* raising and resolving on this.  A surface
        that was not read has an unknown state, and the rule this
        repository has written down twice — in ``_resolve_recovered``
        ("``error`` … the state is unknown and resolving on unknown
        announces a recovery nobody observed") and in
        :mod:`sysadmin.core.schema_guard` — is that unknown must not be
        spent as good news.
        """
        return self.error is None


def _describe(exc: Exception) -> str:
    """The failure as one short line, class name first.

    Mirrors :func:`sysadmin.monitor.agent._truncate_error`'s reasoning at
    a smaller scale: the class name is what classifies the fault, and
    ``ConnectError`` (8400 is down, somebody else's alert) reads very
    differently from ``JSONDecodeError`` (8400 answered with something
    that is not this contract, which would be ours).
    """
    return " ".join(f"{exc.__class__.__name__}: {exc}".split())[:300]


async def _fetch_object(
    client: httpx.AsyncClient, url: str, what: str
) -> tuple[dict[str, Any] | None, str | None]:
    """One GET returning ``(payload, error)``, never raising.

    Extracted from :func:`_fetch` rather than written beside it, because
    the two would be a second statement of what a failed read of 8400
    looks like — and the direction they drift in is the one that matters,
    since one of them would eventually stop treating an unparseable body
    as a failure.  :func:`_fetch` keeps the surface vocabulary; this
    keeps the transport.
    """
    try:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 — every failure is the same news
        logger.warning(
            "estate_surface_unread",
            extra={"surface": what, "url": url, "error": _describe(exc)},
        )
        return None, _describe(exc)
    if not isinstance(payload, dict):
        return None, f"TypeError: expected a JSON object, got {type(payload).__name__}"
    return payload, None


async def _fetch(
    client: httpx.AsyncClient, base_url: str, surface: str
) -> SurfaceResult:
    """Read one surface, converting every failure into a result.

    Nothing raises out of here.  A pull of five surfaces where one throws
    would either lose the other three (if it propagates) or need a
    ``gather(return_exceptions=True)`` and a second place that decides
    what an exception means — and that second place is where the
    "unreachable is not a judgement" rule would get forgotten.
    """
    url = f"{base_url.rstrip('/')}{SURFACE_PATHS[surface]}"
    payload, error = await _fetch_object(client, url, surface)
    if payload is None:
        return SurfaceResult(surface=surface, error=error)
    return SurfaceResult(surface=surface, payload=payload)


async def pull_all(
    client: httpx.AsyncClient, base_url: str
) -> dict[str, SurfaceResult]:
    """Every surface, concurrently, keyed by surface id.

    Concurrent because the five are independent and the producer is one
    process on localhost: five sequential 10-second timeouts against a
    hung 8400 would be a 50-second agent run, which
    ``idle_in_transaction_session_timeout`` has already taught this
    codebase to care about (SNAG-AGENT-003).  The caller holds no
    transaction across this, but the habit is cheap.
    """
    results = await asyncio.gather(
        *(_fetch(client, base_url, surface) for surface in SURFACES)
    )
    return {result.surface: result for result in results}


# --- The arbiter's active lease -----------------------------------------
#
# Everything below serves one consumer that is **not** the estate judge:
# the service family in :mod:`sysadmin.monitor.agent`, which needs to know
# whether a service it has just measured unreachable was stopped on
# purpose (``SNAG-AGENT-011``).
#
# **Why it lives here and not in ``monitor``.** This module is the one
# reader of 8400 in this repository, and a second HTTP caller to the same
# host is the second-owner defect at the size of a client: two places
# that resolve the base URL, two that decide what an exception means, two
# that could come to disagree about whether an unreadable estate is bad
# news.  What stays with the service family is the *judgement* — which
# rung, and which ``services.yaml`` entry is which unit — because that is
# the half ``judgements.py`` rule 3 read in reverse forbids the estate
# judge from acquiring.  So the split is transport here, verdict there,
# and this module deliberately returns a **reading** rather than a
# severity: nothing below knows what a rung is.

#: Path template for one lease by id.
#:
#: Kept out of :data:`SURFACE_PATHS` on purpose.  That map is the
#: vocabulary of the *pull* — five static paths, fetched concurrently,
#: keyed by an id that also keys ``agent_runs.details`` and selects which
#: title patterns a run may sweep.  This path takes a parameter and is
#: fetched by one caller for one question, so putting it in the map would
#: give every surface-keyed consumer a sixth member it must then learn to
#: skip.
LEASE_PATH = "/api/queue/leases/{lease_id}"

#: A lease is granted and its stopped units were read.
ARBITRATION_GRANTED = "granted"

#: The estate answered and no lease is granted.  Nothing is arbitrated.
ARBITRATION_IDLE = "idle"

#: The estate could not be read, or answered something this contract
#: cannot parse.  **Not** a synonym for "nothing is stopped" — see
#: :meth:`ArbitratedStops.stopped`.
ARBITRATION_UNREAD = "unread"


@dataclass(frozen=True)
class ArbitratedStops:
    """Which units the estate's arbiter has stopped under the active lease.

    A **reading**, in :meth:`sysadmin.units.ports.PortAttribution.reading`'s
    sense rather than an answer that can be absent: ``units`` being empty
    is three different facts (no lease, a lease that stops nothing, and a
    read that failed), and a consumer that cannot tell them apart is
    ``ports_checked``'s defect — zero-because-blind served as
    zero-because-clean.  :attr:`reading` is what separates them and is
    always one of the three constants above.

    **Failing open is a property of the shape, not a branch someone has
    to remember.**  ``units`` is populated only on
    :data:`ARBITRATION_GRANTED`, so :meth:`stopped` answers ``False`` for
    every way of not-knowing and the caller's rung is left exactly where
    it was.  That is ``collation.py``'s posture rather than
    ``schema_guard``'s, and it is
    :meth:`~sysadmin.estate.agent.EstateJudgeAgent._attribution`'s stated
    rule one domain over: *the enrichment is not allowed to become a
    dependency of the alert*.  An 8400 that is down must cost this box a
    log line, never the silencing of every service outage on it.
    """

    reading: str
    units: frozenset[str] = frozenset()
    lease_id: int | None = None
    profile: str | None = None
    error: str | None = None

    @property
    def known(self) -> bool:
        """Whether the estate answered at all.

        ``False`` for :data:`ARBITRATION_UNREAD` only.  Callers use it to
        *record* what they knew, never to decide the rung — the rung
        falls out of :meth:`stopped`, which is already correct when this
        is ``False``.
        """
        return self.reading != ARBITRATION_UNREAD

    def stopped(self, unit: str | None) -> bool:
        """Did the arbiter stop ``unit`` under the lease it holds now?

        ``unit`` is a systemd unit name as ``services.yaml`` declares it
        (``venture-chat.service``), which is the same spelling the estate
        writes into ``stopped_units`` — verified against leases 30-34 on
        2026-08-31, every one naming ``["venture-chat.service"]``.

        ``None`` answers ``False``: a service with no unit cannot have
        been stopped by something that stops units, and the estate's
        ``http``-only entries are exactly the ones with no unit to match.
        """
        return unit is not None and unit in self.units


async def read_arbitrated_stops(
    client: httpx.AsyncClient, base_url: str
) -> ArbitratedStops:
    """The units the estate has deliberately stopped, right now.

    **Two calls, and the second one is why.**  The obvious reading of
    ``SNAG-AGENT-011`` was that ``GET /api/queue/invariants`` publishes
    this, because that is the surface :func:`pull_all` already reads.  It
    does not: ``Arbiter.invariants`` selects an explicit column list —
    ``id, profile, requester, granted_at, hold_deadline, hold_overdue`` —
    and pops the last before returning, so ``active_lease`` reaches the
    wire with five keys and ``stopped_units`` is not among them.  The
    field is real and lives on ``gpu_leases``, which estate rule 1
    forbids this repository from reading, and on
    ``GET /api/queue/leases/{id}``, which is ``_public(SELECT * …)`` and
    answers for a **released** lease as readily as a granted one.  So the
    path is ``invariants`` for the id, then the lease for its stops.

    Verified against the producer's own source and against the live
    service on 2026-08-31 rather than taken from the snag's prose, which
    had it wrong in exactly this way: a field is a property of a *route*,
    not of a table, and only the handler's projection can say which.

    **Filing at estate-manager for the field on ``invariants`` was
    weighed and refused.**  It is one call rather than two and is
    arguably the field's right home — ``waiting_reason`` arrived by that
    route, their ADR-0077 after our message ``d1939cf7`` — but it parks a
    cost this box pays *nightly* behind another repository's sitting.
    Two calls on the raise path is the cheaper trade, and if the estate
    ever does publish it here the second hop becomes dead code that
    deletes cleanly.

    Every failure is :data:`ARBITRATION_UNREAD` and nothing raises, which
    is the whole contract — see :class:`ArbitratedStops`.
    """
    payload, error = await _fetch_object(
        client, f"{base_url.rstrip('/')}{SURFACE_PATHS['queue_invariants']}",
        "queue_invariants",
    )
    if payload is None:
        return ArbitratedStops(reading=ARBITRATION_UNREAD, error=error)

    lease = payload.get("active_lease")
    if lease is None:
        # The estate answered and holds nothing.  A real fact, not a
        # failure: this is what every daytime read returns.
        return ArbitratedStops(reading=ARBITRATION_IDLE)
    if not isinstance(lease, dict):
        return ArbitratedStops(
            reading=ARBITRATION_UNREAD,
            error=f"TypeError: active_lease is {type(lease).__name__}",
        )

    lease_id = lease.get("id")
    # `isinstance(True, int)` is True, so bools are refused explicitly —
    # `judge_audit_findings` rule 4's guard, for its reason: a bool
    # formatted into the path yields `/api/queue/leases/True`, a 422 that
    # would read as an unreachable estate.
    if not isinstance(lease_id, int) or isinstance(lease_id, bool):
        return ArbitratedStops(
            reading=ARBITRATION_UNREAD,
            error=f"TypeError: active_lease.id is {type(lease_id).__name__}",
        )

    profile = lease.get("profile")
    lease_payload, error = await _fetch_object(
        client,
        f"{base_url.rstrip('/')}{LEASE_PATH.format(lease_id=lease_id)}",
        "queue_lease",
    )
    if lease_payload is None:
        # The id is carried even though the reading is unread: it is what
        # a human needs to run the second call by hand, and a reading
        # that knows *which* lease it could not read is strictly more
        # useful than one that does not.
        return ArbitratedStops(
            reading=ARBITRATION_UNREAD,
            lease_id=lease_id,
            profile=profile if isinstance(profile, str) else None,
            error=error,
        )

    units = lease_payload.get("stopped_units")
    if units is None:
        # A granted lease whose profile stops nothing — the estate's own
        # `estate-review` profile is declared exactly this way.  Read,
        # and the answer is "none", which is not the same as unread.
        units = []
    if not isinstance(units, list):
        return ArbitratedStops(
            reading=ARBITRATION_UNREAD,
            lease_id=lease_id,
            profile=profile if isinstance(profile, str) else None,
            error=f"TypeError: stopped_units is {type(units).__name__}",
        )

    return ArbitratedStops(
        reading=ARBITRATION_GRANTED,
        units=frozenset(u for u in units if isinstance(u, str)),
        lease_id=lease_id,
        profile=profile if isinstance(profile, str) else None,
    )
