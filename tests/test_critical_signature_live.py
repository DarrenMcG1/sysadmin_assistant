"""A declared signature against the lines this box really stored.

``tests/test_critical_signatures.py`` pins the *rule* — the ladder, the
rung pairing, the title carrying no severity — with a stand-in session
and constants typed from one journal on one day.  What it could not do
is notice that the producer had stopped emitting either constant, and
that is exactly what happened.

**The defect this exists for.**  ``CRITICAL_SIGNATURES`` was written on
2026-09-03 from a ``6.18.48-1-lts`` journal, where amdgpu repeats its own
name after the BDF::

    amdgpu 0000:03:00.0: amdgpu: VRAM is lost due to GPU reset!

The box had already rebooted into ``7.2.2-arch1-1``, which drops the
redundant second prefix.  On 2026-09-04 at 10:35 a real MODE1 reset
destroyed the VRAM of both resident inference servers; the widened filter
stored ``VRAM is lost due to GPU reset!`` for the first time in this
table's life, the declaration matched nothing, and the loudest thing the
monitor said was ten ``warning`` rows naming fragments of the fault.  The
suite was green throughout, because the test guarding the mapping read::

    DECLARED_KEY = ("kernel", signature(VRAM_LOST))
    assert DECLARED_KEY in CRITICAL_SIGNATURES

— a value compared against itself.  It asserts that the declaration
agrees with the constant it was built from, which is true on every
kernel, including one that has reworded the line.  *"Falsify guards in
both directions"*: it meant **provenance** (the producer still emits
this) and asserted a **value**.

**What makes this one discriminate.**  The population is not a constant
but a query, and it is keyed on the half of the line that did *not*
move.  A declared key is the whole normalised line, so it carries two
things: amdgpu's device prefix and its message.  The reword was in the
prefix.  So the witness is the message payload — ``VRAM is lost due to
GPU reset`` — matched with ``LIKE`` against whatever ``log_entries``
holds, and the assertion is that every such row lands on a declared key.
A kernel that rewords the prefix again puts a new spelling in the table
and turns this red on the first reset after it, which is the earliest
moment the fact exists.

It reads ``message`` rather than ``raw_line`` because ``message`` is the
column ``_execute`` computes ``signature`` from — a test that witnessed a
different column would be proving a mapping nothing uses.

**The residue, stated rather than implied.**  A reword of the *payload*
empties the population and this skips.  That is a real blind spot and it
is the reason the skip is loud and names the count: a run reporting
"nothing to compare" is not a run reporting health, and zero-because-
blind must not read as zero-because-clean (``ports_checked``'s rule).
Filed as ``SNAG-LOG-016``.  It cannot be closed by widening the ``LIKE``
without reintroducing the tautology, because any pattern narrow enough to
identify the fault is a restatement of the declaration.
"""

import pytest

from sysadmin.monitor.log_aggregator import CRITICAL_SIGNATURES
from sysadmin.monitor.log_signature import signature

#: The payload half of the declared line — the part no kernel branch has
#: moved.  Deliberately not the declared key: a population selected by the
#: thing under test can only agree with it.
WITNESS_LIKE = "%VRAM is lost due to GPU reset%"

#: Fully qualified. ``search_path`` is not set on a bare connection, and
#: an unqualified name fails identically to an unreachable database — a
#: green verdict over a table nobody read.
QUERY = """
    SELECT message, count(*) AS n
    FROM sysadmin.log_entries
    WHERE source = 'kernel' AND message LIKE %(pattern)s
    GROUP BY message
"""


def _db_available() -> bool:
    from sqlalchemy import create_engine

    try:
        engine = create_engine(
            "postgresql+psycopg2://gaddi@localhost:5432/projects",
            connect_args={"connect_timeout": 2},
        )
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


def _stored_spellings() -> dict[str, int]:
    from sqlalchemy import create_engine, text

    engine = create_engine("postgresql+psycopg2://gaddi@localhost:5432/projects")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(QUERY.replace("%(pattern)s", ":pattern")),
                                {"pattern": WITNESS_LIKE}).all()
    finally:
        engine.dispose()
    return {row[0]: row[1] for row in rows}


@pytest.fixture(scope="module")
def stored() -> dict[str, int]:
    if not _db_available():
        pytest.skip("local postgres (projects DB) not reachable")
    spellings = _stored_spellings()
    if not spellings:
        pytest.skip(
            "no GPU-reset event line has been stored on this box, so there "
            "is nothing to compare the declaration against — this is "
            "'could not tell', not 'the declaration is current'"
        )
    return spellings


class TestTheDeclarationMatchesWhatThisBoxEmits:
    @pytest.mark.premise
    def test_the_witness_exists_and_is_a_real_reset(self, stored):
        """The premise, and why it is not optional.

        Every assertion below is vacuous over an empty table, and an
        empty table is indistinguishable from a declaration nothing can
        reach.  The fixture skips rather than passes; this states what it
        found so a reader of a green run can see the drive had something
        to say.
        """
        assert stored, "fixture should have skipped"
        assert sum(stored.values()) > 0

    def test_every_stored_reset_line_lands_on_a_declaration(self, stored):
        """The entry, refuted — and the shape the tautology could not see.

        One unmatched spelling here is one real MODE1 reset that
        destroyed every GPU client's VRAM and raised nothing above
        ``warning``.
        """
        unmatched = {
            message: n
            for message, n in stored.items()
            if ("kernel", signature(message)) not in CRITICAL_SIGNATURES
        }
        assert not unmatched, (
            "a GPU-reset event line is stored that no declaration matches — "
            "the widened filter is delivering the event to a declaration "
            "that cannot see it, which is 2026-09-04's defect:\n"
            + "\n".join(
                f"  {n:>4} x {message!r}\n       -> {signature(message)!r}"
                for message, n in sorted(unmatched.items())
            )
            + "\n  declared: "
            + "\n            ".join(repr(k[1]) for k in CRITICAL_SIGNATURES)
        )

    def test_the_match_names_the_fault_and_not_a_fragment(self, stored):
        """A matched key must deliver the declared row, not merely exist.

        ``.get`` returning a value is what the raise path acts on, so the
        assertion is on the value rather than on membership.
        """
        for message in stored:
            declared = CRITICAL_SIGNATURES.get(("kernel", signature(message)))
            assert declared is not None
            assert declared.title == "GPU was reset — every client lost its VRAM"
            assert declared.arrives_at == "info"
