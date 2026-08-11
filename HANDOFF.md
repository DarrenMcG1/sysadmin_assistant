# Handoff — 2026-08-11

## Next action

Take Session 36, the briefing envelope, which is unblocked and unstarted, and leave Session 32 alone until the SessionEnd hook appends a session log instead of overwriting the handoff, because without that the evidence it needs does not survive.

## Session 31: idle nudges, and one wrong premise caught by grep

Shipped: an `active` project whose human-written next action has not
changed for **7 days** raises an `info` alert; at **14** it is escalated
to `warning`. Per-project override is `idle_nudge_days` in
`.project.yaml`, beside `alert_threshold` and deliberately separate from
it — a long-cycle repository should be able to relax the commitment clock
without also going unwatched for a missing README.

**No new endpoint, no migration, no restart.** Nudges are `alerts` rows
(`Project <name> next action idle`) raised by the organiser, which is a
oneshot timer, so this goes live on the next timer run. That is the
distinction the previous handoff had to work out the hard way and it held
again here: the daemon serves start-time code, the organiser does not.

### Decisions, and what was rejected

- **7 days, not 5 and not 14-as-first-rung.** The three eligible projects
  turn their actions over in 1–4 days, so 5 is inside normal turnover and
  would nag. 14 as the *first* rung was rejected because a feature that
  can never be observed firing cannot be trusted.
- **Eligibility was extracted, not re-implemented.**
  `next_action.eligible_candidates` now serves both `GET /api/projects/next`
  and the nudge. Two copies of "what counts as a commitment" drift in the
  invisible direction: the endpoint stops offering a project while the
  nudge goes on reminding you about it.
- **Raise once per open nudge, not once per scan.** `raise_alert` inserts
  unconditionally — the mechanism behind SNAG-PROJ-004's 1,664 rows — and
  the organiser runs daily. The health-alert pattern would write one row
  per day per stuck project: a nag in the database rather than the tray.
- **Escalation resolves the quiet row and raises a loud one**, rather than
  updating severity in place. The tray fingerprints on
  `"{severity}:{title}"`, so an in-place change keeps a fingerprint it has
  already suppressed and the escalation is recorded but never spoken.
- **The escalation is a gap, not a multiplier.** A project that relaxes
  its threshold to 21 escalates at 28, not 42.
- **Never `critical`.** Criticals break through DND by configuration;
  waking someone at 02:00 about a roadmap item is how a monitor gets
  muted wholesale.

### What was checked rather than assumed

A live organiser run over 25 repositories reported
`nudges: {raised: 0, escalated: 0, resolved: 0}` — correct, because all
three eligible projects changed their next action that morning. **A clean
run proves only that nothing crashed**, so the ladder was then run over
the real historical series for this repo: the "Session 24: File organiser
tiers" action, **9 scans across 2 days**, which `streak_days` folds to one
2-day run and the ladder scores `info` / `warning` / no-nudge at the
thresholds it should. That 9-to-2 ratio is Session 29's days-not-scans
argument holding on live data rather than in a fixture.

**The design was written three times around the wrong config knob.**
`notifications.desktop.min_severity` looks exactly like the setting that
decides whether an alert is spoken, and **nothing in `sysadmin/` reads
`config.notifications.desktop`** — the live gate is
`tray.notify_min_severity` in a different section, which the tray parses
itself. Both currently read `warning`, so the two have never disagreed
and the redundancy has never surfaced. Filed as **SNAG-CFG-001** and left
unfixed on purpose: it sits on the tray's configuration boundary and this
session changed no notification code.

### State

- 43 new tests, suite **1701 → 1744**; `ruff` and `mypy` clean.
- Alerts table untouched by this run — nothing on the estate is stuck for
  7 days, so there is nothing to see in the tray yet. The first thing that
  will ever fire is an `info` row with no toast behind it.
- `docs/roadmap/tasks.md` Session 31 is ticked with the rejected options
  recorded; `STATUS.md` "Next up" now names Session 36.
