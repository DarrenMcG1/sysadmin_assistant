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

from estate.text import TRUNCATION_MARKER, strip_markdown, truncate_at_word

__all__ = [
    "TRUNCATION_MARKER",
    "strip_markdown",
    "trim_to_words",
    "truncate_at_word",
    "word_count",
]

# Both functions moved to ``estate.text`` in estate-manager Session 4
# (its ADR-0008): the briefing rows that cut with them moved to the
# estate while the log signatures here kept using them — mechanism
# needed on both sides of a seam lives in the library, and a copy held
# here would drift exactly the way the marker itself once did
# (estate-manager ADR-0006). This module re-exports so existing
# importers keep working; the implementations are the library's.


# A sentence ends at terminal punctuation followed by whitespace — and
# never at a bare line break, because strip_markdown unwraps the model's
# headings into lines of their own ("Watch"), and a cut there publishes
# a section's title with nothing under it (found on the 2026-09-28
# review's prose, the first live specimen this was driven at).
_SENTENCE_END = re.compile(r"[.!?](?=\s)")
_WORD = re.compile(r"\S+")


def word_count(text: str) -> int:
    """Whitespace-separated words — the unit a review's limit is stated in."""
    return len(text.split())


def trim_to_words(text: str, limit: int) -> str:
    """Cut ``text`` to at most ``limit`` words at a sentence boundary, visibly.

    The review narratives' backstop.  A model asked for 150 words writes
    anywhere from 90 to 330 (measured 2026-09-29), and neither the
    instruction nor a second "shorten this" pass makes the limit hold, so
    something deterministic has to.  :func:`truncate_at_word` is the
    wrong cut for prose: it counts characters and lands mid-sentence,
    which the task that asked for this called worse than running long.

    So the cut backs up to the last sentence end inside the limit, and —
    ``truncate_at_word``'s second rule — is always marked, because a
    review that stops after its second section and says nothing reads as
    a review that had nothing to watch.  When no sentence ends in the
    second half of the budget (one run-on paragraph), the cut falls at
    the word limit instead: giving up most of the budget to keep a full
    stop would trade the content for the punctuation.

    The result can exceed ``limit`` by the marker's words, as
    ``truncate_at_word``'s can exceed its characters.
    """
    words = list(_WORD.finditer(text))
    if len(words) <= limit:
        return text

    word_end = words[limit - 1].end()
    half_way = words[limit // 2].start()
    boundaries = [m.end() for m in _SENTENCE_END.finditer(text, 0, word_end + 1)]
    cut = boundaries[-1] if boundaries and boundaries[-1] >= half_way else word_end
    return f"{text[:cut].rstrip()} {TRUNCATION_MARKER}"
