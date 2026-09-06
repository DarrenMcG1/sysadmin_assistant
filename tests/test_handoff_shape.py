"""`HANDOFF.md` is parsed by another repository, so its shape is a surface.

estate-manager's `estate_service/projects/roadmap.py` reads this file and
publishes one line from it to the estate board.  Two of its behaviours
make the shape of this document load-bearing, and both were driven
against their parser on 2026-08-31 rather than read out of it:

* ``next_action_from_handoff`` returns the first meaningful line under
  the **first heading containing "next"**, case-insensitively.  A second
  such heading earlier in the file would silently take over the board
  line.
* Failing that, it falls back to ``first_unchecked_task`` — **any**
  ``- [ ]`` anywhere in the document, prefixed with its heading.

So the `## Scheduled action` section added the same day carries two
rules, and this file is what enforces them:

1. **Plain bullets, never ``- [ ]``.**  Driven as a counterfactual: with
   the scheduled item written as a checkbox and the ``## Next action``
   heading renamed, their parser published *"Scheduled action →
   **2026-09-07** — Read the first Monday under lease…"* as this
   repository's next action.  A week-out measurement on the estate board
   is not a next action, and nothing on either side would have said so.
2. **No heading containing "next" but the real one.**  "Scheduled
   action" is deliberately not "Next up" or "Coming next".

The rules are asserted as properties of *this document*, never as a copy
of their parser's logic — that would be a second statement of somebody
else's rule, free to drift.  What is restated here is only which
document shapes are allowed, and the reason is cited rather than
reimplemented.

``scripts/claude-preflight.sh`` prints the section and is the only reader
of it on this box; there is no hook, no check and no estate surface, so
an item that reaches neither the print nor a sitting's eye reaches
nothing.
"""

from __future__ import annotations

import importlib
import pathlib
import re

import pytest

import sysadmin.snag_claims as snag_claims

HANDOFF = pathlib.Path(__file__).resolve().parent.parent / "HANDOFF.md"

#: The heading their parser is allowed to find, and the only one.
NEXT_HEADING = "## Next action"
SCHEDULED_HEADING = "## Scheduled action"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_UNCHECKED_RE = re.compile(r"^\s*[-*]\s+\[\s\]")


def _text() -> str:
    return HANDOFF.read_text(encoding="utf-8")


def _headings(text: str) -> list[str]:
    return [m.group(0) for line in text.splitlines() if (m := _HEADING_RE.match(line))]


def _section_body(text: str, heading: str) -> list[str] | None:
    """The lines under *heading*, up to the next heading of any level."""
    out: list[str] | None = None
    for line in text.splitlines():
        if _HEADING_RE.match(line):
            if out is not None:
                return out
            out = [] if line.strip() == heading else None
            continue
        if out is not None:
            out.append(line)
    return out


class TestOnlyOneHeadingCanClaimTheBoardLine:
    def test_the_document_has_exactly_one_next_heading(self):
        claimants = [h for h in _headings(_text()) if "next" in h.lower()]
        assert claimants == [NEXT_HEADING], (
            "estate-manager's next_action_from_handoff takes the FIRST heading "
            f"containing 'next' and publishes its first line to the board: {claimants}"
        )

    def test_it_is_the_first_heading_after_the_title(self):
        """Ordering is not what their parser keys on, and it is asserted
        anyway: a `## Next action` pushed below a session write-up still
        parses, and a reader opening the file has to hunt for the one
        line that is not history."""
        headings = _headings(_text())
        assert headings[0].startswith("# Handoff — ")
        assert headings[1] == NEXT_HEADING

    def test_the_scheduled_heading_cannot_claim_it(self):
        assert "next" not in SCHEDULED_HEADING.lower()
        assert SCHEDULED_HEADING in _headings(_text())


class TestTheScheduledSectionCarriesNoCheckbox:
    """Rule 1, and its population is whatever the section holds today.

    An empty section passes this vacuously, which is why
    :class:`TestTheDetectorWouldSeeOne` sits beneath it — a sweep that
    finds nothing over a population of zero is not evidence
    (``ports_checked``'s rule).
    """

    def test_no_scheduled_item_is_an_unchecked_task(self):
        body = _section_body(_text(), SCHEDULED_HEADING)
        assert body is not None, f"{SCHEDULED_HEADING} is gone from {HANDOFF.name}"
        offenders = [line for line in body if _UNCHECKED_RE.match(line)]
        assert not offenders, (
            "a `- [ ]` here is published to the estate board as this "
            "repository's next action whenever the `## Next action` heading is "
            f"absent — first_unchecked_task takes any unchecked box: {offenders}"
        )

    def test_nowhere_else_in_the_document_either(self):
        """The fallback is document-wide, so the rule is too.

        Session write-ups below have carried unchecked boxes before; the
        assertion is that they do not *now*, because the fallback would
        reach them first only if `## Next action` were removed — the same
        compound failure, one section further down.
        """
        offenders = [line for line in _text().splitlines() if _UNCHECKED_RE.match(line)]
        assert not offenders, (
            f"an unchecked box in HANDOFF.md is a board line waiting to happen: {offenders}"
        )


class TestTheDetectorWouldSeeOne:
    """Both rules driven at documents that break them.

    Without these, a green suite is satisfied by a detector that has
    stopped reading — and the real file is deliberately clean, so it can
    witness neither rule on its own.
    """

    @pytest.mark.parametrize(
        "bullet", ["- [ ] **2026-09-07** — a task", "  * [ ] indented and starred"]
    )
    def test_it_catches_a_checkbox(self, bullet):
        assert _UNCHECKED_RE.match(bullet)

    @pytest.mark.parametrize("bullet", ["- **2026-09-07** — a plain bullet", "- [x] done"])
    def test_it_passes_what_the_rule_allows(self, bullet):
        assert not _UNCHECKED_RE.match(bullet)

    def test_it_catches_a_second_next_heading(self):
        forged = "# Handoff — 2026-08-31\n\n## Coming next\n\nsomething\n\n## Next action\n\nreal\n"
        claimants = [h for h in _headings(forged) if "next" in h.lower()]
        assert claimants == ["## Coming next", "## Next action"]
        assert claimants[0] != NEXT_HEADING

    def test_the_section_reader_finds_a_body_and_stops_at_the_next_heading(self):
        forged = (
            "# Handoff — 2026-08-31\n\n"
            f"{SCHEDULED_HEADING}\n\n- **2026-09-07** — one\n\n"
            "## Session 1\n\n- [ ] not in the section\n"
        )
        body = _section_body(forged, SCHEDULED_HEADING)
        assert body is not None
        assert [line for line in body if line.strip()] == ["- **2026-09-07** — one"]


class TestPreflightIsTheOnlyReaderAndSaysSo:
    """The section's whole mechanism is a print, and that is stated.

    A scheduled item is enforced by nothing — no hook, no check, no
    estate surface — so if `claude-preflight.sh` stopped printing it, an
    item would be invisible in exactly the way the section exists to
    prevent, and silently.
    """

    def test_every_script_the_conventions_name_is_executable(self):
        """A shell script is only a reader if it can be run.

        Written after shipping the opposite in commit ``30bfbea``: a
        falsification run wrote its backup with Python's ``open(..., "w")``,
        which creates mode ``0644``, and ``mv``-ing that back over the
        script dropped the execute bit. The suite was green, ruff was
        clean, the pre-commit hook passed, and ``./scripts/claude-preflight.sh``
        answered ``permission denied`` for the next sitting — a mode is
        not content, so nothing that reads the file could see it.

        Swept over every ``scripts/*.sh`` rather than the one that broke:
        the failure is a property of how they are edited, not of which
        one, and a guard naming a single file is one rename from
        silence.
        """
        scripts = sorted(
            (pathlib.Path(__file__).resolve().parent.parent / "scripts").glob("*.sh")
        )
        assert scripts, "no scripts/*.sh found — the sweep would pass vacuously"
        import os

        not_runnable = [
            s.name for s in scripts if not os.access(s, os.X_OK)
        ]
        assert not not_runnable, (
            f"these ship without the execute bit and fail at the shell: {not_runnable}"
        )

    def test_preflight_reads_the_scheduled_section(self):
        script = (
            pathlib.Path(__file__).resolve().parent.parent
            / "scripts"
            / "claude-preflight.sh"
        ).read_text(encoding="utf-8")
        assert "scheduled" in script.lower(), (
            "claude-preflight.sh no longer looks for the scheduled section — "
            "nothing else on this box reads it"
        )
        assert "SCHEDULED=" in script


class TestThePublishedLineNamesNoWorkNobodyIsOwed:
    """The blocking half of Session 159's guard.

    ``sysadmin.snag_claims.check_next_action`` is the one implementation
    and this class is its second **consumer**, never a second statement
    of the rule: the module reports at preflight and postflight, where a
    refusal is news to judge, and these tests refuse the commit.  Two
    speakers for one fact is the defect this repository has recorded at
    six scales; ``action_from``'s publish-and-read shape is what makes
    the owner's "both" one owner rather than two.

    What it stops is measured rather than imagined.  Session 138 refused
    ``SNAG-TRAY-011``'s proposed remedy on 2026-08-30; Session 156 read
    one bullet short of the refusal, published the remedy as this
    repository's next action, and their ``roadmap.py`` republished it to
    the estate board verbatim.  Driven over the 21 distinct next actions
    in this file's history, the guard fires on that line and on no other.
    """

    def test_the_register_could_have_answered(self):
        """The premise, asserted separately.

        A guard whose subject is unreadable passes vacuously, and an
        assertion that no id was refused is satisfied by having found no
        entries at all — so what makes the test below evidence is stated
        here rather than assumed.
        """
        entries, problem = snag_claims.load_entries()
        assert not problem, problem
        declared = [
            entry
            for entry in entries
            if entry.is_open and snag_claims.declared_disposition(entry.body)
        ]
        assert declared, (
            "no open entry declares a disposition, so nothing in the register "
            "could have forced a refusal — the guard below would pass blind"
        )

    def test_the_line_could_be_read_at_all(self):
        """The second premise.  A blocking guard that cannot see its own
        subject blocks nothing — ``ports_checked``'s rule at the size of
        a test."""
        line, problem = snag_claims.next_action_line()
        assert not problem, problem
        assert line

    def test_the_reader_can_find_an_id_when_the_line_carries_one(self):
        """The third premise, and Session 181 is what made it owed.

        The two above witness the *register* and the *line*.  Neither
        witnesses the **reader** between them, and the guard below is
        blind exactly when that reader returns nothing — which a line
        naming no entry does legitimately and often.  Session 181's next
        action is about a convention rather than an entry, so it names
        none, and ``check-vacuous-guards.sh`` reported the comprehension
        below as having run over an empty population within one gate run:
        a guard green because nothing was examined, which is
        ``SNAG-TEST-006``'s own shape arriving in a test written to catch
        the estate board publishing the wrong line.

        So the reader is driven at a synthetic line instead, over the
        real register.  It cannot be driven at the real line without
        making the premise depend on today's wording, which is the thing
        that moved.
        """
        entries, problem = snag_claims.load_entries()
        assert not problem, problem
        subject = next(
            (entry.snag_id for entry in entries if entry.snag_id and entry.is_open),
            None,
        )
        assert subject, "the register holds no open entry to read a line about"

        named = snag_claims.read_named_entries(f"Go and look at {subject} today.", entries)

        assert [item.snag for item in named] == [subject], (
            "the reader finds no id in a line that plainly carries one, so an empty "
            "result below would be zero-because-blind rather than zero-because-clean"
        )

    def test_the_next_action_names_no_entry_that_is_owed_nothing(self):
        """Scoped to the refusal and no wider.

        An id this register cannot answer for is reported by
        ``check_next_action`` at preflight and does **not** block a
        commit: that is a different fault with a different remedy, and
        widening a blocking guard onto it would refuse a next action that
        cites another repository's id — which ``SNAG-ESTATE-*``'s two
        minters make an ordinary thing to want to do.
        """
        entries, problem = snag_claims.load_entries()
        line, _ = snag_claims.next_action_line()
        # may-not-turn: the population is the SNAG ids the published line
        # happens to name, and a line about a convention rather than an entry
        # names none — Session 181's does.  So empty here is "nothing to
        # refuse", and the reading that would otherwise be
        # indistinguishable from it, a reader that finds nothing in a line
        # that carries something, is witnessed by
        # test_the_reader_can_find_an_id_when_the_line_carries_one above.
        refused = [
            item.note
            for item in snag_claims.read_named_entries(line or "", entries)
            if item.refused
        ]
        assert not refused, (
            "HANDOFF.md's next action names an entry whose own body says no sitting "
            f"is owed work on it, and the estate board publishes that line: {refused}. "
            f"{snag_claims.REFUSAL_REMEDY}"
        )

    def test_the_local_read_is_the_line_the_board_publishes(self):
        """The pin.  ``next_action_line`` reads this document directly
        rather than importing ``next_action_from_handoff``, because
        ``estate_service`` is on this checkout's path by an editable
        ``.pth`` that is in no lockfile — a production path that goes
        quiet when an undeclared install is pruned is worse than a local
        read pinned against the owner's parser.  "Import where you can,
        pin where you cannot", with the import only *usually* available,
        which is not the same thing.

        Byte equality rather than a comparison of the ids they name: a
        set of ids stays equal through a divergence that changed the
        sentence, and the sentence is what a reader matches against the
        document.

        **The skip is gated on the tree, never on the import**, which is
        the difference between a pin that stops and a pin that goes
        quiet.  ``pytest.importorskip`` would pass on the box where the
        pin matters the moment a ``uv sync`` prunes that ``.pth`` — a
        control disarmed by routine housekeeping, with the suite green.
        A checkout without estate-manager beside it has nothing to pin
        against and skips; one *with* it and no importable module is a
        red, because that is the state where the pin was silently lost.
        """
        if not snag_claims.ESTATE_SERVICE.is_dir():
            pytest.skip(f"{snag_claims.ESTATE_SERVICE} is not on this box — nothing to pin against")
        roadmap = importlib.import_module("estate_service.projects.roadmap")
        ours, problem = snag_claims.next_action_line()
        assert not problem, problem
        assert ours == roadmap.next_action_from_handoff(HANDOFF.read_text(encoding="utf-8"))
