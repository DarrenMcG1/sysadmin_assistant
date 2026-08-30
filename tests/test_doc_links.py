"""Every relative markdown link in a tracked document resolves.

The detector outlives its finding — ``FROZEN_TABLES``' rule, for the
seventh time here. estate-manager's message ``25be77ba`` reported 24
inward links resolving to nothing, all of them citing
``sysadmin/services``, ``sysadmin/agents`` or ``sysadmin/routers``, which
``512af01`` deleted on 2026-08-08. They were broken for **22 days** and
nothing on this box could have said so: the estate refused the check
under its ADR-0073 (the audit may falsify only a claim the *estate*
makes, and how this repository writes links is a claim it makes
nowhere), which is exactly what leaves it here.

Three rules, two of them the opposite of the obvious implementation:

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


def broken_links():
    """Every tracked relative link whose target file does not exist."""
    for path in tracked_markdown():
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
                if not (path.parent / path_part).resolve().exists():
                    yield f"{path.relative_to(REPO)}:{lineno} -> {target}"


def test_every_relative_link_in_a_tracked_document_resolves():
    broken = sorted(broken_links())
    assert not broken, "broken relative markdown links:\n  " + "\n  ".join(broken)


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
