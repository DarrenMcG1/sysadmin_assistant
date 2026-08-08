"""Event-loop-safe reuse of ``httpx.AsyncClient`` instances.

An ``AsyncClient`` binds its pooled keep-alive connections to whichever
event loop was running when those connections were opened.  This service
runs its agents from APScheduler threads via ``asyncio.run()``, which
creates a fresh loop for every run and **closes** it afterwards — so a
client built once during the FastAPI lifespan later hands out connections
belonging to a dead loop and raises ``RuntimeError: Event loop is closed``
(SNAG-AGENT-003).  Only hosts whose pooled connection happened to have
been dropped in the meantime got a fresh connection and looked healthy,
which is why the failure presented as intermittent and per-host.

:class:`LoopBoundClient` records the loop a long-lived client was built on
and lends that client out *only* while the same loop is running.  On any
other loop it yields a short-lived client that is closed as soon as the
caller is done — correct everywhere, and nothing is leaked.

Typical use::

    self._http = LoopBoundClient(lambda: httpx.AsyncClient(timeout=10.0))

    async with self._http.scoped():        # around one agent run
        ...
    async with self._http.borrow() as c:   # at the call site
        await c.get(url)
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import httpx


class LoopBoundClient:
    """A shareable :class:`httpx.AsyncClient` that never crosses event loops."""

    def __init__(self, factory: Callable[[], httpx.AsyncClient]) -> None:
        """Args:
            factory: builds a fresh client; called for every new client.
        """
        self._factory = factory
        self._client: httpx.AsyncClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def client(self) -> httpx.AsyncClient | None:
        """The long-lived client, if one is open (may belong to another loop)."""
        return self._client

    def attach(
        self,
        client: httpx.AsyncClient,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Adopt an already-built client.

        ``loop=None`` means *no affinity* — the client is lent out on any
        loop.  Intended for tests injecting a stub; production code uses
        :meth:`open` or :meth:`scoped`, which record the real loop.
        """
        self._client = client
        self._loop = loop

    async def open(self) -> httpx.AsyncClient:
        """Open the long-lived client, bound to the running loop."""
        await self.close()
        client = self._factory()
        self._client = client
        self._loop = asyncio.get_running_loop()
        return client

    async def close(self) -> None:
        """Close the long-lived client and forget it."""
        client, loop = self._client, self._loop
        self._client = None
        self._loop = None
        if client is None:
            return
        if loop is not None and loop is not asyncio.get_running_loop():
            # Its loop has moved on — awaiting aclose() here would drive a
            # transport attached to a loop we are not running.  Drop the
            # reference instead and let the sockets be reclaimed.
            return
        await client.aclose()

    @asynccontextmanager
    async def borrow(self) -> AsyncIterator[httpx.AsyncClient]:
        """Yield a client that is safe to use on the *currently running* loop.

        Reuses the long-lived client when it belongs to this loop (or has
        no affinity); otherwise builds a throwaway one and closes it on
        exit.
        """
        client = self._client
        if client is not None and self._loop in (None, asyncio.get_running_loop()):
            yield client
            return
        async with self._factory() as fresh:
            yield fresh

    @asynccontextmanager
    async def scoped(self) -> AsyncIterator[httpx.AsyncClient]:
        """Own a client for the duration of the block, bound to this loop.

        Wrap a unit of work that gets its own event loop — an agent run —
        so every :meth:`borrow` inside shares one connection pool and that
        pool is closed deterministically when the block exits.
        """
        previous_client, previous_loop = self._client, self._loop
        async with self._factory() as client:
            self._client = client
            self._loop = asyncio.get_running_loop()
            try:
                yield client
            finally:
                self._client = previous_client
                self._loop = previous_loop
