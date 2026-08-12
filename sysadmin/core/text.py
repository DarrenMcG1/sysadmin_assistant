"""Text normalisation shared across domains.

Lives in ``core`` because both :mod:`sysadmin.files.review` and
:mod:`sysadmin.projects.review` need it and neither may import the other.
Nothing here knows anything about disks or projects — it is string
handling, and the reason it is shared is that the model misbehaves the
same way whatever it is being asked about.

:func:`truncate_at_word` joined them for the same reason from the other
direction: the briefing cuts a next action, the reviews cut a narrative,
and a cut that is invisible is worse than a long line either way.
"""

import re

from estate.text import TRUNCATION_MARKER

__all__ = ["TRUNCATION_MARKER", "strip_markdown", "truncate_at_word"]


def strip_markdown(text: str) -> str:
    """Remove heading, list and emphasis markers the model was told not to emit.

    Instructions are a request, not a constraint. Verified live
    2026-08-06: under an explicit "no markdown, no headings, no numbered
    or bulleted lists" instruction, dria-agent-a-3b produced
    ``### Where the Mess is Coming From``, then ``1. **Node_modules
    directories**:`` on the next attempt. Stripping is deterministic, so
    the stored narrative matches the plain-text format the briefing and
    tray expect whatever the model does.

    Markers are only recognised at the start of a line, so prose keeps
    its hyphens and any inline asterisks.
    """
    cleaned = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        elif stripped.startswith(("- ", "* ", "+ ")):
            stripped = stripped[2:].strip()
        else:
            # "1. ", "2) " — an ordered list the model was asked not to use
            stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        cleaned.append(stripped.replace("**", ""))
    return "\n".join(cleaned).strip()


#: ``TRUNCATION_MARKER`` is imported from ``estate.text`` (top of file) and
#: re-exported for existing importers. The copied constant this replaces
#: *claimed* to match Alfred's and never did — Alfred's carried a leading
#: ``"\n\n"`` (estate-manager ADR-0006). The library owns the bare visible
#: token; the single-space separator in :func:`truncate_at_word` is ours.

#: Below this fraction of the limit, backing up to a word boundary throws
#: away more than it saves — a 180-character limit that surrendered at
#: character 40 because the text held one very long token would report far
#: less than it could have.  A hard cut mid-word is then the honest cut,
#: and the marker still says so.
_MIN_WORD_BOUNDARY_RATIO = 0.5


def truncate_at_word(text: str, limit: int) -> str:
    """Cut ``text`` to roughly ``limit`` characters, visibly.

    Two rules, both learned from ``SNAG-BRIEF-002`` — the briefing served
    ``action[:180]`` as a bare slice, so venture-assistant's next action
    stopped mid-sentence and *nothing said so*.  A truncated instruction
    that looks complete is worse than a long one, and no consumer can
    detect it: 180 characters of prose is indistinguishable from prose
    that happened to be 180 characters.

    1. **Back up to a word boundary**, so the cut lands between words
       rather than inside one.
    2. **Always mark it.** The marker is appended even when the boundary
       search fails, because the mark is the part that carries the
       information.

    The result can exceed ``limit`` by the marker's own length.  That is
    deliberate: a cap that had to swallow the marker to stay under itself
    would be a cap on the wrong thing.
    """
    if len(text) <= limit:
        return text

    cut = text[:limit].rstrip()
    boundary = cut.rfind(" ")
    if boundary >= limit * _MIN_WORD_BOUNDARY_RATIO:
        cut = cut[:boundary]
    # Trailing punctuation left dangling by the cut reads as a typo rather
    # than as a sentence that continues.
    cut = cut.rstrip().rstrip(",;:-—([{\"'")
    return f"{cut.rstrip()} {TRUNCATION_MARKER}"
