"""Shared LLM HTTP client for llama.cpp's llama-server.

The wire mechanics (payload construction, POST, content extraction, the
health probe) live in ``estate.llama`` since 2026-08-12 (estate-manager
ADR-0006; this repository's ADR-0004). What stays here is this service's
convention: **failures degrade to ``None`` with a warning, never an
exception** — callers treat "no narrative" as a first-class outcome — and
the event-loop-safe client lifecycle below.

Note: llama-server serves a single loaded model, so the ``model`` field in
requests is largely informational — it is recorded but does not switch models.
"""

import asyncio
import logging

import httpx
from estate import gpu as estate_gpu
from estate.gpu import GpuBusy, ensure_gpu_idle
from estate.llama import (
    LlamaConnectError,
    LlamaInvalidResponse,
    LlamaStatusError,
    LlamaTimeout,
    chat_payload,
    extract_content,
    post_chat,
    probe_health,
)

from sysadmin.core.async_http import LoopBoundClient
from sysadmin.core.config import get_config

logger = logging.getLogger(__name__)

#: How long a call that follows one of this service's own inferences may
#: wait for that inference to leave the busy counter (``SNAG-GPU-007``).
#: Measured 2026-10-21 over eight drives on llama-server: in six the
#: counter read at most 25 by the second sample, 0.05 s after the reply;
#: in the other two another holder had the card at 96–99 % and it stayed
#: there for the whole 4 s watched.  So the tail is one sample long, the
#: budget is twenty times it, and a card someone else is using is still
#: refused, one second later than before.
OWN_TAIL_BUDGET_SECONDS = 1.0

#: The interval between reads while waiting; one sysfs read each.
OWN_TAIL_POLL_SECONDS = 0.05


async def wait_for_own_tail(pci_slot: str, threshold: int) -> None:
    """Return once the counter reads idle, unreadable, or the budget is spent.

    This does not decide anything.  The single read in
    :meth:`LLMClient.generate` still follows it and still refuses, so a
    wait that runs out ends in the same ``llm_gpu_busy`` as before.  It
    exits on the first idle read, unlike ``estate.gpu.sustained_busy``'s
    fixed window, so an idle card costs one read and no sleep.
    """
    if not pci_slot:
        return
    loop = asyncio.get_running_loop()
    deadline = loop.time() + OWN_TAIL_BUDGET_SECONDS
    while True:
        busy = estate_gpu.sample_gpu_busy(pci_slot)
        if busy is None or busy <= threshold or loop.time() >= deadline:
            return
        await asyncio.sleep(OWN_TAIL_POLL_SECONDS)


class LLMClient:
    """HTTP client for llama-server's OpenAI-compatible API.

    The underlying ``httpx.AsyncClient`` is held by a
    :class:`~sysadmin.core.async_http.LoopBoundClient`: the log
    aggregator calls this from APScheduler threads, each with its own
    short-lived event loop, and a client shared across loops raises
    "Event loop is closed" (SNAG-AGENT-003). This is why the estate
    library takes the client as an argument rather than owning one.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Initialise the client.

        Args:
            transport: optional httpx transport override (used by tests to
                inject a MockTransport).
        """
        self._transport = transport
        self._http = LoopBoundClient(self._build_client)

    async def startup(self) -> None:
        await self._http.open()

    async def shutdown(self) -> None:
        await self._http.close()

    def _build_client(self) -> httpx.AsyncClient:
        timeout = get_config().llm.timeout_seconds
        return httpx.AsyncClient(timeout=timeout, transport=self._transport)

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        *,
        gpu_lease_held: bool = False,
        follows_own_inference: bool = False,
    ) -> str | None:
        """Generate a chat completion from llama-server.

        Returns the response text, or None if the server is unavailable
        — or if the dGPU is busy with foreground work (ADR-0004 as
        amended 2026-08-12): it shares Alfred's server on a GPU someone
        may be gaming on, and a busy GPU degrades to "no narrative this
        run", the same first-class outcome callers already handle.

        **The gate is the single read, and it stays one because this
        call site cannot answer the window's question for every one of
        its invocations** (``estate.gpu.sustained_busy``, estate
        ADR-0074 §2, announced here as message ``df4113cb`` and decided
        in Session 134). That docstring licenses the blocking ~1.5 s
        min-of-N window wherever nobody is waiting on the answer and
        refuses it where a request is held open — a test about the
        *invocation*, not the function, which is the wording change the
        announcement carried. All three producers here are reached both
        ways: ``run_weekly_review`` in :mod:`sysadmin.monitor.log_review`,
        :mod:`sysadmin.monitor.health_review` and
        :mod:`sysadmin.files.review` is a Monday job with nobody
        waiting, while ``POST /api/logs/review/generate``,
        ``POST /api/sysadmin/review/generate`` and
        ``POST /api/files/review/generate`` each ``await`` the same
        function inline and hold the request open across it. That is
        estate-manager's own ``SNAG-ESTATE-090`` shape at three gates
        rather than one.

        Pushing the choice up to the six callers is the available
        remedy and was **costed and refused**, because the measurement
        inverts the obvious ranking three ways. The window's entire
        benefit is the ~1-in-120 transient Alfred sampled on an idle
        desktop. The waiterless path fires **three times a week** — one
        dispatch per weekly review. And a false defer here does not cost
        a review, it costs *prose*: the caller falls back to
        ``build_fallback_narrative`` and still stores, serves and briefs
        a deterministic digest with ``llm_used=False``. So the window
        would rescue roughly one narrative every forty weeks, in
        exchange for a parameter threaded through three signatures and a
        seventh caller free to default it wrongly.

        The waiter is also the **majority** invocation rather than the
        edge case, which is why no sentence here calls this service's
        inference deferrable housekeeping any more: of the six reviews
        this box has generated in its life, **five came from the routes
        and one from the Monday job** (measured 2026-08-30 across
        ``health_reviews``, ``log_reviews`` and ``disk_reviews``).

        ``tests/test_gpu_gate_invocations.py`` holds both halves — the
        premise that each gate is still reached from both classes, and
        the pre-staged rule that an adopted window must go through
        ``asyncio.to_thread``, since every call site here runs inside an
        event loop and the window would otherwise stall it.

        **``gpu_lease_held`` is the absence of a gate, not a third
        sampler** (``SNAG-SCHED-003``, 2026-08-31).  A caller holding an
        estate GPU lease has already had the card read on its behalf, by
        the arbiter, as a *retry* rather than a refusal — and the arbiter
        holds the card until release.  Reading the counter again here
        would put the give-up back while holding the card, which is
        estate-manager's ADR-0076 §4 layering met from this side: a job
        reading sysfs while a row in the estate's own database names the
        holder.  This is estate-manager's ``GpuGate.HELD``; the value
        below it, ``SUSTAINED``, does not exist here because the window
        was costed and refused above, so a ``bool`` expresses everything
        this service has and an enum would carry a member nothing can
        reach.

        It defaults to ``False`` — today's behaviour — so the seventh
        caller the refusal above worries about defaults to the *safe*
        direction: a lease-holder that forgets the flag reads the counter
        once and may defer, which is a lost narrative and never a lost
        review.  What the flag cannot do is the reverse: it is passed
        only where :func:`sysadmin.core.gpu_lease.acquire_review_lease`
        returned a lease id, so asserting a hold nobody has requires
        writing the literal.

        **Note what this does to the refusal above rather than leaving it
        to be inferred.**  The window's argument turned on the gate being
        reached from both invocation classes, so it could not answer
        ``sustained_busy``'s question for all of them.  The waiterless
        class now takes a lease and skips the gate entirely, which leaves
        the gate's population as the three ``POST …/review/generate``
        routes alone — precisely the class the single read is *right*
        for.  The refusal is therefore stronger than when it was written,
        not weaker, and the window's population here is now empty.
        ``tests/test_gpu_gate_invocations.py`` holds that as a measured
        premise rather than as prose.

        **``follows_own_inference`` waits for this service's own tail,
        then reads once as before** (``SNAG-GPU-007``, 2026-10-21).  A
        call made straight after one of ours reads that call still on the
        counter: seven of seven condense passes on the routes were
        refused that way on 2026-09-29, on a card that read 6–12 % a
        moment later.  :func:`wait_for_own_tail` polls until the counter
        reads idle, for at most :data:`OWN_TAIL_BUDGET_SECONDS`, and the
        single read then decides.  This is not the window refused above.
        That one was a fixed min-of-N for every call, to rescue a
        transient seen once in about forty weeks.  This one exits on the
        first idle read, and only the call after our own pays for it, and
        that call was refused every time.  It does nothing when
        ``gpu_lease_held`` is set, because no gate is read then.

        Free-text path: ``temperature=None`` keeps the server's own
        sampling defaults — this call generates prose, not structured
        extraction, so the estate's structured-path temperature pin does
        not apply (estate ADR-0006 decision 3).
        """
        config = get_config()
        model = model or config.llm.model

        if not gpu_lease_held:
            if follows_own_inference:
                await wait_for_own_tail(
                    config.llm.gpu_pci_slot, config.llm.gpu_busy_threshold
                )
            try:
                ensure_gpu_idle(config.llm.gpu_pci_slot, config.llm.gpu_busy_threshold)
            except GpuBusy as e:
                logger.warning(
                    "llm_gpu_busy",
                    extra={
                        "busy_percent": e.busy_percent,
                        "threshold": e.threshold,
                        "model": model,
                    },
                )
                return None

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = chat_payload(model, messages, temperature=None, stream=False)

        try:
            async with self._http.borrow() as client:
                response = await post_chat(client, config.llm.url, payload)
            return extract_content(response)
        except (LlamaTimeout, LlamaConnectError) as e:
            logger.warning(
                "llm_unavailable",
                extra={"error": str(e), "model": model},
            )
            return None
        except LlamaStatusError as e:
            # One status means more than one thing (a 500 is a full KV
            # cache and also an unparseable body), so log llama-server's
            # own text. ``None`` when the body was not its error shape.
            # ``error_message``, not ``message``: LogRecord reserves that
            # name and ``extra`` raises KeyError on it.
            logger.warning(
                "llm_error",
                extra={
                    "status": e.status,
                    "error_message": e.message,
                    "error_type": e.error_type,
                    "model": model,
                },
            )
            return None
        except LlamaInvalidResponse:
            logger.warning(
                "llm_malformed_response",
                extra={"model": model},
            )
            return None
        except Exception as e:
            logger.error(
                "llm_unexpected_error",
                extra={"error": str(e), "model": model},
            )
            return None

    async def is_available(self) -> bool:
        """Check if llama-server is up with its model loaded.

        llama-server returns 200 ``{"status":"ok"}`` when ready, and 503
        while the model is still loading.
        """
        config = get_config()
        try:
            async with self._http.borrow() as client:
                return await probe_health(client, config.llm.url)
        except Exception:
            return False
