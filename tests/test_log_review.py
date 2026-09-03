"""Tests for the weekly log review — Session 27, Tier 3.

Mirrors ``tests/test_disk_review.py``: the gather is mocked so the pure
banding, prompting and fallback can be driven without a database, and
inference is a ``MagicMock`` throughout — no test in this file touches
the GPU.

The figure-free guard is the one that has cost live debugging twice
(Sessions 23 and 24), so it is tested from both ends here: no digit may
reach the model, *and* the signature — which is the one string this tier
hands over verbatim — must be excluded the moment it carries one.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.config import AgentsConfig, AppConfig, LogAggregatorConfig
from sysadmin.core.text import TRUNCATION_MARKER
from sysadmin.monitor.log_actions import (
    NOISE_MIN_OCCURRENCES,
    SIGNATURE_DETAIL_CHARS,
)
from sysadmin.monitor.log_review import (
    REVIEW_INSTRUCTIONS,
    STORM_OCCURRENCES,
    build_facts_section,
    build_fallback_narrative,
    build_review_prompt,
    confidence_phrase,
    direction_phrase,
    figure_free,
    generate_review,
    occurrence_band,
)
from sysadmin.monitor.log_signature import signature_digest
from sysadmin.monitor.log_trends import RATIO_MIN_COUNT, Confidence
from tests.review_prompts import (
    assert_no_figure_reaches_the_model,
    assert_the_digits_are_in_the_instructions,
)

MOD = "sysadmin.monitor.log_review"


def _config():
    return AppConfig(agents=AgentsConfig(log_aggregator=LogAggregatorConfig()))


def _llm(response):
    client = MagicMock()
    client.generate = AsyncMock(return_value=response)
    return client


#: Shaped on the live payload of 2026-08-18 — 11 recommendations, one of
#: them the mosquitto incident carrying six signatures, and the two
#: kernel Bluetooth rows at 39,885 apiece.
DATA = {
    "period_days": 7,
    "generated_at": "2026-08-18T09:00:00+00:00",
    "window_start": "2026-08-11T09:00:00+00:00",
    "confidence": "medium",
    "truncated": False,
    "declared_noise": 0,
    "actions": {
        "total": 11,
        "by_kind": {"new_signature": 8, "surge": 1, "noise": 2},
        "risk_count": 9,
        "top": [
            {
                "kind": "new_signature",
                "severity": "risk",
                "title": "New incident: mosquitto.service then estate-broker-provision.service",
                "action": "Read the journal around the first sighting.",
                "source": "mosquitto.service",
                "signature": "Main process exited, code=dumped, status=N/ABRT",
                "alert_title": "Log error: mosquitto.service — Main process exited",
                "occurrences": 6,
                "member_count": 6,
                "members": ["Failed with result 'core-dump'."],
            },
            {
                "kind": "surge",
                "severity": "risk",
                "title": "venture-assistant-backend.service fault up 2.6x",
                "action": "Read the journal for this unit.",
                "source": "venture-assistant-backend.service",
                "signature": "Task exception was never retrieved",
                "alert_title": "Log warning: venture-assistant-backend.service",
                "occurrences": 26,
                "member_count": 0,
                "members": [],
            },
            {
                "kind": "noise",
                "severity": "advice",
                "title": "kernel: 39885 occurrences, unchanged",
                "action": "Add the block below to config.yaml, then reload.",
                "source": "kernel",
                "signature": "Bluetooth: hciN: Failed to set up firmware (-N)",
                "alert_title": "Log error: kernel — Bluetooth: hciN",
                "occurrences": 39885,
                "member_count": 0,
                "members": [],
            },
        ],
    },
    "signatures": {
        "distinct": 46,
        "by_change": {"new": 8, "returned": 2, "steady": 36},
        "new": 8,
        "groups_read": 56,
    },
    "sources": [
        {
            "source": "kernel",
            "current_errors": 79771,
            "previous_errors": 66,
            "error_delta": 79705,
            "current_warnings": 0,
            "previous_warnings": 0,
            "warning_delta": 0,
            "new_signatures": 1,
        },
        {
            "source": "sportsanalyser-frontend.service",
            "current_errors": 1,
            "previous_errors": 3,
            "error_delta": -2,
            "current_warnings": 5,
            "previous_warnings": 12,
            "warning_delta": -7,
            "new_signatures": 0,
        },
    ],
    "coverage": {
        "runs_observed": 7006,
        "runs_expected": 20160,
        "runs_truncated": 120,
        "runs_instrumented": 7006,
    },
}


class TestFigureFree:
    """Rule 3: the normalised signature is safe *because* it is normalised.

    Measured 2026-08-18 against the live table: 0 of 46 signatures carry
    a digit, because ``signature()`` maps every digit run to ``N``.  The
    exception is structural rather than statistical — ``_HEX`` rewrites
    a hex literal to ``0xN`` — so the guard is a filter, not a claim
    about this box.
    """

    def test_a_normalised_signature_passes(self):
        assert figure_free("Bluetooth: hciN: Failed to set up firmware (-N)")

    def test_a_hex_signature_is_refused(self):
        """``0xN`` is the one shape normalisation leaves a digit in."""
        assert not figure_free("BAR N: cannot reserve region 0xN")

    def test_an_unnormalised_message_is_refused(self):
        assert not figure_free("Bluetooth: hci0: Failed to set up firmware (-2)")


class TestOccurrenceBands:
    """Two of the three edges are borrowed from constants that already exist."""

    def test_the_thin_edge_is_the_ratio_floor(self):
        assert occurrence_band(RATIO_MIN_COUNT - 1) == "a handful"
        assert occurrence_band(RATIO_MIN_COUNT) == "repeated"

    def test_the_loud_edge_is_the_noise_floor(self):
        assert occurrence_band(NOISE_MIN_OCCURRENCES - 1) == "repeated"
        assert occurrence_band(NOISE_MIN_OCCURRENCES) == "loud"

    def test_the_storm_edge_separates_the_kernel_from_everything_else(self):
        assert occurrence_band(STORM_OCCURRENCES) == "storming"
        assert occurrence_band(39885) == "storming"

    def test_the_edges_are_references_not_copies(self):
        """An AST sweep, because a value test cannot see a copy.

        Written first as ``assert NOISE_MIN_OCCURRENCES in thresholds``
        and falsified in the same sitting: replacing the reference with
        the literal ``100`` keeps that assertion true, because the
        literal *is* the value.  The failure it has to catch is somebody
        raising ``NOISE_MIN_OCCURRENCES`` to 120 while the narrative
        goes on calling 100 loud — and at that moment the two agree
        about nothing and the test agrees with both.

        So this asserts there is no second body rather than that two
        bodies match, which is ``tests/test_autogenerate_config.py``'s
        rule: pinning the copy is what removes it as an option.
        ``STORM_OCCURRENCES`` is a reference too — it is invented, and
        it is invented *once*, in the module that documents why.
        """
        import ast
        from pathlib import Path

        source = Path("sysadmin/monitor/log_review.py").read_text()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.AnnAssign | ast.Assign):
                continue
            targets = (
                [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            )
            if not any(
                isinstance(t, ast.Name) and t.id == "OCCURRENCE_BANDS" for t in targets
            ):
                continue
            assert isinstance(node.value, ast.Tuple)
            for pair in node.value.elts:
                assert isinstance(pair, ast.Tuple)
                threshold = pair.elts[0]
                assert isinstance(threshold, ast.Name), (
                    f"OCCURRENCE_BANDS carries the literal "
                    f"{ast.unparse(threshold)} instead of a reference"
                )
            break
        else:  # pragma: no cover - the assignment must exist
            pytest.fail("OCCURRENCE_BANDS assignment not found")


class TestDirectionIsAsymmetric:
    """Truncation is one-directional, so a rise and a fall are not equals.

    A read that hits its ceiling drops entries.  It can only ever make a
    count too low — so a rise survives an incomplete window and a fall
    does not, because a source that went quiet and a source whose reads
    truncated produce the same smaller number.
    """

    def test_a_rise_is_a_rise_at_every_confidence(self):
        for confidence in (c.value for c in Confidence):
            assert direction_phrase(500, confidence) == "got louder"

    def test_a_fall_is_only_called_a_fall_on_a_complete_window(self):
        assert direction_phrase(-40, Confidence.HIGH.value) == "got quieter"

    def test_a_fall_is_hedged_when_part_of_the_window_went_unread(self):
        for confidence in (Confidence.LOW.value, Confidence.MEDIUM.value):
            phrase = direction_phrase(-40, confidence)
            assert "may be the reading" in phrase
            assert "quieter" not in phrase

    def test_no_movement_needs_no_hedge(self):
        assert direction_phrase(0, Confidence.LOW.value) == "held steady"


class TestPromptIsFigureFree:
    """No digit reaches the prompt **from the data**.

    Session 23 and Session 24 both paid a live debugging session for
    this: handed figures and told not to restate them, dria-agent-a-3b
    restated them and derived a new one.

    The rule and its two exclusions — the instruction block, an API
    path — are stated once in :mod:`tests.review_prompts` rather than
    here, in ``test_disk_review`` and in ``test_health_review``, where
    the three copies had quietly diverged (``SNAG-DOCS-004``).
    """

    def test_no_digits_reach_the_model(self):
        assert_no_figure_reaches_the_model(
            build_review_prompt(DATA), REVIEW_INSTRUCTIONS
        )

    def test_the_instruction_block_is_where_the_digits_are(self):
        """The half the claim above deliberately does not cover: the
        three numbered sections and the word cap this module asks the
        model for."""
        assert_the_digits_are_in_the_instructions(REVIEW_INSTRUCTIONS)

    def test_occurrences_become_bands(self):
        prompt = build_review_prompt(DATA)
        assert "storming" in prompt
        assert "39885" not in prompt

    def test_tier_2_titles_never_reach_the_model(self):
        """"kernel: 39885 occurrences, unchanged" is the leak path."""
        prompt = build_review_prompt(DATA)
        assert "39885" not in prompt
        assert "a long-standing fault nobody has silenced" in prompt

    def test_a_figure_free_signature_is_handed_over_verbatim(self):
        """Rule 3: this is the string the reader will match on."""
        assert "Bluetooth: hciN" in build_review_prompt(DATA)

    def test_a_cut_signature_reaches_the_prompt_without_its_discriminator(self):
        """``SNAG-LOG-013``'s fix stamps a cut signature with eight hex
        characters, and this prompt carries no digit from the data.

        The two facts are settled here rather than left to the general
        digit sweep above, because the general sweep's fixture holds no
        cut signature and would go on passing while the leak shipped.
        Both halves are asserted: the discriminator does **not** arrive,
        and the signature still does — gating on the *rendered* line
        instead of on the input would have satisfied the first half by
        deleting every cut signature from the prompt, which is the
        surface with nothing else to say what the fault was.
        """
        long = (
            "cannot allocate memory for the incoming request because the "
            "pool is exhausted and no further connection may be accepted "
            "until something releases one"
        )
        assert len(long) > SIGNATURE_DETAIL_CHARS
        data = {
            **DATA,
            "actions": {
                **DATA["actions"],
                "top": [{**DATA["actions"]["top"][0], "signature": long}],
            },
        }
        prompt = build_review_prompt(data)
        assert "cannot allocate memory" in prompt
        assert TRUNCATION_MARKER in prompt
        assert signature_digest(long) not in prompt
        assert_no_figure_reaches_the_model(prompt, REVIEW_INSTRUCTIONS)

    def test_a_signature_carrying_a_digit_is_dropped_from_the_prompt(self):
        data = {
            **DATA,
            "actions": {
                **DATA["actions"],
                "top": [
                    {**DATA["actions"]["top"][0], "signature": "cannot reserve 0xN"}
                ],
            },
        }
        prompt = build_review_prompt(data)
        assert "0xN" not in prompt
        # …and the row itself survives, named by its source and kind.
        assert "mosquitto.service" in prompt

    def test_a_long_signature_is_cut_and_the_cut_is_marked(self):
        """SNAG-LOG-008's rows are ~250 characters of raw JSON apiece.

        Found on the live report of 2026-08-24: two of five rows carried
        a whole serialised log record as their signature, which quoted in
        full is most of a bounded prompt.  The cap is
        ``SIGNATURE_DETAIL_CHARS``, borrowed from ``log_actions`` where
        it was chosen against these same rows, and the cut is marked
        because a reader may try to match the signature against
        ``GET /api/logs/actions``.
        """
        long_signature = (
            '{"timestamp": "N-N-N N:N:N,N", "level": "WARNING", '
            '"logger": "sysadmin.core.agent", "message": "alert_raised", '
            '"service": "sysadmin-service", "agent": "log_aggregator"}'
        )
        data = {
            **DATA,
            "actions": {
                **DATA["actions"],
                "top": [{**DATA["actions"]["top"][0], "signature": long_signature}],
            },
        }
        prompt = build_review_prompt(data)
        assert TRUNCATION_MARKER in prompt
        assert '"agent": "log_aggregator"' not in prompt

    def test_the_surge_multiple_never_reaches_the_model(self):
        """"up 2.6x" is a figure the model would happily restate."""
        assert "2.6" not in build_review_prompt(DATA)


class TestPromptStructure:
    """The instructions name two lists, so the prompt must label both.

    Found by a live generation on 2026-08-24, with every fixture green.
    Given "at most three of the listed items" against an unlabelled
    faults list followed by an unlabelled movement list, dria-agent-a-3b
    merged them: it nominated ``alfred-backend.service`` and ``kernel``
    for "look at first", neither of which had a recommendation at all.
    It also appended ``.service`` to ``kernel`` — reproducing in prose
    the exact ``journalctl -u kernel`` error Tier 2 removed from the
    emitted commands, the kernel not being a unit.

    Labelling the two lists and scoping each instruction to one fixed
    both, re-verified live.  What this pins is the join: a header
    renamed without the instruction following it leaves the model told
    to read a list that is not labelled, which fails silently and in
    prose.
    """

    def test_every_list_the_instructions_name_is_labelled_in_the_prompt(self):
        """Checked against the *facts* half, never the whole prompt.

        Written first as ``label in prompt`` and falsified in the same
        sitting: the instructions are appended to the prompt, so that
        assertion is satisfied by the instructions quoting themselves and
        a renamed header slips straight past it.  The band test's defect,
        one class over — an assertion true for a reason that has nothing
        to do with what it is checking.
        """
        facts_half = build_review_prompt(DATA).split(REVIEW_INSTRUCTIONS)[0]
        for label in ("OUTSTANDING FAULTS", "VOLUME CHANGES"):
            assert label in REVIEW_INSTRUCTIONS, f"{label} not referenced"
            assert label in facts_half, f"{label} referenced but never labelled"

    def test_the_service_name_is_given_verbatim_with_no_suffix_invented(self):
        """``kernel`` is a source and not a unit; the prompt must say so exactly."""
        data = {
            **DATA,
            "sources": [{**DATA["sources"][0], "source": "kernel"}],
        }
        prompt = build_review_prompt(data)
        assert "- kernel: " in prompt
        assert "kernel.service" not in prompt


class TestFactsSection:
    """Every real number lives here, computed and prepended deterministically."""

    def test_it_carries_the_counts_the_prompt_was_denied(self):
        facts = build_facts_section(DATA)
        assert "46 distinct fault signatures" in facts
        assert "8 of them first seen" in facts
        assert "39885 occurrences" in facts

    def test_it_names_the_signatures_an_incident_swallowed(self):
        """SNAG-ESTATE-001: a roll-up that cannot name anything is a count."""
        assert "covering 6 signatures" in build_facts_section(DATA)

    def test_confidence_is_stated_in_words_not_left_to_be_inferred(self):
        assert "counts are floors" in build_facts_section(DATA)

    def test_a_truncated_read_says_so(self):
        facts = build_facts_section({**DATA, "truncated": True})
        assert "over a subset" in facts

    def test_nothing_recommended_is_said_rather_than_omitted(self):
        data = {**DATA, "actions": {"total": 0, "by_kind": {}, "risk_count": 0, "top": []}}
        assert "nothing recommended" in build_facts_section(data)


class TestConfidencePhrase:
    def test_low_refuses_to_let_the_window_read_as_quiet(self):
        phrase = confidence_phrase(Confidence.LOW.value)
        assert "should be read as quiet" in phrase

    def test_high_says_the_window_was_read(self):
        assert confidence_phrase(Confidence.HIGH.value) == "The whole period was read."


class TestFallback:
    def test_the_digest_carries_the_facts_and_the_first_actions(self):
        narrative = build_fallback_narrative(DATA)
        assert "without LLM narration" in narrative
        assert "46 distinct fault signatures" in narrative
        assert "Look at first: New incident: mosquitto.service" in narrative

    def test_a_quiet_week_says_so(self):
        data = {**DATA, "actions": {"total": 0, "by_kind": {}, "risk_count": 0, "top": []}}
        assert "Nothing new broke" in build_fallback_narrative(data)


class TestGenerateReview:
    def _session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_llm_narrative_is_prefixed_with_computed_facts(self):
        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=DATA)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            review = await generate_review(
                self._session(), llm_client=_llm("Mosquitto crashed.")
            )

        assert review.llm_used is True
        assert review.narrative.startswith("Window: 7 days")
        assert review.narrative.endswith("Mosquitto crashed.")
        assert review.stats == DATA

    @pytest.mark.asyncio
    async def test_read_transaction_is_committed_before_inference(self):
        """Rule 1: inference outlives idle_in_transaction_session_timeout."""
        session = self._session()
        order: list[str] = []
        session.commit = AsyncMock(side_effect=lambda: order.append("commit"))
        client = MagicMock()

        async def _generate(*a, **k):
            order.append("generate")
            return "prose"

        client.generate = _generate

        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=DATA)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            await generate_review(session, llm_client=client)

        assert order == ["commit", "generate"]

    @pytest.mark.asyncio
    async def test_llm_down_falls_back_to_the_digest(self):
        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=DATA)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            review = await generate_review(self._session(), llm_client=_llm(None))

        assert review.llm_used is False
        assert review.model_used is None
        assert "without LLM narration" in review.narrative

    @pytest.mark.asyncio
    async def test_confidence_is_stored_on_the_row_not_only_in_stats(self):
        """A consumer decides whether to show the review on it."""
        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=DATA)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            review = await generate_review(self._session(), llm_client=_llm("prose"))

        assert review.confidence == "medium"

    @pytest.mark.asyncio
    async def test_nothing_observed_is_no_review_at_all(self):
        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=None)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            assert await generate_review(self._session()) is None
