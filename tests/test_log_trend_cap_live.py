"""The trend query's group cap cuts by a stated order, against the real query.

``SNAG-LOG-020``.  :func:`trend_groups` keeps the first
``trend_max_groups`` raw ``(source, severity, message)`` groups, and this
box has more than that (2,472 on 2026-09-30).  The order used to be the
unwindowed ``count()`` alone, and past the first 424 places every group
tied at one row, so the executor chose which were dropped.

The fix has one rule that is the opposite of the obvious one: **each
shape's oldest group goes first**, ahead of every windowed count.  A
signature's ``first_seen`` is the minimum over its groups, and a signature
is new when ``first_seen`` falls in the current window.  A cut that keeps
the recent groups of a pid-embedding message and drops its old ones makes
an established fault read as new.  Measured, every recency-first order
tried did that to 18 kernel signatures.

Two drives, both inside a rolled-back transaction:

- **The hazard.**  One probe message in six groups: one older than both
  windows, five this week, each with its own pid.  The cap is set to the
  number of shapes in the table, which is exactly the size at which only
  the oldest-of-shape groups survive.  The probe must still be served,
  with its old ``first_seen``, and not as new.
- **The whole order.**  The uncapped query's rows must already be in the
  order the docstring states, restated here in Python.  ``COLLATE "C"`` on
  the final tie-break is what makes Python's string order the same one.
"""

import asyncio
import re
from datetime import UTC, datetime, timedelta

import pytest

from sysadmin.core.config import get_config
from sysadmin.monitor.log_query import SHAPE_DIGITS, build_trend_report, trend_groups
from sysadmin.monitor.log_signature import signature
from sysadmin.monitor.log_trends import MessageGroup
from sysadmin.monitor.models.log_entry import LogEntry
from tests.test_log_trend_windows_live import _db_available, _rolled_back

PROBE_SOURCE = "sysadmin-live-probe"
#: One shape and one signature, whatever the pid.
PROBE_TEMPLATE = "sysadmin cap probe: proc worker({pid}) is never committed"
WINDOW_DAYS = 7
UNCAPPED = 1_000_000
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _shape(group: MessageGroup) -> tuple[str, str, str]:
    return (group.source, group.severity, re.sub(SHAPE_DIGITS, "N", group.message))


def _micros(stamp: datetime) -> int:
    """Exact, where ``timestamp()`` is a float at 16 significant digits."""
    return (stamp - EPOCH) // timedelta(microseconds=1)


def _stated_order(groups: list[MessageGroup]) -> list[MessageGroup]:
    """The order :func:`trend_groups` documents, written a second time."""
    oldest: dict[tuple[str, str, str], MessageGroup] = {}
    for group in groups:
        shape = _shape(group)
        held = oldest.get(shape)
        if held is None or (group.first_seen, group.message) < (
            held.first_seen,
            held.message,
        ):
            oldest[shape] = group
    firsts = {id(group) for group in oldest.values()}
    return sorted(
        groups,
        key=lambda g: (
            id(g) not in firsts,
            -g.current,
            -g.previous,
            -g.total,
            -_micros(g.last_seen),
            g.source,
            g.severity,
            g.message,
        ),
    )


async def _drive() -> dict:
    now = datetime.now(UTC)
    old = now - timedelta(days=WINDOW_DAYS * 2 + 6)
    recent = now - timedelta(days=1)
    rows = [(1, old)] + [(pid, recent) for pid in range(2, 7)]
    async with _rolled_back() as session:
        session.add_all(
            LogEntry(
                source=PROBE_SOURCE,
                severity="warning",
                message=PROBE_TEMPLATE.format(pid=pid),
                logged_at=stamp,
            )
            for pid, stamp in rows
        )
        await session.flush()

        window_start = now - timedelta(days=WINDOW_DAYS)
        previous_start = now - timedelta(days=WINDOW_DAYS * 2)
        uncapped, uncapped_cut = await trend_groups(
            session, window_start, previous_start, UNCAPPED
        )
        shapes = len({_shape(group) for group in uncapped})

        config = get_config().agents.log_aggregator
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(config, "trend_max_groups", shapes)
            capped = await build_trend_report(session, WINDOW_DAYS)

    return {
        "old": old,
        "uncapped": uncapped,
        "uncapped_cut": uncapped_cut,
        "shapes": shapes,
        "capped": capped,
        "probes": [t for t in capped.signatures if t.source == PROBE_SOURCE],
    }


@pytest.fixture(scope="module")
def reading() -> dict:
    if not _db_available():
        pytest.skip("local postgres (projects DB) not reachable")
    return asyncio.run(_drive())


class TestTheOldestGroupOfEachShapeSurvivesTheCap:
    @pytest.mark.premise
    def test_the_cap_binds_and_the_probe_is_six_groups_of_one_shape(self, reading):
        """The premise: the cap really cut, and the probe really competed.

        If the cap did not bind, the probe would be served whatever the
        order, and the tests below would pass on a query that ranks
        nothing.  The six probe groups being one shape is what makes the
        cap at the shape count leave exactly one of them.
        """
        probe_groups = [g for g in reading["uncapped"] if g.source == PROBE_SOURCE]
        assert len(probe_groups) == 6
        assert len({_shape(g) for g in probe_groups}) == 1
        assert reading["uncapped_cut"] is False
        assert len(reading["uncapped"]) > reading["shapes"]
        assert reading["capped"].truncated is True
        assert reading["capped"].groups_read == reading["shapes"]

    def test_the_probe_is_served_from_its_oldest_group(self, reading):
        """A recency-first order drops the old group and serves this as new."""
        (probe,) = reading["probes"]
        assert probe.first_seen == reading["old"]
        assert probe.is_new is False

    def test_every_signature_is_still_served(self, reading):
        """Every signature keeps a group, as long as no shape spans two.

        Each signature has a shape, and each shape keeps its oldest
        group.  That reaches every signature only while a shape never
        covers two signatures, which is not guaranteed: ``signature()``
        collapses a hex literal whole and a shape does not.  It held live
        when this was written, 320 shapes over 291 signatures.  If this
        goes red while the tests above stay green, it is that promise
        that failed, not the order.
        """
        present = {
            (g.source, g.severity, signature(g.message)) for g in reading["uncapped"]
        }
        served = {(t.source, t.severity, t.signature) for t in reading["capped"].signatures}
        assert served == present


class TestTheQueryOrderIsTheStatedOne:
    def test_the_uncapped_rows_arrive_in_the_documented_order(self, reading):
        """Every key, including the byte-order tie-break, in one comparison."""
        rows = reading["uncapped"]
        assert rows == _stated_order(rows)
