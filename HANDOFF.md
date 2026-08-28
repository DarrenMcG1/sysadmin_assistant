# Handoff — 2026-08-28

## Next action

Fix `SNAG-TRAY-008` — persist the understudy's spoken set across a restart and decide whether it may adopt a fault raised while the tray was watching, since the reminder sweep's population is what this process announced and a tray restart therefore re-announces every standing fault as news while a fault the tray was speaking for is never adopted when the tray dies, and Session 97's check already treats the entry as a conjunction so a fix closing only one face is reported as a `match` with the moved half in its note rather than as a closure.

## Session 114 is complete — the prediction carries the zone it was copied from

`SNAG-ESTATE-013` is **fixed**. `ops_claims`' `check:expires` marker took
a bare wall clock, so the one marker ever written — copied off an estate
surface publishing `started_at: "2026-08-25T03:32:17.538288+00:00"` —
named an instant an hour before the thing it predicted, and the check
reported the passed boundary **correctly**, having nothing to disagree
with. `EXPIRY_FORMAT` is `%Y-%m-%dT%H:%M%z` and a naive instant is
refused: `SNAG-LOG-009`'s defect one document over, answered with
`journal.since_timestamp`'s posture — refuse the ambiguity, never
resolve it by a default, because a default is right on the box that
wrote the marker and silently wrong by the offset everywhere else.

**The refusal names the fault rather than reporting a malformation.**
`EXPIRY_NAIVE_FORMAT` recognises the old shape without accepting it, so
a naive stamp comes back as *"carries no offset, so it names two
instants — 03:32+01:00 if the sentence is in this box's clock,
03:32+00:00 if it was copied from a UTC-stamped surface"*.
`schema_guard`'s rule that every way of not-knowing fails closed **with
its own message**: the generic "not an instant of the form" would report
this entry's own founding case as a typo, and the two readings are
exactly what the author has to choose between.

**The format was the smaller half; rule 9's pin is what makes the fix
more than a spelling change.** The pin renders the marker's instant
**into this box's zone** before looking for it in the prose. Naive, the
entry's own block satisfied it — the marker said `03:32`, the sentence
said 03:32, and both were an hour from the moment predicted, because two
statements of one fact had nothing to disagree *about*. With an offset
they visibly disagree and the note says which of them is in which clock.
Falsified by pinning against `moment.strftime` instead of
`moment.astimezone().strftime`: the marker's own rendering is then what
is looked for, it is in the prose, and the pin passes exactly as before.

**`@<epoch>` was refused, though the entry names it and
`since_timestamp` renders exactly that for this fault.** The difference
is the reader, not the instant. There the consumer is journalctl, whose
zone is the reader's and unknown and whose `--since` has **no offset
syntax at all**, so an epoch is the only unambiguous thing it takes;
here the consumer is `check_expiry` and the author is a human who must
also write the instant's wall clock into the sentence beside it. An
epoch is unambiguous and unreadable, so accepting one would buy rule 8
by deleting rule 9 — the pin would become checkable by the checker
alone.

**`check_expiry` refuses a naive `now`, and the guard is at the entry
point rather than at the subtraction.** Naive and aware datetimes raise
`TypeError` on their own, loudly — so this is not the silent reading
`since_timestamp` exists to refuse — but only at the first *well-formed*
marker. A document carrying none, which is this one today, would let a
naive caller through until the day somebody wrote a good marker, and the
crash would arrive stamped with that edit.

**⚠️ The entry's "two hours" is two mechanisms and only one of them is
the marker's**, which its own Cause bullet contains without separating:
the timer fired at 04:32 local (the offset — the marker's error) and the
hourly judge swept at 05:32 (the poll interval — not). Driven at the
entry's own producer stamp through the real `check_expiry` before the
fix, the displacement is **1 hour**, exactly this box's offset, and the
check that measured it said so in those words. A fix sized to two hours
would have gone looking for a second cause that is not there.

**The guard ships with an empty live population and a full historical
one**, which is a correction to the way this sitting was handed over.
`git log -S 'check:expires'` finds **one** marker ever written to
`STATUS.md` and it is naive — 1 of 1 — and the block carries **none**
today, so nothing in the document is refused on the day the refusal
lands. That is the reverse of `since_timestamp`, whose population is
empty *by construction* because every caller reads a `timestamp with
time zone`; here it is empty by circumstance, and the next marker anyone
writes is the one the guard exists for.

**The check reported `mismatch` against the fix that closed its entry**,
naming both halves of the shape-of-fix the entry had written down — the
offset-bearing instant parsing, and the zoneless one no longer being
read as a moment. That is the entry refuted by the instrument built to
watch it rather than by its author's say-so. It then retired, since
every member of `CHECKS` names an *open* entry; the **detector** did
not, and the three-zone drive is re-homed as
`TestTheInstantCarriesItsZone` in `tests/test_ops_claims.py` —
`SNAG-LOG-006`'s treatment one sitting on.

**Seven mutations, each red on exactly the right test, and one of them
is the entry's own blindness.** Reverting `EXPIRY_FORMAT` breaks 13;
dropping the `now` guard breaks the single test that drives a marker
carrying no instant at all; rendering the pin in the marker's own zone
breaks the founding case at `Europe/London` and `America/New_York` and
**passes at UTC**, because at zero offset the two renderings are the
same string. So the parametrised zone test carries a `displaced` flag
naming which of its three rows are witnesses and which is a control,
rather than letting three green rows read as three pieces of evidence.

**Measured either side.** Suite **2795 → 2792** (12 added, 15 retired —
the total going down is why the arithmetic is written). Entries **99
either side, open 20 → 19** through `estate.snags.read_snags`. Checks in
the registry **20 → 19**, every open entry still naming one, and
`sysadmin-check-snags` exits **0**. The daemon was restarted (3801574 →
3830192, active 2026-08-28 15:17:21) and `check-ops-claims.sh` is green
on all nine claims.

## What is still open

Nineteen entries, all P3 and all carrying a check. Four are
estate-manager's surfaces rather than this repository's code
(`SNAG-ESTATE-002`, `-005`, `-006`, `-007`) and are filed rather than
fixable here. `SNAG-SYSD-003` needs `sudo` for a system unit edit.
`SNAG-ESTATE-010` has its blob half closed by Session 110 and its rung
half standing by Session 39's design.
