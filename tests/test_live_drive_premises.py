"""Every live drive names the test that holds its premise.

A live drive believes negatives.  ``test_failure_replay_live.py`` says
why in its own docstring — a stand-in notification server printed
``claimed`` and owned nothing a millisecond later, and the wait duly
reported ``False`` after a full budget, *"which reads as a verdict about
the code under test and was a verdict about the harness"*.  So each of
these files asserts that the harness really produced the state before
anything below it means anything.

``SNAG-TRAY-010`` is what this guards, and it is worth being exact about
**which half**.  That entry was a clock the drive could not see it was
reading: :meth:`DndManager.is_active` calls ``datetime.now()`` itself, so
``dnd_manager.should_suppress`` read the real wall clock whatever clock
the notifier was handed, and inside the shipped ``23:00 → 07:00`` window
every send was refused.  The obvious guard — an AST sweep for an
unsupplied singleton clock — **cannot see that**, and the pre-fix file is
the proof: at ``62f8e09`` it named ``dnd`` *zero* times, so the defect was
an absence with no token to key on, the read was transitive through
production code carrying 27 unsupplied clock reads, and four of the five
drives here touch no singleton at all.  What *did* find it is the premise
assertion — ``dnd_suppressing is False`` ordered first so a failure names
the gate — and what that assertion cannot do is exist in a file nobody
wrote it into.

**So the claim here is narrow and stated rather than implied: every live
drive carries a marked premise.**  Not that the premise is a good one —
no sweep can read that — only that the default path, writing a sixth
drive and forgetting, fails instead of shipping green.  It is the shape
``test_schema_guard.py`` uses to keep ``upgrade`` out of
``check-migrations.sh``: satisfiable by a determined author, and that is
not what it is for.

Three rules, two of them the opposite of the obvious implementation:

1. **The marker names the check and never the value.**  A name rule was
   measured first and reaches **3 of 5**: two files carry
   ``test_the_premises_hold_or_nothing_below_means_anything``, one carries
   ``class TestThePremises``, and the other two do not and should not.
   ``TestTheHazardIsReal`` names what it *proves*, which is strictly more
   than "premise" would say, and renaming it to satisfy a detector would
   trade information for a grep.  ``test_failure_replay_live.py`` cannot
   comply at all: its premise differs per test (nobody listening, versus
   a server present), so there is no single test to name.  A decorator
   attaches at the level the premise actually lives — function or class —
   which is exactly the three shapes that exist.
2. **The population is a property, not the glob, and the exemption is
   earned rather than granted.**  ``tests/test_*_live.py`` is a naming
   convention, and a convention is dodgeable by not following it — a
   seventh drive against the live database called anything else would owe
   nothing.  :func:`_opens_a_live_connection` is the property, and a file
   holding it satisfies rule 2 by **marking a premise**, exactly as a
   glob member does.  :data:`PRE_CONVENTION` is what remains: files that
   hold the property and owe no marker, one of them today, each with the
   reason recorded beside it.  That set is a tripwire and not a
   classification — nothing may be added to it without a sitting deciding
   to, which is ``FROZEN_TABLES``' rule at the size of a filename.

   **It held six names for one day and now holds one** (Session 132).
   Session 131 measured the six that open a live connection without being
   named ``_live`` and exempted them wholesale, which is the state the
   handoff called *"a decision nobody has taken"*.  Taken, one file at a
   time, and it went five ways to one:

   - ``test_schema_drift.py`` **owed one and had none**, the strongest of
     the six.  Its whole output is ``diff == []``, and with
     ``FROZEN_TABLES`` widened to cover all thirteen mapped tables — the
     blindfold that constant's own docstring warns about — the comparison
     returns ``[]`` as well.  Driven, not argued: the same opts against an
     empty ``MetaData`` report thirteen ``remove_table`` ops normally and
     **nothing** under the blindfold, so the witness discriminates exactly
     the state the verdict cannot.
   - ``test_schema_guard.py`` owed one in a single test.  Both readers
     answer ``None`` for a schema that has never been migrated, so
     ``async_answer == sync_answer`` is agreement about nothing — and the
     fact was already in the class, asserted by the sibling test and not
     by the one that needs it.
   - ``test_retention.py`` owed two, both the silent direction the module
     is about: an emptied ``TABLE_TIMESTAMP_MAP`` parses no statement, and
     ``configured <= map`` holds over a ``retention_config`` with no rows.
   - ``test_logs_routes.py`` owed one.  ``stored <= declared`` is green
     over an emptied ``log_entries``; the file already argues this way in
     its ``logging_services`` fixture and had not applied it to the half
     that reads the box.  Measured 2026-08-30: 10 stored inside 15
     declared, five names of slack.
   - ``test_open_alert_predicate.py`` owed **the marker and never the
     premise**.  ``test_the_removed_spelling_still_cannot_reach_an_index``
     is docstringed *"The witness.  A constant observation is not
     evidence"* and predates this file by a fortnight.
   - ``test_snag_claims.py`` owes nothing, and is the one name left in
     :data:`PRE_CONVENTION`.  Its reason is in that constant.

   **The property under-read on both of its own axes, and the DSN was
   why** (`SNAG-TEST-007`, closed 2026-09-05).  Measured with a plugin
   recording every ``socket.connect`` per nodeid across a green full
   suite: **14** files open a real connection and **6** were in neither
   half of the population.  Four reach 8400 or 8500 over HTTP, which
   spells no DSN — and the sixth is the sharper one, because
   ``test_abandoned_runs.py``'s own docstring reads *"these run against
   the live database inside a rolled-back transaction"*: the exact axis
   the property claimed to cover, invisible because it reaches
   PostgreSQL through :func:`rolled_back_drive` and never writes a
   connection string out.  :data:`_LIVE_HANDLES` is the widening, and
   the URL literal it refuses is measured rather than argued about.

   Four of the six now hold the property and each was judged one file at
   a time, which is how this rule's exemption set went from six names to
   one.  All four owed a premise and none had one:

   - ``test_estate_surface_payloads.py`` owed the strongest of the four,
     and this module is why: it held the one live instance
     `SNAG-TEST-006`'s sweep found — a guard filtering the estate's
     audit findings down to a check that has filed nothing in its whole
     history — and **no existing guard could have asked it for a
     premise**, which is why that vacuity had no owner.  Its
     :meth:`_check_ran` discriminator existed and ran only in the branch
     where a filter came back empty; the marked premise asks it
     unconditionally.
   - ``test_estate_project_contracts.py`` owed one that its skip gate
     looks like and is not.  ``_estate_available()`` is evaluated once,
     at collection, and asks only whether ``/api/health`` answered 200;
     ``test_live_overview_is_usable`` is the assertion that the producer
     answered with an *estate*, and every shape test below it is a loop
     over what it proves non-empty.
   - ``test_abandoned_runs.py`` owed the marker and had the premise:
     ``test_the_database_really_rejects_a_fifth_status`` is docstringed
     *"The premise the pin rests on"* and predates this file.
   - ``test_ops_claims.py`` owed one for the **document** and none for
     the box, and the split is recorded at the marker rather than left
     as silence — every assertion it makes about the box holds whether
     or not 8500 answered, because ``unknown`` is what that module
     returns for each way of not-knowing.
3. **An empty population is a failure, never a pass.**  A glob that
   matched nothing satisfies rule 1 vacuously and reads identically to
   five compliant files — ``ports_checked``'s rule, and the reason
   ``test_the_population_is_real`` sits above the sweep rather than beside
   it.

The bus drives are deliberately outside rule 2's property.
``test_notify_guard_live.py`` and ``test_failure_replay_live.py`` open no
database at all; they are in scope by the glob, which is the half of the
population the naming convention is genuinely good at.

**What no sweep over ``tests/`` can reach is stated with its population
rather than left to be found again, and that population is empty
today.**  A file whose connection is made *for* it, by production code
it drives, carries no token at all — deciding which drive reaches a
connection is a call graph over ``sysadmin/``, which is Session 131's
stated reason for refusing a sweep.  The blind spot is a property of the
detector and has not moved; what emptied it is `SNAG-TEST-008` being
closed, and the two figures are kept either side so the count
reconciles.

Measured 2026-09-05 with a socket probe over the whole suite, **before**
the close: **14** connecting files, **4** holding none of the three
spellings.  Re-measured **after**: **12** and **2**, and the two that
remain are the pair that always cost nothing —
``test_async_http.py`` dials a ``ThreadingHTTPServer`` it started itself
on an ephemeral port, which is not this box and correctly not the
property; ``test_gpu_lease_live.py`` builds its client from config and is
in scope by the glob, marked.  Neither of the two that left was ever a
:data:`PRE_CONVENTION` name — that set is for files that **hold** the
property, and its tripwire asserts exactly that, so listing them would
have traded a red test for a false statement about the population.

The pair was ``test_alert_dedup.py`` and
``test_service_write_isolation.py``, both reaching 8400 through
``SysAdminAgent._ensure_arbitration`` — an unstubbed fail-open read
inside the very method under test.  Each stubs
:func:`~sysadmin.estate.client.read_arbitrated_stops` at the transport
now and declares :data:`~sysadmin.monitor.agent._NO_ARBITRATION` as the
reading its assertions hold under, with a test in each file pinning that
by **identity** so removing the stub is red on any box.  The reasoning
lives in ``tests/test_alert_dedup.py::_run``; two things it settled
belong here, because both are corrections to what this docstring said
when it filed the entry:

* **The cost was 2.75x what was reported.**  ``16 per suite run`` counted
  *distinct* addresses per nodeid rather than every connect.  The 8 tests
  make **44** connections — 22 HTTP calls, two of the ten-second timeouts
  each on a box that drops packets rather than refusing them.
* **"The answer cannot reach an assertion" was true and its stated reason
  was not.**  This said the reading reaches only ``details['arbitration']``
  *because* ``ServiceEntry(kind="http")`` has no ``systemd_unit``.  Driven
  with ``systemd_unit`` forced non-``None`` under a lease naming every
  spelling in sight, the rung **is** reached — a witness over
  ``_raise_judged`` counts **21** judgements moved ``critical`` →
  ``info`` carrying ``stopped_by_estate: True`` — and all 19 assertions
  still pass.  So the immunity is a property of what those files assert
  on, not of their fixtures, and no reading discriminates.  The first
  stand-in for that drive had no ``reading`` attribute and turned all 19
  red, which is a stand-in that cannot answer wearing the clothes of a
  result.
"""

from __future__ import annotations

import ast
import pathlib
import tomllib

TESTS = pathlib.Path(__file__).resolve().parent

#: This file, which must hold the spellings it hunts for in order to hunt
#: them — so rule 2 would report it as a stray, and did on its first run.
#: Exempted here and driven at in :meth:`test_the_detector_sees_its_owner`,
#: so the exemption is proven necessary rather than assumed.
OWNER = pathlib.Path(__file__).resolve()

#: The drives this file is the guard for.
LIVE_DRIVES = sorted(TESTS.glob("test_*_live.py"))

#: Files that open a live connection, are **not** named ``_live``, and owe
#: no marker.  A name here is a decision, never a way to be green.
#:
#: **One member, and its reason is that the premise is enforced in the
#: producer** (Session 132).  Every live read in ``test_snag_claims.py``
#: goes through :func:`sysadmin.snag_claims.query_one`, whose every way of
#: not-knowing returns ``unknown`` rather than ``match`` —
#: ``schema_guard``'s three verdicts, one module over — and the drive
#: asserts those branches by name:
#: ``test_an_emptied_source_is_unknown_and_never_a_refutation`` and
#: ``test_a_reader_that_parsed_nothing_is_unknown_not_a_match`` are premise
#: assertions that happen to be spelled as verdicts.  So the file holds
#: the property this module is about, eighteen times over, and a single
#: marker would name one check's premise and imply the other seventeen —
#: which is less true than the exemption.  Measured 2026-08-30: **every**
#: registered check is driven to ``unknown`` by a test in the class that
#: names it — 18 of 18 when this was written.
#:
#: **And the habit is enforced now rather than observed** (`SNAG-TEST-002`,
#: closed 2026-08-30).  ``TestEveryCheckCanSayItDoesNotKnow`` in that file
#: sweeps its own registry and refuses a check no class drives to that
#: branch, so the exemption rests on a guard rather than on a count
#: somebody took once.  The figure is not frozen here: the sweep computes
#: it, and a nineteenth check with no such drive is a red test rather than
#: a silently weaker exemption.
#:
#: The mark is deliberately **not** taken there, which would empty this set
#: entirely.  Rule 1 is about a drive asserting that *the box produced the
#: state it reads*; the sweep is a static walk over a source file, so a
#: ``premise`` mark on it would discharge rule 2 with a witness about
#: something else — and this module could not tell.  The exemption stays,
#: with a better reason than it had.
#:
#: **It used to be the one file the detector reported for the wrong hit,
#: and the widening made the hit right** (`SNAG-TEST-007`, 2026-09-05).
#: Until then :func:`_opens_a_live_connection` matched a ``sync_url``
#: read that asserts a DSN's *shape* and never connects, while the real
#: connection was transitive through ``query_one`` — a correct verdict
#: reached from evidence about something else.  Both ``query_one`` and
#: ``check_all`` are :data:`_LIVE_HANDLES` now, so the file is reported
#: for what it does.  The exemption is unmoved, because it never rested
#: on which clause fired; what changes is that a future edit deleting
#: that ``sync_url`` assertion no longer silently drops the file out of
#: the population.
PRE_CONVENTION = frozenset({"test_snag_claims.py"})

#: Substrings that only appear in a real DSN for this box's database.
_DSN_HINTS = ("postgresql+psycopg2://", "postgresql+asyncpg://")

#: Names whose **purpose** is to reach the live box, rather than names of
#: things that merely happen to.  A file that uses one is naming this
#: estate as surely as a file that writes a DSN out.
#:
#: **A URL literal was measured first and refused** (`SNAG-TEST-007`).
#: The obvious widening for the HTTP axis is the DSN rule's own shape —
#: match ``http://localhost:<port>`` the way :data:`_DSN_HINTS` matches a
#: connection string.  It does not transfer, and the reason is what makes
#: this constant necessary: nothing in this tree *models* a DSN (a fake
#: database is spelled ``sqlite:///``), while a loopback URL is exactly
#: how a fake service is spelled — a ``ServiceEntry``'s ``url``, a config
#: leaf's expected value, an ``httpx.MockTransport``'s base.  Measured
#: 2026-09-05 over ``tests/``: **14** files carry a loopback URL with a
#: port and **4** of them open a connection to it, so the literal rule
#: reports ten stand-ins and would put most of the service tests into
#: rule 2's population.  A name cannot be spelled by accident, and the
#: six below reach **6 of 6** connecting files with no false positive.
#:
#: This is a tripwire like :data:`PRE_CONVENTION` and not a call graph:
#: a name earns a place here by being the thing that dials, never by
#: sitting somewhere on the path to something that does.  Adding one is a
#: decision, and :meth:`TestTheLiveHandlesAreReal.test_every_handle_is_a_real_name`
#: refuses a name that no longer exists.
_LIVE_HANDLES = frozenset(
    {
        # tests/test_estate_project_contracts.py — the one statement of
        # 8400's address in `tests/`, and the reachability gate over it.
        "ESTATE_URL",
        "_estate_available",
        # sysadmin/snag_claims.py — the live-database harness.
        #
        # ``query_one`` was in this set for the length of one test run and
        # ``test_every_handle_is_used_by_a_drive`` refused it: the reader
        # every registered check goes through is named in exactly one
        # file, ``tests/test_snag_claims.py``, and named there only as the
        # string inside ``patch.object(snag_claims, "query_one", …)``.  A
        # name whose only appearance is a stub is the *opposite* of
        # evidence — it marks the connection being taken out — so it
        # exempted nothing and is recorded rather than quietly dropped.
        "rolled_back_drive",
        # sysadmin/core/schema_guard.py — reads the live `alembic_version`.
        "live_revision_sync",
        # sysadmin/ops_claims.py — runs the state checks, which is what
        # dials 8500 and what queries the live `alerts` table.
        "check_all",
    }
)


def _dotted(node: ast.expr) -> str:
    """Render an attribute chain as a dotted name, or ``""`` if it is not one."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    parts.append(node.id)
    return ".".join(reversed(parts))


def _is_premise_marker(node: ast.expr) -> bool:
    """Whether a decorator expression is ``pytest.mark.premise``.

    ``@pytest.mark.premise`` and a bare ``@mark.premise`` from a
    ``from pytest import mark`` both resolve; the call form
    ``@pytest.mark.premise()`` does too, because pytest accepts it and a
    detector that did not would refuse a spelling the runner honours.
    """
    if isinstance(node, ast.Call):
        node = node.func
    return _dotted(node).split(".")[-2:] == ["mark", "premise"]


def _marks_a_premise(path: pathlib.Path) -> bool:
    """Whether *path* marks at least one test — or one test class — as its premise."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(
        _is_premise_marker(decorator)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        for decorator in node.decorator_list
    )


def _opens_a_live_connection(path: pathlib.Path) -> bool:
    """Whether *path* names this box rather than modelling it.

    Three spellings, because all three are in the tree: a DSN written
    out, ``get_config().database.sync_url`` resolved from the shipped
    config, and one of :data:`_LIVE_HANDLES` — a name whose job is to
    open the connection.  An ``httpx.MockTransport``, a ``create_engine``
    against a temporary file and a ``ServiceEntry`` carrying a loopback
    ``url`` are none of them, which is the discrimination that keeps this
    from reporting every test that imports SQLAlchemy or names a port.

    **A handle counts where it is used, never where it is imported.**  A
    name in an import list and not a caller is the distinction
    ``tests/test_contract_reachability.py`` draws for its roots, and it
    is the same distinction here: a file that imports ``ESTATE_URL`` to
    re-export it reaches nothing.  ``ast.Import``/``ast.ImportFrom``
    produce ``ast.alias`` nodes and no ``ast.Name``, so skipping them
    costs no special case — and a handle named in *prose* is an
    ``ast.Constant`` and falls out for the same reason, which this
    module's own docstring depends on.

    A **qualified** use counts as a use: ``ops_claims.check_all(...)``
    binds no ``ast.Name`` for the handle, so keying on the bare name
    alone would leave ``import`` plus attribute access as a way to dodge
    the rule without meaning to.  It is deliberately the last segment
    that is matched rather than the dotted chain — which module a drive
    reaches the handle through is not what the property is about.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if any(hint in node.value for hint in _DSN_HINTS):
                return True
        if isinstance(node, ast.Attribute) and node.attr in {"sync_url", "url"}:
            inner = node.value
            if isinstance(inner, ast.Attribute) and inner.attr == "database":
                return True
        if isinstance(node, ast.Name) and node.id in _LIVE_HANDLES:
            return True
        if isinstance(node, ast.Attribute) and node.attr in _LIVE_HANDLES:
            return True
    return False


def _dodges_the_rule(path: pathlib.Path, named: frozenset[str] | set[str]) -> bool:
    """Whether *path* holds the property and discharges it by neither route.

    The two routes are the glob (*named*) and the marker, and they are
    interchangeable on purpose: what rule 2 is about is a file reading the
    live box with nothing asserting the box is as assumed, and a filename
    is only ever a proxy for that.  Composed here rather than inline so
    the clause can be driven at stand-ins — the sweep below reads the real
    ``tests/`` directory and can only ever report what happens to be in
    it, which is a detector nobody has watched fail.
    """
    return (
        path.resolve() != OWNER
        and path.name not in named
        and path.name not in PRE_CONVENTION
        and _opens_a_live_connection(path)
        and not _marks_a_premise(path)
    )


class TestEveryLiveDriveNamesItsPremise:
    """The sweep, and the witness that makes it mean anything."""

    def test_the_population_is_real(self):
        """Ordered first, because the sweep below passes vacuously without it.

        A glob that stopped matching — a rename, a move to a
        subdirectory — leaves ``offenders == []`` and reads exactly like
        five compliant files.  ``ports_checked``'s rule: zero-because-blind
        is never served as zero-because-clean.
        """
        assert len(LIVE_DRIVES) >= 5, (
            "the live-drive glob matches fewer files than the five that "
            f"existed when this was written: {[p.name for p in LIVE_DRIVES]}"
        )

    def test_every_live_drive_marks_its_premise(self):
        offenders = [path.name for path in LIVE_DRIVES if not _marks_a_premise(path)]
        assert offenders == [], (
            "a live drive believes negatives, so it must assert that the "
            "harness produced the state before anything below it means "
            "anything. Mark the test (or the class) that does with "
            f"@pytest.mark.premise: {offenders}"
        )

    def test_no_live_connection_dodges_the_glob(self):
        """Rule 2 — the population is a property, and the glob is a convention.

        Without this, the premise rule is opt-in by filename: a drive
        against the real database called ``test_something_else.py`` owes
        nothing and looks like every unit test beside it.

        A file off the glob discharges it the same way a member does, by
        marking a premise — so the remedy is the convention rather than a
        rename, and :data:`PRE_CONVENTION` shrinks to the files a sitting
        has decided owe none.
        """
        named = {path.name for path in LIVE_DRIVES}
        strays = sorted(
            path.name
            for path in TESTS.rglob("test_*.py")
            if _dodges_the_rule(path, named)
        )
        assert strays == [], (
            "these open a live connection without being named *_live.py and "
            "mark no premise, so nothing asserts the harness produced the "
            "state they read. Mark the test (or class) that does with "
            f"@pytest.mark.premise: {strays}"
        )


class TestTheDetectorCanBeSeenToFail:
    """Driven at stand-ins, because a sweep nobody falsified is a sweep.

    ``test_autogenerate_config.py``'s idiom: two of its five tests exist
    so the walker can be watched failing.  Here the interesting half is
    the near misses — a detector that matched text rather than syntax
    would report this file's own docstring, which names the marker four
    times.
    """

    def _drive(self, tmp_path: pathlib.Path, body: str) -> pathlib.Path:
        path = tmp_path / "test_probe_live.py"
        path.write_text("import pytest\n\n\n" + body, encoding="utf-8")
        return path

    def test_a_drive_with_no_marker_is_reported(self, tmp_path):
        path = self._drive(tmp_path, "def test_it_works():\n    assert True\n")
        assert _marks_a_premise(path) is False

    def test_a_function_level_marker_is_accepted(self, tmp_path):
        path = self._drive(
            tmp_path,
            "@pytest.mark.premise\ndef test_the_premises_hold():\n    assert True\n",
        )
        assert _marks_a_premise(path) is True

    def test_a_class_level_marker_is_accepted(self, tmp_path):
        """The shape ``test_message_backfill_live.py`` and the guard drive use.

        Rule 1's whole point: a premise that lives in a class is marked at
        the class, not by renaming its methods.
        """
        path = self._drive(
            tmp_path,
            "@pytest.mark.premise\nclass TestThePremises:\n"
            "    def test_the_box_is_as_assumed(self):\n        assert True\n",
        )
        assert _marks_a_premise(path) is True

    def test_prose_naming_the_marker_is_read_as_prose(self, tmp_path):
        """Load-bearing rather than tidy — this module's docstring says it four times.

        A textual detector would pass every file that merely *discusses*
        the convention, which is the failure ``test_open_alert_predicate``
        records one sweep over: report the documentation and the reader
        learns to ignore the family.
        """
        path = self._drive(
            tmp_path,
            '"""This drive would use pytest.mark.premise if it had one."""\n'
            "# pytest.mark.premise\n"
            "def test_it_works():\n"
            '    marker = "pytest.mark.premise"\n'
            "    assert marker\n",
        )
        assert _marks_a_premise(path) is False

    def test_a_near_miss_spelling_is_not_a_marker(self, tmp_path):
        """``premises`` is not ``premise``, and pytest would not honour it either.

        The failure mode of a typo'd marker is silence — pytest applies an
        unknown mark without complaint — so the detector has to be the
        thing that notices, which it can only do by refusing the
        near miss rather than matching loosely.
        """
        path = self._drive(
            tmp_path,
            "@pytest.mark.premises\ndef test_the_premises_hold():\n    assert True\n",
        )
        assert _marks_a_premise(path) is False


class TestTheConnectionDetector:
    """Rule 2's half, falsified in both directions."""

    def test_a_written_out_dsn_is_seen(self, tmp_path):
        path = tmp_path / "test_probe.py"
        path.write_text(
            'URL = "postgresql+psycopg2://gaddi@localhost:5432/projects"\n',
            encoding="utf-8",
        )
        assert _opens_a_live_connection(path) is True

    def test_a_config_resolved_dsn_is_seen(self, tmp_path):
        path = tmp_path / "test_probe.py"
        path.write_text(
            "def engine():\n    return create_engine(get_config().database.sync_url)\n",
            encoding="utf-8",
        )
        assert _opens_a_live_connection(path) is True

    def test_a_modelled_database_is_not(self, tmp_path):
        """The discrimination that keeps this off every SQLAlchemy importer.

        A temporary SQLite file and an ``httpx.MockTransport`` are both
        stand-ins, and a detector reporting them would put most of
        ``tests/`` into rule 2's population.
        """
        path = tmp_path / "test_probe.py"
        path.write_text(
            "def engine(tmp_path):\n"
            '    return create_engine(f"sqlite:///{tmp_path}/probe.db")\n',
            encoding="utf-8",
        )
        assert _opens_a_live_connection(path) is False

    def test_the_detector_sees_its_owner(self, tmp_path):
        """Driven at the real owner rather than a reconstruction of it.

        This module names both DSN spellings in :data:`_DSN_HINTS` and
        writes one out in the probe above, so it holds the property it
        detects and rule 2 reported it as a stray on its first run.  The
        exemption is therefore load-bearing, and this is what keeps it
        from silently covering a real stray the day the hints move
        elsewhere.
        """
        assert _opens_a_live_connection(OWNER) is True

    def test_a_live_handle_in_use_is_seen(self, tmp_path):
        """The HTTP axis, which has no literal-shaped evidence of its own.

        ``tests/test_estate_project_contracts.py`` reaches 8400 and
        spells no DSN; what it does spell is the name of the address.
        """
        path = tmp_path / "test_probe.py"
        path.write_text(
            "def test_it():\n"
            '    return httpx.get(f"{ESTATE_URL}/api/health")\n',
            encoding="utf-8",
        )
        assert _opens_a_live_connection(path) is True

    def test_a_qualified_use_is_a_use(self, tmp_path):
        """The clause that removing left every test green.

        Driven as a mutation after the four above were written: deleting
        the ``ast.Attribute`` arm of :func:`_opens_a_live_connection`
        broke nothing, because every handle in this tree happens to be
        imported by name today.  So the arm was carried by a coincidence
        in the current tree rather than by anything watching it, and
        ``import ops_claims`` plus ``ops_claims.check_all(...)`` was a way
        out of rule 2 that nobody would have chosen and nothing would
        have reported.
        """
        path = tmp_path / "test_probe.py"
        path.write_text(
            "from sysadmin import ops_claims\n"
            "\n"
            "def test_it():\n"
            "    return ops_claims.check_all(STATUS_PATH)\n",
            encoding="utf-8",
        )
        assert _opens_a_live_connection(path) is True

    def test_a_handle_that_is_only_imported_is_not_a_use(self, tmp_path):
        """A root is a name *used*, never a name *imported*.

        ``tests/test_contract_reachability.py``'s rule, and it costs no
        special case: an import binds an ``ast.alias`` and no
        ``ast.Name``, so a module re-exporting :data:`ESTATE_URL`
        without dialling it falls out for free.
        """
        path = tmp_path / "test_probe.py"
        path.write_text(
            "from tests.test_estate_project_contracts import ESTATE_URL\n"
            "\n"
            "def test_it():\n"
            "    assert True\n",
            encoding="utf-8",
        )
        assert _opens_a_live_connection(path) is False

    def test_a_handle_named_in_prose_is_read_as_prose(self, tmp_path):
        """Load-bearing rather than tidy — this module names five in its docstrings.

        :func:`_marks_a_premise` has this property for the marker and it
        is asserted there; the handle clause needs its own, because a
        detector matching text would report every module that merely
        *documents* which names reach the box, this one first.
        """
        path = tmp_path / "test_probe.py"
        path.write_text(
            '"""A drive would use rolled_back_drive if it needed the box."""\n'
            "# ESTATE_URL, check_all, query_one\n"
            "def test_it():\n"
            '    handle = "live_revision_sync"\n'
            "    assert handle\n",
            encoding="utf-8",
        )
        assert _opens_a_live_connection(path) is False

    def test_a_loopback_url_literal_is_not_evidence(self, tmp_path):
        """The widening that was measured and refused, pinned as a refusal.

        The obvious HTTP rule is :data:`_DSN_HINTS`' own shape — match
        ``http://localhost:<port>``.  It does not transfer, because a
        loopback URL is how a *fake* service is spelled here: a
        ``ServiceEntry``'s ``url``, a config leaf's expected value, an
        ``httpx.MockTransport``'s base.  Measured 2026-09-05 over
        ``tests/``: **14** files carry one with a port and **4** connect
        to it.  Without this test the refusal is a paragraph, and the
        next reader adds the rule the paragraph argues against.
        """
        path = tmp_path / "test_probe.py"
        path.write_text(
            "def entry():\n"
            '    return ServiceEntry(name="svc", kind="http", '
            'url="http://localhost:8400/api/health")\n',
            encoding="utf-8",
        )
        assert _opens_a_live_connection(path) is False

    def test_a_live_reader_with_no_marker_is_a_stray(self, tmp_path):
        """The clause as it stood before Session 132, still doing its job."""
        path = tmp_path / "test_something_else.py"
        path.write_text(
            "def test_it(tmp_path):\n"
            '    return create_engine("postgresql+psycopg2://gaddi@localhost:5432/projects")\n',
            encoding="utf-8",
        )
        assert _dodges_the_rule(path, frozenset()) is True

    def test_a_live_reader_that_marks_a_premise_is_not(self, tmp_path):
        """The clause Session 132 added, and the reason the set could shrink.

        Five of the six exempted names discharge rule 2 this way now, so
        this is the assertion that makes their removal from
        :data:`PRE_CONVENTION` mean something rather than merely leave
        the sweep quiet.
        """
        path = tmp_path / "test_something_else.py"
        path.write_text(
            "import pytest\n\n\n"
            "@pytest.mark.premise\n"
            "def test_the_box_is_as_assumed():\n"
            '    engine = create_engine("postgresql+psycopg2://gaddi@localhost:5432/projects")\n'
            "    assert engine\n",
            encoding="utf-8",
        )
        assert _dodges_the_rule(path, frozenset()) is False

    def test_a_marker_alone_does_not_put_a_file_in_scope(self, tmp_path):
        """The property is the connection; the marker only discharges it.

        Without this the two halves are indistinguishable — a rule that
        fired on the marker would report every ordinary unit test that
        happened to mark one, which is rule 1's population wearing rule
        2's clothes.
        """
        path = tmp_path / "test_something_else.py"
        path.write_text(
            "def test_it(tmp_path):\n"
            '    return create_engine(f"sqlite:///{tmp_path}/probe.db")\n',
            encoding="utf-8",
        )
        assert _dodges_the_rule(path, frozenset()) is False

    def test_the_pre_convention_set_still_holds_its_property(self):
        """A tripwire, so its members are asserted rather than trusted.

        A file listed here that no longer opens a live connection is an
        exemption outliving its reason, which is how a hand-written set
        rots into a classification nothing checks.
        """
        lapsed = sorted(
            name
            for name in PRE_CONVENTION
            if (TESTS / name).exists() and not _opens_a_live_connection(TESTS / name)
        )
        assert lapsed == [], (
            f"these no longer open a live connection — drop them from "
            f"PRE_CONVENTION: {lapsed}"
        )

    def test_no_exempted_file_has_since_marked_a_premise(self):
        """The other way an exemption outlives its reason.

        A member that has gained a marker discharges rule 2 by the
        ordinary route, so the entry is doing nothing and the next reader
        cannot tell that from an entry doing the work.  ``FROZEN_TABLES``'
        rule again: the set is a stage and not a destination, so leaving
        it must be observable.
        """
        discharged = sorted(
            name
            for name in PRE_CONVENTION
            if (TESTS / name).exists() and _marks_a_premise(TESTS / name)
        )
        assert discharged == [], (
            "these mark a premise and are exempted as well — the exemption "
            f"is no longer load-bearing, so drop them: {discharged}"
        )


class TestTheLiveHandlesAreReal:
    """:data:`_LIVE_HANDLES` is a tripwire, so its members are asserted.

    A handle is a name in another module, and the failure mode of a
    rename there is **silence**: the clause goes on running, matches
    nothing, and the file it was reaching for drops out of rule 2's
    population with no test going red.  That is the shape
    :data:`PRE_CONVENTION` already guards against for filenames, at the
    size of an identifier.

    Bound rather than imported, deliberately.  Importing
    ``tests.test_estate_project_contracts`` evaluates a ``skipif``
    argument that dials 8400, so the check for whether this module names
    the box would make this module name the box.
    """

    @staticmethod
    def _bound_names(path: pathlib.Path) -> set[str]:
        """Every name *defined* in a module — assigned, or bound by a def."""
        names: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
        return names

    def test_every_handle_is_defined_somewhere(self):
        root = TESTS.parent
        bound: set[str] = set()
        for path in [*(root / "sysadmin").rglob("*.py"), *TESTS.rglob("test_*.py")]:
            bound |= self._bound_names(path)
        missing = sorted(_LIVE_HANDLES - bound)
        assert missing == [], (
            "these name nothing under sysadmin/ or tests/ any more, so the "
            "clause that reads them matches nothing and whatever they were "
            f"reaching for has left rule 2's population in silence: {missing}"
        )

    def test_every_handle_is_used_by_a_drive(self):
        """A handle nothing uses is an entry that has stopped doing work.

        The other way the set rots — not a rename, but the last caller
        going away — which reads identically to a handle still earning
        its place.
        """
        unused = sorted(
            handle
            for handle in _LIVE_HANDLES
            if not any(
                handle in self._used_names(path)
                for path in TESTS.rglob("test_*.py")
                if path.resolve() != OWNER
            )
        )
        assert unused == [], (
            f"no drive uses these, so they are exempting nothing: {unused}"
        )

    @staticmethod
    def _used_names(path: pathlib.Path) -> set[str]:
        """The two node kinds :func:`_opens_a_live_connection` matches, and
        for its reason — a tripwire reading a narrower set than the clause
        it guards would refuse a handle the clause is legitimately using.
        """
        used: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
        return used


class TestTheRunnerHalfStaysOn:
    """The shipped ``pyproject.toml``, pinned rather than trusted.

    Two mechanisms refuse a mis-spelled marker and they are not one fact
    stated twice: :func:`_is_premise_marker` refuses a near miss in the
    *syntax*, and ``strict_markers`` refuses an *unregistered* mark at
    collection.  Either alone leaves a hole — a marker spelled
    ``pytest.mark.premis`` is caught by both, but a marker registered and
    then dropped from ``markers`` is caught only by the runner, and a
    drive marked with some other registered mark only by the sweep.

    Pinned here for ``syslog_priority``-against-``PRIORITY_MAP``'s
    reason: the fact lives in a second file this module leans on, so a
    test drives it rather than the reader remembering.
    """

    @staticmethod
    def _ini() -> dict:
        root = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
        return tomllib.loads(root.read_text(encoding="utf-8"))["tool"]["pytest"][
            "ini_options"
        ]

    def test_the_premise_marker_is_registered(self):
        declared = [m.split(":", 1)[0] for m in self._ini().get("markers", [])]
        assert "premise" in declared, (
            "@pytest.mark.premise is unregistered, so strict_markers would "
            "refuse the very files this module requires it on"
        )

    def test_strict_markers_is_the_ini_option_and_not_addopts(self):
        """The spelling is the assertion, because the other one does nothing.

        Measured on pytest 9.0.2: ``--strict-markers`` refuses a typo from
        the command line and is silently ignored from ``addopts``.  So a
        future edit moving it there reads as configured, enforces
        nothing, and this is what notices.
        """
        ini = self._ini()
        assert ini.get("strict_markers") is True, (
            "strict_markers is not enabled as an ini option — an unknown "
            "mark is a warning again"
        )
        assert "strict-markers" not in ini.get("addopts", ""), (
            "--strict-markers via addopts is ignored on pytest 9.0.2; keep "
            "the ini option, which is what actually enforces it"
        )
