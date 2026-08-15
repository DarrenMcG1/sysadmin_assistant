# Handoff — 2026-08-15

## Next action

Run `sudo systemctl restart sysadmin.service` to deploy Session 26c — until it reloads, `/api/units/status` serves no `ports` block and the first port sweep has not run — and then take an execution sitting that works `GET /api/units/actions` end to end rather than adding another detector.

## This session — Session 26c, port collision detection

`sysadmin/units/ports.py` answers the question estate-manager's audit is
**structurally unable to ask**. Their `live_listeners()` runs `ss -H
-tln` deliberately without `-p`, on the stated grounds that *"process
names need privileges for other users' sockets"* — true, and true only
of *other users'*. Measured as `gaddi` on 2026-08-15: **31 listeners, 24
attributed**, every registry-relevant port on the box named with its unit
**and its scope**, blank only for the root-owned and containerised ones
(5432, 1883, 631, 139/445, 8601).

Suite **1701 passed** (from 1653), ruff and mypy clean, **no migration**
— the block rides in `unit_audits.findings['ports']`.

### Three registries claim a port and only one cannot lie

That is the argument for the session existing here rather than in
estate-manager, and it was not in the plan — the plan said "collision
detection". The three are the estate's markdown table (18 rows, projects,
no units), this repository's `services.yaml` (**11 entries carrying
`port:` *and* `systemd: {unit, scope}`** — a hand-declared pair that has
existed since Session 35, is read by two different checks, and had never
been compared), and the kernel. This is the only party on the box holding
all three.

### Four comparisons, two families, and the split decides the surface

`wrong_unit` and `port_shared` are the box disagreeing with itself now —
one alert row per port, port in the title. `duplicate_claim` (invisible
to the estate because `claimed_ports` is a `set`) and `wrong_project` are
a document being wrong while the box is right — ranked advice, last in
`KIND_ORDER`. The armed-orphan split applied a third time, with
`COLLISION_KINDS` living in `ports.py` so the two surfaces cannot come to
disagree about which findings are faults.

### Everything came back clean, and that is the honest result

All 11 declared port↔unit pairs agree with the live cgroup map; no port
has two holders; no registry row is duplicated. *"Nothing on this box has
ever collided"* is now **verified with attribution** rather than
asserted. The one thing the check found is a registry row — 8500 is given
to `sysadmin-service`, which is neither the manifest id
(`sysadmin-assistant`) nor the directory (`sysadmin_assistant`). Recorded
as **evidence, not a finding**: a row may legitimately name a
third-party daemon (`_syncthing_` holds 8384), and telling a typo from a
daemon needs judgement this check does not have. Filed as
`SNAG-ESTATE-005` for its owner; not written into their repository.

### Verified live, because the family ships with zero rows

The estate judge's starting position, and the same answer to it. The
whole agent path ran against the real database in a rolled-back
transaction: the sweep stored the block, and a synthetic `wrong_unit`
gave raise → hold → resolve across three runs, with **0 rows of
residue**.

### One bug the tests caught that mypy could not

`select(Alert.title)` yields the titles themselves, and the dedup read
them as `row.title` — which on a `str` silently returns the bound
`str.title` **method** rather than raising. Every membership test failed,
so the family would have raised a duplicate row on every sweep. Found by
the "a standing collision writes one row" test on its first run, which is
the argument for writing that test at all.

### SNAG-UNITS-001 folded in, and its own premise is what changed

It argued a comment was the only honest fix *because* "this scan does not
know the unit's port". True of the sweep; no longer true of its siblings.
The snippet now emits `kind: http` with a real url and port when the unit
holds **exactly one** audited port, and keeps `kind: systemd` plus the
comment otherwise (zero ports, two ports — picking one is a guess — or a
timer, which holds no socket).

Two limits, both measured rather than assumed, and both filed:

- **Its population is empty today.** All 12 units holding an audited port
  are `monitored`, which `classify_units` drops before they become
  findings — SNAG-UNITS-002's two-thirds-invisible shape again. Driven as
  a counterfactual (pretending `alfred-backend.service` were unwired) it
  reproduces the hand-written entry exactly. This is advice for the
  *next* service wired up, which is what the tier is for.
- **The health path is a guess, and a worse one than I first wrote.**
  `/api/health` is the contract's, and counting every declared entry
  rather than the two in front of me gave the opposite conclusion: right
  for **4 of 11**, wrong for **7**. Kept anyway (`SNAG-UNITS-003`),
  because a wrong url fails **loudly** within one 300 s poll where `kind:
  systemd` under-monitors **silently and for ever** — the trade
  `schema_guard` makes by refusing to boot. The snippet names `/health`
  and `/api/v1/health` so the fix is an edit rather than an
  investigation.

### Decisions taken by the owner, not defaulted

All four comparisons ship (the owner added `duplicate_claim`, which I had
offered as the weakest); collisions get an alert row rather than advice
only; the check runs in the service-discovery agent with the block in
JSONB rather than a migration; and the SNAG-UNITS-001 fix is a real
`kind: http` rather than a comment.

### Rejected, with reasons

**Sharing estate-manager's parser**: `parse_registry` lives in
`estate_service`, which is the *service* — only `estate-lib` is a
dependency here — and the two parsers answer different questions anyway,
since theirs folds rows into the `set` that makes duplicates invisible.
**Deriving `audited_ranges` from their config**: the `base_url`
precedent — a cross-repository lookup goes silently quiet when the other
side reorganises, so it is duplicated and three conformance tests keep
the two honest, including one that fails if their `live_listeners()` ever
gains `-p` (at which point this module is a duplicate and should go).
**Re-detecting unclaimed listeners**: the estate detects, this repository
speaks, and Session 26b-A already gave those findings a voice — so the
sweep's attribution *enriches* their rows in `details` instead, read from
the stored sweep rather than a second `ss` call, and never entering the
title or message.

### Live state, checked rather than copied

Two open alerts in the whole table: one armed orphan
(`garmin-sync.service`) and the roll-up at 12 findings. `GET
/api/units/actions` offers **6 orphans, 5 host units and 13 restart
risks**, all with generated commands and none acted on. Three corrections
to what STATUS.md was claiming: `sportsanalyser-backend.service` is now
**enabled**, `pgbackrest-backup` is **wired** in `services.yaml` (so the
host list is 5 and no longer includes the estate's only database backup),
and the 2026-08-14 restart deployed both SearXNG and the restart family.

### Blocked, named rather than dropped

`SNAG-ESTATE-002`'s residual half — `judge_attention` has still never
been exercised against a populated `/api/projects/attention` payload, and
the producer's fix is delegated as estate-manager's `SNAG-ESTATE-010`.
`SNAG-ESTATE-005`, raised today, is likewise their document and their
fix.

## Next session — the ranked recommendation

**Sub-session action, separately and first**: `sudo systemctl restart
sysadmin.service`. Session 26c is committed and not deployed.

1. **An execution sitting — work `GET /api/units/actions` end to end.**
   Three consecutive sittings (46, 47, 26c) have gone on making the
   diagnosis *speak*, and the live box says nobody has answered: 6
   orphans (one armed and enabled), 5 unwatched host units, 13 units
   whose crash loop can never reach `failed`, 8 stale collations. That is
   `SNAG-ESTATE-001`'s shape one level up — the alarm rings and no one
   moves — and it would be the first sitting in a month that *removes*
   findings. It also tests the advice against reality, which nothing has:
   does a pasted snippet actually load, and does `restart_is_bounded`
   clear on the next sweep? `SNAG-UNITS-002`'s own last bullet names that
   gap.
2. **`SNAG-DB-002`'s `REINDEX` half.** The only open *correctness* risk:
   a B-tree built against glibc 2.43 can miss a row that is present,
   which presents as an alert that never deduplicates or never resolves —
   and this session added two more `title.like` lookups. Loses because it
   is a quiet window over two other apps' 16 GB of data rather than a
   session, and because the risk is a probability, not an observation.
3. **Session 27 (log aggregator tiers).** Loses outright: scoped against
   599,794 open rows, and the table now holds **2**. Sessions 25b/25c
   (reliability Tiers 2–3) lose behind it on the question this repository
   keeps answering the hard way — `GET /api/services/reliability` still
   has no consumer beyond the API.

---

## Previous session (2026-08-15) — SNAG-UNITS-002, fixed as advice rather than alarm

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
