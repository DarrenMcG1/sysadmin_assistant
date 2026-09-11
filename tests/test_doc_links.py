"""Every relative markdown link in a tracked document resolves, and
resolves **inside this repository**.

The detector outlives its finding — ``FROZEN_TABLES``' rule, for the
seventh time here. estate-manager's message ``25be77ba`` reported 24
inward links resolving to nothing, all of them citing
``sysadmin/services``, ``sysadmin/agents`` or ``sysadmin/routers``, which
``512af01`` deleted on 2026-08-08. They were broken for **22 days** and
nothing on this box could have said so: the estate refused the check
under its ADR-0073 (the audit may falsify only a claim the *estate*
makes, and how this repository writes links is a claim it makes
nowhere), which is exactly what leaves it here.

Six rules, four of them the opposite of the obvious implementation:

1. **Block structure is parsed, never approximated by indentation.** A
   line indented four spaces is a code block only when it is not
   continuing a list item, and this repository's documents are almost
   entirely lists. The naive ``startswith("    ")`` rule finds **23** of
   the 24 — it eats ``tasks.md``'s six-space list continuation — so an
   instrument that disagrees with the filing by one is a repair that
   silently leaves one behind.

2. **Existence is asserted; a line anchor is not minted.** 13 of the 24
   carried an ``#L`` anchor and 3 further links resolved while their
   anchor had rotted — ``main.py:123-128`` pointing at a blank line,
   ``agent.py:391`` at an unrelated docstring. An anchor rots invisibly
   to any existence check, so the repair dropped every one rather than
   re-pinning them, and this test asserts the *file* because that is the
   claim it can actually keep.

3. **Tracked files only, via ``git ls-files``.** An untracked scratch
   document is not a surface this repository publishes, and failing on
   one makes the suite depend on the working tree's litter.

4. **Existence was the wrong question on its own, and the guard was
   green for a reason unrelated to its reader** (``SNAG-DOCS-020``,
   2026-09-11). Rule 2 asserts a target exists **on disk**, and this box
   holds the private sibling trees ``~/projects/estate-manager`` and
   ``~/projects/alfred``. So **17** links reaching out of this
   repository with ``../../../`` passed every run and were a 404 for the
   public reader the guard was written for — ``ports_checked``'s rule at
   the size of a link, a guard looking at the wrong filesystem.
   Containment is therefore asserted beside existence, and the two are
   separate findings because the remedies are opposites: a **missing**
   link is repaired or re-pointed, an **escaping** one is de-linked.

5. **Resolve, then compare — or the narrowing ships green and inert.**
   ``Path.is_relative_to`` is purely lexical and does not collapse
   ``..``, so ``<repo>/docs/adr/../../../estate-manager/x`` reads as
   *inside* the repository: measured 2026-09-11, the unresolved test
   answers ``True`` for **all 17** of the escapes it exists to catch.
   The obvious one-line spelling of this rule is thus a no-op that
   cannot be told from a working one by its result, which is why the
   ordering carries a test of its own rather than a comment.

6. **There is no exemption list, and its absence is measured rather
   than assumed.** The natural objection is that the five pointer stubs
   — the four moved guides plus ``docs/adr/0002-estate-manager.md`` —
   are *required* to point out of this repository by the estate rule *a
   moved document leaves a pointer, never a copy*, and so need an
   exemption declared in a document (``routes_by_prefix``'s rule). That
   reads the rule as requiring a **link** where it requires a
   **pointer**, and three measurements separate the two: the rule's
   canonical statement in estate-manager's ``docs/conventions/
   estate-rules.md`` constrains the pointer's *content* and says nothing
   of its form; that repository's own copies of those same four moved
   guides cite back at this tree as a plain backticked path
   (``sysadmin_assistant/docs/guides/``) and not as a link; and this
   repository already spells the same class of citation unlinked
   **112** times against **12** linked. A path is also the *more*
   informative form for the reader who cannot follow it — ``../../../``
   names no repository. So all 17 became plain citations and the
   population of this rule is **empty by repair**, not by exemption,
   which leaves no list a later sitting could reach for as a switch.

The population of rules 4 and 5 is therefore zero, measured
2026-09-11 — so both are driven at synthetic input as well as at the
corpus, because a green guard nobody has seen fail is indistinguishable
from one that cannot.
"""

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

FENCE = re.compile(r"^\s*(```|~~~)")
BULLET = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s)")
LINK = re.compile(r"\[([^\]\n]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_SCHEMES = ("http://", "https://", "mailto:", "#")


def tracked_markdown():
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [REPO / rel for rel in out]


def prose_lines(text):
    """Yield ``(lineno, line)`` for lines that are prose, not code.

    A fenced block is skipped wholesale.  An indented block is skipped
    only when a blank line precedes it *and* no list is open, which is
    the CommonMark rule; inside a list item the same indentation is a
    continuation and may well carry a link.
    """
    in_fence = False
    in_list = False
    prev_blank = True
    for lineno, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            prev_blank = False
            continue
        if in_fence:
            continue
        if not line.strip():
            prev_blank = True
            continue
        indented = line.startswith("    ") or line.startswith("\t")
        if BULLET.match(line):
            in_list = True
        elif not indented:
            in_list = False
        if indented and prev_blank and not in_list:
            prev_blank = False
            continue
        prev_blank = False
        yield lineno, re.sub(r"`[^`]*`", "", line)


def relative_links(docs=None):
    """Yield ``(doc, lineno, target, resolved)`` for every relative link.

    The resolution happens here and once, because rule 5 turns on it:
    a caller handed an unresolved path cannot ask a containment
    question about it and get a true answer.
    """
    for path in tracked_markdown() if docs is None else docs:
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in prose_lines(text):
            for _label, target in LINK.findall(line):
                if target.startswith(SKIP_SCHEMES):
                    continue
                if "..." in target or "…" in target:
                    continue  # prose elision, not a path
                path_part = target.partition("#")[0]
                if not path_part:
                    continue
                yield path, lineno, target, (path.parent / path_part).resolve()


def _site(root, path, lineno, target):
    try:
        doc = path.relative_to(root)
    except ValueError:
        doc = path
    return f"{doc}:{lineno} -> {target}"


def escaping_links(docs=None, root=REPO):
    """Every tracked relative link whose target lies outside the repository.

    Rule 4's half.  Reported apart from ``missing_links`` because the
    remedy is the opposite one: this link is de-linked and cited by
    name, where a missing link is repaired or re-pointed.
    """
    for path, lineno, target, resolved in relative_links(docs):
        if not resolved.is_relative_to(root):
            yield _site(root, path, lineno, target)


def missing_links(docs=None, root=REPO):
    """Every tracked relative link inside the repository that does not exist.

    Scoped to the links containment admits, so the two findings
    partition the corpus and no link is reported twice.  An escaping
    link is a finding whether or not it exists on disk — on this box it
    always does, which is the whole of ``SNAG-DOCS-020``.
    """
    for path, lineno, target, resolved in relative_links(docs):
        if resolved.is_relative_to(root) and not resolved.exists():
            yield _site(root, path, lineno, target)


def test_every_relative_link_in_a_tracked_document_resolves():
    missing = sorted(missing_links())
    assert not missing, "broken relative markdown links:\n  " + "\n  ".join(missing)


def test_no_relative_link_escapes_this_repository():
    """``SNAG-DOCS-020``: they all resolved here and 404'd for everyone else.

    Cite across a repository boundary by name — ``estate-manager
    ADR-0068 §4`` — or by a backticked path, never by a relative link.
    """
    escaping = sorted(escaping_links())
    assert not escaping, (
        "relative links resolving outside this repository (they work on this "
        "box only; cite by name or by a backticked path instead):\n  "
        + "\n  ".join(escaping)
    )


def test_the_detector_sees_a_link_that_escapes_but_exists(tmp_path):
    """Rule 4's witness, because the live population is empty by repair.

    The specimen is the defect exactly: a target that **does** exist,
    so every existence check passes and only containment can speak.
    """
    (tmp_path / "sibling").mkdir()
    (tmp_path / "sibling" / "other.md").write_text("real\n")
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    doc = repo / "docs" / "a.md"
    doc.write_text("Recorded in [their ADR-0068](../../sibling/other.md).\n")

    assert (doc.parent / "../../sibling/other.md").resolve().exists()
    assert sorted(missing_links([doc], root=repo)) == []
    assert sorted(escaping_links([doc], root=repo)) == [
        "docs/a.md:1 -> ../../sibling/other.md"
    ]


def test_a_link_that_escapes_and_is_absent_is_reported_once(tmp_path):
    """``missing_links``' containment clause, which behaviour cannot reach.

    With every escape repaired no link is both outside the repository
    and absent, so deleting ``resolved.is_relative_to(root) and`` is a
    mutation the whole suite passes — driven 2026-09-11, five
    falsifications and this the one that went green.  ``chk_run_status``'
    redundant-conjunct rule: a clause whose removal is invisible in
    behaviour needs a population built for it, or the partition claim
    rests on an accident of today's corpus.
    """
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    doc = repo / "docs" / "a.md"
    doc.write_text("Gone: [somewhere](../../sibling/absent.md).\n")

    assert not (doc.parent / "../../sibling/absent.md").resolve().exists()
    assert sorted(missing_links([doc], root=repo)) == [], "escaping, not missing"
    assert len(list(escaping_links([doc], root=repo))) == 1


def test_the_containment_test_resolves_before_it_compares(tmp_path):
    """Rule 5, pinned against the implementation it refutes.

    ``is_relative_to`` is lexical, so the one-line narrowing anyone
    would write first answers *inside* for a ``..`` escape and ships
    green over the whole finding.  Driven at the refuted form rather
    than described in a comment.
    """
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (tmp_path / "sibling").mkdir()
    (tmp_path / "sibling" / "other.md").write_text("real\n")
    doc = repo / "docs" / "a.md"
    doc.write_text("See [it](../../sibling/other.md).\n")

    unresolved = doc.parent / "../../sibling/other.md"
    assert unresolved.is_relative_to(repo), "the lexical reading this rule exists to refuse"
    assert not unresolved.resolve().is_relative_to(repo)
    assert len(list(escaping_links([doc], root=repo))) == 1


def test_the_two_findings_partition_the_corpus():
    """Every link is escaping, missing, or resolves — exactly one.

    ``routes_by_prefix``' totality, at the size of a link: the rules
    supply the partition and this checks it covers the corpus, so a
    third way of failing cannot arrive as silence.  It counts *links*
    and not ``(doc, line, target)`` triples, because a line may cite
    one document twice and does — ``tasks.md`` cites ``snag_list.md``
    twice on each of four lines, which made the first draft of this
    test red against a corpus that was correct.
    """
    links = list(relative_links())
    escaping = missing = resolves = 0
    for _path, _lineno, _target, resolved in links:
        if not resolved.is_relative_to(REPO):
            escaping += 1
        elif not resolved.exists():
            missing += 1
        else:
            resolves += 1
    assert escaping + missing + resolves == len(links)
    assert (escaping, missing) == (0, 0)
    assert resolves == len(links) > 0, "a guard over an empty corpus is not a guard"


def test_the_detector_sees_a_link_inside_a_list_continuation():
    """The one the naive indentation rule misses.

    ``tasks.md``'s 24th link sits on a six-space continuation line under
    a ``- [x]`` bullet.  A detector that treats four spaces as a code
    fence reports 23 and calls the repair complete, so the case is
    pinned rather than left to the corpus to happen to contain.
    """
    doc = (
        "- [x] **A finding** with prose that wraps and then\n"
        "      cites [a file](nowhere/at/all.py) on the next line\n"
    )
    found = [target for _n, line in prose_lines(doc) for _l, target in LINK.findall(line)]
    assert found == ["nowhere/at/all.py"]


def test_a_link_inside_a_genuine_indented_code_block_is_not_a_finding():
    """The other side of the same rule, or it would fire on examples."""
    doc = "Some prose.\n\n    [an example](does/not/exist.md)\n\nMore prose.\n"
    found = [target for _n, line in prose_lines(doc) for _l, target in LINK.findall(line)]
    assert found == []


def test_a_link_inside_a_fenced_block_is_not_a_finding():
    doc = "Prose.\n\n```\n[an example](does/not/exist.md)\n```\n"
    found = [target for _n, line in prose_lines(doc) for _l, target in LINK.findall(line)]
    assert found == []
