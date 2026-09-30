"""The word limit a review narrative is held to, by code rather than request.

Two of the three LLM-narrated weekly reviews break the limit their own
prompt states.  Measured by splitting the stored ``narrative`` at the
blank line after the deterministic facts block and counting what the
model wrote: the disk review's prose ran 97–329 words with six of seven
over 150 (2026-09-29), and the log review's ran 190, 195, 197 and 211,
all four over (2026-09-30).  The health review's two ran 65 and 74 and
is not held here, because nothing it has stored needed holding.

The mechanism was built for the disk review in Session 293 and moved
here when the log review adopted it, with the two things that differed
made parameters: the second pass's prompt, which names the review and
its three sections, and the prefix of the log events, so a week that
needed the trim is still attributable to one review in ``log_entries``.
Everything else is one rule, stated once:

* :data:`NARRATIVE_WORD_LIMIT` is what every first prompt asks for, so
  the instruction and the code cannot disagree.
* :data:`CONDENSE_WORD_TARGET` is what the second pass asks for — the
  margin, because even a tighter ask misses sometimes.
* :func:`~sysadmin.core.text.trim_to_words` is the only step that
  guarantees the limit, and its cut is always marked.
"""

import logging
from typing import Any

from sysadmin.core.text import strip_markdown, trim_to_words, word_count

logger = logging.getLogger(__name__)

#: The narrative's word budget — the model's prose alone, not the facts
#: block prepended to it, which is deterministic and bounded by the data.
NARRATIVE_WORD_LIMIT = 150

# The second pass, asked only when the first ran over.  The limit above
# is a request, and dria-agent-a-3b keeps it about half the time on the
# disk review and never on the log review.  Asking this pass for 120
# rather than 150 is the margin: six condense drives of two long disk
# drafts returned 49–126 words five times and 206 once (2026-09-29), so
# even a tighter ask misses sometimes, and :func:`hold_to_word_limit`
# trims whatever it cannot bring in.
CONDENSE_WORD_TARGET = 120


def condense_instructions(review: str, parts: str) -> str:
    """The second pass's instruction for one review.

    ``review`` names the text ("the disk review") and ``parts`` its three
    sections in order, in words, because a condense that drops a section
    is the one outcome a cut would have avoided.  The rest — no new
    content, no number, no markdown — is the same for every review, so it
    is written here once.
    """
    return (
        f"Shorten {review} below to at most {CONDENSE_WORD_TARGET} words. "
        f"Keep its three parts in order: {parts}. Do not add anything that "
        "is not already in it, and do not state any number. Plain prose "
        "only: no markdown, no headings, no lists."
    )


def build_condense_prompt(instructions: str, prose: str) -> str:
    """The second pass's prompt: the first pass's prose, and a shorter ask.

    It stays figure-free for the same reason each first prompt is: the
    only data it carries is prose the model wrote from a prompt with no
    figures in it, so there is nothing here for it to restate or derive.
    """
    return f"{instructions}\n\nReview:\n{prose}"


async def hold_to_word_limit(
    client: Any,
    prose: str,
    *,
    instructions: str,
    system: str,
    event_prefix: str,
    gpu_lease_held: bool = False,
) -> str:
    """Bring the model's prose within :data:`NARRATIVE_WORD_LIMIT` words.

    ``prose`` is the first pass with its markdown already stripped, so a
    heading's ``###`` is not counted as a word.  ``instructions`` is the
    review's :func:`condense_instructions`, ``system`` its system prompt,
    and ``event_prefix`` names it in the log (``disk_review`` →
    ``disk_review_narrative_condensed``).

    Three steps, each taken only when the one before left it over:

    1. **Keep it as written** — about half the disk review's first passes
       already fit, and none of the log review's have.
    2. **Ask once more, shorter.**  A condensed review keeps all three
       sections, which a cut cannot.
    3. **Trim at a sentence boundary, visibly**
       (:func:`~sysadmin.core.text.trim_to_words`) — the only step that
       guarantees the limit.  It trims the condensed text when there is
       one, since that carries all three sections in fewer words, and the
       original when the second pass came back empty or not at all.

    A second pass that fails is not a failed review: the first pass's
    prose is already in hand, so every outcome here still stores
    ``llm_used=True`` with the model's own words.  Each step past the
    first is logged with both counts, so a week that needed the trim is
    visible in ``log_entries`` rather than only as a marker in the text.

    **Which step does the work depends on the invocation**, measured live
    2026-09-29 on the disk review.  The Monday jobs hold a GPU lease and
    skip the gate, and there the condense pass did all of it: six of
    eight first passes ran 161–257 words and all six came back at 60–106,
    none trimmed.  The ``POST …/review/generate`` routes hold no lease, so
    the second call reads the busy counter — and reads *this service's
    own first pass* still on it: seven of seven calls made straight after
    an inference were refused.  On a route the trim is therefore the
    usual step, not the rare one (``SNAG-GPU-007``).
    """
    words = word_count(prose)
    if words <= NARRATIVE_WORD_LIMIT:
        return prose

    condensed = await client.generate(
        build_condense_prompt(instructions, prose),
        system=system,
        gpu_lease_held=gpu_lease_held,
    )
    condensed = strip_markdown(condensed).strip() if condensed else ""
    if condensed and word_count(condensed) <= NARRATIVE_WORD_LIMIT:
        logger.info(
            f"{event_prefix}_narrative_condensed",
            extra={"words_before": words, "words_after": word_count(condensed)},
        )
        return condensed

    candidate = condensed or prose
    trimmed = trim_to_words(candidate, NARRATIVE_WORD_LIMIT)
    logger.warning(
        f"{event_prefix}_narrative_trimmed",
        extra={
            "words_before": words,
            "words_condensed": word_count(condensed) if condensed else None,
            "words_after": word_count(trimmed),
        },
    )
    return trimmed
