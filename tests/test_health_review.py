"""Tests for the weekly system health review — Session 25, Tier 3.

Mirrors ``tests/test_log_review.py``: the gather is mocked so the pure
banding, phrasing and fallback can be driven without a database, and
inference is a ``MagicMock`` throughout — no test in this file touches
the GPU.

Three of these pin defects the **live run** found and no fixture would
have, which is the reason this file was written after driving the module
against the real tables rather than before:

* the prompt named only ``unreliable``/``failing`` services and so
  dropped two degraded ones with real outages the instant a third went
  unreliable (:class:`TestFlappiest`);
* handed "The monitor was down for much of this period", the model
  published "The machine was down for much of the week" — the inversion
  the rule exists to prevent (:class:`TestConfidencePhrase`);
* the model opened with a conversational preamble that would have
  reached the briefing verbatim (:class:`TestPromptStructure`).

And one pins the claim **all three** Tier 3 modules make, in the narrow
form that is true of all three (:class:`TestPromptIsFigureFree`).  The
rule itself is stated once, in :mod:`tests.review_prompts`; each module
asserts its own prompt against it.
"""

import copy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.config import (
    AgentsConfig,
    AppConfig,
    ServiceActionsConfig,
    SysAdminAgentConfig,
)
from sysadmin.monitor.health_review import (
    COVERAGE_AGENT,
    NARRATED_METRICS,
    REVIEW_INSTRUCTIONS,
    STEADY_FRACTION,
    build_facts_section,
    build_fallback_narrative,
    build_review_prompt,
    confidence_phrase,
    coverage_confidence,
    direction_phrase,
    generate_review,
    grade_phrase,
    movement_phrase,
)
from sysadmin.monitor.reliability import LOW_COVERAGE_FRACTION
from tests.review_prompts import (
    assert_no_figure_reaches_the_model,
    assert_the_digits_are_in_the_instructions,
)

MOD = "sysadmin.monitor.health_review"


def _config():
    return AppConfig(agents=AgentsConfig(sysadmin=SysAdminAgentConfig()))


def _llm(response):
    client = MagicMock()
    client.generate = AsyncMock(return_value=response)
    return client


#: Shaped on the live payload of 2026-08-25: 30 services scored, mean
#: 98.2, ``venture-chat`` unreliable across three outage episodes,
#: 17 distinct alert titles against 39, and the two comparison windows
#: observed at 17.01 % and 96.33 % of expected runs.
DATA = {
    "period_days": 7,
    "generated_at": "2026-08-25T11:00:00+00:00",
    "window_start": "2026-08-18T11:00:00+00:00",
    "previous_start": "2026-08-11T11:00:00+00:00",
    "confidence": "low",
    "comparable": False,
    "coverage": {
        "agent": "sysadmin",
        "runs_observed": 343,
        "previous_runs_observed": 1942,
        "runs_expected": 2016,
        "fraction": 0.1701,
        "previous_fraction": 0.9633,
        "percent": 17.01,
        "previous_percent": 96.33,
        "comparable": False,
    },
    "services": {
        "summary": {
            "services_scored": 30,
            "reliable": 27,
            "degraded": 2,
            "unreliable": 1,
            "failing": 0,
            "muted": 3,
            "low_confidence": 30,
            "mean_score": 98.2,
        },
        "flappiest": [
            {
                "service": "venture-chat",
                "episodes": 3,
                "score": 69,
                "grade": "unreliable",
                "uptime_percent": 84.38,
                "longest_outage_minutes": 205.0,
                "confidence": "low",
            },
            {
                "service": "searxng",
                "episodes": 2,
                "score": 89,
                "grade": "degraded",
                "uptime_percent": 99.4,
                "longest_outage_minutes": 5.0,
                "confidence": "low",
            },
            {
                "service": "alfred-frontend",
                "episodes": 1,
                "score": 90,
                "grade": "degraded",
                "uptime_percent": 94.59,
                "longest_outage_minutes": 85.0,
                "confidence": "low",
            },
        ],
        "recommendations_total": 4,
        "recoverable_points": 37,
        "suppressed_by_confidence": 0,
        "muted_skipped": 3,
        "top": [
            {
                "kind": "outage",
                "severity": "advice",
                "service": "venture-chat",
                "title": "venture-chat: 84.38% uptime this window",
                "action": "Find out why venture-chat is unavailable.",
                "recoverable_points": 16,
                "grade": "unreliable",
                "confidence": "low",
                "evidence": "event",
            }
        ],
    },
    "alerts": {
        "distinct_titles": 17,
        "previous_distinct_titles": 39,
        "title_delta": -22,
        "rows": 24,
        "previous_rows": 59650,
        "by_severity": {"warning": 10, "critical": 6, "info": 1},
        "new_titles": ["Critical disk usage on /"],
        "cleared_titles": ["Log error: kernel"],
    },
    "anomalies": {
        "count": 1,
        "previous_count": 3,
        "listed": 1,
        "items": [
            {
                "title": "Unusual RAM usage",
                "resource": "ram",
                "direction": "below",
                "z_score": -3.29,
                "value": 12.4,
                "mean": 18.1,
                "at": "2026-08-24T06:58:00+00:00",
            }
        ],
    },
    "resources": {
        "metrics": [
            {
                "metric": "cpu_percent",
                "label": "CPU",
                "current_mean": 4.62,
                "previous_mean": 5.66,
                "samples": 145,
                "previous_samples": 188,
            },
            {
                "metric": "ram_percent",
                "label": "RAM",
                "current_mean": 16.72,
                "previous_mean": 15.2,
                "samples": 145,
                "previous_samples": 188,
            },
            {
                "metric": "swap_percent",
                "label": "swap",
                "current_mean": 0.0,
                "previous_mean": 0.0,
                "samples": 145,
                "previous_samples": 188,
            },
            {
                "metric": "load_avg_15m",
                "label": "load",
                "current_mean": 1.68,
                "previous_mean": 1.99,
                "samples": 145,
                "previous_samples": 188,
            },
        ],
        "samples": 333,
        "disk_evidence": {
            "mount": "/",
            "current_percent": 78.1,
            "baseline_percent": 77.3,
            "samples": 145,
            "narrated_by": "GET /api/files/review",
        },
    },
}


def _data(**overrides):
    """A copy of :data:`DATA` with top-level keys replaced."""
    return {**DATA, **overrides}


def _data_alerts(**overrides):
    return _data(alerts={**DATA["alerts"], **overrides})


# ── Rule 3: the currency is distinct titles ──────────────────────────


class TestTheCurrencyIsDistinctTitles:
    """One row per failed check is not one row per incident.

    Measured on the live table 2026-08-25 across the two comparison
    windows: **24 rows against 59,650**, of which **59,200 shared one
    title**.  The same windows hold 17 distinct titles against 39.  A
    delta computed from rows says the machine improved 2,485-fold; a
    delta computed from titles says it raised rather fewer distinct
    faults, which is the true and readable statement.
    """

    def test_the_prompt_sentence_is_written_from_titles_not_rows(self):
        """Falsified by phrasing ``rows``: a 2,485x fall reads the same
        as a 2.3x one through :func:`direction_phrase`, so the assertion
        is on the *number that was used*, not on the wording."""
        # Titles fell (-22) while rows also fell.  Flip only the titles:
        # if the module were reading rows, the sentence would not move.
        rose = _data_alerts(distinct_titles=50, previous_distinct_titles=39, title_delta=11)
        assert "raised more distinct faults" in build_review_prompt(rose)
        # Rows are unchanged between the two payloads and still say
        # "fell", so a rows-reading implementation cannot pass both.
        assert rose["alerts"]["rows"] < rose["alerts"]["previous_rows"]

    def test_rows_are_recorded_as_evidence_and_never_phrased(self):
        prompt = build_review_prompt(DATA)
        assert "59650" not in prompt and "59,650" not in prompt
        # …but the facts section, which is deterministic and not the
        # model's, names both so a future reader can tell a week with
        # more faults from a week with one loud one.
        facts = build_facts_section(DATA)
        assert "24 and 59650 raw alert rows" in facts
        assert "17 this period against 39 last" in facts


# ── Rule 4: the refusal is asymmetric ────────────────────────────────


class TestDirectionIsAsymmetric:
    """A rise survives an unwatched window; a fall does not.

    ``log_review.direction_phrase``'s argument against a different
    mechanism.  Monitor downtime is one-directional in exactly the way
    read truncation is: it can hide alerts that were never recorded and
    can never invent one.
    """

    def test_a_rise_is_trustworthy_however_unequal_the_windows(self):
        assert direction_phrase(5, comparable=False) == "raised more distinct faults"
        assert direction_phrase(5, comparable=True) == "raised more distinct faults"

    def test_a_fall_is_stated_plainly_when_both_windows_were_watched(self):
        assert direction_phrase(-5, comparable=True) == "raised fewer distinct faults"

    def test_a_fall_is_refused_when_the_windows_were_not_watched_equally(self):
        """Falsified by making the phrase symmetric — this is the only
        one of the four that changes, which is what 'asymmetric' means."""
        phrase = direction_phrase(-5, comparable=False)
        assert "may be the watching rather than the machine" in phrase

    def test_no_change_is_no_change_either_way(self):
        assert direction_phrase(0, comparable=False) == direction_phrase(0, comparable=True)


class TestComparable:
    """Both windows must clear the bar, not just this one.

    The previous window is the *complete* one on this box, so a one-sided
    check would report poor coverage and still let every delta through
    unqualified.
    """

    def test_a_fall_survives_the_refusal_only_when_both_windows_are_good(self):
        good = _data(comparable=True, confidence="high")
        assert "raised fewer distinct faults." in build_review_prompt(good)
        assert "may be the watching" not in build_review_prompt(good)

    def test_confidence_reuses_the_scorers_own_threshold(self):
        """Never a second copy of 0.5 — imported, so the two cannot drift.

        Written against the constant rather than the literal on purpose:
        editing ``LOW_COVERAGE_FRACTION`` must move this test with it, and
        a hardcoded 0.5 here would let a review call a window trustworthy
        while every score inside it says the opposite.
        """
        assert coverage_confidence(LOW_COVERAGE_FRACTION) == "high"
        assert coverage_confidence(LOW_COVERAGE_FRACTION - 0.0001) == "low"
        assert coverage_confidence(1.0) == "high"
        assert coverage_confidence(0.0) == "low"


class TestConfidencePhrase:
    """The subject of the sentence is the monitor, and it is spelt out.

    Handed "The monitor was down for much of this period", the live
    dria-agent-a-3b generation of 2026-08-25 opened with **"The machine
    was down for much of the week"** — the exact inversion this rule
    exists to prevent, on a review whose other sections describe genuine
    service outages.  Naming the *monitoring service* and then denying
    the inference in the next clause is what stopped it.
    """

    def test_the_low_phrase_names_the_monitoring_service_not_the_machine(self):
        phrase = confidence_phrase("low", comparable=False)
        assert "monitoring service" in phrase
        assert "says nothing about how the machine behaved" in phrase

    def test_the_only_claim_about_the_machine_is_a_denial(self):
        """Repaired after it passed against the code it was meant to break.

        As first written this asserted ``"machine was down" not in
        phrase`` — a string absent from the pre-fix wording *and* the
        fixed one, so it could never fail either way.  It was testing the
        model's output through a fixture that never contains it, which is
        the ``waived``/cadence shape Session 78 found twice in eight.

        The property that actually distinguishes the two wordings is the
        **denial**: the old phrase named one subject and said nothing
        about the other, leaving the model free to substitute it.  So the
        machine must be mentioned, and every clause mentioning it must be
        denying rather than asserting.
        """
        import re

        phrase = confidence_phrase("low", comparable=False)
        #: The two shapes a clause naming the machine is allowed to
        #: take.  Both deny; neither asserts.  The second belongs to the
        #: ``comparable`` half, which is a separate claim and was what
        #: caught the first version of this assertion being too narrow.
        denials = ("says nothing about", "describes the watching")

        clauses = [c for c in re.split(r"[.]", phrase) if "machine" in c]
        assert clauses, "the inference must be denied, not merely avoided"
        assert all(any(d in c for d in denials) for c in clauses), clauses
        assert any("says nothing about" in c for c in clauses), clauses

    def test_the_two_claims_are_separable(self):
        """Coverage of *this* window and parity *between* windows fail
        separately, so they are two sentences rather than one."""
        both_bad = confidence_phrase("low", comparable=False)
        only_thin = confidence_phrase("low", comparable=True)
        only_unequal = confidence_phrase("high", comparable=False)
        assert "not watched equally closely" in both_bad
        assert "not watched equally closely" not in only_thin
        assert "not watched equally closely" in only_unequal
        assert "record is complete" in only_unequal


# ── Rule 5: disk belongs to the disk review ──────────────────────────


class TestDiskIsDeferred:
    """One weekly narrative per fact, and disk already has one.

    ``GET /api/files/review`` writes a paragraph about occupancy, its
    direction and its projected threshold crossings, into the *same*
    06:00 briefing.
    """

    def test_no_disk_metric_is_narrated(self):
        assert not any("disk" in key for key, _ in NARRATED_METRICS)

    def test_the_prompt_states_the_omission_rather_than_hiding_it(self):
        prompt = build_review_prompt(DATA)
        assert "disk is covered by a separate review" in prompt
        assert "do not discuss disk space" in REVIEW_INSTRUCTIONS.lower()

    def test_the_prompt_carries_no_disk_figure(self):
        prompt = build_review_prompt(DATA)
        assert "78.1" not in prompt and "77.3" not in prompt

    def test_the_evidence_is_kept_so_the_review_stays_auditable(self):
        """Refusing a *sentence* is not refusing the data — a reader
        auditing ``stats`` must be able to see the mount this review
        deliberately did not discuss."""
        evidence = DATA["resources"]["disk_evidence"]
        assert evidence["current_percent"] == 78.1
        assert evidence["narrated_by"] == "GET /api/files/review"

    def test_the_fallback_names_the_review_that_does_cover_disk(self):
        """An omission a reader has to infer is one they will not infer:
        without this line, a reader concludes the review looked at the
        disk and found nothing worth saying."""
        narrative = build_fallback_narrative(DATA)
        assert "GET /api/files/review" in narrative
        assert "not covered here" in narrative


# ── Rule 2: no figure reaches the model from the data ────────────────


class TestPromptIsFigureFree:
    """The precise claim, asserted through the shared statement of it.

    Session 79 stated the narrow form here and drove the two siblings
    from this module, because their docstrings claimed something wider
    than they held.  Both are reworded now (``SNAG-DOCS-004``), so each
    module asserts its own prompt and the rule itself lives once, in
    :mod:`tests.review_prompts` — which also records why the instruction
    half is out of scope and why an API path may carry a digit.
    """

    def test_no_digit_reaches_the_data_half(self):
        assert_no_figure_reaches_the_model(
            build_review_prompt(DATA), REVIEW_INSTRUCTIONS
        )

    def test_the_instruction_block_is_where_the_digits_are(self):
        assert_the_digits_are_in_the_instructions(REVIEW_INSTRUCTIONS)

    def test_a_service_name_is_not_filtered_the_way_a_signature_is(self):
        """A name is not a measurement.

        ``log_review`` drops a signature carrying a digit, because a
        signature is a rendering of a log line.  A service called
        ``postgres15`` is a *name*, and a gate that cannot tell the two
        apart would delete the service from the review entirely — a worse
        outcome than the model reading a digit that says nothing about
        the week.  Empty population on this box (0 of 30), so this
        asserts the policy rather than an observation.
        """
        named = _data(
            services={
                **DATA["services"],
                "flappiest": [
                    {**DATA["services"]["flappiest"][0], "service": "postgres15"}
                ],
            }
        )
        assert "postgres15" in build_review_prompt(named)


# ── The flappiest list ───────────────────────────────────────────────


class TestFlappiest:
    def test_every_service_that_dropped_out_is_named(self):
        """The defect the live run found and no fixture would have.

        The first draft listed only ``unreliable``/``failing`` services
        and fell back to the whole list when there were none.  Driven
        against the live table it dropped ``searxng`` and
        ``alfred-frontend`` — both degraded, both with real outages — at
        the exact moment ``venture-chat`` went unreliable.  A rule that
        hides two faults the instant a third appears is worse than no
        rule, and the instruction block already caps the model at three.
        """
        prompt = build_review_prompt(DATA)
        for service in ("venture-chat", "searxng", "alfred-frontend"):
            assert service in prompt

    def test_the_grade_travels_with_each_name(self):
        """What replaced the filter: the model ranks off the grade word,
        so dropping the grade would make the fix worse than the defect."""
        prompt = build_review_prompt(DATA)
        assert "venture-chat: dropped out repeatedly, graded unreliable." in prompt
        assert "alfred-frontend: dropped out once, graded degraded." in prompt

    def test_no_outage_says_so_rather_than_saying_nothing(self):
        quiet = _data(services={**DATA["services"], "flappiest": []})
        assert "No service dropped out this period." in build_review_prompt(quiet)

    def test_the_facts_section_orders_by_episodes(self):
        facts = build_facts_section(DATA)
        assert "venture-chat 3, searxng 2, alfred-frontend 1" in facts


class TestGradePhrase:
    """A roll-up takes the loudest rung it swallows — as prose."""

    def test_failing_outranks_unreliable_outranks_degraded(self):
        assert "failed outright" in grade_phrase({"failing": 1, "unreliable": 9, "degraded": 9})
        assert "was unreliable" in grade_phrase({"failing": 0, "unreliable": 1, "degraded": 9})
        assert "degraded" in grade_phrase({"failing": 0, "unreliable": 0, "degraded": 1})

    def test_a_clean_week_is_a_result(self):
        assert grade_phrase({"failing": 0, "unreliable": 0, "degraded": 0}) == (
            "every service held up"
        )


# ── Resource movement ────────────────────────────────────────────────


class TestMovementPhrase:
    def test_inside_the_band_is_steady(self):
        assert movement_phrase(100.0, 100.0) == "held steady"
        assert movement_phrase(100.0 * (1 + STEADY_FRACTION / 2), 100.0) == "held steady"

    def test_outside_the_band_has_a_direction(self):
        assert movement_phrase(100.0 * (1 + STEADY_FRACTION * 2), 100.0) == (
            "ran higher than last period"
        )
        assert movement_phrase(100.0 * (1 - STEADY_FRACTION * 2), 100.0) == (
            "ran lower than last period"
        )

    def test_an_unsampled_metric_says_so_rather_than_reading_as_zero(self):
        """``ports_checked``'s rule: not-measured must never be served as
        measured-and-flat."""
        assert movement_phrase(None, 5.0) == "was not sampled"
        assert movement_phrase(5.0, None) == "has no earlier period to compare against"

    def test_a_zero_baseline_does_not_divide(self):
        assert movement_phrase(0.0, 0.0) == "stayed at nothing"
        assert movement_phrase(3.0, 0.0) == "rose from nothing"


# ── The prompt's shape ───────────────────────────────────────────────


class TestPromptStructure:
    def test_every_named_section_is_present(self):
        prompt = build_review_prompt(DATA)
        for heading in (
            "SERVICE RELIABILITY:",
            "ALERT ACTIVITY:",
            "ANOMALIES:",
            "RESOURCE TREND",
        ):
            assert heading in prompt

    def test_the_model_is_told_not_to_preamble(self):
        """The live generation of 2026-08-25 opened with "I'll help you
        analyze the Linux workstation's health report. Let me break it
        down:" — conversational filler that would have reached the
        briefing verbatim, since ``strip_markdown`` removes formatting
        and not prose.  Re-driven after this clause was added, the same
        model opened directly with the first section.
        """
        assert "do not introduce, acknowledge or restate the request" in (
            REVIEW_INSTRUCTIONS
        )

    def test_a_quiet_period_still_yields_a_prompt(self):
        """"Nothing broke" is the most useful thing this review can say,
        and a review that only appears when something broke teaches its
        reader that its absence means health."""
        quiet = _data(
            services={
                **DATA["services"],
                "flappiest": [],
                "recommendations_total": 0,
                "top": [],
                "summary": {**DATA["services"]["summary"], "unreliable": 0, "degraded": 0},
            },
            anomalies={"count": 0, "previous_count": 0, "listed": 0, "items": []},
        )
        prompt = build_review_prompt(quiet)
        assert "No service dropped out this period." in prompt
        assert "No resource strayed from its recent average." in prompt


class TestFactsSection:
    def test_coverage_is_stated_for_both_periods(self):
        """A qualifier the reader has to infer is one they will not
        infer, and one window's completeness says nothing about a
        comparison."""
        facts = build_facts_section(DATA)
        assert "17.01% of expected runs this period, 96.33% last" in facts

    def test_the_confidence_sentence_closes_the_block(self):
        assert build_facts_section(DATA).splitlines()[-1] == confidence_phrase(
            "low", comparable=False
        )

    def test_nothing_recommended_is_said_rather_than_omitted(self):
        quiet = _data(
            services={**DATA["services"], "recommendations_total": 0, "top": []}
        )
        assert "no service met a threshold" in build_facts_section(quiet)


def _folding_score():
    """One service carrying both deductions — the shape that folds.

    ``venture-chat``'s live shape on 2026-09-02: an outage row and a
    flapping row about one service, which ``SNAG-SYSD-006``'s fold turns
    into one row standing for two findings.
    """
    from sysadmin.monitor.reliability import Deduction, ReliabilityScore

    return ReliabilityScore(
        service="vc",
        score=49,
        grade="failing",
        uptime_percent=74.04,
        checks_measured=1988,
        failed_checks=516,
        outage_episodes=13,
        longest_outage_minutes=205.0,
        confidence="high",
        deductions=[
            Deduction(kind="downtime", points=26, detail=""),
            Deduction(kind="instability", points=25, detail=""),
        ],
    )


class TestFallback:
    def test_the_digest_carries_the_facts_and_says_it_is_a_digest(self):
        narrative = build_fallback_narrative(DATA)
        assert "without LLM narration" in narrative
        assert "Window: 7 days" in narrative

    def test_the_digest_names_actions_rather_than_counting_them(self):
        """``SNAG-ESTATE-001``: a roll-up that cannot name anything is a
        count, and a count is not news."""
        assert "venture-chat: 84.38% uptime this window" in build_fallback_narrative(DATA)

    def test_the_digest_names_what_a_folded_row_stands_for(self):
        """The same rule, one consumer downstream of the fold.

        ``SNAG-SYSD-006``'s fold promises to name every finding it
        swallows; this projection keeps ``title`` and ``action``, which
        are the **anchor's**, so without ``stands_for`` the digest names
        one finding and never tells the reader the other exists — the
        roll-up that cannot name anything, rebuilt inside the fix for
        it.  Live shape: ``alfred-career-mail-timer``'s ``outage`` row
        stands for the ``timer_failed`` finding whose step is the
        useful one.
        """
        data = copy.deepcopy(DATA)
        data["services"]["top"][0]["stands_for"] = [
            "venture-chat: 13 separate outages this window"
        ]
        narrative = build_fallback_narrative(data)
        assert "venture-chat: 13 separate outages this window" in narrative
        assert "Also stands for" in narrative

    def test_a_row_standing_only_for_itself_says_nothing_extra(self):
        """The majority case: no fold, no clause."""
        assert "Also stands for" not in build_fallback_narrative(DATA)

    def test_the_projection_carries_the_fold_through_from_the_real_rows(self):
        """The wiring, driven rather than injected.

        The test above hands ``build_fallback_narrative`` a fixture with
        ``stands_for`` already in it, so it pins the **renderer** and
        says nothing about the projection that fills the field —
        emptying ``_service_facts``' list passes it cleanly.  This
        drives the real ``recommend`` at the live specimen's shape and
        asserts the swallowed finding survives into the digest, which is
        the only assertion that fails when the two halves stop being
        connected.
        """
        from sysadmin.monitor.health_review import _service_facts
        from sysadmin.monitor.service_recommendations import recommend

        scores = [_folding_score()]
        advice = recommend(
            scores,
            ServiceActionsConfig(),
            check_interval_seconds=300,
            now=datetime(2026, 9, 2, 9, 0, tzinfo=UTC),
        )
        facts = _service_facts(scores, advice)

        assert len(advice.recommendations) == 1
        assert facts["top"][0]["stands_for"] == [
            "vc: 13 separate outages this window"
        ]

        data = copy.deepcopy(DATA)
        data["services"] = facts
        assert "13 separate outages" in build_fallback_narrative(data)


# ── Generation ───────────────────────────────────────────────────────


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
                self._session(), llm_client=_llm("The box held up.")
            )

        assert review.llm_used is True
        assert review.narrative.startswith("Window: 7 days")
        assert review.narrative.endswith("The box held up.")
        assert review.stats == DATA
        assert review.confidence == "low"

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
    async def test_nothing_observed_yields_no_review(self):
        """``None`` means the monitor recorded nothing, which is not the
        same as nothing having happened and must not be stored as an
        empty review."""
        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=None)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            assert await generate_review(self._session()) is None


# ── Wiring ───────────────────────────────────────────────────────────


class TestWiring:
    def test_the_review_is_not_under_the_get_only_services_prefix(self):
        """The one place this tier departs from its siblings' naming.

        ``/api/services`` promises no non-GET route beneath it and a test
        asserts it.  A ``POST .../review/generate`` there could only ship
        by narrowing that guard to admit the route being added, so the
        review took the prefix its content already belonged to.
        """
        from sysadmin.main import create_app

        app = create_app()
        paths = {r.path for r in app.routes}
        assert "/api/sysadmin/review" in paths
        assert "/api/sysadmin/review/generate" in paths
        assert not any(p.startswith("/api/services/review") for p in paths)

    def test_the_services_guard_still_holds(self):
        """Asserted here as well as at its owner, because this session is
        the one that had a reason to weaken it."""
        from sysadmin.main import create_app

        app = create_app()
        for route in create_app().routes:
            if route.path.startswith("/api/services"):
                assert getattr(route, "methods", set()) <= {"GET", "HEAD"}
        assert app is not None

    def test_the_job_is_planned_and_wired(self):
        """Planned-and-unwired is a ``KeyError`` at startup; wired-and-
        unplanned never runs and looks exactly like one that does."""
        from sysadmin.core.jobs import plan_jobs
        from sysadmin.main import JOB_TARGETS

        planned = {spec.job_id for spec in plan_jobs(_config())}
        assert "weekly_health_review" in planned
        assert "weekly_health_review" in JOB_TARGETS

    def test_the_schedule_does_not_collide_with_another_generation(self):
        """One llama-server generation in flight at a time on one card.

        05:15 is the log review, 05:30 is ``estate-manager-review.timer``
        (another repository's generation, verified on the box
        2026-08-25), 05:45 is the disk review and 06:00 is the briefing.
        The chain therefore grows at the front.
        """
        schedules = _config().schedules
        assert (schedules.health_review_hour, schedules.health_review_minute) == (5, 0)
        taken = {
            (schedules.log_review_hour, schedules.log_review_minute),
            (schedules.disk_review_hour, schedules.disk_review_minute),
            (schedules.briefing_hour, schedules.briefing_minute),
            (5, 30),  # estate-manager-review.timer
        }
        assert (
            schedules.health_review_hour,
            schedules.health_review_minute,
        ) not in taken

    def test_retention_has_both_halves(self):
        """A config row the map cannot resolve is silent; a map entry for
        a missing table is loud.  Migration 016 writes both."""
        from sysadmin.core.retention import KEEP_LATEST_PER, TABLE_TIMESTAMP_MAP

        assert TABLE_TIMESTAMP_MAP["health_reviews"] == "generated_at"
        assert "health_reviews" in KEEP_LATEST_PER

    def test_the_review_no_longer_announces_itself_with_an_alert(self):
        """``SNAG-AGENT-010``, and what this test used to assert.

        Two tests stood here.  One pinned that
        ``"Weekly system health review ready"`` matched no
        :data:`RESOLVABLE_TITLE_PATTERNS` entry, reasoning that an
        announcement filed under ``sysadmin`` was *"one wrong suffix away
        from being resolved by the next health check"* — so escaping the
        sweep was the property being protected.  Read the other way that
        is the defect: the row could not be resolved by anything, and
        :func:`~sysadmin.core.retention.purge_statement` deletes an
        ``alerts`` row only when it is resolved.  The suite was pinning
        an immortal row as intended behaviour, which is why the entry was
        found by counting the table rather than by a red test.

        The other asserted the announcement named an agent
        ``chk_alert_agent`` admits.  Both retire with the write.
        :mod:`tests.test_review_announcements` holds the guard now, for
        all three reviews rather than this one.
        """
        from tests.test_review_announcements import REVIEW_MODULES

        assert "sysadmin.monitor.health_review" in REVIEW_MODULES

    def test_the_briefing_renders_the_section_when_a_review_exists(self):
        from sysadmin.briefing.data import render_sections

        gathered = {
            "services": None,
            "logs": {"entries": 0, "errors": 0, "sources": 0},
            "filesystem": None,
            "log_review": None,
            "disk_review": None,
            "health_review": MagicMock(narrative="prose"),
        }
        titles = [s["title"] for s in render_sections(gathered)]
        assert "Weekly System Health Review" in titles

    def test_the_briefing_omits_the_section_rather_than_emitting_it_empty(self):
        from sysadmin.briefing.data import render_sections

        gathered = {
            "services": None,
            "logs": {"entries": 0, "errors": 0, "sources": 0},
            "filesystem": None,
            "log_review": None,
            "disk_review": None,
            "health_review": None,
        }
        titles = [s["title"] for s in render_sections(gathered)]
        assert "Weekly System Health Review" not in titles


class TestCoverageAgent:
    def test_the_coverage_agent_is_the_one_that_writes_the_data(self):
        """Named rather than passed: a caller free to choose would be
        free to choose an agent whose cadence has nothing to do with the
        rows being counted."""
        assert COVERAGE_AGENT == "sysadmin"

    def test_generated_at_is_a_parseable_instant(self):
        datetime.fromisoformat(DATA["generated_at"]).astimezone(UTC)


# ── The gather half ──────────────────────────────────────────────────


class TestGatherCoverage:
    """The two-sidedness of ``comparable``, driven rather than assumed.

    Every test above takes ``comparable`` from a fixture, so none of them
    reaches the rule that computes it — and that rule is the one a
    one-sided implementation would get wrong in the direction that
    matters: on this box the *previous* window is the complete one, so
    checking only the current window reports poor coverage and still lets
    every delta through unqualified.
    """

    @staticmethod
    def _session(current: int, previous: int):
        session = AsyncMock()
        row = MagicMock(current=current, previous=previous)
        result = MagicMock()
        result.one = MagicMock(return_value=row)
        session.execute = AsyncMock(return_value=result)
        return session

    @staticmethod
    async def _coverage(current: int, previous: int):
        from sysadmin.monitor.health_review import _gather_coverage

        now = datetime(2026, 8, 25, 12, tzinfo=UTC)
        return await _gather_coverage(
            TestGatherCoverage._session(current, previous),
            now.replace(day=18),
            now.replace(day=11),
            now,
            window_days=7,
            interval_seconds=300,
        )

    @pytest.mark.asyncio
    async def test_expected_runs_are_arithmetic_off_the_interval(self):
        cov = await self._coverage(2016, 2016)
        assert cov["runs_expected"] == 2016  # 7 days / 300 s
        assert cov["percent"] == 100.0

    @pytest.mark.asyncio
    async def test_both_windows_good_is_comparable(self):
        assert (await self._coverage(2000, 1950))["comparable"] is True

    @pytest.mark.asyncio
    async def test_a_thin_current_window_is_not_comparable(self):
        """The live shape: 343 against 1,942."""
        cov = await self._coverage(343, 1942)
        assert cov["comparable"] is False
        assert coverage_confidence(cov["fraction"]) == "low"

    @pytest.mark.asyncio
    async def test_a_thin_previous_window_is_not_comparable_either(self):
        """Falsified by checking only the current window — this is the
        case a one-sided rule passes and must not."""
        cov = await self._coverage(2000, 100)
        assert cov["comparable"] is False
        assert coverage_confidence(cov["fraction"]) == "high"

    @pytest.mark.asyncio
    async def test_a_zero_interval_cannot_divide(self):
        from sysadmin.monitor.health_review import _gather_coverage

        now = datetime(2026, 8, 25, 12, tzinfo=UTC)
        cov = await _gather_coverage(
            self._session(10, 10),
            now.replace(day=18),
            now.replace(day=11),
            now,
            window_days=7,
            interval_seconds=0,
        )
        assert cov["runs_expected"] > 0


class TestResourceHelpers:
    """The three pure readers, which the mocked tests above never touch."""

    def test_swap_percent_is_derived_not_stored(self):
        from sysadmin.monitor.health_review import _swap_percent

        assert _swap_percent(MagicMock(swap_used_mb=512, swap_total_mb=1024)) == 50.0

    def test_a_box_with_no_swap_is_not_a_box_at_zero_percent(self):
        """``ports_checked``'s rule: no swap device configured and a swap
        device sitting empty are different facts, and dividing by zero to
        report the first as the second is the readable-looking answer."""
        from sysadmin.monitor.health_review import _swap_percent

        assert _swap_percent(MagicMock(swap_used_mb=0, swap_total_mb=0)) is None

    def test_root_occupancy_comes_out_of_the_per_mount_blob(self):
        from sysadmin.monitor.health_review import _root_percent

        assert _root_percent({"/": {"percent": 78.1}, "/home": {"percent": 12.0}}) == 78.1

    def test_a_malformed_blob_reads_as_unknown_rather_than_zero(self):
        from sysadmin.monitor.health_review import _root_percent

        assert _root_percent(None) is None
        assert _root_percent({}) is None
        assert _root_percent({"/": "78.1"}) is None
        assert _root_percent({"/": {"used_gb": 1207.0}}) is None

    def test_mean_of_nothing_is_not_zero(self):
        from sysadmin.monitor.health_review import _mean

        assert _mean([]) is None
        assert _mean([1.0, 2.0]) == 1.5
