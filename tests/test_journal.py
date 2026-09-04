"""Direct tests for :mod:`sysadmin.monitor.journal`.

**The first ones it has had.** Every existing test patches ``read_journal``
out (``test_log_alert_dedup.py``) or asserts a *different* journalctl
invocation (``test_log_actions.py``'s ``journal_command``, which builds the
command a recommendation tells a human to run). The command this module
actually executes was unasserted, which is how ``-n 500`` came to bound
raw lines while the severity filter ran in Python over what was left.
"""

import ast
import json
import pathlib
from unittest.mock import AsyncMock, patch

import pytest

from sysadmin.monitor.journal import (
    PRIORITY_MAP,
    SEVERITY_ORDER,
    admits,
    max_priority_for,
    message_text,
    read_ceiling,
    read_journal,
    unwrap_json_message,
)
from sysadmin.monitor.log_signature import signature


class TestMaxPriorityFor:
    """The ``-p`` ceiling is derived from ``PRIORITY_MAP``, not restated."""

    @pytest.mark.parametrize(
        ("severity_filter", "expected"),
        [
            ("critical", 2),
            ("error", 3),
            ("warning", 4),
            ("info", 6),
            ("debug", 7),
        ],
    )
    def test_ceiling_per_severity(self, severity_filter: str, expected: int) -> None:
        assert max_priority_for(severity_filter) == expected

    def test_agrees_with_priority_map_for_every_code(self) -> None:
        """The round trip, which is the point of deriving it.

        For every severity, the codes journalctl would admit under the
        derived ceiling must be exactly the codes ``PRIORITY_MAP`` maps to
        that severity or louder. Asserting the two sides separately is what
        lets them drift; this asserts they are one fact.
        """
        for severity, floor in SEVERITY_ORDER.items():
            ceiling = max_priority_for(severity)
            admitted = {int(c) for c in PRIORITY_MAP if int(c) <= ceiling}
            expected = {
                int(code)
                for code, name in PRIORITY_MAP.items()
                if SEVERITY_ORDER.get(name, 0) >= floor
            }
            assert admitted == expected, severity

    def test_unknown_filter_admits_everything(self) -> None:
        """Matching the Python filter's own ``.get(..., 0)`` fallback.

        Failing differently on the two sides would mean a typo in
        ``services.yaml`` silently narrows the read while the filter below
        stays wide — a source going quiet for a reason nothing reports.
        """
        assert max_priority_for("nonsense") == max(int(c) for c in PRIORITY_MAP)


def _entry(priority: str, message: str, cursor: str) -> str:
    return json.dumps(
        {
            "PRIORITY": priority,
            "MESSAGE": message,
            "__CURSOR": cursor,
            "__REALTIME_TIMESTAMP": "1755000000000000",
        }
    )


class TestPriorityIsPassedToJournalctl:
    """``-p`` bounds the ceiling; without it 61 % of the budget was waste."""

    @pytest.mark.asyncio
    async def test_kernel_error_filter_passes_p_err(self) -> None:
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal("kernel", severity_filter="error")

        cmd = run.call_args[0][0]
        assert "-p" in cmd
        assert cmd[cmd.index("-p") + 1] == "3"
        assert "-k" in cmd and "-u" not in cmd

    @pytest.mark.asyncio
    async def test_user_unit_warning_filter_passes_p_warning(self) -> None:
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal(
                "alfred-backend.service", severity_filter="warning", user=True
            )

        cmd = run.call_args[0][0]
        assert cmd[cmd.index("-p") + 1] == "4"
        assert "--user" in cmd

    @pytest.mark.asyncio
    async def test_ceiling_and_priority_travel_together(self) -> None:
        """``-n`` and ``-p`` are one mechanism, so both must be present.

        ``-n`` alone is the defect this fixes; ``-p`` alone would read an
        unbounded storm into memory. A command carrying one and not the
        other is worse than the version before either.
        """
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal("kernel", severity_filter="error", limit=250)

        cmd = run.call_args[0][0]
        assert cmd[cmd.index("-n") + 1] == "250"
        assert cmd[cmd.index("-p") + 1] == "3"


class TestPythonFilterRemainsTheAuthority:
    """``-p`` is an optimisation on the ceiling, not the decision."""

    @pytest.mark.asyncio
    async def test_entry_below_the_filter_is_still_dropped(self) -> None:
        """Belt and braces, and deliberately not removed.

        A stub returning what ``-p`` would have excluded stands in for
        journalctl behaving differently from this module's reading of it.
        The entry must not be stored.
        """
        stdout = "\n".join(
            [
                _entry("3", "a real error", "c1"),
                _entry("6", "chatter that -p should have excluded", "c2"),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error")

        assert [e["message"] for e in read.entries] == ["a real error"]

    @pytest.mark.asyncio
    async def test_cursor_still_advances_over_every_entry_read(self) -> None:
        """The rule survives ``-p``, which is why the comment stayed.

        ``-p`` means the discarded entry is not normally returned at all,
        so the two sets coincide in production. The rule is about what was
        *read*, so it is asserted against a read that contains both.
        """
        stdout = "\n".join(
            [
                _entry("3", "a real error", "c1"),
                _entry("6", "chatter", "c2"),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error")

        assert read.cursor == "c2"


class TestTruncationNowCountsRelevantEntries:
    @pytest.mark.asyncio
    async def test_truncated_when_the_read_fills_the_limit(self) -> None:
        stdout = "\n".join(_entry("3", f"e{i}", f"c{i}") for i in range(5))
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error", limit=5)

        assert read.truncated is True

    @pytest.mark.asyncio
    async def test_not_truncated_below_the_limit(self) -> None:
        stdout = "\n".join(_entry("3", f"e{i}", f"c{i}") for i in range(4))
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error", limit=5)

        assert read.truncated is False


class TestLongFieldsAreReadInFull:
    """``-a``, and why its absence was a crash rather than a lost detail.

    ``journalctl -o json`` substitutes ``null`` for any field over ~4096
    bytes unless ``-a`` is passed.  ``MESSAGE`` therefore arrived as
    ``None`` for every record this daemon writes with a traceback in it,
    and the aggregator's ``entry["message"][:5000]`` raised ``TypeError``
    (``SNAG-LOG-004``).
    """

    @pytest.mark.parametrize(
        ("unit", "user"),
        [("kernel", False), ("sysadmin.service", False), ("alfred.service", True)],
    )
    @pytest.mark.asyncio
    async def test_all_is_passed_for_every_source_shape(
        self, unit: str, user: bool
    ) -> None:
        """Every branch of the command builder, because ``-a`` is inserted
        before the ``-k``/``-u``/``--user`` edits and an index slip would
        drop it from exactly one of them."""
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal(unit, severity_filter="warning", user=user)

        assert "-a" in run.call_args[0][0]

    @pytest.mark.asyncio
    async def test_all_travels_with_the_ceiling_and_the_priority(self) -> None:
        """The three flags are one mechanism and must not drift apart.

        ``-n`` bounds the read, ``-p`` makes the bound count entries that
        matter, and ``-a`` makes the entries themselves readable.  A
        command carrying two of the three has been shipped twice now.
        """
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal("kernel", severity_filter="error", limit=250)

        cmd = run.call_args[0][0]
        assert "-a" in cmd
        assert cmd[cmd.index("-n") + 1] == "250"
        assert cmd[cmd.index("-p") + 1] == "3"


class TestMessageText:
    """The guard behind ``-a``, for the shapes journalctl may still return."""

    def test_a_string_is_itself(self) -> None:
        assert message_text("kernel: it broke") == "kernel: it broke"

    def test_a_byte_array_is_decoded(self) -> None:
        """``-a`` renders a non-UTF-8 field as an array of byte values.

        The one new shape ``-a`` introduces — without it the same field is
        ``null``, so this branch could not previously be reached.
        """
        assert message_text([104, 105]) == "hi"

    def test_invalid_utf8_bytes_are_replaced_not_raised(self) -> None:
        assert message_text([0xFF, 105]) == "�i"

    def test_a_nonsense_array_is_empty_rather_than_fatal(self) -> None:
        assert message_text([1, "two", None]) == ""

    @pytest.mark.parametrize("value", [None, 42, {"a": 1}])
    def test_anything_else_is_empty_string(self, value: object) -> None:
        """``""`` and never ``None``: a caller slicing the result is the
        whole defect, so the fallback must be sliceable."""
        assert message_text(value) == ""


class TestATruncatedFieldNoLongerPoisonsTheRun:
    """The end-to-end shape of ``SNAG-LOG-004``, asserted at this module's
    boundary — the aggregator slices what comes out of here."""

    @pytest.mark.asyncio
    async def test_null_message_yields_a_sliceable_entry(self) -> None:
        """Stands in for journalctl truncating despite ``-a``.

        ``-a`` is the fix, and this is the belt to its braces: the
        ``-p``/Python-filter pairing is written the same way and for the
        same reason.  A record journald declines to return in full must
        cost that record's text and nothing else.
        """
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "PRIORITY": "3",
                        "MESSAGE": None,
                        "__CURSOR": "c1",
                        "__REALTIME_TIMESTAMP": "1755000000000000",
                    }
                ),
                _entry("3", "a readable error", "c2"),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("sysadmin.service", severity_filter="error")

        assert len(read.entries) == 2
        # What the aggregator does next, verbatim — this raised TypeError.
        assert [e["message"][:5000] for e in read.entries] == ["", "a readable error"]
        assert read.cursor == "c2"

    @pytest.mark.asyncio
    async def test_every_entry_carries_a_string_message(self) -> None:
        """The invariant, rather than the instance.

        Whatever shapes journald returns, nothing leaves this module with
        a ``message`` a caller cannot slice.
        """
        stdout = "\n".join(
            [
                json.dumps(
                    {"PRIORITY": "3", "MESSAGE": m, "__CURSOR": f"c{i}",
                     "__REALTIME_TIMESTAMP": "1755000000000000"}
                )
                for i, m in enumerate([None, [104, 105], "plain", 7])
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("sysadmin.service", severity_filter="error")

        assert [type(e["message"]) for e in read.entries] == [str] * 4


class TestUnwrapJsonMessage:
    """``format: json`` — the declaration, and what it must never swallow."""

    def test_the_message_is_lifted_out_of_the_envelope(self) -> None:
        line = json.dumps(
            {
                "timestamp": "2026-08-17 15:02:11,004",
                "level": "ERROR",
                "logger": "sysadmin.core.scheduler",
                "message": "scheduler_job_error",
                "service": "sysadmin-service",
            }
        )
        assert unwrap_json_message(line) == (
            "scheduler_job_error",
            {"logger": "sysadmin.core.scheduler"},
        )

    def test_plain_text_survives_a_json_declaration(self) -> None:
        """The load-bearing case, and the reason this fails open.

        systemd writes its **own** lines into a unit's journal at error
        level — ``Failed to start SportsAnalyser - Frontend (Next.js).``
        appears 668 times live. A declaration that discarded non-JSON
        would silence exactly the line saying the service died.
        """
        text = "Failed to start SportsAnalyser - Frontend (Next.js)."
        assert unwrap_json_message(text) == (text, {})

    @pytest.mark.parametrize(
        "text",
        [
            '{"message": "unterminated',        # looks like JSON, is not
            "[1, 2, 3]",                        # JSON, but not an object
            '{"level": "ERROR"}',               # object, but no message
            '{"message": 42}',                  # message, but not a string
            '{"message": ""}',                  # message, but empty
        ],
    )
    def test_anything_it_cannot_read_is_returned_unchanged(self, text: str) -> None:
        assert unwrap_json_message(text) == (text, {})

    def test_a_missing_logger_is_absent_rather_than_none(self) -> None:
        """An absent key beats a null value: ``metadata`` is served back,
        and a ``logger: null`` reads as "we looked and there was none"."""
        assert unwrap_json_message('{"message": "boom"}') == ("boom", {})

    def test_a_non_string_logger_is_dropped(self) -> None:
        assert unwrap_json_message('{"message": "boom", "logger": 7}') == ("boom", {})


class TestDeclaredFormatIsHonouredByReadJournal:
    @staticmethod
    def _record(priority: str, message: str) -> str:
        return json.dumps(
            {
                "PRIORITY": priority,
                "MESSAGE": message,
                "__CURSOR": "c1",
                "__REALTIME_TIMESTAMP": "1755000000000000",
            }
        )

    ENVELOPE = json.dumps(
        {
            "timestamp": "2026-08-17 15:02:11,004",
            "level": "ERROR",
            "logger": "sysadmin.core.scheduler",
            "message": "scheduler_job_error",
        }
    )

    @pytest.mark.asyncio
    async def test_text_is_the_default_and_leaves_the_envelope_alone(self) -> None:
        """A source that declares nothing reads exactly as it did before
        the field existed — the whole of the compatibility claim."""
        with patch(
            "sysadmin.monitor.journal._run",
            new=AsyncMock(return_value=self._record("3", self.ENVELOPE)),
        ):
            read = await read_journal("sysadmin.service", severity_filter="error")

        assert read.entries[0]["message"] == self.ENVELOPE
        assert "logger" not in read.entries[0]["metadata"]

    @pytest.mark.asyncio
    async def test_json_unwraps_and_carries_the_logger_into_metadata(self) -> None:
        with patch(
            "sysadmin.monitor.journal._run",
            new=AsyncMock(return_value=self._record("3", self.ENVELOPE)),
        ):
            read = await read_journal(
                "sysadmin.service", severity_filter="error", log_format="json"
            )

        entry = read.entries[0]
        assert entry["message"] == "scheduler_job_error"
        assert entry["metadata"]["logger"] == "sysadmin.core.scheduler"

    @pytest.mark.asyncio
    async def test_severity_comes_from_priority_and_never_from_the_envelope(
        self,
    ) -> None:
        """``"level": "ERROR"`` sits right beside the message and is
        ignored on purpose.

        ``JournalLevelPrefixFormatter`` already puts the level in
        ``PRIORITY``, so reading it here too would be two statements of
        one fact that can disagree — and only the prefix is visible to
        ``journalctl -p err`` and ``OnFailure=``. This record says
        ``PRIORITY=4`` and ``level: ERROR``; the answer must be
        ``warning``.
        """
        with patch(
            "sysadmin.monitor.journal._run",
            new=AsyncMock(return_value=self._record("4", self.ENVELOPE)),
        ):
            read = await read_journal(
                "sysadmin.service", severity_filter="warning", log_format="json"
            )

        assert read.entries[0]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_raw_line_keeps_the_envelope_the_message_dropped(self) -> None:
        """The unwrap moves what identity is built from, not what is kept.

        Asserted by *recovering* the envelope rather than by substring:
        ``raw_line`` is the journalctl record, so the envelope is nested
        inside it JSON-escaped, and a naive ``in`` test passes for the
        wrong reasons or fails for none. It also pins the truncation —
        an envelope past ``raw_line``'s 2000 characters is not recoverable
        and this asserts the case where it is.
        """
        with patch(
            "sysadmin.monitor.journal._run",
            new=AsyncMock(return_value=self._record("3", self.ENVELOPE)),
        ):
            read = await read_journal(
                "sysadmin.service", severity_filter="error", log_format="json"
            )

        recovered = json.loads(read.entries[0]["raw_line"])["MESSAGE"]
        assert json.loads(recovered)["logger"] == "sysadmin.core.scheduler"
        assert json.loads(recovered)["level"] == "ERROR"

    @pytest.mark.asyncio
    async def test_a_systemd_line_in_a_declared_json_journal_is_untouched(self) -> None:
        """Driven live against ``sportsanalyser-frontend`` before it was
        written down: six real entries, all plain text, all preserved."""
        stdout = "\n".join(
            [
                self._record("3", "Failed to start SysAdmin Monitoring Service."),
                self._record("3", self.ENVELOPE),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal(
                "sysadmin.service", severity_filter="error", log_format="json"
            )

        assert [e["message"] for e in read.entries] == [
            "Failed to start SysAdmin Monitoring Service.",
            "scheduler_job_error",
        ]


# --- A declaration cannot be narrowed out of the read (SNAG-CFG-006) ----


class TestReadCeilingIsWidenedByADeclaration:
    """The ``-p`` half, derived so a ``SIGHUP`` cannot disarm it.

    ``arrives_at`` used to be *asserted* against the shipped
    ``config.yaml``.  ``sysadmin/reload.py`` re-reads that file on
    ``SIGHUP`` and ``severity_filter`` is not ``RESTART_ONLY``, so
    narrowing the kernel source back to ``error`` disarmed the
    declaration on the running daemon with the suite still green.  A
    derived relation cannot be broken by an edit.
    """

    def test_nothing_declared_is_max_priority_for_unchanged(self) -> None:
        for severity in SEVERITY_ORDER:
            assert read_ceiling(severity) == max_priority_for(severity)
            assert read_ceiling(severity, {}) == max_priority_for(severity)

    def test_a_quieter_declaration_widens_the_ceiling(self) -> None:
        """Wider is a **larger** ``-p``, because ``-p N`` admits ``0..N``.

        The wording reads backwards and is worth pinning as a value: the
        declaration needing the widest read is the *quietest* one, since
        a quiet rung sits at a high priority number.
        """
        assert read_ceiling("error") == 3
        assert read_ceiling("error", {"sig": "info"}) == 6

    def test_the_widest_declaration_wins(self) -> None:
        assert read_ceiling("error", {"a": "warning", "b": "info"}) == 6
        assert read_ceiling("error", {"a": "warning"}) == 4

    def test_a_declaration_never_narrows_the_configured_read(self) -> None:
        """One direction only.

        A declaration says where a line *arrives*, so it can only ever
        ask for more.  Reading it as a floor would let a declaration at
        ``critical`` shrink a source configured at ``info`` — a
        declaration silencing the source it was added to.
        """
        assert read_ceiling("info", {"sig": "critical"}) == 6


class TestAdmitsIsTheHalfTheEntryMissed:
    """Both gates move together, and widening one alone is inert.

    ``SNAG-CFG-006`` named only the ``-p`` ceiling.  Measured against the
    live kernel journal with ``severity_filter`` at ``error``, forcing
    ``-p 6`` returned the same 32 entries and the same **zero** ``VRAM is
    lost due to GPU reset!`` lines, because the Python filter — which
    ``read_journal`` calls the authority on what is stored — drops them
    one loop later.
    """

    SIG = "amdgpu N:N:N.N: VRAM is lost due to GPU reset!"
    LINE = "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!"

    def test_a_line_at_or_above_the_floor_is_admitted(self) -> None:
        assert admits("error", "error", "boom", None) is True
        assert admits("critical", "error", "boom", None) is True

    def test_a_line_below_the_floor_is_dropped_with_nothing_declared(self) -> None:
        assert admits("info", "error", self.LINE, None) is False
        assert admits("info", "error", self.LINE, {}) is False

    def test_a_declared_signature_below_the_floor_is_admitted(self) -> None:
        assert signature(self.LINE) == self.SIG
        assert admits("info", "error", self.LINE, {self.SIG: "info"}) is True

    def test_the_widening_is_per_signature_and_never_wholesale(self) -> None:
        """The narrowing must still govern everything nobody declared.

        Lowering the floor to the declaration's rung instead would store
        all 1,823 info-level kernel lines a boot while ``config.yaml``
        said ``error`` — a config edit that does nothing, which is worse
        than the gap it closes.  Measured live: the fixed reader stores
        35 where the wide one stores 1,823.
        """
        declared = {self.SIG: "info"}
        assert admits("info", "error", self.LINE, declared) is True
        assert admits("info", "error", "an undeclared info line", declared) is False

    def test_an_unknown_filter_still_admits_everything(self) -> None:
        """The same fallback ``max_priority_for`` makes on the other side
        of the same read, so a typo in ``services.yaml`` cannot narrow one
        gate and widen the other."""
        assert admits("debug", "nonsense", "anything", None) is True


class TestBothGatesMoveTogetherInReadJournal:
    """End to end, which is the assertion the entry's fix would fail."""

    @pytest.mark.asyncio
    async def test_the_ceiling_and_the_store_both_widen(self) -> None:
        sig = signature("amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!")
        stdout = "\n".join(
            [
                _entry("3", "ring gfx_0.0.0 timeout", "c1"),
                _entry("6", "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!", "c2"),
                _entry("6", "amdgpu 0000:03:00.0: GPU reset begin!", "c3"),
            ]
        )
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)
        ) as run:
            read = await read_journal(
                "kernel", severity_filter="error", declared={sig: "info"}
            )

        cmd = run.call_args[0][0]
        # Half one: journalctl is asked for the line at all...
        assert cmd[cmd.index("-p") + 1] == "6"
        # ...half two: and the Python gate lets it through, while its
        # equally-quiet, undeclared sibling is still dropped.
        assert [e["message"] for e in read.entries] == [
            "ring gfx_0.0.0 timeout",
            "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!",
        ]

    @pytest.mark.asyncio
    async def test_widening_the_ceiling_alone_would_store_nothing_new(self) -> None:
        """The entry's own named fix, modelled and refuted.

        A read whose ceiling is wide and whose declaration is absent is
        exactly what ``max(max_priority_for(...), arrives_at)`` alone
        produces once journalctl has handed the lines over.  It stores
        neither of them.
        """
        stdout = "\n".join(
            [
                _entry("3", "ring gfx_0.0.0 timeout", "c1"),
                _entry("6", "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!", "c2"),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error", declared=None)

        assert [e["message"] for e in read.entries] == ["ring gfx_0.0.0 timeout"]

    @pytest.mark.asyncio
    async def test_a_declaration_is_matched_against_the_unwrapped_message(self) -> None:
        """The reorder, pinned where it is observable.

        The message is composed before the rung gate now, so a
        ``format: json`` source's declaration is matched against what
        ``unwrap_json_message`` returns rather than against the envelope
        — which is the string ``_execute`` computes its own key from.
        Matching the envelope would put a signature nobody can declare on
        one side of the gate and the declaration on the other.
        """
        envelope = json.dumps(
            {"timestamp": "2026-09-04T10:36:31", "level": "INFO",
             "logger": "sysadmin.core.agent", "message": "manual_run_cancelled"}
        )
        stdout = _entry("6", envelope, "c1")
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal(
                "sysadmin.service",
                severity_filter="error",
                log_format="json",
                declared={signature("manual_run_cancelled"): "info"},
            )

        assert [e["message"] for e in read.entries] == ["manual_run_cancelled"]

    @pytest.mark.asyncio
    async def test_the_cursor_still_advances_over_a_line_the_gate_drops(self) -> None:
        """``-p`` used to make the two sets coincide; this pulls them apart.

        A declaring source reads at the declaration's rung and stores at
        its own, so journalctl now returns lines ``admits`` drops — which
        makes the cursor rule load-bearing again rather than merely
        defensive.  Advancing only past *kept* entries would leave the
        resume point behind the undeclared quiet lines and re-read them
        for ever.
        """
        sig = signature("amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!")
        stdout = "\n".join(
            [
                _entry("6", "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!", "c1"),
                _entry("6", "undeclared chatter", "c2"),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal(
                "kernel", severity_filter="error", declared={sig: "info"}
            )

        assert len(read.entries) == 1
        assert read.cursor == "c2"


class TestNoReaderGatesOnSeverityByHand:
    """One statement of when a line is stored, and a sweep that keeps it.

    There were exactly two hand-rolled floor comparisons before
    ``SNAG-CFG-006`` — ``read_journal``'s and ``_read_log_file``'s — and
    the whole defect was that widening one of them was not enough.  A
    third would be the same shape again, and the failure mode of the
    copy is *silence*: a declared line simply never stored.

    ``test_autogenerate_config.py``'s idiom, reused: the walker is run at
    its own owner as well, which must trip every rule, so a detector
    that has stopped detecting cannot pass by finding nothing.
    """

    OWNER = "sysadmin/monitor/journal.py"

    @staticmethod
    def _hand_rolled(path: pathlib.Path, *, owner: bool = False) -> list[str]:
        """Comparisons of **this module's** ``SEVERITY_ORDER`` by hand.

        An ``ast`` walk rather than a text sweep, because ``journal.py``
        and ``log_aggregator.py`` both name the constant in prose and a
        docstring is an ``ast.Constant`` that falls out for free.

        **Keyed on provenance, never on the name**, which the first draft
        got wrong and the walker itself reported.
        ``sysadmin/core/escalation.py`` defines a *different*
        ``SEVERITY_ORDER`` — three alert rungs against five log
        severities — and compares it twice, correctly; the aggregator's
        own import comment records that collision as a trap.  A
        name-keyed sweep names the module that avoided it.  So a file is
        examined only when it imports the constant **from
        ``sysadmin.monitor.journal``**, and the owner is examined because
        it is where the constant lives.
        """
        tree = ast.parse(path.read_text())
        if not owner:
            imported = any(
                isinstance(node, ast.ImportFrom)
                and node.module == "sysadmin.monitor.journal"
                and any(alias.name == "SEVERITY_ORDER" for alias in node.names)
                for node in ast.walk(tree)
            )
            if not imported:
                return []

        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            for side in (node.left, *node.comparators):
                if not isinstance(side, ast.Call):
                    continue
                func = side.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "get"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "SEVERITY_ORDER"
                ):
                    found.append(f"{path}:{node.lineno}")
                    break
        return found

    def test_no_module_outside_the_owner_compares_a_rung_by_hand(self) -> None:
        offenders = []
        for path in pathlib.Path("sysadmin").rglob("*.py"):
            if path.as_posix() == self.OWNER:
                continue
            offenders += self._hand_rolled(path)

        assert offenders == [], (
            "these compare a log severity against a floor by hand; "
            f"call journal.admits instead: {offenders}"
        )

    def test_the_walker_trips_at_its_own_owner(self) -> None:
        """Driven at the module that *is* the hand-written form.

        Without this the sweep above passes for a detector that matches
        nothing at all — the shape this repository has shipped twice.
        """
        assert self._hand_rolled(pathlib.Path(self.OWNER), owner=True), (
            "the detector found no comparison in the one module that "
            "must contain one — it has stopped detecting"
        )
