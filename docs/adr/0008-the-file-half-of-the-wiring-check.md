# ADR-0008: The file half of the `wiring` check crosses the seam; the other half does not

Decided 2026-09-08, Session 201, answering estate-manager's cross-repo
message `ecceab5e-2a9c-4e02-a3d0-be763ad313eb` (filed 2026-09-08, before
the commit that carried the change it announces) and the owner's
recommendation recorded in their
[ADR-0132](../../../estate-manager/docs/adr/0132-the-estate-owns-dotfiles-and-may-wire-a-hook.md)
§6.

**Half taken, half declined.** `settings_unparseable` and
`settings_not_an_object` are read here now —
`sysadmin/estate/hook_wiring.py`, judged by `judge_hook_wiring` on a
sixth surface. `hook_not_wired` and `hook_wired_undeclared` stay with the
estate and are still judged here off `GET :8400/api/audit/findings`, as
[ADR-0006](0006-wiring-joins-ports.md) admitted them.

The recommendation was to move the **whole** check. That is declined,
and §2 is why: a move relocates the *comparator* and leaves both
*operands* the estate's, so a green result would have meant exactly what
it meant before. The split is not a smaller version of the
recommendation — it is aimed at a different half of the check, and it is
the half where independence is actually recoverable.

---

## 1. What moved on 2026-09-08, and the half of it the message did not frame

*(Recorded by the session 2026-09-08.)*

Their ADR-0132 made two rulings in one sitting, and both reach this
repository. The message frames the first; the second is the one that
falsified sentences in **this** repository's source.

**Ruling 1 — the estate may write `settings.json`'s `hooks` key.** So
[their ADR-0067](../../../estate-manager/docs/adr/0067-the-wiring-of-a-hook-is-a-claim.md)'s
justification for the check — *"the only check whose subject the estate
can neither write nor repair, which is why nothing had ever looked"* —
is false for that key, and the check partly audits its own writes. That
is what the message is about.

**Ruling 2 — `~/projects/dotfiles` is a registry project at `status:
active`.** Measured here rather than taken: `~/.claude/settings.json` is
a **symlink** to `/home/gaddi/projects/dotfiles/claude/settings.json`
(since 2026-09-06), and that tree carries `.project.yaml` at `active` as
of today. ADR-0006 §1 admitted `wiring` on a six-clause ownership test
whose **first clause** was *"the file is in no repository at all, not
merely unowned within one"*. It is in one now.

So two of six clauses moved on one day, by one ruling each:

| clause | 2026-08-30 | 2026-09-08 |
|---|---|---|
| no repository owns it | in **no repository at all** | **false** — `dotfiles` owns it |
| estate-wide by construction | yes | unchanged |
| the estate may not alert | yes | unchanged |
| repairable only by the owner | yes (their ADR-0024) | **false** for the `hooks` key |
| this service raises nothing about it itself | yes | unchanged — re-measured, nothing under `sysadmin/` or `sysadmin_tray/` reads `~/.claude`; six mentions, all prose |
| **nobody says it at all** | yes | **unchanged, and it is the clause that decides** |

The last one was re-measured rather than carried: this module is still
the only consumer of `GET /api/audit/findings` outside the estate's own
publisher, and `dotfiles` carries `docs/roadmap/` and **no `docs/adr/`**
— so a `wiring` finding filed against it lands in a surface with no
reader and a repository with no process for it. The judging stays,
therefore, but **it no longer rests on the argument that was written
down**, and three sites in `sysadmin/estate/judgements.py` asserted the
two clauses that went. Those are corrected in the same commit, which is
work owed whichever way the check question was answered.

## 2. Why moving the whole check restores nothing

*(Recorded by the session 2026-09-08. This is the decisive section and
it is the part the recommendation could not contain, because it is a
fact about what the check computes rather than about where it lives.)*

The check compares two operands:

- **A** — each hook script's `# estate-hook-event:` declaration, in
  `estate-manager/hooks/`, estate-owned by adoption (their ADR-0021);
- **B** — `~/.claude/settings.json`'s `hooks` key, estate-writable since
  ADR-0132.

and a **comparator** — `run_check`, which resolves A's declarations
against B's commands through the symlink and files a finding per
disagreement.

ADR-0132 removed the independence of **operand B**. Moving `run_check`
into this repository changes who performs the **comparison**. Both
operands stay the estate's. *A comparison of two statements by one
author is not made independent by changing who does the comparing.*

**Today's commit is the specimen, and it is not hypothetical.**
estate-manager built `memory-index-notice.sh` on the morning of
2026-09-08, wrote its `# estate-hook-event: Stop` declaration, wrote the
matching `Stop` entry into `settings.json` (`dotfiles` commit `54247f8`),
and its own check then reported **0 findings with all six hooks
`WIRED`** — their ADR-0132 §8. Run from this repository, against those
same two files, it reports 0 findings too. The instrument is compromised
at its inputs; the code's postal address is not what fixes it.

That shape has a name in this repository already. ADR-0006 §2 refused
admitting `wiring` by name alone because it would have been *"correct,
green and inert"*; a whole-check move is the same object one level up —
it would have closed the estate's row, cost a working seam, and delivered
nothing measurable.

**The independence that was lost is also narrower than it reads.** The
owner was never an independent *author* of operand B: their ADR-0067 §1
records that estate-manager's own `tasks.md` *"hands them the exact JSON
block to paste into it"*. The owner was a **transcription channel**. What
ADR-0132 removed is the transcription step — so the failure class the
check was built for, an owner mis-pasting an estate-authored block
(2026-08-25, a top-level key and a missing `]`), is **designed out for
this key rather than left unwatched**. The class that is genuinely
uninstrumented — the estate writing A and B consistently *wrong* — was
uninstrumented before ADR-0132 too, because the check has never asked
whether a declaration is *correct*, only whether two statements agree.

## 3. Where the line falls, and why it falls at the inputs

*(Recorded by the session 2026-09-08.)*

The check's four codes do not take the same inputs, and that is the whole
of the split:

| code | severity | inputs | owner |
|---|---|---|---|
| `hook_not_wired` | `warn` | declarations **+** `settings.json` | estate |
| `hook_wired_undeclared` | `info` | declarations **+** `settings.json` | estate (and never judged here) |
| `settings_unparseable` | `warn` | `settings.json` **alone** | **here** |
| `settings_not_an_object` | `warn` | `settings.json` **alone** | **here** |

The bottom two need no statement of the estate's at all, so an
independent party genuinely can hold them — and they are the two carrying
the consequence the check exists for: a file that does not parse takes
**every** hook on this box down, the blocking `Stop` one included, and no
hook can report it because they all fail open.

The top two cannot be held independently by anyone while one party writes
both operands, and taking them here would additionally make this
repository parse `estate-hook-event:` — a format estate-manager owns and
has already changed once (`aspect`, and `none` as a legitimate value).
That is `SNAG-ESTATE-002`'s rule: splitting a producer's format is this
repository parsing something the estate owns.

## 4. The four rules the implementation encodes

*(Recorded by the session 2026-09-08. Three are the opposite of the
obvious implementation.)*

1. **It is a surface, not a special case.** `read_settings` returns a
   `SurfaceResult` and the agent merges it into the same map the five
   pulls land in, so `read`, `unread`, `_judge`, `_resolve_gone` and
   `by_surface` all reach it with no branch of its own. A special case
   would have had to restate every one of those rules, and the first one
   a later session forgot would be the one that mattered. It also buys
   the property the split exists for: **8400 being down does not blind
   the local read**, which is pinned by a test.

2. **"Cannot look" and "looked, and it is broken" are different
   answers, and the surface already had the vocabulary.** An unreadable
   or absent file yields `error` — the surface is unread, so nothing is
   raised *and nothing is swept*; a present-but-broken file yields a
   payload, because that is a fact about the box rather than about this
   reader's reach. The estate's own check draws the line in the same
   place for the same reason (their ADR-0016 §3), which is what let a
   local read slot into a contract built for HTTP with no second
   vocabulary invented for it.

3. **A sixth surface, which ADR-0006 §7 refused — and the refusal is
   superseded by its own stated reason.** That reason was *"it arrives
   in the same payload from the same HTTP call, so it is one surface"*.
   This half no longer arrives in that payload at all. Folding it into
   `audit_findings` would let a successful pull of 8400 resolve a row
   raised from the local filesystem, which is precisely the "resolving on
   unknown" the per-surface scoping exists to prevent. The partition had
   to move with it: `audit_findings`' wiring pattern narrows from
   `Estate hook %` to `Estate hook % not wired for %`, and a pattern left
   wide is one of the eleven falsifications below.

4. **The severity is cited, not recomputed.** ADR-0006 §3 rule 4 already
   considered `critical` for *this exact fault* and refused it. The fault
   has not changed; only who observes it has, so the rung is inherited
   rather than re-argued — a second derivation of one policy is what this
   repository's docstrings call `SNAG-DB-003`'s shape.

## 5. What the live drive found that reading could not

*(Recorded by the session 2026-09-08.)*

The family ships with a **zero-row population** — `wiring` has filed zero
findings in its whole history (938 across 262 runs to 2026-09-03; the
live audit on 2026-09-08 serves 13 checks and 5 findings, `docs` ×2,
`ports` ×2, `vram` ×1, and none of them `wiring`) — so it was driven
against the real file rather than only against literals. Two things came
out of it that no fixture would have said:

- **The fault sentence stated its position twice.** Composed as
  `f"{exc.msg} at line {exc.lineno}"` — which is what the estate's check
  does — a truncated `settings.json` reads *"Unterminated string starting
  at **at** line 671"*, because several of json's messages already end in
  "at" and expect the position to follow. `str(exc)` is the exception's
  own sentence and composes for all of them. Recomposing it by hand was a
  second statement of the producer's format, and the doubling only
  appears on the messages that carry a position, so a hand-written
  fragment never shows it. **The estate's check has the identical
  doubling**, reported back in the close note as an observation.

- **The row has a trap to carry and it is one day old.** The live read
  resolves to `/home/gaddi/projects/dotfiles/claude/settings.json`, so
  the obvious fix edits a file whose changes are tracked in a repository
  the editor was not told about. `details['resolves_to']` and the message
  name it — `monitor/collation.py` rule 4's *"the remedy's trap is
  carried in the alert"* — and only when the read actually resolved
  somewhere else, so the sentence cannot assert a symlink that is not
  there.

**Eleven mutations were driven and eleven killed by the test written for
each**, checked by failing-test name rather than by exit status: a
mutation killed by an unrelated test is not a guard. The one worth
naming is reporting a broken file as `error` instead of a payload — the
fail-*wrong* direction, which would make the surface unread and the one
fault this family exists for silent.

**Another entry's control had to be measured, not assumed.**
`SNAG-ESTATE-009`'s test asserted the probe's sweep saw exactly
`{"audit_findings"}`, and the sixth surface legitimately joins that set.
All **29** `check-snag-claims` verdicts are byte-identical either side of
this change, so it is a premise that had gone too narrow rather than a
control the fix broke; the assertion now names the four estate surfaces
the probe declines, which is what it was always about.

## 6. The limits, stated rather than implied

*(Recorded by the session 2026-09-08.)*

- **A `wiring` finding with no usable `event` is now skipped, which
  reverses a fail-open posture.** Two things can produce one — a
  file-level finding (now ours by a different route) and a malformed
  per-hook finding — and they are **indistinguishable on the wire**,
  because `code` has no column on `AuditFinding` (`SNAG-ESTATE-006`). So
  one rule must cover both. The per-hook half is empty by the
  *producer's* construction, read from their source: `declared_hooks`
  drops empty tokens, so `DeclaredHook.events` holds only non-empty
  strings, and `hook_not_wired` is emitted inside `for event in
  hook.events`. A third title for a shape the producer cannot emit would
  be machinery invented against zero.

- **The estate will go on filing the two file-level codes and nothing
  will judge them.** That is deliberate — two owners of one lifecycle
  would have the two surfaces' sweeps disagree about when to close a row
  they both title `WIRING_FILE_TITLE` — and it is recorded in the code
  rather than left as a silence, which is `SNAG-CFG-001`'s shape.
  Retiring them is the estate's call and is recommended to them by
  message, not assumed.

- **This repository cannot see a disagreement about *which file*.** The
  estate's check reads a configured path and this reads a constant. If
  those ever part company, both report cleanly about different files and
  nothing says so. Empty population today — measured, they resolve to
  the same file — and filed as `SNAG-CFG-007`.

- **`WIRING_FILE_TITLE` was renamed** from *"Estate hook wiring
  unreadable"*, because *unreadable* became precisely the case that
  raises **nothing**. A title is an alert's identity and renaming one
  orphans every open row carrying it; that is free here and never will be
  again, on the zero-row measurement above.

## 7. Rejected

*(Recorded by the session 2026-09-08.)*

- **Move the whole check, as recommended.** §2. It relocates the
  comparator and not the operands, so a green result would mean exactly
  what it meant before — correct, green and inert — while costing the
  ADR-0005 swap on the half where the estate's declarations are genuinely
  the right input.
- **Decline entirely and state the residual.** A complete answer, and it
  was this session's own first recommendation. Refused because it treats
  the check as one indivisible thing, which §3 shows it is not: two of
  its four codes take an input no estate statement reaches, and declining
  leaves an instrument unheld that could be held.
- **Build it and leave it unwired until the estate retires its half.**
  Correct, green and inert again, and dependent on another repository's
  timetable. Narrowing on the **consumer** side is entirely within this
  repository's authority — `JUDGED_AUDIT_CHECKS` is ours — so one speaker
  arrives immediately and the estate's retirement becomes tidying rather
  than a blocker.
- **Judge both producers until the estate drops its half.** Two owners of
  one lifecycle; both rows carry one title, so dedup hides the
  duplication and the two sweeps disagree about the close.
- **A config leaf for the settings path.** A knob with exactly one legal
  value is `SNAG-CFG-001` at the size of a setting. The function takes a
  path, which is what makes it testable without one.
- **Also detect "the `hooks` key is missing entirely".** That is the
  2026-08-25 top-level-paste shape, and naming *which* hooks are
  unwired needs the estate's declarations — §3's line, walked from the
  other side.
