"""Every mapped table, and the rules autogenerate compares it by.

``Base.metadata`` is only complete once each model module has been
imported, and after Phase 2 those modules live in six packages. Alembic
autogenerate and the schema-drift test both need the whole set, so the
aggregation lives here rather than being repeated in each — a table
missing from one copy and not the other is exactly the silent drift the
drift test exists to catch.

``COMPARISON_OPTS`` is that same argument one step further, and closes
`SNAG-DB-003`. Knowing *which* tables are mapped is only half of a
comparison; the other half is which of the live schema's tables this
metadata claims to be authoritative for, and until now that half was
hand-copied between ``alembic/env.py`` and
``tests/test_schema_drift.py``. The two copies fail in **opposite
directions**: an exclusion present only in ``env.py`` makes the drift
guard fail loudly and announce itself, while one present only in the
test is silent — the guard stays green while the next ``alembic
revision --autogenerate`` still sees the frozen tables as
live-but-unmodelled and writes ``op.drop_table('project_snapshots')``
into a migration whose author was doing something else entirely.
Measured on 2026-08-16 with the exclusion removed: autogenerate proposed
``remove_table`` for both, against 3,739 and 4 live rows. Migration 014
has since dropped both deliberately, so ``FROZEN_TABLES`` is empty and
that risk has no population today — the guard against the copy coming
back is what remains, and see the constant for why it outlives its
members.

The options travel as one dict rather than as loose constants because
the flags fail the same silent way the exclusions do. A ``compare_type``
that is set in ``env.py`` and absent from the guard leaves the guard
green while blind to exactly the drift it exists to catch — so the
guard would be measuring a weaker comparison than the one it certifies.

**This is production configuration that the test borrows, not test
scaffolding pushed into the package.** ``include_object`` is what
``alembic revision --autogenerate`` uses whether or not a test suite
exists; the drift guard is the second caller. Session 43 left the
placement open on the grounds that a shared constant in ``sysadmin/``
puts a testing concern into the shipped package — it does not, once the
direction of ownership is stated that way round.

What deliberately does **not** move is the ``SET search_path TO public``
both callers issue before configuring. It is a property of the
*connection* rather than of the comparison (``env.py`` also creates the
schema there, which no test may do), and its drift fails in the loud
direction: a caller pointing search_path at ``sysadmin`` reflects every
table twice and the guard fails with phantom diffs rather than passing
while blind.

This module sits beside ``main.py`` on purpose. Both are composition
roots: they are allowed to import every domain, and no domain imports
them.
"""

from typing import Any

from sqlalchemy.schema import SchemaItem

from sysadmin.core.models.agent_run import AgentRun
from sysadmin.core.models.alert import Alert
from sysadmin.core.models.base import Base
from sysadmin.core.models.retention_config import RetentionConfig
from sysadmin.files.models.disk_review import DiskReview
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.desktop_notification import DesktopNotification
from sysadmin.monitor.models.health_review import HealthReview
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.models.log_review import LogReview
from sysadmin.monitor.models.reliability_score import ReliabilityScore
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.units.models import UnitAudit

ALL_MODELS = (
    AgentRun,
    Alert,
    DesktopNotification,
    DiskReview,
    FilesystemAudit,
    HealthReview,
    LogEntry,
    LogReview,
    ReliabilityScore,
    ResourceSnapshot,
    RetentionConfig,
    ServiceHealth,
    UnitAudit,
)


SCHEMA = "sysadmin"

#: Live tables this repository deliberately does not model, excluded so
#: neither the drift guard nor a future ``--autogenerate`` proposes
#: dropping data nothing here owns. One copy — see the module docstring;
#: both consumers read it from here, and
#: ``tests/test_autogenerate_config.py`` fails if a second one appears.
#:
#: **The population is empty, and the mechanism outlives it.** It held
#: ``project_snapshots`` and ``project_reviews`` from estate-manager
#: ADR-0005 until migration 014 dropped them, so every table in the live
#: schema is mapped again. Emptying it is not a tidy-up: an entry here is
#: a *blindfold* over the drift guard, which compares whatever
#: ``include_object`` admits — so migration 014 did not need a new test to
#: prove the three tables are gone, it needed this set to stop hiding
#: them. That is also why the constant stays rather than being deleted
#: with its last member. A domain leaving and stranding its tables is a
#: shape this estate has produced once and will again; deleting the set
#: would take ``test_autogenerate_config.py``'s guard against a second
#: copy with it, which is retiring a check in silence at the moment
#: nothing is exercising it.
#:
#: An entry added here must be paired with a *drop* entry on the roadmap.
#: Frozen is a stage, not a destination — a table left frozen indefinitely
#: costs a nightly purge, a line in every count of the schema, and this
#: exclusion, which is what migration 014 was reclaiming.
FROZEN_TABLES: set[str] = set()


def include_object(
    obj: SchemaItem,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: SchemaItem | None,
) -> bool:
    """Decide whether autogenerate compares this object at all.

    Three exclusions, and they are not the same kind of thing. Another
    schema's tables are not ours to model — the ``projects`` database
    also holds PersonalAssistant's. ``alembic_version`` is alembic's own
    bookkeeping. ``FROZEN_TABLES`` are ours, live, and deliberately
    unmodelled, which is the one an autogenerate run would act on — and
    the one that is empty since migration 014, so the third branch is a
    mechanism with no members rather than a rule with no reader.

    Alembic calls this positionally, so the leading parameter is named
    ``obj`` rather than shadowing the builtin its own documentation uses.
    """
    if type_ == "table":
        if getattr(obj, "schema", None) != SCHEMA:
            return False
        if name == "alembic_version":
            return False
        if name in FROZEN_TABLES:
            return False
    return True


def include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Restrict schema reflection to the sysadmin schema.

    The models' metadata carries an explicit ``schema="sysadmin"``, so
    autogenerate must reflect sysadmin tables under that explicit name.
    Without this (and with search_path pointed at sysadmin), the same
    tables were reflected twice — once as ``sysadmin.x`` and once as
    default-schema ``x`` — producing phantom add/remove diffs.
    """
    if type_ == "schema":
        return name == SCHEMA
    return True


#: The whole comparison, in one object. ``alembic/env.py`` splats it into
#: ``context.configure`` and ``tests/test_schema_drift.py`` into
#: ``MigrationContext.configure(opts=...)``, so the migration tool and the
#: guard that certifies it cannot be comparing different things. Connection
#: setup (``url``/``connection``, search_path, ``CREATE SCHEMA``) stays with
#: each caller: it is not part of what is compared.
COMPARISON_OPTS: dict[str, Any] = {
    "target_metadata": Base.metadata,
    "version_table_schema": SCHEMA,
    "include_schemas": True,
    "include_object": include_object,
    "include_name": include_name,
    "compare_type": True,
}

__all__ = [
    "ALL_MODELS",
    "COMPARISON_OPTS",
    "FROZEN_TABLES",
    "SCHEMA",
    "Base",
    "include_name",
    "include_object",
    *sorted(model.__name__ for model in ALL_MODELS),
]
