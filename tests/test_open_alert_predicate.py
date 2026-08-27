"""The open-alert predicate, stated once and reaching its index.

``SNAG-AGENT-007`` was filed as *four unbounded reads of the alerts table
per 300-second run*, and ranked P3 because the open set is small.  Driven
against the live table the ranking is wrong for a reason the entry never
names: it costed the read by its **result** and the cost is in its
**scan**.  ``alerts`` has carried ``idx_alerts_active … WHERE resolved =
FALSE`` since it was created; every one of the nineteen readers spelled
the predicate ``Alert.resolved.is_(False)``, which renders ``resolved IS
false``; and PostgreSQL matches a partial index structurally, so not one
of them could reach it.  666,936 rows, zero of them open for this agent:
41,644 buffers and 33.3 ms, four times a run.

These tests pin the three things that fix has to keep true — that the
predicate renders the index's own string, that nobody states it by hand
again, and that the two projections share one definition of the row set.
"""

import ast
import pathlib

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql

from sysadmin.core.models.alert import Alert, unresolved

#: The module that owns the predicate.  Excluded from the sweep below
#: and then driven at it deliberately — a detector nothing can trip is
#: not a detector, and ``tests/test_autogenerate_config.py`` settled that
#: idiom here by running its walker at its own owner.
OWNER = pathlib.Path("sysadmin/core/models/alert.py")

#: What both partial indexes on ``alerts`` declare.
INDEX_PREDICATE = "resolved = FALSE"


def _sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def _hand_written(path: pathlib.Path) -> list[int]:
    """Lines where a module states the open predicate itself.

    Both removed spellings: ``Alert.resolved.is_(...)``, which is what
    the nineteen readers wrote, and ``Alert.resolved == …``, which is
    what a reader reaching for the index by hand would write next.

    An AST walk rather than a grep, for ``test_contract_reachability``'s
    reason: prose is ``ast.Constant`` and falls out for free, so the
    docstrings that *describe* this defect — including this file's — do
    not read as instances of it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[int] = []
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "is_":
                target = node.func.value
        elif isinstance(node, ast.Compare) and any(
            isinstance(op, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)) for op in node.ops
        ):
            target = node.left
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "resolved"
            and isinstance(target.value, ast.Name)
            and target.value.id == "Alert"
        ):
            found.append(node.lineno)
    return found


class _CapturingSession:
    """Records what a reader asks the database for, and answers nothing.

    The first draft of the two tests below composed their own
    ``select(...)`` from ``_open_alert_criteria`` and asserted against
    that — which is the test asserting a statement **it** wrote, so
    rewriting ``_open_alert_titles`` to pull whole rows again left both
    green.  Caught by driving the falsification rather than reasoning
    about it, the seventh guard in this repository to pass against
    deliberately broken code and the third to assert a value where it
    meant provenance.  Only the producer can answer what the producer
    selects.
    """

    def __init__(self):
        self.statements: list[object] = []

    async def execute(self, statement):
        self.statements.append(statement)
        return self

    def scalars(self):
        return self

    def all(self):
        return []


async def _statement_of(reader) -> str:
    session = _CapturingSession()
    await reader(session)
    assert len(session.statements) == 1, session.statements
    return _sql(session.statements[0])


class TestThePredicateAndTheIndexAgree:
    """One string, in two places that cannot be allowed to drift."""

    def test_it_renders_the_index_predicate_literally(self):
        sql = _sql(select(Alert.title).where(unresolved()))
        assert "resolved = false" in sql.lower()
        assert "is false" not in sql.lower(), (
            "the BooleanTest spelling is back; PostgreSQL will not prove it "
            "implies the partial index's predicate and every reader falls to "
            "a sequential scan"
        )

    def test_the_model_declares_the_same_string(self):
        """Pinned against the indexes, never restated beside them.

        ``max_priority_for`` against ``PRIORITY_MAP``'s rule: the two
        halves live in different constructs — a Python expression and a
        ``text()`` fragment PostgreSQL parses — so neither can import the
        other and a test is what holds them together.
        """
        partials = [
            str(index.dialect_options["postgresql"]["where"])
            for index in Alert.__table__.indexes
            if index.dialect_options["postgresql"].get("where") is not None
        ]
        assert len(partials) == 2, f"expected two partial indexes, got {partials}"
        assert {p.lower() for p in partials} == {INDEX_PREDICATE.lower()}

        rendered = _sql(select(Alert.title).where(unresolved())).lower()
        assert INDEX_PREDICATE.lower() in rendered

    def test_the_column_cannot_be_null(self):
        """The proof that the substitution preserved meaning.

        ``IS false`` and ``= false`` differ on exactly one input, and a
        ``NOT NULL`` column cannot supply it.  Nineteen call sites were
        rewritten on the strength of this one fact, so it is asserted
        rather than remembered — and it is asserted against the *column*,
        which is where the guarantee lives, not against a migration.
        """
        assert Alert.__table__.c.resolved.nullable is False


class TestNoReaderStatesItByHand:
    """The audit, kept running.

    ``SNAG-API-004`` and ``SNAG-DB-003`` were each the third instance of
    a rule stated twice, and each was found because somebody happened to
    look.  Nineteen copies of this one reached production; nothing was
    looking.  This is.
    """

    def test_no_module_states_the_open_predicate_by_hand(self):
        offenders = [
            f"{path}:{line}"
            for path in sorted(pathlib.Path("sysadmin").rglob("*.py"))
            if path != OWNER
            for line in _hand_written(path)
        ]
        assert offenders == [], (
            "the open-alert predicate is being stated by hand; use "
            f"unresolved() from sysadmin.core.models.alert: {offenders}"
        )

    def test_the_sweep_trips_at_its_owner(self):
        """Driven at the real owner rather than a synthetic stand-in.

        ``unresolved()`` *is* the hand-written form — that is what makes
        it the one definition — so the owner is the only module in the
        tree that must trip every rule, and using it means the detector
        is exercised against the exact construct it exists to find rather
        than against a reconstruction of it.
        """
        assert _hand_written(OWNER), "the sweep no longer sees its own owner"

    def test_the_sweep_sees_the_spelling_that_was_removed(self, tmp_path):
        module = tmp_path / "reader.py"
        module.write_text(
            "from sysadmin.core.models.alert import Alert\n"
            "def open_rows():\n"
            "    return select(Alert).where(Alert.resolved.is_(False))\n"
        )
        assert _hand_written(module) == [3]

    def test_the_sweep_reads_prose_as_prose(self, tmp_path):
        """A docstring naming the defect is not an instance of it.

        Load-bearing rather than tidy: this file, the model's own
        docstring and migration 017 all quote ``Alert.resolved.is_(False)``
        to explain what was removed, and a textual detector would report
        all three and teach the reader to ignore the family — which is
        ``RecommendationInfo`` looking alive off one line of prose,
        already paid for once here.
        """
        module = tmp_path / "prose.py"
        module.write_text(
            '"""Was Alert.resolved.is_(False); see unresolved()."""\n'
            "# Alert.resolved == False was the other spelling.\n"
            "X = 1\n"
        )
        assert _hand_written(module) == []


class TestOneDefinitionTwoProjections:
    """The tension the entry names, and where it is resolved.

    *"the dedup caller needs only titles, so a ``select(Alert.title)``
    projection would fix it — at the cost of a second definition of 'this
    agent's open rows' sitting beside ``_active_alerts``"*.  It is not a
    second definition, because a projection and a predicate are not the
    same kind of thing: what a caller wants **back** may differ per
    caller, which rows it is **asking about** may not.
    """

    @pytest.fixture
    def agent(self):
        from sysadmin.monitor.agent import SysAdminAgent

        return SysAdminAgent()

    async def test_the_two_readers_ask_about_the_same_rows(self, agent):
        rows = await _statement_of(agent._active_alerts)
        titles = await _statement_of(agent._open_alert_titles)
        assert rows.split("WHERE")[1] == titles.split("WHERE")[1]

    async def test_the_dedup_reader_projects_one_column(self, agent):
        titles = await _statement_of(agent._open_alert_titles)
        selected = titles.split("FROM")[0]
        assert "alerts.title" in selected
        assert "alerts.details" not in selected, (
            "the dedup snapshot is materialising rows again — SNAG-AGENT-005's "
            "_open_alerts pulled 593,814 ORM objects on its first live run"
        )

    def test_every_reader_in_the_agent_goes_through_the_criteria(self):
        """No fourth reader may assemble the scope itself.

        The WHERE-identity test above passes just as happily against two
        readers that each spell ``Alert.agent == self.name, unresolved()``
        — which is the copy the entry warns about, wearing the fix's
        clothes.  So the agent-scope comparison is counted instead, and
        there is exactly one: inside ``_open_alert_criteria``.
        """
        tree = ast.parse(
            pathlib.Path("sysadmin/monitor/agent.py").read_text(encoding="utf-8")
        )
        scopes = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Attribute)
            and node.left.attr == "agent"
            and isinstance(node.left.value, ast.Name)
            and node.left.value.id == "Alert"
        ]
        assert len(scopes) == 1, f"agent scope stated {len(scopes)} times: {scopes}"


class TestThePlanOnTheLiveTable:
    """The only half a fixture cannot assert.

    Everything above is true of a string.  Whether the planner *reaches*
    the index is a property of this box, and it is the property the entry
    is actually about — so it is asked of the live table, and the old
    spelling is driven beside it as the witness.  Without that pair a
    plan that never seq-scans anything (an empty table, a planner setting
    someone changed) reads exactly like a working fix.

    ``enable_seqscan = off`` makes the pair discriminate independently of
    how big the table happens to be today: with the old spelling **no**
    partial index is usable at all, so it seq-scans even when told not
    to, which is the difference being measured rather than a cost that
    varies with row count.
    """

    @staticmethod
    def _plan(where: str) -> str:
        from sqlalchemy import create_engine

        from sysadmin.core.config import get_config

        engine = create_engine(get_config().database.sync_url)
        try:
            with engine.connect() as conn:
                conn.execute(text("SET LOCAL enable_seqscan = off"))
                rows = conn.execute(
                    text(
                        "EXPLAIN (COSTS OFF) SELECT title FROM sysadmin.alerts "
                        f"WHERE agent = 'sysadmin' AND {where}"
                    )
                ).scalars()
                return "\n".join(rows)
        except Exception as exc:  # noqa: BLE001 — an unreachable database is a skip
            pytest.skip(f"the database did not answer ({exc.__class__.__name__})")
        finally:
            engine.dispose()

    def test_the_removed_spelling_still_cannot_reach_an_index(self):
        """The witness.  A constant observation is not evidence."""
        plan = self._plan("resolved IS false")
        assert "Seq Scan" in plan, (
            "the old spelling now reaches an index, so this box can no longer "
            f"tell the two apart and the verdict below means nothing:\n{plan}"
        )

    def test_the_predicate_in_use_reaches_a_partial_index(self):
        plan = self._plan(_sql(select(Alert.title).where(unresolved())).split("WHERE")[1])
        assert "Seq Scan" not in plan, plan
        assert "idx_alerts_active" in plan or "idx_alerts_open_by_agent" in plan, plan
