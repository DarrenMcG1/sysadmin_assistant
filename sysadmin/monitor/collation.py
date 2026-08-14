"""Databases whose text ordering no longer matches the OS that built it.

``SNAG-DB-002``: a routine glibc upgrade moved this box from locale data
2.43 to 2.44.  PostgreSQL records the collation version a database was
created with, precisely so it can say that it no longer matches — and
every ``psql`` session has been printing that warning since.  Nothing
reads it, which is the whole finding: **this application is the thing on
this box whose job is to notice**, and it was discovered by a human
happening to open a shell.

**Why it is not cosmetic.**  A B-tree index on a text column was built
against 2.43's ordering.  An index scan walks to where a string *used
to* sort, so a lookup can miss a row that is present.  The ``sysadmin``
schema alone holds 25 indexes, several on text — ``alerts.title`` is
matched with ``LIKE`` in ``_resolve_recovered``, ``service_health``
carries ``service_name`` — and a silently missed row there would present
as an alert that never deduplicates or never resolves, which is
indistinguishable from the bugs this repository keeps finding by hand.

**Why it is not urgent.**  glibc's changes between minor versions are
usually confined to unusual scripts, and no wrong result has been
observed here.  "Low" is a probability rather than a guarantee, which is
an awkward pair to hold — and is exactly why it belongs on a surface
that keeps saying so rather than in someone's memory.

Four rules, three of them the opposite of the obvious implementation.

1. **Not-knowing is not a mismatch, and this fails *open*** — the
   opposite of :mod:`sysadmin.core.schema_guard`, deliberately.  Both
   halves of the comparison must be non-NULL before a row is raised.
   ``template0`` reports no recorded version at all, and a database
   under the ``C`` locale provider has no actual version to compare
   against; ``recorded != actual`` in Python treats both as a fault and
   invents an alert whose remedy does not exist.  The guard refuses to
   boot on not-knowing because serving against the wrong schema is
   worse than not serving; here the cost of a false positive is an
   operator asked to reindex a database that is fine, so the test is
   ``IS NOT NULL AND <>`` on both sides.

2. **One row per database, and the databases are not filtered.**  Eight
   of eleven are stale here, five of them Alfred's dev and test copies.
   Filtering to "the ones that matter" needs a second registry of estate
   facts living in this repository, which the estate manager exists to
   prevent — and a test database is where a wrong-ordering bug is
   *cheapest* to find.  One row each rather than one for the cluster,
   because the remedy is per-database (``REINDEX DATABASE`` names one)
   and a row that resolves the moment its own database is reindexed
   shows progress; a single cluster row stays open until the last one is
   done and says nothing in between.

3. **Raised once per open row, never once per run.**  The sysadmin agent
   polls every 300 s and a stale collation persists for weeks, so
   ``_check_thresholds``'s pattern **as it then stood** — ``raise_alert``
   unconditionally, let ``_resolve_recovered`` sweep — would have
   written **2,304 rows a day** for this one fault.  That is
   ``SNAG-AGENT-004`` and ``SNAG-AGENT-005`` reappearing a third time,
   and this module is written knowing it.  Writing it down is what
   surfaced ``SNAG-AGENT-006``: the divergence between this family and
   the one beside it was the finding, and the service and threshold
   families deduplicate too as of that fix.

4. **Therefore this family owns its own lifecycle and must stay out of**
   :data:`sysadmin.monitor.agent.RESOLVABLE_TITLE_PATTERNS`.  The reason
   has narrowed and it is worth being exact about which half survived.
   The original argument was that dedup and that sweep are mutually
   exclusive — the sweep closes any owned row the run did not *raise*,
   so a deduplicating family's still-true row flip-flops, and each flip
   clears the tray's ``{severity}:{title}`` fingerprint and notifies
   again.  ``SNAG-AGENT-006`` refuted the general form by changing the
   exclusion set to what the run **judged**, following
   :mod:`sysadmin.estate.agent`; dedup suppresses the raise, never the
   judgement, so there is no longer anything to flip.  What stands is
   the narrower rule: this family **resolves its own rows by id**, and a
   second owner closes a row while the first still holds it true — the
   defect this repository has now found at three scales.  Nothing here
   feeds that sweep's judged set, so joining the tuple would resolve
   these rows on the first run and re-raise them on the next.
   ``tests/test_collation_check.py`` pins the title against every
   pattern in that tuple.

The remedy's own trap is carried in the alert rather than left to the
reader: ``ALTER DATABASE … REFRESH COLLATION VERSION`` on its own clears
the warning by asserting the versions now match, **without rebuilding
anything**.  Run alone it converts a loud known risk into a silent one,
so the message always names ``REINDEX`` first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

#: ``details`` key naming the database an alert is about.
#:
#: Open rows are found by this rather than by parsing the title apart,
#: matching how the stall and failure families locate their own — a title
#: is a sentence for a human and splitting one to recover a value is a
#: parser nobody remembers writing.
COLLATION_DETAIL_KEY = "collation_database"

#: Severity for a stale collation.
#:
#: Never ``critical``: that severity breaks through the DND windows by
#: configuration and is reserved, by ``sysadmin_tray.notifications``, for
#: the alerts that stay on screen.  A fault with no wrong result yet
#: observed does not earn that.  Never ``info`` either — ``info`` is
#: below ``tray.notify_min_severity`` on this box, so it would be raised
#: into silence, which is the state this check exists to end.
COLLATION_SEVERITY = "warning"

#: Both sides of the comparison, per database, from one catalog read.
#:
#: ``pg_database`` is a **cluster-wide** catalog, so the existing
#: connection to ``projects`` sees every database without a second
#: engine, a second credential or a loop over connections.  Filtering in
#: SQL rather than in Python keeps the NULL rule (see the module
#: docstring) in one place: ``IS DISTINCT FROM`` would report ``2.43``
#: against ``NULL`` as a difference, which is true and not a fault.
MISMATCH_SQL = text(
    """
    SELECT datname,
           datcollversion AS recorded,
           pg_database_collation_actual_version(oid) AS actual
    FROM pg_database
    WHERE datcollversion IS NOT NULL
      AND pg_database_collation_actual_version(oid) IS NOT NULL
      AND datcollversion <> pg_database_collation_actual_version(oid)
    ORDER BY datname
    """
)


def collation_title(datname: str) -> str:
    """The alert title for ``datname`` carrying stale collation data.

    The database name is last, which keeps the title clear of every
    pattern in ``RESOLVABLE_TITLE_PATTERNS`` — those all match on a final
    word (``% degraded``, ``% critical``, …).  Rule 4 in the module
    docstring depends on that and a test asserts it.
    """
    return f"Stale collation version on {datname}"


@dataclass(frozen=True)
class Mismatch:
    """One database whose recorded collation version is out of date."""

    datname: str
    recorded: str
    actual: str

    @property
    def title(self) -> str:
        return collation_title(self.datname)

    @property
    def message(self) -> str:
        """What broke, what it can cost, and the remedy in order.

        The order is the load-bearing part — see the module docstring on
        ``REFRESH`` alone.
        """
        return (
            f"{self.datname} was created with collation version "
            f"{self.recorded}; the operating system now provides "
            f"{self.actual}. Text indexes were built against the old "
            f"ordering, so a lookup can miss a row that is present. "
            f"Fix, in this order: REINDEX DATABASE {self.datname}, then "
            f"ALTER DATABASE {self.datname} REFRESH COLLATION VERSION. "
            f"REFRESH on its own only silences the warning."
        )

    @property
    def details(self) -> dict[str, Any]:
        """Both versions, and the remedy as statements rather than prose.

        ``remedy`` is a list because the two statements must run in that
        order and a reader copying one line out of a paragraph is how the
        ``REFRESH``-only trap gets sprung.
        """
        return {
            COLLATION_DETAIL_KEY: self.datname,
            "recorded_version": self.recorded,
            "actual_version": self.actual,
            "remedy": [
                f"REINDEX DATABASE {self.datname}",
                f"ALTER DATABASE {self.datname} REFRESH COLLATION VERSION",
            ],
        }


def evaluate(
    mismatches: list[Mismatch], open_databases: set[str]
) -> list[Mismatch]:
    """Which mismatches still need a row — those with none already open.

    Rule 3: a stale collation persists until someone reindexes, so
    raising unconditionally writes one row per database per run for
    weeks.  The predicate is deliberately trivial and deliberately here
    rather than inline in the agent, so the raise decision and the
    resolve decision below it read from one module.
    """
    return [m for m in mismatches if m.datname not in open_databases]


def resolved_databases(
    open_databases: set[str], mismatched: set[str]
) -> set[str]:
    """Open rows whose database is no longer mismatched.

    Covers three endings with one set difference, which is the
    ``_resolve_recovered`` argument applied locally: the database was
    reindexed and refreshed, or it was dropped, or it was recreated on
    the current locale data.  A per-database loop over *current*
    mismatches can only ever see the first — the other two never appear
    in a query result again, so their rows would stay open for ever.
    """
    return open_databases - mismatched
