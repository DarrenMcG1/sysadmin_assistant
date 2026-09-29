"""Tests for the shared text helpers in ``sysadmin/core/text.py``.

``strip_markdown`` is exercised through the reviews that need it
(tests/test_disk_review.py).  ``truncate_at_word`` gets its own file
because it exists to close SNAG-BRIEF-002, whose whole defect was that a
cut left no evidence it had happened — so the marker is the assertion
that matters, not the length.
"""

from sysadmin.core.text import (
    TRUNCATION_MARKER,
    trim_to_words,
    truncate_at_word,
    word_count,
)

# The model's prose from the 2026-09-28 disk review, verbatim from
# ``disk_reviews`` (the part after the facts block): 171 words against a
# limit of 150, with markdown already stripped.  The first live specimen
# trim_to_words was driven at, and the one that refuted counting a bare
# line break as a sentence end — the cut then kept the "Watch" heading
# with nothing under it.
SPECIMEN_2026_09_28 = """Where the Mess is Coming From

The disk occupation has been increasing, particularly in the following categories:

Rebuildable Dependency Directories:
Node modules and virtual environments are large and regenerate.
Removing these directories would free significant space.

Stale Downloads:
Downloads in the `~/Downloads` directory have grown significantly.
Cleaning these files could free substantial space.

Files Outside Their Category Folders:
Files are not organized in their respective directories.
Organizing these files could free up space.

Clear First

The first three items to address are:

Rebuildable Dependency Directories:
Node modules and virtual environments (`node_modules` and `.venv`) are very large.
Deleting these directories would free space and save disk space.

Stale Downloads:
Downloads in `~/Downloads` have grown significantly.
Cleaning these downloads could free up significant space.

Files Outside Their Category Folders:
Files are not organized in their respective directories.
Organizing these files could free up space.

Watch

Currently, there is no urgent item that needs immediate attention. However, the trend in rebuildable dependency directories and stale downloads should be monitored as they continue to grow."""  # noqa: E501 — verbatim


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


class TestTrimToWords:
    """The backstop that makes a review narrative's word limit hold.

    Like :func:`truncate_at_word` the marker is an assertion in its own
    right: a review cut after its second section reads, unmarked, as one
    that had nothing to watch.
    """

    def test_prose_within_the_limit_is_returned_untouched(self):
        text = "Mess is in Downloads.\nClear it first."
        assert trim_to_words(text, 7) == text

    def test_the_cut_lands_after_the_last_sentence_that_fits(self):
        text = "One two three. Four five six. Seven eight nine."
        assert trim_to_words(text, 7) == (
            f"One two three. Four five six. {TRUNCATION_MARKER}"
        )

    def test_a_cut_is_always_marked(self):
        assert trim_to_words("word " * 200, 150).endswith(TRUNCATION_MARKER)

    def test_a_run_on_is_cut_at_the_limit_rather_than_giving_up_the_budget(self):
        """The only full stop is in the first half, so keeping it would
        throw away most of the words the limit allows."""
        text = "Short. " + " ".join(["word"] * 40)
        result = trim_to_words(text, 20)
        assert word_count(result.removesuffix(TRUNCATION_MARKER)) == 20

    def test_a_heading_line_is_not_a_sentence_end(self):
        text = "Clear the downloads first.\nWatch\nNothing is trending badly."
        assert trim_to_words(text, 5) == (
            f"Clear the downloads first. {TRUNCATION_MARKER}"
        )

    def test_line_breaks_before_the_cut_survive(self):
        text = "First section here.\nSecond section here.\nThird section here."
        assert trim_to_words(text, 6) == (
            f"First section here.\nSecond section here. {TRUNCATION_MARKER}"
        )

    def test_the_live_specimen_comes_in_under_the_limit(self):
        assert word_count(SPECIMEN_2026_09_28) == 171
        result = trim_to_words(SPECIMEN_2026_09_28, 150)
        body = result.removesuffix(TRUNCATION_MARKER).rstrip()
        assert word_count(body) <= 150
        assert body.endswith("Organizing these files could free up space.")
        assert result.endswith(TRUNCATION_MARKER)
