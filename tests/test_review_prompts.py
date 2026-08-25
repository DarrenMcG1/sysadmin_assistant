"""The shared statement of rule 2, driven at things that must break it.

:mod:`tests.review_prompts` is three assertions the three Tier 3 review
test modules now share.  A shared assertion that cannot be seen to fail
is worth less than the three copies it replaced, because a copy at least
had a reader; these tests are here so each of its three rules is
observed refusing something.

They are also where the *divergence* is recorded.  Before
``SNAG-DOCS-004`` the rule was written three times and the copies
disagreed in two places — ``test_disk_review`` and ``test_log_review``
stripped API paths and ``test_health_review`` did not; ``test_health_review``
asserted the instruction boundary was found and the other two did not.
Each disagreement had a right side, so the shared helper is the union.
:class:`TestTheBoundaryIsAsserted` is the half that would otherwise have
been lost by deduplicating onto either sibling.
"""

import pytest

from tests.review_prompts import (
    assert_no_figure_reaches_the_model,
    assert_the_digits_are_in_the_instructions,
    data_half,
)

INSTRUCTIONS = "Write three sections. Hard limit 150 words."


class TestTheBoundaryIsAsserted:
    """Rule 3: a boundary that cannot be found is not a half.

    The two sibling copies were ``prompt.split(instructions)[0]``, which
    returns the **whole prompt** when the instruction block is absent.
    That is not a false green on its own — with no instructions there
    are no instruction digits to exclude, so the digit test would pass
    for a stricter reason — but the helper would be returning something
    other than what its name says, which is ``ports_checked``'s rule one
    directory over: zero-because-clean must not be served as
    zero-because-blind.
    """

    def test_a_prompt_without_its_instructions_is_refused(self):
        with pytest.raises(AssertionError, match="present and separable"):
            data_half("facts only, no instructions", INSTRUCTIONS)

    def test_the_old_form_would_have_returned_the_whole_prompt(self):
        """The behaviour being replaced, pinned so the reason survives."""
        prompt = "facts only, no instructions"
        assert prompt.split(INSTRUCTIONS)[0] == prompt

    def test_the_head_is_returned_verbatim_when_the_boundary_is_found(self):
        assert data_half(f"facts\n{INSTRUCTIONS}", INSTRUCTIONS) == "facts\n"


class TestADigitInTheDataIsRefused:
    """Rule 1, the whole point of the family."""

    def test_a_figure_in_the_data_half_fails_and_names_its_line(self):
        with pytest.raises(AssertionError, match="disk at 78 percent"):
            assert_no_figure_reaches_the_model(
                f"clean line\ndisk at 78 percent\n{INSTRUCTIONS}", INSTRUCTIONS
            )

    def test_the_instruction_half_is_out_of_scope(self):
        """The false half of the two docstrings this closed: the section
        numbers and the word cap are digits and are allowed."""
        assert_no_figure_reaches_the_model(f"clean line\n{INSTRUCTIONS}", INSTRUCTIONS)


class TestAnApiPathMayCarryADigit:
    """Rule 2, which is policy rather than a patch.

    Measured 2026-08-25 against all three live fixtures: exactly one
    data half contains an API path at all and that path is digit-free,
    so the strip is a **no-op today** and is kept for the day a route is
    versioned.  Asserting it therefore needs a path that does not exist
    yet.
    """

    def test_a_versioned_route_is_not_read_as_a_leak(self):
        assert_no_figure_reaches_the_model(
            f"Run POST /api/v2/files/clean/downloads\n{INSTRUCTIONS}", INSTRUCTIONS
        )

    def test_a_digit_beside_a_path_is_still_a_leak(self):
        """The strip must not swallow the rest of the line."""
        with pytest.raises(AssertionError):
            assert_no_figure_reaches_the_model(
                f"Run POST /api/files/clean — 25 GB\n{INSTRUCTIONS}", INSTRUCTIONS
            )


class TestTheInstructionsAreWhereTheDigitsAre:
    def test_digit_free_instructions_are_refused(self):
        with pytest.raises(AssertionError, match="section numbers"):
            assert_the_digits_are_in_the_instructions("Write sections. Be brief.")

    def test_a_real_instruction_block_passes(self):
        assert_the_digits_are_in_the_instructions(INSTRUCTIONS)
