"""The file half of the estate's wiring check, read here rather than pulled.

``docs/adr/0008-the-file-half-of-the-wiring-check.md`` holds why one half
of estate-manager's check 11 crossed the seam on 2026-09-08 and the other
half deliberately did not.  These drive the half that did.

**Every specimen is built from this box's real ``settings.json``** rather
than from a hand-written fragment, because the two defects this sitting
found were both invisible to a fragment: json's own message already ends
in "at" on the errors that carry a position, and the live file is a
symlink whose target is in a repository the editor is not told about.
A 40-byte truncation of the real file reproduces the 2026-08-25 shape;
a three-line literal does not.
"""

import json
import os
import stat
from pathlib import Path

import pytest

from sysadmin.estate import hook_wiring
from sysadmin.estate.judgements import (
    DEFAULT_SEVERITY,
    SURFACE_TITLE_PATTERNS,
    WIRING_FILE_TITLE,
    judge_hook_wiring,
)


def _real_settings() -> str:
    """This box's own file, or a stand-in shaped like it.

    The tests below need *a JSON document long enough that truncating it
    leaves an unterminated string*, which is the shape the founding
    incident had.  The real file is that; the fallback keeps the file
    tests meaningful on a machine that has no ``~/.claude``.
    """
    live = hook_wiring.SETTINGS_PATH.expanduser()
    try:
        return live.read_text(encoding="utf-8")
    except OSError:
        return json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "x" * 400}]}]}})


@pytest.fixture
def settings(tmp_path: Path) -> Path:
    path = tmp_path / "settings.json"
    path.write_text(_real_settings(), encoding="utf-8")
    return path


class TestTheReaderSeparatesBrokenFromUnreadable:
    """Rule 2, which is the whole reason a local read returns a
    ``SurfaceResult``: the agent gates raising *and* resolving on
    ``read``, so "the file is broken" and "I could not look" must not
    arrive as the same answer.  The estate's own check draws the line in
    the same place (their ADR-0016 §3)."""

    def test_a_clean_file_is_read_with_no_fault(self, settings):
        result = hook_wiring.read_settings(settings)
        assert result.read is True
        assert result.payload is not None
        assert result.payload["fault"] is None
        assert result.payload["kind"] is None

    def test_a_readable_broken_file_is_a_payload_and_not_an_error(self, settings):
        """The direction that matters. Reporting this as ``error`` would
        make the surface unread, and an unread surface raises nothing —
        so the one fault this family exists for would be silent, which is
        precisely the state the estate's check was built to end."""
        raw = settings.read_text()
        settings.write_text(raw[: len(raw) - 40])

        result = hook_wiring.read_settings(settings)

        assert result.read is True
        assert result.error is None
        assert result.payload["kind"] == hook_wiring.KIND_UNPARSEABLE

    def test_a_file_that_is_not_there_is_unread(self, tmp_path):
        """Not a finding. An auditor that cannot look must not file as
        though it had, and a tree deployed somewhere without this file is
        not an owner who deleted their hook wiring."""
        result = hook_wiring.read_settings(tmp_path / "absent.json")

        assert result.read is False
        assert result.payload is None
        assert "FileNotFoundError" in result.error

    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads unreadable files")
    def test_a_file_that_cannot_be_opened_is_unread(self, settings):
        """The other way to be blind, and the one a missing-file test
        cannot witness: the path exists, so an implementation testing
        ``exists()`` rather than catching ``OSError`` passes that test and
        fails this one."""
        settings.chmod(stat.S_IWUSR)
        try:
            result = hook_wiring.read_settings(settings)
        finally:
            settings.chmod(stat.S_IRUSR | stat.S_IWUSR)

        assert result.read is False
        assert result.payload is None

    def test_valid_json_that_is_not_an_object_is_a_fault(self, tmp_path):
        """It parses and declares no hooks, which is the same consequence
        by a different route — so it is a fault and not a clean read."""
        for body in ("[1, 2, 3]", '"a string"', "42", "null"):
            path = tmp_path / "s.json"
            path.write_text(body)
            result = hook_wiring.read_settings(path)
            assert result.read is True
            assert result.payload["kind"] == hook_wiring.KIND_NOT_AN_OBJECT, body


class TestTheFaultCarriesJsonsOwnSentence:
    """The defect the live drive found and no fixture would have."""

    def test_the_position_is_not_stated_twice(self, settings):
        """``exc.msg`` for a truncated document is *"Unterminated string
        starting at"* — the position is meant to follow it, and
        ``f"{msg} at line {n}"`` therefore reads "starting at at line
        671". ``str(exc)`` is the sentence that composes for every
        message, which is the producer's own format rather than a second
        statement of it."""
        raw = settings.read_text()
        settings.write_text(raw[: len(raw) - 40])

        fault = hook_wiring.read_settings(settings).payload["fault"]

        assert " at at " not in fault
        assert "line" in fault

    def test_the_fault_is_a_non_empty_string_on_every_broken_shape(self, tmp_path):
        """:func:`judge_hook_wiring` gates on exactly that, so a reader
        that returned ``None`` or ``""`` here would raise nothing while
        reporting a fault — a family switched off by a type."""
        for body in ("{", "[]", "nope"):
            path = tmp_path / "s.json"
            path.write_text(body)
            fault = hook_wiring.read_settings(path).payload["fault"]
            assert isinstance(fault, str) and fault.strip(), body


class TestTheReadNamesWhereItActuallyLanded:
    """The trap is one day old: since 2026-09-06 this path is a symlink
    into ``~/projects/dotfiles``, so the obvious fix edits a tracked file
    in a repository nobody mentioned."""

    def test_a_symlink_names_its_target(self, tmp_path):
        target = tmp_path / "tracked" / "settings.json"
        target.parent.mkdir()
        target.write_text("{")
        link = tmp_path / "settings.json"
        link.symlink_to(target)

        payload = hook_wiring.read_settings(link).payload

        assert payload["path"] == str(link)
        assert payload["resolves_to"] == str(target)

    def test_a_plain_file_names_no_target(self, settings):
        """The key is absent rather than equal to ``path``: a message
        saying *"it is a symlink to <itself>"* is worse than saying
        nothing, and :func:`judge_hook_wiring` gates the clause on
        presence."""
        assert "resolves_to" not in hook_wiring.read_settings(settings).payload

    def test_a_symlink_loop_is_described_rather_than_raised(self, tmp_path):
        """The guard's only reachable input, and it is not an
        ``OSError``.

        ``_where`` runs at the top of :func:`read_settings`, *before* the
        file is opened, and the docstring promises resolution failure is
        reported as absence rather than raised — so an uncaught one takes
        down the surface whose whole job is to say every hook on this box
        is down.  Until 2026-09-08 the guard read ``except OSError`` and
        could not catch this: :func:`pathlib.check_eloop` re-raises the
        errno-40 error as a ``RuntimeError``, which is not an ``OSError``
        subclass.  Reported by estate-manager as ``f5e450cb`` after their
        identical line survived a mutation, and re-measured here.

        This is the input that keeps the guard alive.  It dies under both
        mutants — deleting the ``try`` entirely, and restoring it as
        ``except OSError`` — where an assertion about the *shape* of a
        clean read dies under neither.
        """
        a, b = tmp_path / "a.json", tmp_path / "b.json"
        a.symlink_to(b)
        b.symlink_to(a)

        result = hook_wiring.read_settings(a)

        assert result.error is not None
        assert result.payload is None
        assert not result.read

    def test_a_self_referential_loop_is_the_same_answer(self, tmp_path):
        """The one-file shape, because ``check_eloop`` is reached by a
        different route and a reader repairing this by hand is at least
        as likely to type it."""
        link = tmp_path / "settings.json"
        link.symlink_to(link)

        assert hook_wiring.read_settings(link).error is not None

    def test_the_guard_reports_absence_rather_than_a_wrong_target(
        self, tmp_path
    ):
        """``_where``'s own contract, which the surface test cannot
        observe: a loop yields no payload at all, so *"the path is named
        and where it lands is not"* is only assertable here.  A guard
        that returned ``resolves_to`` pointing at the first hop would be
        worse than silence — ``judge_hook_wiring`` gates its clause on
        presence."""
        a, b = tmp_path / "a", tmp_path / "b"
        a.symlink_to(b)
        b.symlink_to(a)

        where = hook_wiring._where(a)

        assert where == {"path": str(a)}

    def test_the_guard_is_narrow_because_the_population_is(self, tmp_path):
        """Why this is not ``except Exception``.

        ``resolve(strict=False)`` *swallows* every other hostile input —
        estate-manager drove six and four returned a path.  Pinning that
        is what stops a later reader widening the guard to a bare
        ``except``, which would report a genuinely undescribable path as
        a plain one.  Loops are the population; these are the
        non-members.
        """
        deep = tmp_path / ("x" * 300)
        through_a_file = tmp_path / "file.txt" / "settings.json"
        (tmp_path / "file.txt").write_text("not a directory")

        chain = tmp_path / "link0"
        chain.symlink_to(tmp_path / "target.json")
        (tmp_path / "target.json").write_text("{}")

        for path in (deep, through_a_file, chain):
            assert hook_wiring._where(path)["path"] == str(path), path

    def test_the_path_is_expanded(self):
        """``SETTINGS_PATH`` is stored unexpanded on purpose, so the
        expansion has to happen at read time. A reader that skipped it
        would report ``~/.claude/settings.json`` as unreadable on every
        box."""
        payload_or_error = hook_wiring.read_settings()
        rendered = payload_or_error.payload or {"path": payload_or_error.error}
        assert "~" not in str(rendered.get("path", ""))


class TestTheJudgeSpeaksOnlyForAFault:
    def test_a_clean_read_is_no_judgement(self):
        assert judge_hook_wiring({"path": "/x", "kind": None, "fault": None}) == []

    def test_a_fault_is_one_row_on_its_own_surface(self):
        [judged] = judge_hook_wiring(
            {"path": "/x/settings.json", "kind": "unparseable", "fault": "boom"}
        )
        assert judged.title == WIRING_FILE_TITLE
        assert judged.surface == "hook_wiring"
        assert judged.severity == DEFAULT_SEVERITY

    def test_the_title_belongs_to_this_surface_and_no_other(self):
        """The partition the sweep depends on. ``audit_findings`` was
        narrowed to ``Estate hook % not wired for %`` on the same day this
        surface appeared, and a pattern left wide would let a successful
        pull of 8400 resolve a row raised from the local filesystem."""
        import re

        def like(pattern, value):
            return re.fullmatch(pattern.replace("%", ".*"), value) is not None

        for surface, patterns in SURFACE_TITLE_PATTERNS.items():
            matched = any(like(p, WIRING_FILE_TITLE) for p in patterns)
            assert matched is (surface == "hook_wiring"), surface

    def test_the_message_says_what_it_costs(self):
        """``alert.message`` reaches a notification body verbatim, and the
        news is not that a file is malformed — it is that every hook on
        the box is down and none of them can say so."""
        [judged] = judge_hook_wiring(
            {"path": "/x/settings.json", "kind": "unparseable", "fault": "boom"}
        )
        assert "every hook on this box is down" in judged.message
        assert "fail open" in judged.message

    def test_the_symlink_trap_is_named_only_when_there_is_one(self):
        base = {"path": "/x/settings.json", "kind": "unparseable", "fault": "boom"}
        [plain] = judge_hook_wiring(base)
        [linked] = judge_hook_wiring({**base, "resolves_to": "/repo/settings.json"})

        assert "symlink" not in plain.message
        assert "/repo/settings.json" in linked.message

    @pytest.mark.parametrize("fault", [None, "", "   ", 5, ["boom"], {"a": 1}, True])
    def test_a_payload_it_cannot_read_raises_nothing(self, fault):
        """Fails *open* — ``monitor/collation.py``'s posture rather than
        ``schema_guard``'s — because a false positive here tells an owner
        whose hooks are fine that every one of them is down, and a family
        that cries wolf once is one nobody reads twice."""
        assert judge_hook_wiring({"path": "/x", "fault": fault}) == []

    def test_the_details_carry_the_whole_reading(self):
        """Evidence, not identity. The title is fixed, so everything that
        distinguishes one occurrence from another has to be in the blob."""
        payload = {
            "path": "/x/settings.json",
            "resolves_to": "/repo/settings.json",
            "kind": "unparseable",
            "fault": "boom",
        }
        [judged] = judge_hook_wiring(payload)
        assert judged.details == payload


class TestThePremiseThisFamilyRestsOn:
    """Live, and it asserts *"we can look"* rather than *"it is fine"*.

    A family whose surface is permanently unread raises nothing and looks
    exactly like a family with nothing to report — this repository's
    ``ports_checked`` rule, at the size of a whole check. If the harness
    ever moves where its settings live, this goes red; if the file is
    genuinely broken, this still passes and the *alert* is the mechanism
    that speaks.
    """

    def test_the_real_settings_file_can_be_looked_at(self):
        result = hook_wiring.read_settings()
        assert result.read is True, result.error
