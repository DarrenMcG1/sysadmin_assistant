# Handoff — 2026-08-28

## Next action

Fix `SNAG-LOG-008` — ten of this daemon's own stored log rows are frozen as raw JSON because they were ingested before the `format: json` declaration existed, so no read will ever unwrap them, and the sitting should measure whether retention has already emptied the population before deciding between a backfill and closing the entry as moot.

## Session 115 is complete — the understudy remembers, and adopts what it never announced

`SNAG-TRAY-008` is **fixed, both faces**. `DesktopNotifier._spoken` was
an in-memory dict and the reminder sweep's population was exactly its
keys, so a fault raised while the tray was watching was never adopted
when the tray died, and a daemon restart forgot everything it had
announced. `desktop_notifications` (migration 018) is the store;
`DesktopNotifier._adopt` is the scope.

**The measurement is the finding, and nobody had taken it.**
`sysadmin.service` started **111 times in 28.26 days**, median uptime
**1.77 h**, mean 6.17 h, and **5 of 110** lives reached the 24 hours
`reminder_hours` asks for. `SNAG-TRAY-007`'s reminder was therefore
structurally unavailable on **95 %** of this daemon's lives. The entry
filed its population as zero and stopped there, which is why that half
was invisible for twelve days.

**The same number refutes the entry's own shape-of-fix.** It asks for
adoption *"only when the tray has been absent for a full
`reminder_hours`"*. `TrayPresence` is monotonic and in-memory by
deliberate design — its docstring argues for both — so a process
observes 24 h of absence only by living 24 h, which is one life in
twenty-two. Written as a **refusal** the fix would have been correct,
green and inert. It ships as an **anchor**: the absence sets the adopted
fault's `last_spoken_at` back, capped at one interval, so a fault
adopted the moment the tray leaves still waits a full interval — the
quiet-by-construction property the entry wanted — and one adopted after
a day of silence speaks at once.

**Decision taken, and it is the reason both halves shipped together: the
two faces are multiplicative rather than independent.** Adoption alone
re-adopts on every restart and re-arms its own anchor, so on a
1.77-hour daemon it would never speak. The store alone leaves face 1
exactly as filed. `SNAG-AGENT-008`'s shape — a fix for one half is not
half the benefit, it is none. Persisting without deciding the scoping
question was therefore not an option the measurement left open.

**Options rejected.** A durable *tray-presence* reading, which would
have let the entry's gate ship as written: refused because
`TrayPresence`'s own docstring argues against inheriting a belief about
the tray across a restart, and because it needs a second write path for
a fact whose short reading must stay in-memory. A state **file** rather
than a table: refused because `sysadmin.service` is a system unit and a
`StateDirectory=` needs `sudo`, and because a config-declared path is a
new leaf the reload has to classify. Persisting rule 2's stamp-forward:
refused because the store records what was **said**, and a watching tray
is a belief about another process — the stated cost is one early toast
if the daemon restarts while the tray is up and the tray then dies
inside that one grace window.

**Three consequences, each the opposite of the obvious version.** The
notifier's clock became a **wall** clock — no monotonic value survives a
process, and on Linux `CLOCK_MONOTONIC` does not survive a suspend
either, which a 24-hour interval about elapsed human time should count;
`TrayPresence` keeps monotonic for its own 180-second question and the
two now differ on purpose. The store is written once per **notification**
rather than once per sweep. And the old cheapest gate — *"a sweep that
has said nothing issues no query at all"* — is exactly the entry, so it
became **one query per process**.

**The check retired with the entry; the detector did not.**
`tests/test_desktop_store_live.py` is the same two-sweep timeline
against the real database, and it is **stronger than the check it
replaces**: once adoption landed, "the restarted instance restated its
predecessor's fault" was producible by adoption alone, so it asks *how*
it was inherited — a restored episode carries a reminder already sent
and is not marked adopted.

**`rolled_back_drive` had to be hardened first, and the leak was not
hypothetical.** `_remember` must commit, and that harness rolled back a
plain session — so the first full-suite run after the fix committed the
probe's transaction: three rows into `alerts` and three into
`desktop_notifications`, found by counting either side and deleted by
hand. The session now joins the connection's transaction by savepoint.
Any future probe driving code that owns its own transaction depends on
this.

**Deploying it found a second, independent reason the reminder path was
inert, and it is the more serious half of the sitting.** `DesktopNotifier`
resolved `get_session_factory()` — the *application's* pooled engine —
while every call it makes runs on a loop that is not the application's:
the sweep is an APScheduler job and `scheduler._run_async` wraps each
firing in its own `asyncio.run`, and `on_alert_raised` is published from
inside an agent's run, which is another. A pooled asyncpg connection
belongs to the loop that opened it, so the first query out of the
restarted daemon raised `RuntimeError: got Future … attached to a
different loop`, then `InternalClientError: got result for unknown
protocol state 3`. **`_still_open` has carried that defect since Session
55 and never once executed on this box**, because the sweep's old first
gate — *"a daemon that has announced nothing issues no query at all"* —
returned before reaching it. `SNAG-TRAY-007`'s reminder could not have
worked here even for a fault the daemon *had* announced, and
`SNAG-TRAY-008`'s own symptom is what hid it. `_factory()` returns
`get_scheduler_session` now, and the commit belongs to that context
manager rather than being restated beside it. **The next sitting should
assume other module-level singletons reaching for the pooled factory are
suspect** — this one was found only because a new query got past a gate
that had been short-circuiting for twelve weeks.

**Its first live exercise adopted a real fault** — `High VRAM usage on
AMD Radeon RX 7900 XTX`, open on this box and never announced here
because the tray was watching. Under the old code nothing would ever
have restated it. It is also why the live test asserts a **floor** on
the restated count rather than an equality: the population is the box's
and it moves.

**Live population here is still zero, and that is by design.** The tray
runs on this box, so the tray gate returns before adoption and
`desktop_notifications` stays empty — the feature is for the window
where the tray is down, which is the only window the understudy has ever
existed for.

**Deployed twice.** Migration 018 applied; the first restart (16:09:40,
PID 3830192 → 3859841) is what exposed the loop defect, and the second
(16:18:54, PID 3859841 → 3865932) carries its fix — verified over a full
sweep cycle: **0** `desktop_spoken_load_failed`, **0** loop errors,
sweeps firing at `interval[0:03:00]`. `schema_revision_verified revision:
018`, `/health` **200**, twelve jobs scheduled. Suite **2801**
(2792 + 37 − 28), ruff and mypy clean.

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
