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
    try:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 — every failure is the same news
        logger.warning(
            "estate_surface_unread",
            extra={"surface": surface, "url": url, "error": _describe(exc)},
        )
        return SurfaceResult(surface=surface, error=_describe(exc))

    if not isinstance(payload, dict):
        # Defensive for the same reason `core/contracts.py` parses
        # defensively: the producer is another repository on its own
        # release cycle, and a list where a dict was promised is a
        # contract break rather than an outage.
        return SurfaceResult(
            surface=surface,
            error=f"TypeError: expected a JSON object, got {type(payload).__name__}",
        )
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
