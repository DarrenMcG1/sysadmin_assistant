"""The understudy's two faces, driven against the real database.

``SNAG-TRAY-008``'s check retired with the entry on 2026-08-28 — every
member of ``snag_claims.CHECKS`` names an *open* one — and **the detector
did not**.  This is that drive re-homed, ``FROZEN_TABLES``' rule and
Session 112's precedent: deleting a guard along with its last finding
takes the guard against the defect coming back, at the moment nothing
else is exercising it.

What it adds over ``tests/test_desktop_notifier.py``, which models the
database with a fake, is everything a fake cannot answer.  The fake was
written from the statements this code builds, so it agrees with them by
construction; PostgreSQL does not.  ``array_agg(DISTINCT severity)``,
``GROUP BY title`` under an ``ORDER BY MIN(created_at)``, the expanding
``NOT IN``, ``ON CONFLICT (title) DO UPDATE`` finding the right
constraint, and a ``float`` seconds → ``timestamptz`` → ``float``
round trip are all real here and all fakeable into agreement.

**The timeline is the check's, unchanged**, because it is what made the
verdict a conjunction:

1. the tray is watching; :data:`UNHEARD_TITLE` is raised and the
   understudy is correctly silent;
2. the tray goes away; :data:`ANNOUNCED_TITLE` is raised and it speaks;
3. a full ``reminder_hours`` passes and the first sweep runs — the
   witness, and the **first face** (a fault raised while the tray was
   watching, adopted);
4. the daemon restarts — a second instance, same clock, same session,
   and the only thing it lacks is what the first one said;
5. another interval passes and the second sweep runs — the second
   witness, and the **second face** (its predecessor's fault, restored).

Two leaves are supplied and everything the entry is about sits above
both: the transport (a list rather than ``notify-send``) and the two
clock readings.  The rows are real and the transaction is rolled back —
and the session **joins the outer transaction by savepoint**, because
``DesktopNotifier._remember`` commits and a plain rollback-in-a-finally
would leak.  That is not hypothetical: it happened once during this
session's own suite run, three rows into ``alerts`` and three into
``desktop_notifications``, before the harness was hardened.
"""

import asyncio
from contextlib import asynccontextmanager

import pytest

from sysadmin.core.config import get_config
from sysadmin.monitor import desktop as understudy
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.desktop import DesktopNotifier, TrayPresence
from sysadmin.monitor.models.desktop_notification import DesktopNotification

UNHEARD_TITLE = "sysadmin-live-probe: a fault raised while the tray was watching"
ANNOUNCED_TITLE = "sysadmin-live-probe: a fault the first notifier announced"
RESTARTED_TITLE = "sysadmin-live-probe: a fault the restarted notifier announced"
PROBE_TITLES = (UNHEARD_TITLE, ANNOUNCED_TITLE, RESTARTED_TITLE)
PROBE_MESSAGE = "sysadmin live probe row — never committed"


def _db_available() -> bool:
    from sqlalchemy import create_engine

    try:
        engine = create_engine(
            "postgresql+psycopg2://gaddi@localhost:5432/projects",
            connect_args={"connect_timeout": 2},
        )
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


class _SharedSession:
    """Hand the notifier the drive's session without letting it close one.

    Every database call in the module does ``async with factory() as
    session``, which against a real ``async_sessionmaker`` would open and
    close one — and closing this one would end the transaction every
    probe row lives in.  ``commit()`` is deliberately **not** intercepted:
    the session below joins the outer transaction by savepoint, so a
    commit releases a savepoint and the rollback still owns the drive.
    Suppressing it here would be the stand-in lying about the database,
    and the production write really does commit.
    """

    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        # Expired on entry, because production opens a **fresh** session
        # here and a fresh session has no identity map. Sharing one keeps
        # every row loaded by an earlier call, and ``_remember`` writes
        # through Core — so the next ``_load_spoken`` would be handed the
        # ORM objects as they were before the last reminder and restore a
        # stale ``reminders_sent``. That is the stand-in's artefact and
        # not the code's, and it cost a real assertion to find.
        self._session.expire_all()
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        # Production's factory is ``get_scheduler_session``, which
        # commits on a clean exit — so a stand-in that did not would let
        # the savepoint hardening in this file go unexercised and would
        # model a write path the daemon does not have.
        if exc[0] is None:
            await self._session.commit()
        return False


def _supplied_presence(elapsed):
    """The tray gate with its one clock reading supplied rather than slept.

    ``TrayPresence`` is monotonic and takes no clock parameter — its own
    docstring argues for both — so one leaf is overridden and
    ``is_watching`` and ``absent_for`` above it stay the module's own,
    still reading the live ``tray_grace_seconds``.  ``mark_seen()`` is
    called so ``ever_seen`` is true: the entry's first face is a tray
    that was *here and left*, and a presence that had never marked one
    would model a daemon that started before the tray.
    """

    class SuppliedPresence(TrayPresence):
        def __init__(self) -> None:
            super().__init__()
            self.mark_seen()

        def seconds_since_seen(self) -> float:
            return elapsed()

    return SuppliedPresence()


def _recorded(session, clock):
    """The real understudy with ``notify-send`` replaced by a list."""

    class RecordedNotifier(DesktopNotifier):
        def __init__(self) -> None:
            super().__init__(
                session_factory=lambda: _SharedSession(session), clock=clock
            )
            self.sent: list[tuple[str, str, str]] = []

        async def send(self, severity: str, title: str, body: str) -> bool:
            self.sent.append((severity, title, body))
            return True

    return RecordedNotifier()


def _restated(sent, title: str) -> bool:
    """Did *title* reach a screen — as a lone reminder or inside a roll-up?

    Both shapes, because ``_restate`` folds at ``_ROLLUP_THRESHOLD`` and
    this drive puts two and then three faults through it.  A probe
    reading titles alone would report the landed fix as silence.
    """
    return any(title == sent_title or title in body for _, sent_title, body in sent)


@asynccontextmanager
async def _rolled_back():
    """A session on a connection whose transaction is rolled back.

    ``join_transaction_mode="create_savepoint"`` is the load-bearing
    argument: the code under test commits.
    """
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.pool import NullPool

    config = get_config()
    engine = create_async_engine(
        config.database.url,
        poolclass=NullPool,
        connect_args={
            "server_settings": {"search_path": f"{config.database.schema_},public"}
        },
    )
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            factory = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            async with factory() as session:
                try:
                    yield session
                finally:
                    await session.rollback()
                    await outer.rollback()
    finally:
        await engine.dispose()


async def _drive() -> dict:
    from sqlalchemy import func, select, update

    from sysadmin.core.models.alert import Alert, unresolved

    async with _rolled_back() as session:
        agent = SysAdminAgent()
        agent._pending_events = []  # buffer, never publish

        pre_existing = set(
            await session.scalars(
                select(Alert.title).where(
                    Alert.title.in_(list(PROBE_TITLES)), unresolved()
                )
            )
        )

        # **The open population is controlled, inside the transaction
        # that is about to be rolled back.** Rule 6 adopts from the open
        # rows, so the box's own standing faults are candidates — and the
        # roll-up names only ``_MAX_LISTED_TITLES`` before it starts
        # counting, so five live faults sorting ahead of the probe's push
        # its own witnesses out of the body and every assertion below
        # reads as silence. That is the mutable-population trap
        # (``a-probe-keys-on-identity-not-a-mutable-field``) arriving
        # through a *cap* rather than through a title, and it is not
        # avoidable by choosing better titles: the count is the thing
        # that moves. Quieting them here is the same act as writing the
        # probe's own rows and is undone by the same rollback.
        quieted = (
            await session.execute(
                update(Alert)
                .where(unresolved())
                .values(resolved=True, resolved_at=func.now())
            )
        ).rowcount

        # One fake timeline in seconds — wall-clock shaped now, which is
        # what makes it storable: ``_remember`` renders it through
        # ``datetime.fromtimestamp``, so the round trip is the column's
        # and not a delta anything has to keep in step.
        now = [0.0]

        def clock() -> float:
            return now[0]

        config = get_config().notifications.desktop
        interval = config.reminder_hours * 3600
        standing = understudy.tray_presence
        understudy.tray_presence = _supplied_presence(clock)
        try:
            first = _recorded(session, clock)

            async def announce(notifier, title: str):
                await agent.raise_alert(session, "warning", title, PROBE_MESSAGE)
                event = agent._pending_events[-1][1]
                assert event["title"] == title, "raise_alert no longer buffers a title"
                before = len(notifier.sent)
                await notifier.on_alert_raised(event)
                return tuple(notifier.sent[before:])

            watched = await announce(first, UNHEARD_TITLE)

            now[0] = config.tray_grace_seconds + 1.0
            unwatched = await announce(first, ANNOUNCED_TITLE)

            # Read before any sweep. The reminder in step 3 writes the
            # same row, so without this the announce-time write is
            # invisible and removing it breaks nothing — which is what a
            # falsification run said, and it is the write that carries a
            # fault announced by a daemon that then dies before its first
            # reminder is due.
            announced_row = (
                await session.scalars(
                    select(DesktopNotification).where(
                        DesktopNotification.title == ANNOUNCED_TITLE
                    )
                )
            ).first()

            now[0] += interval + 1.0
            mark = len(first.sent)
            first_count = await first.sweep_reminders()
            first_sent = tuple(first.sent[mark:])

            # 4 — the restart.  A second instance, and the only thing it
            # lacks is what the first one said.
            second = _recorded(session, clock)
            after_restart = await announce(second, RESTARTED_TITLE)

            now[0] += interval + 1.0
            mark = len(second.sent)
            second_count = await second.sweep_reminders()
            second_sent = tuple(second.sent[mark:])

            session.expire_all()  # the drive's own read, same reason
            stored = {
                row.title: row
                for row in await session.scalars(select(DesktopNotification))
            }
            inherited = second._spoken.get(ANNOUNCED_TITLE)
        finally:
            understudy.tray_presence = standing

        return {
            "pre_existing": pre_existing,
            "quieted": quieted,
            "spoke_while_watched": bool(watched),
            "spoke_unwatched": bool(unwatched),
            "spoke_after_restart": bool(after_restart),
            "witness_first": _restated(first_sent, ANNOUNCED_TITLE),
            "unheard_adopted": _restated(first_sent, UNHEARD_TITLE),
            "witness_second": _restated(second_sent, RESTARTED_TITLE),
            "remembered": _restated(second_sent, ANNOUNCED_TITLE),
            "first_count": first_count,
            "second_count": second_count,
            "adopted_titles": {t for t, row in stored.items() if row.adopted},
            "stored_titles": set(stored),
            "written_at_announce": announced_row is not None,
            # How the restarted instance came by its predecessor's fault.
            # ``remembered`` alone cannot say: with adoption working, the
            # second instance would pick the same title up off the open
            # rows and the two mechanisms are indistinguishable by output.
            # Restoration keeps the episode — a reminder already sent and
            # ``adopted`` false; adoption resets both.
            "inherited_adopted": None if inherited is None else inherited.adopted,
            "inherited_reminders": (
                None if inherited is None else inherited.reminders_sent
            ),
            "stored_reminders": stored[ANNOUNCED_TITLE].reminders_sent,
        }


@pytest.fixture(scope="module")
def reading():
    if not _db_available():
        pytest.skip("local postgres (projects DB) not reachable")
    return asyncio.run(_drive())


class TestTheUnderstudyAgainstTheRealDatabase:
    def test_the_premises_hold_or_nothing_below_means_anything(self, reading):
        """The witness, and the reason it is not optional.

        Both faces are measured as **speech**, and a notifier that had
        stopped sweeping at all is silent in the same way a broken one
        is — so each sweep has to produce the fault its own instance
        announced before its other output means anything.
        """
        assert reading["pre_existing"] == set(), "a live row collides with a probe title"
        assert reading["spoke_while_watched"] is False
        assert reading["spoke_unwatched"] is True
        assert reading["spoke_after_restart"] is True
        assert reading["witness_first"] is True
        assert reading["witness_second"] is True

    def test_the_first_face_a_fault_the_tray_spoke_for_is_adopted(self, reading):
        assert reading["unheard_adopted"] is True
        assert UNHEARD_TITLE in reading["adopted_titles"]
        # Exact, because the drive quiets the box's own open rows inside
        # its transaction first. Without that the adoption scan is
        # *supposed* to find them — the first live run picked up a real
        # ``High VRAM usage on AMD Radeon RX 7900 XTX`` opened four
        # minutes earlier — and five of them sorting ahead of the probe
        # push its witnesses out of the roll-up body entirely.
        assert reading["first_count"] == 2

    def test_the_second_face_a_restart_inherits_what_was_said(self, reading):
        """And *how* it inherited it, which the retired check could not say.

        That check asked only whether the restarted instance restated its
        predecessor's fault — and once rule 6 landed, adoption produces
        exactly that output from the open rows, so a fix for face 1 alone
        would have read as both faces closed. The two are told apart by
        what survives: a restored fault carries the reminder the first
        instance already sent and is not marked adopted, and an adopted
        one is a fresh episode.
        """
        assert reading["remembered"] is True
        assert reading["second_count"] == 3
        assert reading["inherited_adopted"] is False
        assert reading["inherited_reminders"] >= 1

    def test_an_announcement_is_written_before_any_reminder_is_due(self, reading):
        """A daemon that announces a fault and dies before the first

        reminder must still be carrying it when it comes back.
        """
        assert reading["written_at_announce"] is True

    def test_an_announced_fault_is_stored_unadopted(self, reading):
        """The flag is what bounds adoption across a restart, so it has to

        distinguish the two paths against the real column default.
        """
        assert reading["stored_titles"] == set(PROBE_TITLES)
        assert reading["adopted_titles"] == {UNHEARD_TITLE}

    def test_the_upsert_carries_the_reminder_count_forward(self, reading):
        """Two reminders, two increments, against the real ``ON CONFLICT``.

        The in-memory count cannot witness this — the sweep increments it
        before anything reads it back — so the assertion is on the
        *stored* value, which is the one a restart depends on.
        """
        assert reading["stored_reminders"] >= 2

    def test_nothing_survives_the_rollback(self):
        """The property that makes writing to the live database allowable.

        Asserted rather than promised, and it is the assertion that would
        have caught the leak this session actually produced.
        """
        if not _db_available():
            pytest.skip("local postgres (projects DB) not reachable")
        from sqlalchemy import create_engine, text

        engine = create_engine("postgresql+psycopg2://gaddi@localhost:5432/projects")
        try:
            with engine.connect() as conn:
                alerts = conn.execute(
                    text(
                        "SELECT count(*) FROM sysadmin.alerts WHERE title = ANY(:t)"
                    ),
                    {"t": list(PROBE_TITLES)},
                ).scalar()
                stored = conn.execute(
                    text(
                        "SELECT count(*) FROM sysadmin.desktop_notifications "
                        "WHERE title = ANY(:t)"
                    ),
                    {"t": list(PROBE_TITLES)},
                ).scalar()
        finally:
            engine.dispose()
        assert (alerts, stored) == (0, 0)
