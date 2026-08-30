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
2. **The population is a property, not the glob.**  ``tests/test_*_live.py``
   is a naming convention, and a convention is dodgeable by not following
   it — a seventh drive against the live database called anything else
   would owe nothing.  :func:`_opens_a_live_connection` is the property,
   and :data:`PRE_CONVENTION` is the six files that hold it today and
   predate this file.  That set is a tripwire and not a classification:
   nothing may be added to it without a sitting deciding to, which is
   ``FROZEN_TABLES``' rule at the size of a filename.
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

#: Files that open a live connection and are **not** named ``_live``.
#:
#: Measured 2026-08-30, and every one predates the convention.  A seventh
#: name appearing here is a drive that dodged the glob, which is the one
#: thing rule 2 exists to catch — so it is added by a sitting that has
#: decided it owes no premise, never to make this file green.
PRE_CONVENTION = frozenset(
    {
        "test_logs_routes.py",
        "test_open_alert_predicate.py",
        "test_retention.py",
        "test_schema_drift.py",
        "test_schema_guard.py",
        "test_snag_claims.py",
    }
)

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
        """
        named = {path.name for path in LIVE_DRIVES}
        strays = sorted(
            path.name
            for path in TESTS.rglob("test_*.py")
            if path.resolve() != OWNER
            and path.name not in named
            and path.name not in PRE_CONVENTION
            and _opens_a_live_connection(path)
        )
        assert strays == [], (
            "these open a live connection without being named *_live.py, so "
            "the premise rule above cannot see them. Rename them, or add "
            f"them to PRE_CONVENTION with a reason: {strays}"
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
