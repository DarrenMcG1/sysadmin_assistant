"""The word-limit hold shared by the disk and log reviews.

Moved from ``tests/test_disk_review.py`` with the mechanism, on
2026-09-30, when the log review adopted it.  Each review's own test file
keeps what is particular to it: that its first prompt states the limit
this module holds, that its condense prompt names its own three
sections, and that ``generate_review`` stores the held prose.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.core.text import TRUNCATION_MARKER, word_count
from sysadmin.core.word_limit import (
    CONDENSE_WORD_TARGET,
    NARRATIVE_WORD_LIMIT,
    build_condense_prompt,
    condense_instructions,
    hold_to_word_limit,
)

# Sentences of ten words each, so a count is a sentence count times ten.
SENTENCE = "Stale downloads keep growing and should be cleared this week."

INSTRUCTIONS = condense_instructions("the test review", "one, two, and three")
SYSTEM = "You are a test."


def _prose(sentences: int) -> str:
    return " ".join([SENTENCE] * sentences)


def _llm_sequence(*responses):
    """A client whose successive ``generate`` calls return ``responses``."""
    client = MagicMock()
    client.generate = AsyncMock(side_effect=list(responses))
    return client


async def _hold(client, prose: str, **kwargs) -> str:
    return await hold_to_word_limit(
        client,
        prose,
        instructions=INSTRUCTIONS,
        system=SYSTEM,
        event_prefix="test_review",
        **kwargs,
    )


class TestHoldToWordLimit:
    """The limit holds whatever the model does with the instruction.

    Measured 2026-09-29 on dria-agent-a-3b: the disk review's first pass
    ran 92–289 words over six drives of one prompt (two over 150), and a
    condense pass brought five of six long outputs in and one out at 206
    — so neither the instruction nor the second pass is the guarantee,
    and only the trim is.
    """

    @pytest.mark.asyncio
    async def test_prose_within_the_limit_costs_no_second_pass(self):
        client = _llm_sequence()
        prose = _prose(15)
        assert word_count(prose) == NARRATIVE_WORD_LIMIT

        assert await _hold(client, prose) == prose
        client.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_long_prose_is_condensed_by_a_second_pass(self):
        condensed = _prose(8)
        client = _llm_sequence(condensed)

        assert await _hold(client, _prose(28)) == condensed
        client.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_the_second_pass_is_handed_the_first_pass_prose(self):
        long_prose = _prose(28)
        client = _llm_sequence(_prose(8))

        await _hold(client, long_prose, gpu_lease_held=True)

        (prompt,), kwargs = client.generate.await_args
        assert prompt == build_condense_prompt(INSTRUCTIONS, long_prose)
        assert prompt.startswith(INSTRUCTIONS)
        assert prompt.endswith(long_prose)
        assert kwargs["system"] == SYSTEM
        assert kwargs["gpu_lease_held"] is True

    @pytest.mark.asyncio
    async def test_a_condensed_review_still_over_is_trimmed_visibly(self):
        """The 206-word condense of 2026-09-29: the pass ran and missed."""
        client = _llm_sequence(_prose(21))

        result = await _hold(client, _prose(28))

        assert result.endswith(TRUNCATION_MARKER)
        body = result.removesuffix(TRUNCATION_MARKER).rstrip()
        assert word_count(body) == NARRATIVE_WORD_LIMIT
        assert body.endswith(SENTENCE)

    @pytest.mark.asyncio
    async def test_a_second_pass_that_fails_trims_the_first(self):
        """``None`` is the client's unavailable answer — the review keeps
        the prose it already has rather than falling back to the digest."""
        long_prose = "First pass. " + _prose(20)
        client = _llm_sequence(None)

        result = await _hold(client, long_prose)

        assert result.startswith("First pass.")
        assert result.endswith(TRUNCATION_MARKER)

    @pytest.mark.asyncio
    async def test_an_empty_second_pass_is_not_a_short_review(self):
        """Zero words is within any limit, and is not a review."""
        client = _llm_sequence("   ")

        result = await _hold(client, "First pass. " + _prose(20))

        assert result.startswith("First pass.")

    @pytest.mark.asyncio
    async def test_markdown_in_the_second_pass_is_stripped(self):
        client = _llm_sequence("### Watch\n- " + SENTENCE)

        assert await _hold(client, _prose(28)) == f"Watch\n{SENTENCE}"


class TestTheLogEventsNameTheirReview:
    """Two reviews share this code, so the event says which one ran over.

    The events were ``disk_review_…`` literals before the move, and a
    shared literal would have left a trimmed week unattributable in
    ``log_entries``.
    """

    @pytest.mark.asyncio
    async def test_a_condense_is_logged_under_the_callers_prefix(self, caplog):
        with caplog.at_level(logging.INFO, logger="sysadmin.core.word_limit"):
            await _hold(_llm_sequence(_prose(8)), _prose(28))

        assert [r.getMessage() for r in caplog.records] == [
            "test_review_narrative_condensed"
        ]

    @pytest.mark.asyncio
    async def test_a_trim_is_logged_under_the_callers_prefix(self, caplog):
        with caplog.at_level(logging.INFO, logger="sysadmin.core.word_limit"):
            await _hold(_llm_sequence(None), _prose(28))

        (record,) = caplog.records
        assert record.getMessage() == "test_review_narrative_trimmed"
        assert record.levelno == logging.WARNING


class TestCondenseInstructions:
    def test_the_second_pass_asks_for_less_than_the_limit(self):
        """The margin: an ask of exactly the limit lands over it more often."""
        assert CONDENSE_WORD_TARGET < NARRATIVE_WORD_LIMIT
        assert f"at most {CONDENSE_WORD_TARGET} words" in INSTRUCTIONS

    def test_the_review_and_its_parts_are_named(self):
        assert INSTRUCTIONS.startswith("Shorten the test review below")
        assert "Keep its three parts in order: one, two, and three." in INSTRUCTIONS
