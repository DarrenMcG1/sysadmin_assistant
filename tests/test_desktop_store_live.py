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

**Three leaves are supplied** and everything the entry is about sits
above all of them: the transport (a list rather than ``notify-send``),
the two clock readings, and — since ``SNAG-TRAY-010`` — the DND gate.

That third one was the entry, and it was missing because it does not
*look* like a clock.  :meth:`DndManager.is_active` calls
``datetime.now()`` itself, so it reads the **real** wall clock whatever
clock the notifier was handed; the shipped ``notifications.dnd.schedule``
is ``23:00 → 07:00`` and the probes are raised at ``warning``, which
``allow_critical`` does not exempt.  Run inside that window every send
was refused and this file failed **6 of 7** — the premise test among
them — which is where Session 129 found it at 05:23.

The symptom read as a contradiction and that is what made it worth
recording: *silent, yet the rows are stored and adopted.*  DND gates
:meth:`DesktopNotifier._handle` before the send and the ``due`` filter
before :meth:`_restate`, and **not** :meth:`_adopt`, which writes
unconditionally — so all three probe titles were adopted and stored by a
notifier that had never spoken.  :data:`sent_total` in the reading is
what tells the two apart at a glance, and it is asserted rather than
merely recorded: **zero** means a gate above the sweep refused
everything, where a sweep that ran and found nothing due leaves the
announce-time sends behind it.

The rows are real and the transaction is rolled back —
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
from sysadmin.monitor.dnd import dnd_manager
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


def _hold_dnd_off() -> bool | None:
    """The third leaf: DND held off.  Returns what to restore afterwards.

    Shaped like ``standing = understudy.tray_presence`` beside it rather
    than as a context manager, because the two leaves are installed and
    restored by one ``try``/``finally`` and a second idiom for the second
    leaf would read as a second mechanism.

    ``set_manual_override`` rather than a monkeypatch, because it is the
    manager's **public** way of saying exactly this and the route and the
    tray both use it — a stand-in reaching past it would model a state
    the box cannot be in.  ``None`` is restored rather than ``False``:
    the two differ (``None`` defers to the schedule) and a drive that
    left the singleton forced-off would silence the DND window for every
    test after it in the same process, which is this file's own leak
    class one object over.

    Not a narrowing of what is under test.  Gate 1 (tray presence) is
    supplied for the same reason one line up: the entry is about the
    store and adoption, and a gate above them decides nothing about
    either.  What is refused is the *other* two repairs — skipping
    overnight hides a regression for a third of every day, and letting
    it fail overnight is ``SNAG-TRAY-010``.
    """
    standing = dnd_manager.manual_override
    dnd_manager.set_manual_override(False)
    return standing


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
        # Captured, because the leak guard below asserts the drive put
        # back *what it found* rather than a literal. Pinning ``None``
        # would be an assertion about whatever ran before this file in
        # the same process, and would fire at a correct restore.
        standing_dnd = _hold_dnd_off()
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

            # Read while the leaf is still held, because that is the only
            # moment it says anything: it is the *supplied* verdict, so it
            # witnesses that the override took rather than that the box
            # happens to be outside the window. Asked of ``dnd_manager``
            # and not of the notifier, which is the subject.
            dnd_suppressing = dnd_manager.should_suppress("warning")
            sent_total = len(first.sent) + len(second.sent)
        finally:
            dnd_manager.set_manual_override(standing_dnd)
            understudy.tray_presence = standing

        return {
            "pre_existing": pre_existing,
            "quieted": quieted,
            # **The one number that separates the two silences**
            # (``SNAG-TRAY-010``).  Every other "did it speak" reading
            # below is a ``bool`` over a *slice* of ``sent``, so all of
            # them read ``False`` whether the sweep ran and found nothing
            # due or a gate above the sweep refused the lot — and the
            # entry's symptom was the whole set reading ``False`` at
            # once, which no slice can attribute.  The total can: a sweep
            # that merely found nothing due still leaves the two
            # announce-time sends behind it, so **zero** is only
            # reachable by a gate above ``_handle``.  Total across both
            # instances, because the restart is inside the timeline.
            "sent_total": sent_total,
            # The gate that was actually shut, kept beside the number it
            # explains rather than left to the next reader to guess.
            "dnd_suppressing": dnd_suppressing,
            "dnd_standing": standing_dnd,
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
            # ``.get``, not ``[...]``, and that is ``SNAG-TRAY-010``'s
            # lesson rather than defensive habit.  A gate above the sweep
            # can leave this title unstored — ``min_severity: critical``
            # does, since ``_adopt`` admits no rung below the threshold
            # either — and a ``KeyError`` raised while *building* the
            # reading takes the premise test down with everything else,
            # so the one assertion written to name the cause never runs.
            # Absent is a reading; a traceback is not.
            "stored_reminders": (
                None
                if ANNOUNCED_TITLE not in stored
                else stored[ANNOUNCED_TITLE].reminders_sent
            ),
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

        **The first two assertions are ordered ahead of the rest so a
        failure names the gate rather than the symptom** — which is the
        whole of ``SNAG-TRAY-010``.  Run inside the DND window this file
        reported six failures whose loudest was ``spoke_unwatched is
        False``, a sentence about the sweep, for a fault entirely above
        it.  ``dnd_suppressing`` fires first and says so outright;
        ``sent_total`` catches the class rather than the member, since
        ``min_severity``, ``enabled`` and a future fourth gate all silence
        the announce path the same way.

        ``sent_total`` is asserted as *non-zero* and not as a figure.
        The figure is the roll-up's shape, and ``first_count`` /
        ``second_count`` below own that; what is claimed here is only
        that something above the sweep did not refuse the lot, which is
        exactly the discrimination the total was added for.
        """
        assert reading["pre_existing"] == set(), "a live row collides with a probe title"
        assert reading["dnd_suppressing"] is False, (
            "DND is suppressing the probe's rung — the drive's third leaf "
            "did not take, so every reading below is about a gate above "
            "the sweep (SNAG-TRAY-010)"
        )
        assert reading["sent_total"] > 0, (
            "nothing was ever sent, at announce time or after — a gate "
            "above _handle refused everything, so the sweep is not what "
            "these readings are measuring"
        )
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
        assert (reading["stored_reminders"] or 0) >= 2

    def test_the_dnd_leaf_is_put_back(self, reading):
        """The third leaf is restored, and this is the discriminating half.

        ``dnd_suppressing`` in the premise can only witness that the
        override *took*; held permanently it would read the same. This is
        the other direction, and it is the assertion with a live
        population behind it: ``dnd_manager`` is a process-wide singleton
        that :meth:`DndManager.set_manual_override` documents as taking
        precedence over the schedule, so a drive that walked away leaving
        it forced-off would silence the ``23:00 → 07:00`` window for
        every test that ran after it in the same process — and would do
        so *invisibly*, since the effect is a notification nobody
        receives.  ``tests/test_dnd.py`` and ``tests/test_alerts_api.py``
        both drive that singleton.

        Asserted against **what the drive found**, never against
        ``None``.  A literal would be a claim about whatever ran before
        this file in the same process, and it fires at a *correct*
        restore — measured: forcing the singleton on before the drive
        turned this red while the restore was working perfectly.  It is
        also still discriminating both ways, because ``None`` and
        ``False`` are different states (``None`` defers to the schedule,
        ``False`` overrides it), so dropping the restore leaves ``False``
        against a standing ``None`` and this fires.
        """
        assert reading["sent_total"] > 0  # the drive really ran
        assert dnd_manager.manual_override == reading["dnd_standing"]

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
