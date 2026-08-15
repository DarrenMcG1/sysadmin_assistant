# Handoff — 2026-08-15

## Next action

Run `sudo systemctl restart sysadmin.service` to deploy both the SearXNG entry carried over from 2026-08-14 and this session's restart-limit family, neither of which exists on the live API until the daemon reloads, and then take Session 26c (port collision detection) as the next roadmap session.

## This session — SNAG-UNITS-002, fixed as advice rather than alarm

17 of the 20 hand-written units on this box that declare `Restart=` have
a start limit their own restart cadence can never reach, so a crash loop
never enters `failed`, no `OnFailure=` hook can fire, and `systemctl
is-failed` reports nothing wrong. The estate-wide form of
`SNAG-ESTATE-001`, whose two PersonalAssistant units restart-looped
52,178 times in exactly that state.

Suite **1653 passed** (from 1631), ruff and mypy clean, **no migration** —
the family lives in the audit row's JSONB blob.

### The measurement changed the design before any code was written

The snag costed the fix as "one line per unit" under
`GET /api/units/actions`. Driving the real sweep in-process first showed
why that is not the cheap option it reads as:

| sweep category | unbounded |
|---|---|
| **`monitored`** | **11** |
| `orphaned` | 4 (all disarmed) |
| `host` | 2 |

`classify_units` drops `monitored` units before they become findings, so
**two thirds of the population had nothing to hang advice on**. The
detection had existed since Session 46 — `restart_is_bounded`, and
`restart_bounded` on every finding — and the question "which units here
can loop for ever" was answerable for six units and invisible for every
live service on the box. That is the same shape Session 46 removed for
armed orphans, one layer up.

### Three decisions taken by the owner, not defaulted

**Scope: all of them, whoever owns the unit.** The tier already advises
on units this repository does not own — every `unmonitored`/`host`
recommendation tells you to wire another project's unit. The estate rule
that bites is about *writing* into another repository, and a paste-ready
line served over a GET is a pointer. The `detail` names the owning
project so the reader knows whose edit it is; 11 of the 13 belong to four
other repositories.

**Surface: advice-only, count as evidence in the roll-up's `details`.**
Deliberately not added to `scan.actionable` — that is the roll-up alert's
title *and* the number `alert_threshold` is compared against, so 13
latent risks there would trip the threshold on their own and read as 13
new gaps to wire up. No alert family of its own, for the reason the armed
split was worth making: one row per unit is right for a fault in progress
and wrong for a latent one.

**Rank: second, above `unmonitored`.** The two are competing safety nets
and this is the stronger one — a wedged unit is seen as `unreachable`
only if something polls it, whereas a reachable start limit makes systemd
itself say so, to a hook, whether or not this service is running.

### Orphans are excluded, and that is the opposite of the obvious rule

A broken unit that also loops reads like the worst case and belongs here
twice over. It cannot: the orphan recommendation is *remove it*, and a
start limit on a file you should delete is two contradictory instructions
for one unit. Nothing is lost — an armed orphan that loops is exactly
what `armed_alert_severity` already promotes to `critical`. **The family
ships with 13, not 17.**

### The remedy is checked against the detection

`suggested_start_limit_interval` picks the smallest round window clearing
`RestartSec x (burst - 1)` by 1.5x, and a test feeds every live shape back
through `restart_is_bounded` requiring `True`. A second test appends the
emitted snippet to a real unit file and re-scans, which is the only thing
proving the two lines land in a section systemd reads them from.

That pairing is the one thing this family was closest to getting wrong.
Advice that clears a symptom without fixing the fault is precisely what
`ALTER DATABASE … REFRESH COLLATION VERSION` does in `SNAG-DB-002`, and
it is cheap to build here by accident. Where **no** window would help —
`RestartSec` beyond an hour, or `infinity` — it emits no snippet at all
and says to lower `RestartSec` instead, because a number that does not
work costs the family its reader.

**The margin cuts the opposite way from the intuition and has its own
test**: a *longer* `StartLimitIntervalSec` is a *stricter* limiter,
because more starts fit inside it. Anyone "tightening" it to be safe
would make the loop more immortal.

### The verdict is now checkable

`UnitFinding` carries `restart_sec`, `start_limit_interval` and
`start_limit_burst` — the three numbers `restart_bounded` was computed
from. Without them the boolean asks a reader to trust arithmetic they
cannot see, and the naive version of that arithmetic is wrong in **both**
directions (`personalassistant-backend` declares no burst and is
unbounded; a bare `Restart=always` declares no burst and is bounded).

### Verified live, then rolled back

The real sweep written to `unit_audits` and read back through the
router's rehydration: blob carries `restart_unbounded_count: 13`, the
arithmetic inputs survive JSONB, and `/actions` builds **25
recommendations — 6 orphan, 13 restart, 1 unmonitored, 5 host**. Residue
0; `unit_audits` still holds 50 rows with the same newest `scanned_at`.

## The live box, checked rather than assumed

- **Two deploys are owed on one restart.** The daemon has been up since
  2026-08-14 15:03:47; the SearXNG commit landed at 23:15 and this
  session's is later still. `/api/sysadmin/status` serves 25 services and
  no searxng, and the open roll-up alert reads `Unmonitored systemd
  units: 14 findings` where the current `services.yaml` gives 12 — the
  daemon is serving from the config it loaded yesterday afternoon
- **The alerts table is genuinely quiet**: 2 unresolved rows, both
  `warning`, both accurate (`garmin-sync.service` armed, and the
  roll-up). That is the whole of the 598,091-row era
- **`project_organiser` last ran 2026-08-13 07:35 and that is correct** —
  it left for the estate's 8400 service that day and remains in
  `AGENT_NAMES` only because the constraint is add-only
- **`file_organiser` has run 13 times in three days**, last 2026-08-14
  15:04. `SNAG-AGENT-003`'s "run once in its life" was cured by Session
  41's transaction split; the entry is still open and its symptom is not

## Next session — ranked

**Sub-session actions first, because neither is a session:**

1. `sudo systemctl restart sysadmin.service` — the whole deploy for two
   sittings' work. Two minutes, and `sudo` wants a password so it is the
   owner's
2. `systemctl --user enable sportsanalyser-backend.service` — carried
   from an earlier sitting, still not done

**Recommended: Session 26c — port collision detection.**

It wins on three things rather than priority. Its route is **already
decided and measured** (2026-08-14): `ss -ltnp` unprivileged attributes
every registry-relevant port, `/proc/<pid>/cgroup` names the unit *with
scope in the path*, and three alternatives are rejected with reasons — so
it is an implementation sitting, not a design one. It is the half the
estate is **structurally blocked from**, running `ss` without `-p`, so
nobody else will do it. And it extends what landed yesterday: Session
26b-A gave the audit's port findings a voice, and this supplies the
attribution that voice currently cannot make.

**Runners-up, and why each lost:**

- **`SNAG-UNITS-001` — the `kind: systemd` snippet has no marker saying
  it is the weaker of two shapes.** Directly adjacent to the file this
  session just rewrote, and the fix is one comment line. It lost because
  it is twenty minutes, not a session — but it should be **folded into
  26c**, which is the sitting that will know a port for every unit it
  looks at, and is therefore the one sitting where the comment could
  become a real `kind: http` suggestion
- **Session 27 — log aggregator tiers, taken with `SNAG-AGENT-002`.**
  Lost because its premise has evaporated. It was scoped against a table
  holding 599,794 open rows; Session 42's raise rule took that to 2, and
  the tiers were the workaround for a volume that no longer exists
- **Session 25b/25c — reliability Tiers 2–3.** Real feature work, and it
  loses on the question this repository keeps answering the hard way:
  who reads it. `GET /api/services/reliability` has no consumer beyond
  the API itself, so a narrative layer on top would be a third scorer
  nobody polls

**Named as blocked rather than dropped**: `SNAG-ESTATE-002`'s residual
half — `judge_attention` has never been exercised against a populated
`/api/projects/attention` payload, which has answered `{"health": [],
"nudges": []}` on every check including after an overnight scheduled scan.
It cannot be unblocked here; the producer's fix is delegated to
estate-manager as its `SNAG-ESTATE-010`. `SNAG-DB-002`'s `REINDEX` half
stays open by choice — it touches two other apps' data and wants a quiet
window and a human.
