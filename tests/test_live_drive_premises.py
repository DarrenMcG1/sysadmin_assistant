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
     :data:`PRE_CONVENTION`.  Its reason is in that constant, and it is
     also the one the detector reports for the **wrong hit**.
3. **An empty population is a failure, never a pass.**  A glob that
   matched nothing satisfies rule 1 vacuously and reads identically to
   five compliant files — ``ports_checked``'s rule, and the reason
   ``test_the_population_is_real`` sits above the sweep rather than beside
   it.

The bus drives are deliberately outside rule 2's property.
``test_notify_guard_live.py`` and ``test_failure_replay_live.py`` open no
database at all; they are in scope by the glob, which is the half of the
population the naming convention is genuinely good at.
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
#: names it — 18 of 18 when this was written — and the figure is served
#: live by ``sysadmin-check-snags``' ``unknown_branch_unenforced`` rather
#: than frozen here.  Nothing *enforces* the habit, which is the
#: exemption's stated cost and is `SNAG-TEST-002`.
#:
#: It is also the one file the detector reports for the **wrong hit**.
#: :func:`_opens_a_live_connection` matches a ``sync_url`` read that
#: asserts a DSN's *shape* and never connects; the real connection is
#: transitive, through ``query_one``.  Right by accident, and the blind
#: spot it names is stated rather than fixed — deciding which drive
#: reaches a connection is a call graph over ``sysadmin/``, not a sweep
#: over ``tests/``, which is Session 131's own reason for refusing a
#: sweep.  Measured 2026-08-30: of the nineteen files naming a
#: transitively-connecting helper, this is the only one that reaches a
#: connection, so the blind spot has a population of one and it is listed.
PRE_CONVENTION = frozenset({"test_snag_claims.py"})

#: Substrings that only appear in a real DSN for this box's database.
_DSN_HINTS = ("postgresql+psycopg2://", "postgresql+asyncpg://")


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
    """Whether *path* names this box's database rather than modelling it.

    Two spellings, because both are in the tree: a DSN written out, and
    ``get_config().database.sync_url`` resolved from the shipped config.
    An ``httpx.MockTransport`` or a ``create_engine`` against a temporary
    file is neither, which is the discrimination that keeps this from
    reporting every test that imports SQLAlchemy.
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
