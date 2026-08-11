# Handoff — 2026-08-11

## Next action

Run `sudo systemctl restart sysadmin.service` so the daemon serves the new `GET /api/projects/momentum` route alongside the desktop notifier wired earlier today, then decide whether alfred-glance should consume the momentum headline before starting Session 36, the briefing envelope.

## Session 32: the blocker named the wrong evidence

`GET /api/projects/momentum` ships — how often a session starts in a
repository and nothing ships.

Session 32's recorded blocker was "the SessionEnd hook overwrites
`docs/sessions/handoff.md`, so session history does not survive", with
two candidate fixes: an append-only `docs/sessions/log.jsonl` written by
the hook, **or** sysadmin recording handoff-date transitions per scan.
The second had been true since 2026-08-06. Session 28 writes
`handoff_age_days` on every scan, so `scanned_at − handoff_age_days`
reconstructs the date a handoff was written, and a change in that value
between two scans *is* an observed session. No hook, no writer, no
migration, no new table. The record exists at all because
`~/.claude/hooks/require-handoff.sh` is a **Stop** hook that blocks a
code-changing session until `HANDOFF.md` carries today's date — the
session log is a side effect of a guard rail.

**The measurement rule was wrong first, and the live series is what
showed it.** Attributing a landing at the scan that first saw the new
handoff reads as common sense and is wrong, because the handoff is
written *before* the work is committed. The scan at `2026-08-10 09:06`
saw this repository's new handoff while `last_commit_at` still read
2026-08-08; that day's six commits arrived afterwards, and a productive
day was scored as dropped. Scan timing was deciding the answer. A commit
dated in `[session_date, next_session_date)` is now that session's
output, which is independent of when the scanner happened to look.
`test_a_commit_after_the_scan_still_counts_as_landed` exists so this
cannot come back — and note that no fixture with an even cadence would
have caught it.

A second correction came from the same run. `observed_from` reported the
first scan rather than the first *dated* scan, so this repository's
series read as running from 2026-05-13 when only 22 of its 198 snapshots
carry a roadmap block. Five sessions over "three months" is a different
claim from five sessions over five days, and nothing in the response
said which one it was.

## Decisions taken, and what was rejected

**Both landings are reported.** `dropped_code` is a session that shipped
no code; `dropped` is one that shipped nothing at all; `docs_only` is the
gap. Summing them would erase the difference between a session that
wrote up what it decided and one that went quiet. This needed no scanner
change and no backfill: `findings['git']` is written **only when** a
housekeeping commit was skipped — 77 rows of 3,635 — so its absence
means the newest commit *is* the newest code commit, and the fallback to
`last_commit_at` is exact rather than approximate. That was checked in
`get_last_code_commit_date` before being relied on, because the same
absence could equally have meant "not recorded".

**A new endpoint rather than an alert or a board field**, chosen
deliberately: it ranks the estate and carries a `worst` headline with a
prose `reason`, the same accountability obligation `/api/projects/next`
has. The list is invisible to a one-line consumer, so the sentence is
where the choice defends itself.

**The population is `ACTIVELY_SCORED`** (`active` + `undeclared`),
imported from the agent rather than restated. It is deliberately *wider*
than `/api/projects/next`, which additionally requires a stated next
action: a commitment needs someone to have written one down, whereas a
session that shipped nothing is a fact about a repository whether or not
it has a plan. `ImbaBots` is `undeclared` and is measured for exactly
that reason.

**Rejected: making the count look firmer than it is.** Every figure is a
lower bound and the field names say so. A session that changed no code
never wrote a handoff and was never observed; two sessions on one date
collapse into one; the oldest observation is a state rather than a
transition, so the session behind it is uncounted — the same rule
`build_narrative_history` applies to `next_action_changed`, and for the
same reason (calling the first point a change invents an event whose
existence depends on `limit`).

## What it says about this estate

Verified against the live database before the endpoint was believed, and
it disagrees with the health scores:

| Project | Sessions | Landed code | Dropped |
|---|---|---|---|
| `alfred-glance` | 2 | **0** | 2 |
| `venture-assistant` | 3 | 1 | 2 |
| `sysadmin_assistant` | 5 | 4 | 1 |
| `Alfred` | 4 | 4 | 0 |
| `ImbaBots` | **0 measured** | — | — |

`alfred-glance` has opened two sessions since 2026-08-09 and its last
code commit is 2026-08-03. This repository's single drop is 2026-08-09,
and `git log` confirms zero commits that day — the rule was checked
against ground truth rather than trusted.

## Blocked, and left open on purpose

**`ImbaBots` measures zero sessions, and that is the right answer** —
but only after opening the repository, which is the lesson. It was first
written up here as "commits without ever moving its handoff date, so
either the Stop hook is not firing or that work is not done through
Claude Code sessions". Both alternatives are false, and reasoning from
the endpoint's own output instead of from the repository is what
produced them.

ImbaBots' last session is `edbd8c2` (2026-08-07 12:03), which changed 22
`game/` files **and** `docs/handoff.md` in one commit — the habit was
kept. Its first scan in the window falls after that commit, so 2026-08-07
is its **baseline**: a state, not a transition, and therefore uncounted
by design. The only later commit, `7144fc5` on 2026-08-10, is the estate
migration promoting `docs/handoff.md` to the root, run from *this*
repository.

**The residual defect is real but elsewhere**, and is now
`SNAG-PROJ-013`: ImbaBots' first heading is `# Handoff — M5 (Tier 2) ·
⚠ …` with no `YYYY-MM-DD`, and `require-handoff.sh` greps the first
heading for today's date — so **the next code-changing session there
will be blocked until someone adds one**.

**That one-line fix was started and then deliberately abandoned**, which
is the more useful record. The hook fires on *any* dirty tree or commit
that day, not only code, and demands **today's** date — so editing
ImbaBots on a day nobody worked there writes a handoff for a session
that did not happen. On the next scan that is a handoff-date transition,
i.e. a **phantom session in the endpoint this session just built**; and
because `docs(…)` is not in `code_commit_ignore`, the doc commit itself
would set `last_commit_at` to that day and the phantom would read as
*landed*. The `unverified` machinery exists to stop mtime inventing a
session, and back-writing a date does the same thing on purpose. Adding
`docs(handoff)` to `code_commit_ignore` to soften it was rejected too:
it changes staleness measurement estate-wide to accommodate one edit,
and the row is still a phantom.

So ImbaBots is left alone. The hook will stop its next real session, on
a real date, and its block message already says the first heading must
carry today's date — the mechanism working rather than a trap. Close
`SNAG-PROJ-013` when a dated ImbaBots handoff appears.

**Every session currently reads `unverified`.** `handoff_date_source` is
recorded from today and the organiser has not run since, so no observed
session yet carries the field and the hedge in `reason` is
unconditional. Re-read the endpoint after the next timer run; if the
hedge is still on every row a week from now, something is wrong with the
scanner half.

**Nothing consumes this.** It is a GET with a headline sentence built
for a one-line surface, and alfred-glance is the obvious reader — but
Session 30 was closed unbuilt because its consumer declined the arc, so
ask before assuming.
