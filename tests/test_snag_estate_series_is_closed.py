"""This repository's ``SNAG-ESTATE-*`` series is closed, and a test is what closes it.

ADR-0015 refused to judge the estate's ``pointers`` check, and this is the
half of that decision that speaks instead.  The check's minter half
(``check_snag_minters``) compares estate-manager's own snag list against
every other repository's and files ``snag_id_collision_unmarked`` /
``snag_id_marker_unfounded`` at 05:00 — findings that, since their
ADR-0142, reach no person at all.

**Only this repository can open one.**  Two repositories on this box
define ``SNAG-ESTATE-*`` ids (measured 2026-09-27: estate-manager 206,
this one 15), the estate mints upward from its highest, and every id here
sits below it.  So the estate cannot collide with us by minting; only a
write to *this* file can — a new id (an unmarked collision) or a renamed
or removed one (a marker of theirs that now names nothing).  Both windows
the estate measured were opened by commits here (``6330e40``,
``270e401``).  The cheapest place to say so is the one source that can
cause it, before the 05:00 run ever sees the working tree.

**The set is read with the producer's parser, never a regex.**
``estate.snags.read_snags`` is what ``check_snag_minters`` reads with, so
this guard counts exactly what their check counts.  A list-item grep
counts **14**; the parser counts **15**, because ``SNAG-ESTATE-016`` is a
row in this file's archive *table* — and the estate had already marked
it.  A second implementation of "which ids does this file define" is the
thing that would drift, and the one that decides a collision is theirs.
"""

from __future__ import annotations

from estate.snags import read_snags

from sysadmin.core.config import REPO_ROOT

SNAG_DOCUMENT = REPO_ROOT / "docs" / "roadmap" / "snag_list.md"

#: The fifteen ids estate-manager's register already marks as minted here
#: too.  Changing this set is a change to *their* document's truth, so it
#: is announced to them before the commit that carries it — never edited
#: here to make the test pass.
CLOSED_SERIES = frozenset(
    {f"SNAG-ESTATE-{n:03d}" for n in range(1, 15)} | {"SNAG-ESTATE-016"}
)

_ADVICE = (
    "Mint into a family this repository owns alone (SNAG-DOCS, SNAG-CFG, "
    "SNAG-PORT, ...): every SNAG-ESTATE-* id here collides with a different "
    "defect in estate-manager's register. A renamed or removed id leaves their "
    "'Also minted' marker naming nothing, so file at estate-manager first. "
    "See docs/adr/0015-pointers-has-an-owner-and-the-cause-is-here.md."
)


def estate_series(text: str) -> frozenset[str]:
    rows, _dialect = read_snags(text)
    return frozenset(
        row.snag_id.upper()
        for row in rows
        if row.snag_id and row.snag_id.upper().startswith("SNAG-ESTATE-")
    )


class TestTheSeriesIsClosed:
    def test_this_register_defines_exactly_the_closed_series(self):
        minted = estate_series(SNAG_DOCUMENT.read_text(encoding="utf-8"))
        added, removed = sorted(minted - CLOSED_SERIES), sorted(CLOSED_SERIES - minted)
        assert not added and not removed, f"added {added}, removed {removed}. {_ADVICE}"


class TestTheReaderSeesWhatTheEstateSees:
    """The guard is only as wide as its reader, so the reader is driven."""

    def test_a_new_bullet_entry_is_seen(self):
        text = "## Open\n\n- [P3] SNAG-ESTATE-017: **a new defect**\n"
        assert estate_series(text) == {"SNAG-ESTATE-017"}

    def test_a_table_row_is_seen(self):
        """The shape a list-item grep misses, and the one 016 is written in."""
        text = (
            "## Archive\n\n| ID | Summary | Fixed |\n|---|---|---|\n"
            "| SNAG-ESTATE-016 | a fixed defect | 2026-09-04 |\n"
        )
        assert estate_series(text) == {"SNAG-ESTATE-016"}

    def test_a_citation_in_prose_is_not_a_minting(self):
        """Citing their id repo-qualified is what the collision rule asks for."""
        text = "## Open\n\n- [P3] SNAG-DOCS-099: **x** — see estate-manager `SNAG-ESTATE-073`\n"
        assert estate_series(text) == frozenset()
