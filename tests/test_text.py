"""Tests for the shared text helpers in ``sysadmin/core/text.py``.

``strip_markdown`` is exercised through the reviews that need it
(tests/test_disk_review.py).  ``truncate_at_word`` gets its own file
because it exists to close SNAG-BRIEF-002, whose whole defect was that a
cut left no evidence it had happened — so the marker is the assertion
that matters, not the length.
"""

from sysadmin.core.text import TRUNCATION_MARKER, truncate_at_word


class TestTruncateAtWord:
    def test_short_text_is_returned_untouched(self):
        assert truncate_at_word("Ship the thing.", 180) == "Ship the thing."

    def test_text_at_exactly_the_limit_is_not_marked(self):
        text = "x" * 50
        assert truncate_at_word(text, 50) == text

    def test_a_cut_is_always_marked(self):
        """The marker, not the length, is what SNAG-BRIEF-002 was about.

        180 characters of prose is indistinguishable from prose that
        happened to be 180 characters, so a consumer cannot detect an
        unmarked cut however carefully it reads.
        """
        result = truncate_at_word("word " * 100, 40)
        assert result.endswith(TRUNCATION_MARKER)

    def test_the_cut_lands_between_words(self):
        result = truncate_at_word("alpha beta gamma delta epsilon", 14)
        body = result.removesuffix(TRUNCATION_MARKER).strip()
        assert body == "alpha beta"

    def test_dangling_punctuation_is_dropped(self):
        """A trailing comma before the marker reads as a typo."""
        result = truncate_at_word("counts, sizes, and dates go here", 8)
        assert result == f"counts {TRUNCATION_MARKER}"

    def test_one_enormous_token_is_still_cut_and_still_marked(self):
        """No word boundary to back up to — the hard cut is the honest one.

        Surrendering to the boundary search would report far less than the
        limit allows, which is a second silent loss on top of the first.
        """
        result = truncate_at_word("x" * 500, 20)
        assert result.startswith("x" * 20)
        assert result.endswith(TRUNCATION_MARKER)

    def test_the_snag_brief_002_action_is_marked(self):
        """The live string from the snag: venture-assistant's next action.

        It stopped at ``…GROUP BY 1\\` for`` — mid-sentence, mid-thought,
        with nothing to say so.
        """
        action = (
            "Next up → Review the first scoring sample from the 2026-08-06 "
            "nightly run: check `SELECT lens, count(*), avg(score) FROM "
            "idea_score GROUP BY 1` for lenses that never fire, then decide "
            "whether the rubric or the prompt is at fault."
        )
        result = truncate_at_word(action, 180)

        assert TRUNCATION_MARKER in result
        # Backing up to the boundary must not throw away most of the cap.
        assert len(result) > 150
        body = result.removesuffix(TRUNCATION_MARKER).strip()
        assert not action[len(body) :].startswith(tuple("abcdefghijklmnopqrstuvwxyz"))
