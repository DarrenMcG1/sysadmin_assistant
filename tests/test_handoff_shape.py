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


class TestTheTwoSectionsDoNotCompeteForTheBoardSlot:
    """Rule 3, added 2026-09-12 — and it is not the estate's check moved.

    ``## Scheduled action`` exists so that *"a week-out measurement
    cannot stall the pipeline"*, which is its own preamble's wording.
    On 2026-09-11 the pipeline was stalled anyway, from the other end:
    the scheduled item stayed correctly in its section, and the **next
    action delegated to it** — *"the next sitting should therefore start
    from the scheduled reading due 2026-09-14"*, written on 2026-09-11
    and published to the estate board verbatim.  The section held the
    work and the board published the wait.

    So the rule is a property of *this document*: a date the document
    has itself declared as scheduled work may not also be the operative
    subject of the line the board publishes.  The two sections address
    one slot and must not both claim it.

    **This is deliberately not estate-manager's ``docs`` check, and the
    operands are what say so.**  Theirs
    (``docs:…:next_action_not_startable``, which filed against this
    repository at 13:55 on 2026-09-11) compares the next action's dates
    against the handoff's own date, and reads one document against a
    convention they own.  This compares the next action against the
    **scheduled section beside it**, and reads one document against
    itself.  ``docs/adr/0008-the-file-half-of-the-wiring-check.md``
    draws that line: what distinguishes two checks is the inputs they
    take, not the conclusion they happen to share.

    **Why a guard here at all, when theirs already fires.**  Measured
    2026-09-11: their finding reaches no session in this repository.
    ``scripts/claude-preflight.sh`` names ``:8400`` nowhere,
    ``~/.claude/hooks/inbox-notice.sh`` fetches ``/api/estate/messages``
    and nothing else, ``session-notice.sh`` only publishes outbound, and
    this repository's own hourly pull of ``/api/audit/findings`` filters
    on ``JUDGED_AUDIT_CHECKS`` — which does not name ``docs`` and,
    by :func:`sysadmin.estate.judgements.judge_audit_findings`'s
    ownership test, must not.  The finding about this repository was
    found by a session going to look, prompted by an unrelated message.
    A rule deferred to a check whose finding cannot arrive is a rule
    nothing holds; ``SNAG-DOCS-022`` carries the delivery gap itself.

    **The rule is narrower than the naive one, and the naive one was
    measured and refused.**  Over all 248 published next actions in this
    file's history, *"names any date later than the handoff's own"*
    fires 7 times and **2 of the 7 are legitimate**: ``91fd90e7``'s date
    is a *deadline* (*"do it before 2026-09-11, because ``log_entries``
    has a 30-day retention"*) and ``305152a4``'s is the *subject* of the
    work (*"write a prediction for the 2026-09-16 retention
    boundary"*) — both startable the day they were written, and the
    producer files at ``warn`` for exactly that reason.  A blocking
    guard refusing 2 in 7 correctly-written lines teaches the operator
    to reach for ``--no-verify``, which is ``SNAG-DB-005``'s rule 3
    against disarming a check for the case it exists for.  The rule
    below fires **2 of 248** and both are true gates: ``dfe930e5`` (the
    line that occasioned it) and ``9f736275`` (*"on or after
    2026-09-01"*, its date also declared in the section).

    **Its cost is filed rather than implied.**  It is blind to a gate
    the next action states and the section never declared — 3 of the
    248, of which ``53342dd4`` and ``4b86abfe`` predate the section
    existing at all and only ``ae202f89`` is a live miss.  Catching that
    one needs the preposition (*"on or after"* against *"before"*),
    which is deciding that an English sentence is a claim — a human's
    job, ``SNAG-ESTATE-012``'s standing refusal.  ``SNAG-DOCS-023``
    carries it.

    **No wall clock is read, and that is load-bearing rather than
    tidy.**  Both dates come from the document, so the verdict is a
    property of the file and cannot move between two runs of the same
    commit.  A guard comparing against ``date.today()`` goes red at
    midnight with no edit behind it, which this repository has already
    recorded as a harness reading a clock it did not supply.
    """

    #: A date this document writes, in the one form both readers use.
    _DATE_RE = re.compile(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}")

    def _own_date(self, text: str) -> str | None:
        """The handoff's own date, off the first heading the Stop hook reads.

        ``~/.claude/hooks/require-handoff.sh`` takes ``grep -m1 '^#'``
        and requires today's date in it, so the first heading is already
        a parse target with an enforced shape; this reads the same line
        rather than introducing a second convention for one fact.
        """
        for line in text.splitlines():
            if line.startswith("#"):
                found = self._DATE_RE.search(line)
                return found.group(0) if found else None
        return None

    def _gated(self, text: str, line: str) -> list[str]:
        """Dates the line shares with the scheduled section, in the future.

        The conjunct is not decoration.  A *past* date shared with the
        section is an **overdue** scheduled item being taken, which is
        the section working — Session 206 discharged one two days late —
        so refusing it would refuse the discharge along with the stall.
        """
        own = self._own_date(text)
        if own is None:
            return []
        body = _section_body(text, SCHEDULED_HEADING)
        if body is None:
            return []
        declared = "\n".join(body)
        return sorted(
            {
                found
                for found in self._DATE_RE.findall(line)
                if found > own and found in declared
            }
        )

    def test_the_document_carries_both_dates_to_compare(self):
        """The premise, asserted separately.

        Three reads have to land before the sweep below is evidence:
        the handoff's own date, the published line, and the scheduled
        section.  Any one of them returning nothing makes the rule pass
        over an empty population — ``ports_checked``'s rule, which this
        file already applies one class up.
        """
        text = _text()
        assert self._own_date(text) is not None, (
            "the first heading carries no ISO date, so the guard below has "
            "nothing to compare against and passes blind"
        )
        line, problem = snag_claims.next_action_line()
        assert not problem, problem
        assert line
        assert _section_body(text, SCHEDULED_HEADING) is not None, (
            f"{SCHEDULED_HEADING} is gone, so every date reads as undeclared"
        )

    def test_the_next_action_does_not_delegate_to_a_scheduled_item(self):
        line, problem = snag_claims.next_action_line()
        assert not problem, problem
        assert line
        gated = self._gated(_text(), line)
        assert not gated, (
            "the published next action names a date this document has already "
            f"declared under '{SCHEDULED_HEADING}': {gated}. The estate board "
            "publishes this line verbatim, so it would tell the next sitting to "
            "wait rather than to start. Name work that is startable now; the "
            "dated item is already where it belongs and preflight prints it."
        )


class TestTheGateDetectorWouldSeeOne:
    """Rule 3 driven at documents that break it and at documents that do not.

    The real file is deliberately clean, so on its own it witnesses
    neither the rule nor the two refusals the rule was narrowed by — a
    green sweep over a compliant document is satisfied by a detector
    that has stopped reading.  The three forgeries below are the
    corpus's own specimens, reduced.
    """

    def _check(self, text: str) -> list[str]:
        instance = TestTheTwoSectionsDoNotCompeteForTheBoardSlot()
        line = next(
            (
                stripped
                for raw in text.split(NEXT_HEADING, 1)[-1].splitlines()
                if (stripped := raw.strip()) and not stripped.startswith("#")
            ),
            "",
        )
        return instance._gated(text, line)

    def _forge(self, action: str, scheduled: str) -> str:
        return (
            "# Handoff — 2026-09-11 (Session 217)\n\n"
            f"{NEXT_HEADING}\n\n{action}\n\n"
            f"{SCHEDULED_HEADING}\n\n{scheduled}\n\n"
            "## What this sitting did\n\nnothing\n"
        )

    def test_it_catches_the_line_that_occasioned_it(self):
        """``dfe930e5``, reduced to its operative clause."""
        forged = self._forge(
            "The next sitting should start from the scheduled reading due 2026-09-14.",
            "- **2026-09-14** — Discriminate the cold-start hypothesis.",
        )
        assert self._check(forged) == ["2026-09-14"]

    def test_a_deadline_is_not_a_gate(self):
        """``91fd90e7``: startable now, and the date is when it stops being.

        The naive rule refuses this; the producer files it at ``warn``
        and says a reword answers it.  A blocking guard must not.
        """
        forged = self._forge(
            "Take `SNAG-LOG-010` and do it before **2026-09-11**, because "
            "`log_entries` has a 30-day retention.",
            "- **2026-09-14** — something else entirely.",
        )
        assert self._check(forged) == []

    def test_a_date_that_is_the_subject_is_not_a_gate(self):
        """``305152a4``: the work is writing *about* the date, today."""
        forged = self._forge(
            "Give the `expires` family its first live member by writing a "
            "prediction for the 2026-09-16 retention boundary.",
            "- **2026-09-14** — something else entirely.",
        )
        assert self._check(forged) == []

    def test_an_overdue_scheduled_item_may_be_taken(self):
        """The conjunct's own witness: past dates are the discharge."""
        forged = self._forge(
            "Discharge the scheduled reading due 2026-09-07, two days overdue.",
            "- **2026-09-07** — Read the first Monday under lease.",
        )
        assert self._check(forged) == []

    def test_a_missing_scheduled_section_reads_as_no_declaration(self):
        """Fails *open*, and the direction is argued rather than assumed.

        ``TestTheScheduledSectionCarriesNoCheckbox`` already refuses a
        document with no such section, so the absence cannot go
        unreported — it is simply not reported *twice*, and not by the
        rule whose whole question is what the section declares.
        """
        text = (
            "# Handoff — 2026-09-11\n\n"
            f"{NEXT_HEADING}\n\nStart from the reading due 2026-09-14.\n"
        )
        assert self._check(text) == []

    def test_a_document_with_no_date_in_its_heading_is_not_judged(self):
        text = (
            "# Handoff\n\n"
            f"{NEXT_HEADING}\n\nStart from the reading due 2026-09-14.\n\n"
            f"{SCHEDULED_HEADING}\n\n- **2026-09-14** — a thing.\n"
        )
        assert self._check(text) == []
