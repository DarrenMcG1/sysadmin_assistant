"""Re-measure the operational claims the session-opening block prints.

``SNAG-ESTATE-008``.  ``docs/roadmap/STATUS.md`` opens with a block that
tells the next sitting what is owed — a restart, a migration, an alert row
waiting on someone.  Nothing has ever checked it.  Measured on 2026-08-16,
**all three actions it carried had already been done**, two of them by a
party that never touched the document, and the block went on asking for
them for five sittings; on 2026-08-24 the same file asserted a retention
boundary three hours before it happened.  Six consecutive sittings have
paid for this.

The previous ranking demoted the fix for having "no obvious enforcement
point, since these claims live in prose".  That is the part that stopped
being true rather than the part that is hard: ``scripts/claude-preflight.sh``
already runs at the start of every sitting and already prints those
claims — it just prints them *from the prose*, with nothing between the
document and the reader.  This module is what goes between.

Six rules, three of them the opposite of the obvious implementation:

1. **The parsed region is exactly the region preflight prints.**  Not the
   whole file, which restates old figures on purpose ("44 before Session
   27") and would make every claim ambiguous, and not a machine-readable
   marker either — an ``<!-- routes=46 -->`` comment beside the sentence
   is a second statement of one fact that can disagree with the first,
   which is ``SNAG-DB-003``'s shape arriving in a document.  The prose
   *is* the artefact under test, so the prose is what is read.

2. **Every way of not-knowing is ``unknown``, never ``match``.**  A claim
   whose pattern finds nothing, a claim the block states two ways, a
   database that will not answer and a unit systemd has never heard of
   are four different faults and none of them is agreement —
   ``UnitScanResponse.ports_checked``'s rule, and the reason the verdicts
   and the exit statuses are :mod:`sysadmin.core.schema_guard`'s three
   rather than a boolean.  Note the second of those: two *different*
   values for one claim inside the printed block is drift with both
   halves in one file, which is worth naming rather than resolving by
   taking the first match.

3. **Two kinds of check, and conflating them would have you edit the
   wrong artefact.**  A ``claim`` compares the document against the box —
   a mismatch means the *document* is stale.  A ``state`` check compares
   the box against this checkout — a mismatch means the *box* is stale,
   and no wording in STATUS.md would fix it.  They print together because
   they are read together at the top of a sitting, and they are separate
   fields because the remedies are opposites.

4. **The deploy check compares file mtimes, never commit times**, and the
   obvious version is wrong on this box *today*.  The daemon entered
   active at 09:58:28 and the newest commit touching ``sysadmin/`` landed
   at 10:05:22, so a commit-time rule reports a restart owed; the content
   is identical, because this repository restarts to verify and commits
   afterwards.  The newest ``.py`` on disk was written 09:57:46, 42
   seconds *before* the start, which is the question actually being
   asked: is the running process serving what is on disk.

   **The population is the daemon's import graph, and it took eleven
   sittings and a 77-minute outage to make it so** (2026-09-06).  This
   rule used to sweep every ``.py`` under ``sysadmin/`` and priced the
   consequence in its own last sentence — *"and so can a file the daemon
   never imports — this one, the moment it is written"* — as a rare miss
   costing a needless ``kill -TERM`` that "is not privileged and takes a
   second".  Both halves were wrong.  Measured: **50 of 191** commits
   touching this package touch *only* the six modules the daemon cannot
   reach, so the miss is a quarter of the check's fires rather than a
   rare one, and ``tasks.md`` records the restart being paid on eleven
   consecutive sittings "whose restart moves nothing a caller can
   observe".  The second is ``SNAG-SYSD-007``: five restarts in ten
   minutes trip ``StartLimitBurst``, recovery from ``inactive`` needs a
   polkit challenge ``sudo -n`` cannot supply, and one of those five was
   this claim's.  The box was down 77 minutes.  A cost written from the
   mechanism rather than from the box had priced the wrong option first,
   for the second time in this file.

   :func:`daemon_modules` is the narrowing and it is a **walk of the
   source, not a trace of an import** — the opposite of what the entry
   proposed.  A trace answers with what a process *did* import, which
   misses :mod:`sysadmin.core.llm_client`, lazily imported inside three
   review functions and named at module scope nowhere; the sitting that
   opened this concluded from exactly that that the population had to
   come from the running daemon over a new surface.  It does not.  A
   function-level ``import`` is in the tree as plainly as a top-level
   one, so the walk reaches 94 of 100 with no endpoint, no contract
   entry and no restart to bootstrap.  What is dropped is the six
   console-script entry points and ``metadata.py``, each read fresh by a
   process of its own, for which no restart of *this* daemon could
   change anything.

   The cost is still stated and it is still one-directional.  A checkout
   or a rebase rewrites mtimes, and a module the daemon would import
   lazily but has not yet is counted here, so this can still report a
   restart owed for code that is already current — never the reverse.
   And a file *outside* the graph is now named rather than swept:
   ``ports_checked``'s rule, because "considered, and no restart is owed
   for it" and "nobody looked" must not read the same.

5. **The unresolved-alert count is a gauge, and both directions are news
   in opposite ways.**  A *rise* is a row the block does not account for.
   A *fall* is the case this snag was filed for: ``SNAG-DB-002``'s eight
   collation rows resolved themselves at 18:01:48 when estate-manager ran
   the ``REINDEX``, this application observed the remedy land, and four
   documents went on asking for it for three days.  So the open titles
   are named rather than counted — ``details['truncated_sources']``'s
   rule, in the surface that sets the agenda.

6. **Nothing here writes to a document.**  A check that corrects the file
   it reads becomes a second author of the claim, and the next sitting
   cannot tell a measured number from a written one.  It reports; the
   sitting edits.  For the same reason there is no ``--quiet``: the one
   flag :mod:`sysadmin.core.schema_guard` needed has three shell callers
   asking for it, this has none, and an option nothing passes is the
   ``SNAG-CFG-001`` shape at the size of a flag.

``SNAG-ESTATE-011`` added three more, and the first is the one that
decides whether a marker beside prose is a defect or a convention:

7. **A marker names a check; it never restates a value.**  Rule 1 refuses
   ``<!-- routes=46 -->`` beside a sentence, and it is right to: a marker
   holding a *figure* can agree with the box while the prose beside it
   says something else, and nothing notices — ``SNAG-DB-003``'s two
   statements of one fact, arriving in a document.  ``<!--check:routes-->``
   is not that.  There is still exactly one figure in the document, the
   one in the prose, and the named check reads it from there.  So the two
   can never disagree about a fact, because the marker states none.  It
   buys the enforcement point the convention had no way to have: a figure
   this module can test that no line claims is reported, which is
   ``SNAG-ESTATE-008``'s *"every ops action names the check that closes
   it"* with something behind it.  The marker is **additive and cannot
   subtract** — every pattern-bearing claim runs whether or not a marker
   names it — because a marker that gated a check would make "delete the
   marker" a way to retire one, which is rule 2's silent retirement
   wearing the fix for it.

8. **A prediction is timed, not measured.**  ``SNAG-ESTATE-011`` was
   opened by a block asserting a retention boundary three hours before it
   happened.  Nothing about that sentence was wrong when written and
   nothing about it was measurable when written, so no amount of pattern
   reaches it; ``<!--check:expires …-->`` is the one family whose members
   the *document* declares rather than this module.  Before its moment the
   claim stands; after its moment it is ``unknown``, never ``mismatch`` —
   the prediction may well have come true, and "nobody went back" is
   exactly what rule 2 reserves ``unknown`` for.

9. **The one fact stated twice is pinned rather than trusted.**  An
   ``expires`` marker must carry a *date* and an *offset*, because the
   prose carries neither — "clears at 03:32" names a wall clock, no day
   and no zone, and a pattern that guessed either would be wrong once per
   prediction.  That makes the instant the single exception to rule 7, so
   it is handled the way
   :func:`sysadmin.core.logging_setup.syslog_priority` is handled against
   ``journal.PRIORITY_MAP``: not asserted on each side, *pinned* — the
   wall clock the marker renders **in this box's zone** must appear in the
   block, or the claim is ``unknown`` and says which two moments disagree.
   The pin is against **the marker's own sentence**, since
   ``SNAG-DOCS-008``.  It searched the whole printed region for as long
   as rule 10 stood alone, and said so — "the weaker half; a block naming
   ``03:32`` twice for two different reasons would satisfy it" — which
   turned out to describe the document rather than a hypothetical: 28 of
   its 86 distinct wall clocks are already stated more than once.  See
   :func:`check_expiry` for the drive that settled it.

   The offset is what makes the pin more than a spelling check
   (``SNAG-ESTATE-013``).  Without one, a UTC stamp copied into a
   sentence written in BST renders back as the same string it came in as
   and the pin passes — the marker and the prose agree, and both are an
   hour from the moment predicted.  With one, they visibly disagree, and
   the note says which of them is in which clock.

``SNAG-ESTATE-016`` added the tenth, and it is the correction rule 9
predicted against itself.  ``SNAG-DOCS-008`` then applied it to rule 9 —
filed in *this* repository's namespace rather than as a seventeenth
``SNAG-ESTATE-*``, which estate-manager's message ``153c1c96`` records as
having two minters and no owner (they are at 131; every colliding pair
names a different defect).  Both are about this module's own claims
machinery rather than about the estate, which is what that ruling says
the area should have been all along:

10. **A claim about prose is read from one sentence, because the region
    is append-only.**  Rule 1 says the parsed region is exactly what
    preflight prints, and that is right for a *figure*: bold emphasis
    separates the current number from the history the same block carries,
    and :func:`read_claim` refuses two matches outright.  A **membership**
    claim has no such anchor.  ``check_open_titles`` asked whether every
    open row's title appeared anywhere in the region, and the region grew
    to **178,301 characters** of accumulated sittings — so a title
    satisfied the test on the strength of having been written down once,
    four sittings ago, and the check reported ``match`` over a sentence
    naming a row that was not open.  :func:`claim_sentence` narrows the
    haystack to the sentence bearing the marker: 290 characters at the
    commit that opened the entry, and the discrimination back.

    **The marker decides where to look, never whether to look.**  That is
    what keeps this inside rule 7 rather than making it the exception: the
    population comes from the alert table and is measured either way, so
    an absent marker yields ``unknown`` with the remedy named, and can
    never yield ``match``.  Rule 2's tri-state is what makes a marker
    load-bearing without making it a switch.

    **Rule 9's pin was left as it was, and the reason given was half of
    one** — corrected by ``SNAG-DOCS-008`` the next day.  Deferring a
    second change was right; the argument offered for it was not.  It
    read "the two fail in different directions — a pin that cannot find
    its instant is ``unknown`` and loud, where a membership test that
    finds a title anywhere is ``match`` and silent", which is true of one
    of the pin's two directions and silent about the other.  A pin that
    finds its instant *in an unrelated sentence* is ``match`` and silent,
    which is this rule's own defect with a five-character needle instead
    of a title — and a needle drawn from 1440 values, in a block already
    spending 6 % of them.  Both narrowings now read one sentence, through
    the one locator; :func:`Marker.sentence` records why ``expires`` could
    not simply call :func:`claim_sentence` to get there.

**This module sits beside main.py** for the reason :mod:`sysadmin.reload`
and :mod:`sysadmin.metadata` do: it composes ``core`` with every domain
(the route count comes from :func:`sysadmin.main.create_app`, which
imports all of them), so a ``core/ops_claims.py`` would break the rule
that makes every other boundary real.  ``tests/test_import_boundary.py``
now names it as the fourth composition root.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess  # noqa: S404 — one read-only `systemctl show`
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from sysadmin.core.config import REPO_ROOT, get_config
from sysadmin.core.escalation import humanise_hours
from sysadmin.core.schema_guard import (
    EXIT_STATUS,
    SchemaVerdict,
    schema_status,
)
from sysadmin.core.unit_failure import OWN_UNIT

#: The same three words and the same exit map as the schema check, imported
#: rather than restated.  ``mismatch`` is a claim that is false; ``unknown``
#: is a claim nobody managed to test, and rule 2 is the whole reason those
#: are not one verdict.
type Verdict = SchemaVerdict

STATUS_PATH = REPO_ROOT / "docs" / "roadmap" / "STATUS.md"

#: The package rule 4's population is drawn from.
PACKAGE = "sysadmin"

#: The module ``sysadmin.service`` runs, and so the root of every import
#: the running process can hold.  Named rather than inlined because it is
#: the one fact :func:`daemon_modules` cannot derive: what systemd starts
#: is stated in the unit file, not in the source.
DAEMON_ROOT_MODULE = f"{PACKAGE}.main"

#: How many open alert titles are printed before the rest are counted.
#: A cap that drops rows silently is the roll-up defect ``SNAG-ESTATE-001``
#: names, so the overflow is stated.
MAX_NAMED_ALERTS = 5

#: One pattern per claim, anchored on the emphasis this file uses for a
#: figure it has measured.  The bold is load-bearing: it is what separates
#: the current number from the history the same sentence carries.
#:
#: The spaces are literal because :func:`flatten` has already run — see
#: there for why that is not a tidying step.
CLAIM_PATTERNS: dict[str, str] = {
    "routes": r"\*\*(\d+) routes\*\*",
    "tables": r"\*\*(\d+) tables\*\*",
    "migration_head": r"head \*\*(\d+)\*\*",
    "alerts": r"holds \*\*(\d+)\*\* unresolved",
    "daemon_start": r"restarted at \*\*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\*\*",
    "health": r"`/health` answers \*\*(\d+)\*\*",
}

#: Checks a marker may name that carry no pattern of their own, and why
#: each one has none.  ``schema`` and ``deploy`` test the box against this
#: checkout, so there is no sentence to read (rule 3).  ``open_titles`` is
#: answered from the alert table against the block's *membership* sentence
#: rather than from a figure — it reads no value, only a haystack, which is
#: rule 10.  ``expires`` is the one family whose *members* are declared by
#: the marker rather than by this module — rule 8.
KEYLESS_CHECKS: frozenset[str] = frozenset({"schema", "deploy", "open_titles", "expires"})

#: Every name a marker may carry, **derived** from the two sets above
#: rather than written beside them — ``max_priority_for`` against
#: ``PRIORITY_MAP``'s rule, and for its reason: a third list is a third
#: thing to forget.  A marker naming anything else is reported rather than
#: ignored, because a check nobody implements is silence wearing a
#: convention's clothes.
CHECK_KEYS: frozenset[str] = frozenset(CLAIM_PATTERNS) | KEYLESS_CHECKS

#: ``<!--check:key-->``, optionally with an argument: ``<!--check:expires
#: 2026-08-25T03:32 the estate scan row-->``.  An HTML comment because it
#: must not render — the document is read by people first — and matched
#: after :func:`flatten`, so a marker may wrap onto its own line.
MARKER_RE = re.compile(r"<!--\s*check:\s*([a-z_]+)\s*([^>]*?)\s*-->")

#: A markdown code span, closing on a backtick run of its **own length**.
#: ``SNAG-DOCS-005``: a marker inside one is a *quotation*, and reading it
#: as a claim fails quietly in both directions — a quoted key nothing
#: implements is reported as a broken marker, and a quoted key that *is*
#: implemented silences the ``unclaimed`` finding beside a sentence that
#: claims nothing.
#:
#: The same-length run is what separates this fix from the naive
#: ``` `[^`]+` ``` and it was settled by running it rather than by
#: argument.  Markdown writes a span that itself contains one with a
#: doubled fence — ``the `<!--check:routes-->` marker`` — which is a live
#: shape in ``snag_list.md``; the naive pattern closes at the *inner*
#: backtick and leaves the marker bare.  ``SNAG-DOCS-005``'s check was
#: built to tell the two apart before either was written, and it did:
#: driven against the naive pattern it reported the entry *narrowed*, and
#: against this one *refuted*.  So the entry closed on a run rather than
#: on the argument this comment is making, and the check left the
#: registry with it.
#:
#: Copied in shape from :func:`sysadmin.snag_claims.strip_code_spans`
#: rather than imported.  That module is the other composition root, so
#: an import would couple two of them to share a regex, and it would put
#: a snag-list parse at the mercy of an edit made for this dashboard.
#: Behaviour is pinned across the two by ``tests/test_ops_claims.py``
#: instead: import where you can, pin where you cannot.
CODE_SPAN_RE = re.compile(r"(`+)[\s\S]*?\1")

#: Where one sentence of the flattened block ends: a terminator, any closing
#: emphasis or bracket it carries, then whitespace or the end of the region.
#:
#: **The lookahead alone is not enough, and the shape that says so is this
#: document's own.**  A quoted ``sysadmin.service`` is already safe, because
#: :func:`_veiled` blanks the span around it — so the lookahead's real
#: population is a full stop in *prose*.  Measured on the live region: **290**
#: full stops there carry no space after them, and the overwhelming shape is
#: ``.**`` — a bolded lead-in sentence, which is how nearly every paragraph
#: in this block opens.  Without the trailing class the terminator is refused
#: and the sentence runs backwards through the whole lead-in, which is rule
#: 10's defect at one paragraph instead of at 178 kB.  ``)`` and ``*`` are
#: both in the class because the block's parentheticals close ``.)*``.
SENTENCE_END_RE = re.compile(r"""[.!?][*_)\]"'’”]*(?=\s|$)""")

#: The instant an ``expires`` marker carries: minute resolution,
#: unambiguous about the *date* — which is the whole reason the marker
#: carries an instant the prose does not, since "clears at 03:32" names a
#: wall clock and no day — and, since ``SNAG-ESTATE-013``, unambiguous
#: about the **zone**.
#:
#: It used to take a bare wall clock read as local.  The one marker ever
#: written was copied off an estate surface publishing
#: ``2026-08-25T03:32:17.538288+00:00``, and the offset was dropped on the
#: way in: the prediction then named an instant an hour before its subject
#: here, and would have named one four hours *after* it west of Greenwich.
#: Nothing in this module could say so, because a zoneless stamp has no
#: zone to disagree with.  ``SNAG-LOG-009`` one document over, answered the
#: way :func:`sysadmin.monitor.journal.since_timestamp` answers it — the
#: ambiguity is **refused**, never resolved by a default, because a default
#: is correct on the box that wrote the marker and silently wrong
#: everywhere else.
#:
#: **``@<epoch>`` is deliberately not accepted, though that is exactly what
#: ``since_timestamp`` renders for the same fault**, and the difference is
#: the reader rather than the instant.  There the consumer is journalctl,
#: whose zone is the reader's and unknown, and whose ``--since`` has no
#: offset syntax at all — an epoch is the only unambiguous thing it takes.
#: Here the consumer is :func:`check_expiry` and the *author* is a human,
#: who must also write the instant's wall clock into the sentence beside it
#: (rule 9).  An epoch is a figure no reader can pin against a sentence, so
#: accepting one would buy unambiguity by making the one fact stated twice
#: checkable by the checker alone — which is rule 9 deleted in order to
#: satisfy rule 8.
EXPIRY_FORMAT = "%Y-%m-%dT%H:%M%z"

#: The shape every ``expires`` marker written before 2026-08-28 carries.
#: **Recognised, never accepted.**  A naive instant is refused; this is
#: what lets the refusal name the fault rather than report a generic
#: malformation, which is ``schema_guard``'s rule that every way of
#: not-knowing fails closed *with its own message*.  "This carries no
#: offset, and here are the two instants it names" is a remedy; "not an
#: instant of the form ``%Y-%m-%dT%H:%M%z``" is a puzzle whose answer is
#: the defect.
EXPIRY_NAIVE_FORMAT = "%Y-%m-%dT%H:%M"

#: How the pinned wall clock is rendered back out of an ``expires``
#: instant, to be looked for in the prose.  Rule 9.  Rendered **in this
#: box's zone**, never in the marker's own: the prose is a sentence a human
#: wrote on this box, so local is the clock it is in, and demanding the
#: local rendering is what turns the pin from a spelling check into the
#: thing that catches a UTC stamp copied into a sentence written in BST.
EXPIRY_CLOCK_FORMAT = "%H:%M"


@dataclass(frozen=True)
class Claim:
    """One line of the report.

    Attributes:
        key: the identifier used in :data:`CLAIM_PATTERNS` and in tests.
        subject: what is being claimed, in words.
        kind: ``"claim"`` when the document is being tested against the
            box, ``"state"`` when the box is being tested against this
            checkout.  Rule 3 — the remedies are opposites.
        documented: what the block says, or ``None``.  On a ``claim`` that
            means the sentence could not be read; on a ``state`` check
            there is no sentence to read, which is why ``kind`` is a field
            and not an inference from this one.
        measured: what the box says, or ``None`` when it could not be
            measured.
        verdict: see :data:`Verdict`.
        note: one sentence naming the fault, its direction and its remedy.
            Empty only on ``match``.
        detail: evidence too long for ``note`` — the open alert titles,
            the file whose mtime is newer than the daemon.
    """

    key: str
    subject: str
    kind: str
    documented: str | None
    measured: str | None
    verdict: Verdict
    note: str = ""
    detail: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Reading the document
# ---------------------------------------------------------------------------


def printed_region(document: str) -> str | None:
    """The part of STATUS.md the session-opening banner shows.

    From the top of the file through the end of the Quick Status table —
    the sub-session block, the ranked recommendation and the table, which
    together are what a sitting reads before it decides anything.  Rule 1.

    Returns ``None`` when the table's heading is absent, because a region
    guessed from a file whose shape has changed would silently narrow to
    nothing and report every claim as unreadable for the wrong reason.
    """
    lines = document.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip().startswith("## Quick Status")),
        None,
    )
    if start is None:
        return None
    end = next(
        (i for i, line in enumerate(lines[start + 1 :], start + 1) if line.startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[:end])


def flatten(region: str) -> str:
    """The region as one line of prose, decoration removed.

    Blockquote markers stripped and every run of whitespace collapsed to a
    single space.  **This is not a tidying step, and skipping it retires
    claims silently.**  The first rewrite of the block under this check
    wrapped ``holds **2**`` and ``unresolved`` onto two lines with a ``>``
    between them, and the claim came back *unreadable* — correct by rule 2
    and useless, because ``unknown`` for a reason no reader would guess is
    how a check goes quiet.  A paragraph reflow must not be able to do
    that, so the patterns are matched against prose rather than against
    markdown.
    """
    stripped = [re.sub(r"^\s*>\s?", "", line) for line in region.splitlines()]
    return re.sub(r"\s+", " ", " ".join(stripped))


def read_claim(region: str, key: str) -> tuple[str | None, str]:
    """The value the block states for ``key``, or ``None`` and why not.

    Two distinct matches are refused rather than resolved: a block that
    states one figure two ways has already drifted, and taking the first
    would report agreement with whichever half happened to be written
    first (rule 2).
    """
    pattern = CLAIM_PATTERNS[key]
    found = {match.group(1) for match in re.finditer(pattern, flatten(region))}
    if not found:
        return None, f"the block states no figure matching /{pattern}/"
    if len(found) > 1:
        stated = ", ".join(sorted(found))
        return None, f"the block states {len(found)} different figures ({stated})"
    return found.pop(), ""


@dataclass(frozen=True)
class Marker:
    """One ``<!--check:…-->`` the block carries.

    Attributes:
        key: the check the sentence stands behind.  A name, never a value
            — see rule 7 for why that distinction is the whole design.
        argument: whatever followed it, empty for every check but
            ``expires``.
        sentence: the one sentence it stands in, markers stripped.

    **The sentence is carried rather than looked up, and that is what
    makes rule 9's narrowing expressible at all** (``SNAG-DOCS-008``).
    :func:`claim_sentence` finds a sentence *by key* and so must refuse a
    key stated twice; ``expires`` is the one family whose members the
    document declares, and two predictions in one block are two markers
    with one key — the shape that reader exists to refuse.  Reading the
    sentence off the marker asks about the **occurrence** instead of
    about the name, which is the question a per-marker check has.

    It is a field rather than a ``(region, marker)`` helper because a
    span is only meaningful against the string it was measured in, and a
    helper taking both invites a caller to pass a region the markers did
    not come from — :func:`sysadmin.monitor.journal.since_timestamp`'s
    argument for taking a ``datetime``: make the mistake unrepresentable
    rather than merely unlikely.
    """

    key: str
    argument: str
    sentence: str


def read_markers(region: str) -> list[Marker]:
    """Every marker in the printed region, in the order it states them.

    Read off the *flattened* region for :func:`flatten`'s reason: a marker
    that wrapped onto its own line behind a ``>`` would otherwise stop
    being a marker, which is the silent retirement rule 2 exists to
    prevent, arriving through the mechanism meant to prevent it.

    **Code spans are removed before the read** — ``SNAG-DOCS-005``.  A
    marker between backticks is a sentence *about* the convention rather
    than a line using it, and this block is the likeliest place on the box
    for such a sentence: it carried *"One thing this block deliberately
    does not do: quote a marker"* for as long as this function could not
    tell the two apart, which made the emptiness of the entry's population
    an avoidance rather than a measurement.  See :data:`CODE_SPAN_RE` for
    why the pattern closes on a run of its own length, and why it is a
    copy rather than an import.

    **The veiling is length-preserving, where it used to collapse each
    span to one space.**  Both see the same markers — the live document
    is pinned either way by ``tests/test_ops_claims.py`` — but only the
    length-preserving one yields offsets that still index the prose, and
    a marker that cannot say *where* it is cannot carry the sentence it
    stands in.  So the two veilings became one when rule 9's pin was
    narrowed (``SNAG-DOCS-008``); a second veiling that agrees with the
    first is a second statement of one fact, waiting to stop agreeing.
    """
    prose = flatten(region)
    veiled = _veiled(prose)
    unmarked = _unmarked(veiled)
    ends = [match.end() for match in SENTENCE_END_RE.finditer(unmarked)]
    return [
        Marker(
            match.group(1),
            match.group(2).strip(),
            _sentence_at(prose, ends, _anchor(unmarked, match.start())),
        )
        for match in MARKER_RE.finditer(veiled)
    ]


def _anchor(unmarked: str, start: int) -> int:
    """Where a marker sits for the purpose of finding its sentence.

    **The last non-space character before it, not the marker's own
    start** — which is to say a marker belongs to the sentence it
    *closes*, never to the one after it.  An author attaches a marker by
    writing the sentence and then the marker, so
    ``…nothing done.**<!--check:expires …-->`` must anchor on the sentence
    that ends at ``done.**``; anchoring on the marker's own offset lands
    it past that terminator and yields the **next** sentence, which in
    that specimen is empty.

    Both failure modes are silent in the direction ``SNAG-DOCS-008``
    closed, which is why this is arithmetic rather than a convention
    asked of authors: an empty sentence pins nothing, and before
    :func:`_unmarked` the same shape ran the sentence *backwards* through
    the preceding paragraph.  Whitespace is skipped on the **unmarked**
    string, so a marker following another marker anchors past both.
    """
    return len(unmarked[:start].rstrip())


def _unmarked(veiled: str) -> str:
    """``veiled`` with every marker blanked, length preserved.

    :data:`SENTENCE_END_RE` ends a sentence at a terminator followed by
    whitespace or the end of the region, and a marker is neither — so
    ``…clears at 03:32.**<!--check:expires …-->`` has no terminator the
    reader can see, and the sentence runs *backwards* through whatever
    precedes it.  That is the pin getting quietly **wider**, which is the
    direction ``SNAG-DOCS-008`` exists to close, arriving through the
    fix for it: the note this module now prints tells an author to move
    the marker into the sentence naming the clock, and writing it flush
    against the full stop is the obvious way to do that.

    Blanking is the same rule :func:`_veiled` applies to a code span, one
    span over — **what is a marker is not prose** — and it is a second
    veil rather than a wider first one because :func:`read_markers` has to
    *find* the markers in the string it searches.  Both preserve length,
    so a position in one is that position in all three.

    Found by writing the fixture in the style the new note recommends and
    watching two predictions come back sharing one sentence.
    """
    return MARKER_RE.sub(lambda match: " " * len(match.group(0)), veiled)


def _sentence_at(prose: str, ends: list[int], anchor: int) -> str:
    """The sentence of ``prose`` containing ``anchor``, markers stripped.

    The one locator both narrowings use — :func:`claim_sentence` for a
    membership claim (rule 10) and :func:`read_markers` for a marker's own
    sentence (rule 9, since ``SNAG-DOCS-008``).  Two implementations of
    "where does this sentence begin" is ``SNAG-DB-003``'s shape, and this
    module has refused that copy three times already.

    ``ends`` is computed once by the caller rather than per marker: it is
    a property of the region, and a block with ten markers would otherwise
    scan the whole flattened document ten times.

    **The markers are stripped out of what comes back**, which is the job
    the deleted ``prose_without_markers`` used to do one span wider.  A
    pin that searches text *containing* the marker matches the marker's
    own copy of the instant and passes whatever the sentence says — the
    check agreeing with itself by construction, found by driving a
    reworded block through the real script rather than a fixture.  It
    matters twice over here, because an ``expires`` argument is free text
    describing the prediction: a marker sharing the sentence could put
    the answer into it.
    """
    begin = max((end for end in ends if end < anchor), default=0)
    finish = min((end for end in ends if end >= anchor), default=len(prose))
    return MARKER_RE.sub(" ", prose[begin:finish]).strip()


def _veiled(prose: str) -> str:
    """The flattened region with every code span blanked, length preserved.

    :func:`read_markers` blanks spans with a single space because it only
    needs the *set* of markers.  Locating a sentence needs offsets that
    still index the original, so this substitutes a run of spaces of the
    span's own length instead — the mask and the text are the same string
    twice, and a position found in one is the same position in the other.

    Both jobs are the same rule read twice: **what is inside backticks is
    quoted, not stated.**  ``SNAG-DOCS-005`` applied it to a marker; rule
    10 applies it to a full stop, which is what lets ``sysadmin.service``
    sit inside a sentence without ending it.
    """
    return CODE_SPAN_RE.sub(lambda match: " " * len(match.group(0)), prose)


def claim_sentence(region: str, key: str) -> tuple[str | None, str]:
    """The one sentence standing behind ``<!--check:key-->``, or why not.

    Rule 10.  :func:`read_claim` narrows the block to a *value* by
    pattern; this narrows it to a *span* by marker, for the checks whose
    subject is prose rather than a figure.

    **Two markers with one key are refused rather than resolved** —
    :func:`read_claim`'s rule, for its reason.  A block naming the same
    check twice has two candidate sentences and taking the first would
    report agreement with whichever was written first; the document
    carries a live instance of the shape today, ``migration_head`` being
    marked in two places.

    The markers are stripped out of what comes back — see
    :func:`_sentence_at`, which does the stripping for both narrowings.

    **This asks about a name; :attr:`Marker.sentence` asks about an
    occurrence**, and the refusal below is the whole difference.  A key
    stated twice leaves this reader two candidate sentences and no way to
    choose, so it refuses (:func:`read_claim`'s rule, for its reason).
    That is right for every check whose key names one claim, and it is
    exactly wrong for ``expires``, whose members the *document* declares:
    two predictions are two markers with one key.  So rule 9's pin reads
    the sentence off its own marker rather than calling this
    (``SNAG-DOCS-008``).
    """
    markers = [marker for marker in read_markers(region) if marker.key == key]
    if not markers:
        return None, (
            f"no sentence carries <!--check:{key}--> — the block states no "
            "claim this check can be pointed at"
        )
    if len(markers) > 1:
        return None, (
            f"{len(markers)} sentences carry <!--check:{key}--> — the block names "
            "the check twice and only one of them can be the claim"
        )
    return markers[0].sentence, ""


def load_region(path: Path | None = None) -> tuple[str | None, str]:
    """:func:`printed_region` of STATUS.md on disk, or ``None`` and why not."""
    target = path or STATUS_PATH
    try:
        document = target.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"{target} could not be read ({exc.__class__.__name__})"
    region = printed_region(document)
    if region is None:
        return None, f"{target} has no '## Quick Status' heading"
    return region, ""


# ---------------------------------------------------------------------------
# Measuring the box
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UnitState:
    """What systemd says about :data:`OWN_UNIT`.

    ``loaded`` is a separate field for a reason worth stating: ``systemctl
    show`` answers for a unit that does not exist, exits ``0``, and prints
    ``ActiveState=inactive`` — "nobody looked" rendered as a measurement,
    which is the exact shape this module exists to remove.  Every consumer
    gates on ``loaded`` before reading anything else.
    """

    loaded: bool
    active_state: str
    entered_at: float | None
    main_pid: str = ""
    problem: str = ""


def measure_unit(unit: str = OWN_UNIT) -> UnitState:
    """``systemctl show`` for the daemon, as data.

    ``--timestamp=unix`` is asked for rather than the default rendering,
    which is a local wall clock with an abbreviated zone name
    (``Mon 2026-08-24 09:58:28 BST``) that ``strptime`` cannot read back
    unambiguously.  ``SNAG-LOG-009``'s rule, met from the reading side:
    an epoch carries no zone, so nothing has to agree about one.
    """
    try:
        result = subprocess.run(
            [
                "systemctl",
                "show",
                unit,
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "ActiveEnterTimestamp",
                "-p",
                "MainPID",
                "--timestamp=unix",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return UnitState(
            False, "", None, problem=f"systemctl could not be run ({exc.__class__.__name__})"
        )

    props = dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )
    if props.get("LoadState") != "loaded":
        state = props.get("LoadState") or "no answer"
        return UnitState(False, "", None, problem=f"systemd reports {unit} as {state}")

    stamp = props.get("ActiveEnterTimestamp", "").lstrip("@")
    entered = float(stamp) if stamp.isdigit() else None
    return UnitState(True, props.get("ActiveState", ""), entered, props.get("MainPID", ""))


def measure_routes() -> tuple[int | None, str]:
    """How many routes this checkout's application declares.

    ``APIRoute`` rather than ``app.routes``, which is four longer: FastAPI
    adds ``/openapi.json``, ``/docs``, ``/docs/oauth2-redirect`` and
    ``/redoc`` as plain Starlette routes of its own.  The block's figure
    has always been the routes this repository writes, and counting
    FastAPI's would move it by four the first sitting anybody looked.
    """
    try:
        from fastapi.routing import APIRoute

        from sysadmin.main import create_app

        app = create_app()
    except Exception as exc:  # noqa: BLE001 — any import-time fault is "unknown"
        return None, f"create_app() raised {exc.__class__.__name__}"
    return len([route for route in app.routes if isinstance(route, APIRoute)]), ""


def measure_health() -> tuple[str | None, str]:
    """The status code ``GET /health`` answers with, as a string.

    A different fact from :func:`check_deploy`'s, and the pair is why both
    are worth having: systemd reporting ``active`` says the *process* is
    up, and this says the *application* is serving.  ``SNAG-DB-005`` is
    the case where they part company — the daemon was dead for 23 hours
    while ``systemctl`` had plenty to say about it, and the block's own
    sentence is about the route rather than the unit.

    Loopback rather than ``service.host``, which is ``0.0.0.0`` here and
    is a bind address rather than somewhere to send a request.
    """
    config = get_config()
    url = f"http://127.0.0.1:{config.service.port}/health"
    try:
        response = httpx.get(url, timeout=5.0)
    except Exception as exc:  # noqa: BLE001 — a daemon that will not answer is "unknown"
        return None, f"{url} did not answer ({exc.__class__.__name__})"
    return str(response.status_code), ""


@dataclass(frozen=True)
class DatabaseFacts:
    """The two counts one connection can answer, plus the open titles."""

    tables: int | None
    unresolved: int | None
    open_titles: tuple[str, ...]
    problem: str = ""


def measure_database() -> DatabaseFacts:
    """Table count and unresolved alerts, on one short-lived connection.

    The sync engine that exists for Alembic, opened and disposed —
    :func:`sysadmin.core.schema_guard.live_revision_sync`'s pattern, and
    for its reason: every caller of this module runs outside a running
    application, so ``get_engine()`` would raise before any query ran.

    ``alembic_version`` is excluded from the table count because the
    *document* excludes it — the Database row reads "14 tables (15
    counting ``alembic_version``)", so the figure being tested is the one
    without it.
    """
    config = get_config()
    schema = config.database.schema_
    engine = create_engine(config.database.sync_url)
    try:
        with engine.connect() as conn:
            tables = conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name <> 'alembic_version'"
                ),
                {"schema": schema},
            ).scalar_one()
            rows = conn.execute(
                text(  # noqa: S608 — the schema name is configuration, not input
                    f"SELECT severity, title FROM {schema}.alerts "
                    "WHERE resolved IS false ORDER BY created_at DESC"
                )
            ).fetchall()
    except Exception as exc:  # noqa: BLE001 — an unreachable database is "unknown"
        return DatabaseFacts(
            None, None, (), f"the database did not answer ({exc.__class__.__name__})"
        )
    finally:
        engine.dispose()

    titles = tuple(f"{severity}: {title}" for severity, title in rows)
    return DatabaseFacts(int(tables), len(titles), titles)


@dataclass(frozen=True)
class SourceSweep:
    """The newest ``.py`` either side of the daemon's import graph.

    Attributes:
        served: the newest module the running process can hold, and when.
            ``None`` when the graph is empty, which is a fault rather than
            a clean box and is why it is not simply an epoch of zero.
        unserved: the newest module it cannot — a console script, or
            ``metadata.py``, which alembic reads.  Carried so the claim
            can *name* a file a sitting has just edited instead of going
            quiet about it; the daemon serving its own code and nobody
            having looked at the rest are different facts.
        problem: why the graph could not be walked.  Rule 2 — a partial
            walk is a narrower population, and narrowing silently is the
            one direction rule 4 must not fail in, so an incomplete walk
            yields no population at all.
    """

    served: tuple[Path, float] | None = None
    unserved: tuple[Path, float] | None = None
    problem: str = ""


def newest_source(paths: Iterable[Path]) -> tuple[Path, float] | None:
    """The most recently written of ``paths``, and when.

    Rule 4.  A file's mtime is what the daemon read at start, so it is
    what decides whether the running process is serving the checkout.
    Pure, and taking its population as an argument rather than sweeping
    for one: which files are the daemon's is :func:`daemon_modules`'
    question, and answering both here is what let a sweep of *every*
    ``.py`` stand in for a sweep of the daemon's for the life of the
    module.
    """
    newest: tuple[Path, float] | None = None
    for path in paths:
        stamp = path.stat().st_mtime
        if newest is None or stamp > newest[1]:
            newest = (path, stamp)
    return newest


def _module_name(path: Path, root: Path) -> str:
    """The dotted name of a ``.py`` under ``root``'s parent."""
    parts = list(path.relative_to(root.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imported_names(tree: ast.AST, me: str, is_init: bool) -> set[str]:
    """Every ``sysadmin.*`` name an import statement anywhere in ``tree`` names.

    ``ast.walk`` rather than a scan of ``tree.body``, and that is the
    whole reason this is an AST walk rather than a runtime trace: a
    *function-level* import is an edge the daemon takes at its first call
    and a constructed ``create_app()`` never takes at all.
    :mod:`sysadmin.core.llm_client` is imported inside three review
    functions and by nothing at module scope, so a population measured by
    importing the app drops it and stops reporting the one restart it
    genuinely owes.

    A ``from`` target may name a module or an attribute of one and the
    syntax cannot tell them apart, so both readings are returned and the
    caller keeps whichever is a file.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = me if is_init else me.rpartition(".")[0]
                base = package.split(".")[: -(node.level - 1) or None]
                module = ".".join([*base, *([node.module] if node.module else [])])
            else:
                module = node.module or ""
            names.add(module)
            names.update(f"{module}.{alias.name}" for alias in node.names)
    return {name for name in names if name == PACKAGE or name.startswith(PACKAGE + ".")}


def _ancestry(name: str) -> list[str]:
    """``a.b.c`` and every package above it.

    Importing ``a.b.c`` executes ``a/__init__.py`` and ``a/b/__init__.py``
    before it, so those files are the daemon's too and an edit to one owes
    a restart.  The ancestors are *not* an alternative reading of the
    target — that is what the second name :func:`_imported_names` returns
    is for, and it is redundant, since a ``from x.y import Z`` already
    yields ``x.y`` in its own right.  This clause is the one carrying the
    package-initialisation fact, and driving the mutation is what said so:
    dropping it loses six ``__init__.py`` files here, none of which any
    statement in this package names.

    Every ancestor rather than one, although one reaches all eleven of
    this package's inits today.  That is a coincidence of which modules
    happen to be imported directly, not a property of the rule, and its
    failure mode is a package added at depth whose ``__init__.py`` falls
    out of the population in silence.
    """
    parts = name.split(".")
    return [".".join(parts[: index + 1]) for index in reversed(range(len(parts)))]


def daemon_modules(package: Path | None = None) -> tuple[frozenset[Path], str]:
    """Every ``.py`` under ``sysadmin/`` the daemon's import graph reaches.

    The population rule 4 compares mtimes over.  ``sysadmin.service``
    runs ``main:create_app``, so what the running process can hold is
    what is reachable from :data:`DAEMON_ROOT_MODULE` — and *only* that:
    the other modules in this package are console-script entry points
    (:mod:`sysadmin.snag_claims`, this module, :mod:`sysadmin.vacuous_guards`,
    :mod:`sysadmin.monitor.message_backfill`, :mod:`sysadmin.core.failure_replay`)
    and :mod:`sysadmin.metadata`, which ``alembic/env.py`` reads.  Each of
    those runs in a process of its own that reads its file fresh on every
    invocation, so no restart of this daemon could make any of them less
    stale, and a claim that a restart is owed for one is a claim about
    nothing.  Measured 2026-09-06: 94 of 100.

    **A walk of the source, not a trace of an import**, which is the
    opposite of the obvious implementation and the reason the whole fix
    is cheap.  A trace answers with what a process *did* import, so it
    misses a lazy edge until something takes it — and the previous
    sitting concluded from that that the population had to come from the
    running daemon over a new surface.  It does not: an import statement
    inside a function body is in the tree exactly as plainly as one at
    module scope, and reading the tree costs no endpoint, no contract
    entry and no restart to bootstrap.

    What it buys instead of exactness is a stated direction.  A module
    the daemon *would* import lazily but has not yet is counted here, so
    an edit to it reports a restart owed that the next import would have
    served anyway — rule 4's own failure direction, a needless
    ``kill -TERM``, and never a missed one.

    Returns the reachable paths and a problem string; the walk is total
    or it is nothing, because a graph that stopped early is a *narrower*
    population and narrowing silently is the one direction rule 4 must
    not fail in.  ``__pycache__`` is skipped for the reason it always
    was: it is written *by* the run, so counting it would make every
    daemon look one import older than itself.  **Removing that clause
    here changes no output** — a file under ``__pycache__`` carries a
    dotted name nothing imports, so reachability already excludes it —
    and it is kept anyway, for ``abandoned_runs``' reason: its
    visibility is what stops a reader deleting the *other* copy, in
    :func:`sweep_sources`, where the same filter is the only thing
    keeping a build artefact out of the claim's detail.  A behavioural
    test cannot reach a clause whose removal is invisible, so it is
    pinned by reading the source instead.
    """
    root = package or (REPO_ROOT / "sysadmin")
    try:
        files = {
            _module_name(path, root): path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts
        }
    except OSError as exc:  # noqa: BLE001 — an unreadable tree is "unknown"
        return frozenset(), f"could not read {root} ({exc.__class__.__name__})"
    if DAEMON_ROOT_MODULE not in files:
        return frozenset(), f"no {DAEMON_ROOT_MODULE} under {root}"

    seen: set[str] = set()
    queue = [DAEMON_ROOT_MODULE]
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        path = files[name]
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError) as exc:
            return frozenset(), f"could not parse {path.name} ({exc.__class__.__name__})"
        for target in _imported_names(tree, name, path.name == "__init__.py"):
            for candidate in _ancestry(target):
                if candidate in files and candidate not in seen:
                    queue.append(candidate)
    return frozenset(files[name] for name in seen), ""


def sweep_sources(package: Path | None = None) -> SourceSweep:
    """The newest ``.py`` on each side of the daemon's import graph.

    Both sides, because the six modules outside the graph are still code
    a sitting has just edited and a reader who saw the edit needs to be
    told it was considered rather than left to infer it from silence —
    ``UnitScanResponse.ports_checked``'s rule, at the size of a sentence.
    They are carried as ``detail`` rather than as ``note`` because
    :class:`Claim` documents a note as empty on a ``match`` and this is a
    match: the daemon is serving its own code.
    """
    root = package or (REPO_ROOT / "sysadmin")
    served, problem = daemon_modules(root)
    if problem:
        return SourceSweep(problem=problem)
    everything = {path for path in root.rglob("*.py") if "__pycache__" not in path.parts}
    return SourceSweep(newest_source(served), newest_source(everything - served))


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------


def _local(stamp: float) -> str:
    """An epoch as the local wall clock the block writes its times in.

    The measurement is the epoch; this is only how it is rendered to sit
    beside a sentence a human wrote in local time.  ``SNAG-LOG-009``
    forbids a rendered local time *in a command*, where the reader's zone
    is unknown; here the reader is the document, whose zone is this box's.
    """
    return datetime.fromtimestamp(stamp).strftime("%Y-%m-%d %H:%M:%S")


def compare_claim(
    key: str,
    subject: str,
    documented: str | None,
    doc_problem: str,
    measured: str | None,
    measure_problem: str,
    note: str = "",
) -> Claim:
    """One document-against-box comparison, with rule 2's tri-state.

    Both sides must be present to compare.  When either is missing the
    verdict is ``unknown`` and the note names *which* side failed, because
    "the sentence has been reworded" and "PostgreSQL is down" call for
    entirely different responses from the sitting reading this.
    """
    if documented is None or measured is None:
        problems = [problem for problem in (doc_problem, measure_problem) if problem]
        return Claim(
            key, subject, "claim", documented, measured, "unknown", "; ".join(problems)
        )
    if documented == measured:
        return Claim(key, subject, "claim", documented, measured, "match")
    return Claim(key, subject, "claim", documented, measured, "mismatch", note)


def check_routes(region: str, region_problem: str) -> Claim:
    documented, doc_problem = (None, region_problem) if not region else read_claim(region, "routes")
    count, measure_problem = measure_routes()
    measured = None if count is None else str(count)
    note = ""
    if documented is not None and measured is not None and documented != measured:
        note = (
            f"create_app() declares {measured} routes, not {documented} — "
            "the Quick Status table is stale"
        )
    return compare_claim(
        "routes", "API routes", documented, doc_problem, measured, measure_problem, note
    )


def check_tables(region: str, region_problem: str, facts: DatabaseFacts) -> Claim:
    documented, doc_problem = (None, region_problem) if not region else read_claim(region, "tables")
    measured = None if facts.tables is None else str(facts.tables)
    note = ""
    if documented is not None and measured is not None and documented != measured:
        note = (
            f"the sysadmin schema holds {measured} tables, not {documented} "
            "(alembic_version excluded on both sides)"
        )
    return compare_claim(
        "tables", "Database tables", documented, doc_problem, measured, facts.problem, note
    )


def check_migration_head(region: str, region_problem: str, head: str | None) -> Claim:
    """The head the document names against the head this checkout packages.

    Deliberately not the same question as :func:`check_schema` below, and
    the pair is what makes the answer complete: this one catches a
    migration written since the table row was, and that one catches a
    migration nobody applied.  A document, a checkout and a database are
    three parties and two comparisons.
    """
    documented, doc_problem = (
        (None, region_problem) if not region else read_claim(region, "migration_head")
    )
    note = ""
    if documented is not None and head is not None and documented != head:
        note = f"this checkout's migrations end at {head}, not {documented}"
    return compare_claim(
        "migration_head",
        "Alembic head (documented)",
        documented,
        doc_problem,
        head,
        "the packaged head could not be read",
        note,
    )


def check_alerts(region: str, region_problem: str, facts: DatabaseFacts) -> Claim:
    """Rule 5 — the count, its direction, and the titles behind it."""
    documented, doc_problem = (None, region_problem) if not region else read_claim(region, "alerts")
    measured = None if facts.unresolved is None else str(facts.unresolved)
    note = ""
    if documented is not None and measured is not None and documented != measured:
        moved = int(measured) - int(documented)
        if moved > 0:
            note = (
                f"{moved} more unresolved row(s) than the block accounts for — "
                "something opened since it was written"
            )
        else:
            note = (
                f"{-moved} fewer unresolved row(s) than the block accounts for — "
                "a row it treats as open has resolved, so an action it asks for "
                "may already be done (SNAG-ESTATE-008's founding case)"
            )
    detail: tuple[str, ...] = ()
    if facts.open_titles:
        named = facts.open_titles[:MAX_NAMED_ALERTS]
        detail = named
        if len(facts.open_titles) > MAX_NAMED_ALERTS:
            detail = (*named, f"… and {len(facts.open_titles) - MAX_NAMED_ALERTS} more")
    claim = compare_claim(
        "alerts", "Unresolved alerts", documented, doc_problem, measured, facts.problem, note
    )
    return replace(claim, detail=detail)


def check_daemon_start(region: str, region_problem: str, unit: UnitState) -> Claim:
    documented, doc_problem = (
        (None, region_problem) if not region else read_claim(region, "daemon_start")
    )
    measured = _local(unit.entered_at) if unit.entered_at is not None else None
    note = ""
    if documented is not None and measured is not None and documented != measured:
        note = (
            f"{OWN_UNIT} has been active since {measured}, not {documented} — "
            "it has restarted since the block was written, and nothing recorded why"
        )
    return compare_claim(
        "daemon_start",
        "Daemon start time",
        documented,
        doc_problem,
        measured,
        unit.problem or f"{OWN_UNIT} reports no ActiveEnterTimestamp",
        note,
    )


def check_schema(status_verdict: Verdict, current: str | None, problem: str | None) -> Claim:
    """Is the live database at this checkout's head — the box, not the block.

    ``SNAG-DB-005`` ran for 23 hours because nothing asked this until a
    restart did.  The pre-commit hook blocks on it and postflight warns;
    this is the third moment, and it is the earliest one: a sitting that
    opens with the database behind is a sitting whose first restart kills
    the daemon.
    """
    return Claim(
        "schema",
        "Live schema at packaged head",
        "state",
        None,
        current,
        status_verdict,
        problem or "",
    )


def check_deploy(unit: UnitState) -> Claim:
    """Is the running daemon serving the code on disk — rule 4.

    The population is the daemon's own import graph, never every ``.py``
    under ``sysadmin/``.  Six modules here are console-script entry
    points and alembic's metadata, each read fresh by a process of its
    own, so a restart of *this* daemon cannot make any of them less
    stale.  Sweeping them cost eleven consecutive sittings a
    ``kill -TERM`` that moved nothing a caller could observe, and
    ``SNAG-SYSD-007`` is what that eventually cost: five restarts in ten
    minutes tripped ``StartLimitBurst`` and the box was down 77 minutes,
    one of the five being this claim's.

    A newer module *outside* the graph is still named, on a ``match``
    and in ``detail``.  Going quiet about a file the sitting has just
    written would leave a reader unable to tell "considered, and no
    restart is owed for it" from "never looked at" — ``ports_checked``'s
    rule, and the distinction this check spent eleven sittings unable to
    draw.
    """
    sweep = sweep_sources()
    if not unit.loaded or unit.entered_at is None:
        return Claim(
            "deploy",
            "Daemon serves the code on disk",
            "state",
            None,
            None,
            "unknown",
            unit.problem or f"{OWN_UNIT} reports no ActiveEnterTimestamp",
        )
    if sweep.problem:
        return Claim(
            "deploy",
            "Daemon serves the code on disk",
            "state",
            None,
            None,
            "unknown",
            sweep.problem,
        )
    if sweep.served is None:
        return Claim(
            "deploy",
            "Daemon serves the code on disk",
            "state",
            None,
            None,
            "unknown",
            f"no module reachable from {DAEMON_ROOT_MODULE}",
        )
    path, stamp = sweep.served
    if stamp <= unit.entered_at:
        return Claim(
            "deploy",
            "Daemon serves the code on disk",
            "state",
            None,
            f"active since {_local(unit.entered_at)}",
            "match",
            "",
            _unserved_detail(sweep.unserved, unit.entered_at),
        )
    remedy = f"kill -TERM {unit.main_pid}" if unit.main_pid not in ("", "0") else "restart it"
    return Claim(
        "deploy",
        "Daemon serves the code on disk",
        "state",
        None,
        f"active since {_local(unit.entered_at)}",
        "mismatch",
        f"the running process predates the newest source edit — {remedy} "
        "(Restart=always brings it straight back, no sudo while it is up — "
        "SNAG-SYSD-007)",
        (f"{path.relative_to(REPO_ROOT)} written {_local(stamp)}",),
    )


def _unserved_detail(
    unserved: tuple[Path, float] | None, entered_at: float
) -> tuple[str, ...]:
    """Name a newer module the daemon does not import, or say nothing.

    Only when it is newer than the start, because that is the reading a
    sitting would otherwise have taken for a restart owed.  An older one
    is not a fact anybody is about to misread.
    """
    if unserved is None or unserved[1] <= entered_at:
        return ()
    path, stamp = unserved
    return (
        f"{path.relative_to(REPO_ROOT)} written {_local(stamp)} is outside the "
        f"daemon's import graph — read fresh by its own process, so no restart "
        f"is owed for it",
    )


def check_health(region: str, region_problem: str) -> Claim:
    """The status code the block says ``/health`` answers with."""
    documented, doc_problem = (None, region_problem) if not region else read_claim(region, "health")
    measured, measure_problem = measure_health()
    note = ""
    if documented is not None and measured is not None and documented != measured:
        note = (
            f"GET /health answers {measured}, not {documented} — the daemon is "
            "up enough for systemd and not serving"
        )
    return compare_claim(
        "health", "/health answers", documented, doc_problem, measured, measure_problem, note
    )


def check_open_titles(region: str, region_problem: str, facts: DatabaseFacts) -> Claim:
    """Is every unresolved row named in the sentence that claims to name them?

    :func:`check_alerts` compares the *count*, which is what moves when a
    row opens or closes.  This asks the finer question the count cannot:
    a swap — one row resolving as another opens — holds the total still
    while the block's sentence about *which* rows are open goes silently
    wrong.  Today's block names all four of its four and explains why each
    is expected; the count alone would agree with a block naming none.

    **One direction only, and the other has an owner.**  A row the block
    names that has since resolved is ``SNAG-ESTATE-008``'s founding case
    and is already reported, by :func:`check_alerts`'s *fall* note.  What
    that note cannot say is that a row nobody wrote about is open, so this
    is the direction taken here — and a title is matched as a substring
    because the block quotes it inside backticks with prose around it.

    **The haystack is one sentence, and it used to be the whole region**
    (``SNAG-ESTATE-016``, rule 10).  The substring test is right; what was
    never weighed is that the region it ran over is **append-only**.  It
    flattened to **178,301 characters** at ``9a3fe30``, because every past
    sitting's account accumulates below the current sentence — so a
    recurring fault's title has been written down before and satisfied the
    test whatever the current sentence said.  Measured at that commit, not
    reasoned about: the sentence named ``GPU was reset — every client lost
    its VRAM``, which was **not** open, and omitted
    ``High VRAM usage on AMD Radeon RX 7900 XTX``, which was — and the
    check reported ``4 named, 4 open``, ``match``.  The missing title's one
    occurrence in the region sat **126 lines below the marker**, in an
    account of a fault four sittings old.  :func:`claim_sentence` narrows
    the haystack to 290 characters and the two blocks then differ in
    exactly the one title, which is the whole discrimination.

    **What it deliberately did not become** is a check that also refuses a
    *name with no row*.  That is the direction the paragraph above
    reserves for the fall note, and the block legitimately names a
    resolved title while explaining a fall — today's carries three such
    parentheticals.  Narrowing the sentence is what makes them harmless:
    they sit outside it, so they neither satisfy this check nor offend it.

    **The marker cannot make this check quieter than ``unknown``, which is
    what keeps it inside rule 7.**  A marker is additive and may never gate
    a check, and here it decides *where to look* rather than *whether to
    look* — the population is the alert table's and is read either way.
    Deleting the marker therefore turns a ``mismatch`` into an ``unknown``
    that names the remedy, never into a ``match``: rule 2's tri-state doing
    the job an on/off switch could not.  This is the only enforcement
    ``open_titles`` has, since it carries no pattern and
    :func:`check_markers`' *unclaimed figure* finding runs over
    :data:`CLAIM_PATTERNS` alone.
    """
    if facts.open_titles is None or facts.unresolved is None:
        return Claim(
            "open_titles", "Open rows named in the block", "claim", None, None, "unknown",
            facts.problem,
        )
    if not region:
        return Claim(
            "open_titles", "Open rows named in the block", "claim", None,
            f"{facts.unresolved} open", "unknown", region_problem,
        )
    sentence, sentence_problem = claim_sentence(region, "open_titles")
    if sentence is None:
        return Claim(
            "open_titles", "Open rows named in the block", "claim", None,
            f"{facts.unresolved} open", "unknown",
            f"{sentence_problem} — add <!--check:open_titles--> beside the sentence "
            "that lists them",
        )
    # ``open_titles`` are rendered "severity: title" for the alert report;
    # the block quotes the title alone, so the severity is dropped before
    # the substring test rather than being written into the document.
    unnamed = tuple(
        entry for entry in facts.open_titles if entry.split(": ", 1)[-1] not in sentence
    )
    documented = f"{len(facts.open_titles) - len(unnamed)} named"
    measured = f"{len(facts.open_titles)} open"
    if not unnamed:
        return Claim(
            "open_titles", "Open rows named in the block", "claim", documented, measured, "match"
        )
    return Claim(
        "open_titles",
        "Open rows named in the block",
        "claim",
        documented,
        measured,
        "mismatch",
        f"{len(unnamed)} unresolved row(s) the marked sentence does not name — a row "
        "nobody wrote about is the one a sitting will not account for, and a title "
        "written down by a past sitting further down the block does not count",
        tuple(f"unnamed: {title}" for title in unnamed),
    )


def _convention(key: str, subject: str, note: str) -> Claim:
    """A finding about the block's own bookkeeping — rule 7's third kind.

    Neither the document's figures nor the box are wrong; what is wrong is
    the pairing between them, and the remedy is a marker rather than a
    reworded sentence or a ``kill -TERM``.  Rule 3 keeps ``claim`` and
    ``state`` apart because their remedies are opposites; this is a third
    remedy, so it is a third kind rather than a flavour of either.
    """
    return Claim(key, subject, "convention", None, None, "unknown", note)


def check_markers(region: str, markers: list[Marker]) -> list[Claim]:
    """The convention's two failure modes — rule 7.

    **A marker naming a check nobody implements** is a typo, a rename, or
    a check deleted out from under the sentence that relies on it.  Each
    of the three ends the same way: the sentence looks verified and is
    not, which is worse than prose, because prose does not claim to have
    been checked.

    **A figure this module can test that no marker claims** is the
    convention's whole point — ``SNAG-ESTATE-008`` asked for *"every ops
    action names the check that closes it"*, and this is the only place
    that can be enforced.  Note the asymmetry with the checks themselves:
    every pattern-bearing claim still runs whether or not a marker names
    it, so the marker can never make a check quieter.  It exists to make
    an *unmarked* claim loud, never to gate a marked one — a convention
    that could switch a check off would be a way to retire one by
    editing a document, which is precisely what rule 2 refuses.
    """
    named = {marker.key for marker in markers}
    findings = [
        _convention(
            f"marker:{key}",
            f"Block names check '{key}'",
            f"nothing implements '{key}' — the sentence relying on it is unchecked "
            f"(known: {', '.join(sorted(CHECK_KEYS))})",
        )
        for key in sorted(named - CHECK_KEYS)
    ]
    if not region:
        return findings
    findings.extend(
        _convention(
            f"unclaimed:{key}",
            f"Unclaimed figure '{key}'",
            "the block states a figure this check can test and no line names it — "
            f"add <!--check:{key}--> beside the sentence",
        )
        for key in sorted(CLAIM_PATTERNS)
        if key not in named and read_claim(region, key)[0] is not None
    )
    return findings


def expiry_example(now: datetime) -> str:
    """``now`` written the way an ``expires`` marker must carry it.

    ``isoformat`` rather than ``strftime(EXPIRY_FORMAT)``: the latter
    renders ``+0100`` where every surface anyone copies a stamp from —
    the estate's ``started_at``, this repository's own JSON — renders
    ``+01:00``.  Both parse, and the example a message hands an author
    should look like the thing they will paste beside it.
    """
    return now.astimezone().isoformat(timespec="minutes")


def _malformed_instant(text: str) -> str:
    """Why an ``expires`` argument did not yield an instant — rule 8.

    Two distinguishable faults, and the naive one is the whole of
    ``SNAG-ESTATE-013``'s population: every marker written before
    2026-08-28 is a bare wall clock.  A generic "not of the form" would
    report the commonest case as a typo, so the naive shape is recognised
    (never accepted) and the message names the **two instants** the stamp
    could mean rather than picking one.  Picking one is the defect: local
    is right on the box that wrote it and wrong by the offset everywhere
    else, which is why :func:`sysadmin.monitor.journal.since_timestamp`
    refuses rather than converts.
    """
    try:
        naive = datetime.strptime(text, EXPIRY_NAIVE_FORMAT)
    except ValueError:
        return f"'{text}' is not an instant of the form {EXPIRY_FORMAT}"
    here = naive.astimezone().isoformat(timespec="minutes")
    utc = naive.replace(tzinfo=UTC).isoformat(timespec="minutes")
    if here == utc:
        return (
            f"'{text}' carries no offset — write it as {utc}.  This box's clock agrees "
            "with UTC at that instant, so the two readings coincide today and will not "
            "across the year, which is why the offset is required rather than inferred"
        )
    return (
        f"'{text}' carries no offset, so it names two instants — {here} if the sentence "
        f"is in this box's clock, {utc} if it was copied from a UTC-stamped surface.  "
        "Write the offset rather than leaving this module to choose (SNAG-ESTATE-013)"
    )


def check_expiry(marker: Marker, now: datetime) -> Claim:
    """One prediction, against the clock — rules 8 and 9.

    ``SNAG-ESTATE-011`` was opened by a block asserting a retention
    boundary **three hours before it happened**: "the row clears at 03:32
    with nothing done", written at 00:30.  Nothing about that sentence was
    wrong, and nothing about it could be measured either — which is why it
    is a different class from every other claim here and needs a different
    mechanism.  A prediction is not checked, it is *timed*: before its
    moment it stands, and after its moment it is ``unknown`` until a human
    has looked, because "the prediction came true" and "nobody went back"
    are the two readings and only one of them is health.

    ``unknown`` rather than ``mismatch`` deliberately.  A passed boundary
    does not make the sentence false — rule 2's whole point is that a
    claim nobody managed to test is its own verdict.

    **The instant must carry an offset and a naive one is refused**
    (``SNAG-ESTATE-013``).  The marker that opened that entry was copied
    off a surface publishing UTC and written as a bare wall clock, so it
    named a moment an hour before its subject here — and the check
    reported the passed boundary correctly, having nothing to disagree
    with.  See :data:`EXPIRY_FORMAT` for why the remedy is an offset
    rather than ``@<epoch>``, which is what ``since_timestamp`` renders
    for the identical fault one document over.

    **``now`` must be aware, and the guard is here rather than left to
    the subtraction below.**  A naive ``now`` and an aware ``moment``
    raise ``TypeError`` on their own, loudly — so this is not the silent
    reading ``since_timestamp`` exists to refuse — but only at the first
    *well-formed* marker.  A document carrying none, which is this one
    today, would let a naive caller through until the day somebody wrote
    a good marker, and the crash would arrive stamped with that edit.
    Refusing at the entry point puts the failure where the mistake is.
    ``TypeError`` because that is what comparing the two raises already:
    this brings the same fault forward, it does not invent a new one.

    **The pin is against the marker's own sentence, and it used to be
    against the whole printed region** (``SNAG-DOCS-008``).  Rule 9
    always admitted the wide search was "the weaker half" — *"a block
    naming 03:32 twice for two different reasons would satisfy it"* — and
    on 2026-09-04 that was measured rather than supposed: the region
    states **86** distinct wall clocks, **28** of them more than once, so
    an arbitrary instant already had a 6 % chance of being pinned by a
    sentence about something else, rising with every sitting the block
    accretes.  Driven at the live region, a marker reading
    ``2026-09-05T04:45+00:00`` beside a sentence saying ``04:45`` — a UTC
    stamp copied into a BST sentence, ``SNAG-ESTATE-013``'s founding
    fault exactly — came back **``match``**, swallowed by eleven
    unrelated mentions of ``05:45``.  Against a block that does not
    happen to say ``05:45`` the same marker returns ``unknown`` carrying
    that entry's own diagnostic.

    So the two failure directions are not symmetric, which is what rule
    10 got half right when it left this alone.  *Not* finding the instant
    is ``unknown`` and loud, as that rule said; *finding it elsewhere* is
    ``match`` and silent, which is the direction rule 10 was itself
    opened for and did not carry across.  Narrowed, both directions are
    loud: a prediction whose clock sits in a neighbouring sentence is
    reported, and the remedy is to move the marker or restate the clock —
    one edit, and it fails in the direction that costs an edit rather
    than in the direction that hides a zone error.
    """
    if now.tzinfo is None:
        raise TypeError(
            "check_expiry needs an aware clock: a naive one is read as local, "
            "which is the ambiguity an expires marker's offset exists to remove"
        )
    parts = marker.argument.split(None, 1)
    label = parts[1] if len(parts) > 1 else "prediction"
    subject = f"Block predicts: {label}"
    if not parts:
        return _convention(
            "expires:?", subject, "the marker carries no instant — expected "
            f"<!--check:expires {expiry_example(now)} what it is about-->",
        )
    try:
        moment = datetime.strptime(parts[0], EXPIRY_FORMAT)
    except ValueError:
        return _convention(f"expires:{parts[0]}", subject, _malformed_instant(parts[0]))

    key = f"expires:{parts[0]}"
    clock = moment.astimezone().strftime(EXPIRY_CLOCK_FORMAT)
    stated = moment.strftime(EXPIRY_CLOCK_FORMAT)
    prose = marker.sentence
    if clock not in prose:
        note = (
            f"the marker names {clock} and the sentence it stands in does not — pinned "
            "rather than trusted, because the instant is the one fact stated twice here. "
            "Move the marker into the sentence naming the clock, or name the clock in "
            "this one; the whole block is deliberately not searched (SNAG-DOCS-008)"
        )
        if stated != clock and stated in prose:
            note = (
                f"the marker's instant is {clock} on this box and the sentence says "
                f"{stated}, which is that moment in the marker's own zone — the sentence "
                "and the stamp are in different clocks, which is the copy "
                "SNAG-ESTATE-013 was opened by"
            )
        return Claim(
            key, subject, "claim", parts[0], _local(moment.timestamp()), "unknown", note,
        )

    hours = (moment - now).total_seconds() / 3600
    if hours > 0:
        return Claim(
            key, subject, "claim", parts[0], f"{humanise_hours(hours)} to run", "match"
        )
    return Claim(
        key, subject, "claim", parts[0], f"passed {humanise_hours(-hours)} ago", "unknown",
        "the block predicts a moment that has passed and nobody re-measured it — "
        "measure it or reword the sentence",
    )


def check_all(path: Path | None = None, now: datetime | None = None) -> list[Claim]:
    """Every check, measured once each, state checks first.

    The state checks run even when STATUS.md cannot be read at all: a
    missing document is a reason to know less about the document, never a
    reason to stop asking whether the box is behind its checkout.
    """
    region, region_problem = load_region(path)
    facts = measure_database()
    unit = measure_unit()
    status = schema_status()
    region_text = region or ""
    markers = read_markers(region_text)
    # Local and aware — the document's prose is a local wall clock (rule 9)
    # and `check_expiry` refuses a naive one.  A naive `now` handed in by a
    # caller is passed through unchanged and refused there: normalising it
    # here would resolve the caller's ambiguity by guessing, which is the
    # move `EXPIRY_FORMAT` exists to refuse one layer down.
    moment = now or datetime.now().astimezone()

    return [
        check_schema(status.verdict, status.current, status.problem),
        check_deploy(unit),
        check_routes(region_text, region_problem),
        check_tables(region_text, region_problem, facts),
        check_migration_head(region_text, region_problem, status.head),
        check_alerts(region_text, region_problem, facts),
        check_daemon_start(region_text, region_problem, unit),
        check_health(region_text, region_problem),
        check_open_titles(region_text, region_problem, facts),
        *(
            check_expiry(marker, moment)
            for marker in markers
            if marker.key == "expires"
        ),
        *check_markers(region_text, markers),
    ]


def overall(claims: list[Claim]) -> Verdict:
    """``mismatch`` outranks ``unknown``, which outranks ``match``.

    Not ``max()`` over :data:`EXIT_STATUS`, which would put ``unknown``
    (2) above ``mismatch`` (1) and report a check that failed to run as
    more urgent than a claim measured false.
    """
    verdicts = {claim.verdict for claim in claims}
    if "mismatch" in verdicts:
        return "mismatch"
    if "unknown" in verdicts:
        return "unknown"
    return "match"


MARKERS: dict[str, str] = {"match": "ok", "mismatch": "no", "unknown": "??"}


def render(claims: list[Claim]) -> list[str]:
    """The report as lines, marker first so a shell caller can colour it."""
    lines = []
    for claim in claims:
        sides = []
        if claim.kind == "claim":
            sides.append(f"block says {claim.documented or '—'}")
        if claim.kind != "convention":
            sides.append(f"measured {claim.measured or '—'}")
        line = f"{MARKERS[claim.verdict]} {claim.subject}"
        if sides:
            line += f": {', '.join(sides)}"
        if claim.note:
            line += f" — {claim.note}"
        lines.append(line)
        lines.extend(f"   {item}" for item in claim.detail)
    return lines


def main(argv: list[str] | None = None) -> int:
    """``sysadmin-check-claims`` — does the block that opens a sitting hold?

    Exit status is :data:`sysadmin.core.schema_guard.EXIT_STATUS`:
    ``0`` every claim holds, ``1`` at least one is false, ``2`` at least
    one could not be tested and none is false.
    """
    parser = argparse.ArgumentParser(
        description="Re-measure the ops claims docs/roadmap/STATUS.md opens with."
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help=f"the document to read claims from (default {STATUS_PATH})",
    )
    args = parser.parse_args(argv)

    claims = check_all(args.status_file)
    for line in render(claims):
        print(line)
    return EXIT_STATUS[overall(claims)]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
