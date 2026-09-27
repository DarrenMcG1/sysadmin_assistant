# Units and ports — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

`GET /api/units/*` is the service-discovery pair (Session 26): the sweep as
measured, and the sweep as ranked advice. Both are **GET-only and always
will be** — the fix for an unmonitored unit is an edit to a hand-curated
YAML file whose comments carry the reasoning, and the fix for an orphan is
`systemctl disable && rm`, neither of which a scheduled agent should do on
its own. A test asserts no non-GET route exists under `/api/units`.

**The sweep has two alert families, and the split is SNAG-ESTATE-001's
durable half** (Session 46). `ALERT_TITLE` is the rolled-up count of
everything worth doing eventually; `ARMED_TITLE_PREFIX` is one row per
**armed orphan** — a unit whose project is gone and which systemd will
nonetheless start. The roll-up cannot name anything, and that is the
whole defect: `Unmonitored systemd units: 17 findings` was open,
accurate and unread for eight days while two of those seventeen
restart-looped 52,178 times and stalled the kernel. The diagnosis was
complete, correct and machine-readable the entire time. A count is not
news.

**The "will it loop" test is arithmetic, not the presence of a
setting**, and the obvious rule is wrong in *both* directions.
`personalassistant-backend.service` declares no `StartLimitBurst=`, so
systemd's defaults apply (`DefaultStartLimitIntervalSec=10s`,
`DefaultStartLimitBurst=5`) — a limit **does** exist. It also sets
`RestartSec=10`, putting starts ten seconds apart, so five can never fit
inside a ten-second window: the limiter is unreachable and the unit
restarted 34,517 times without once entering `failed`. In the other
direction a bare `Restart=always` restarts every 100ms, five starts fit
easily, and the loop *is* terminal — so "no `StartLimitBurst=`" would
have opened a critical on most of this box's healthy services on its
first run. `restart_is_bounded` asks whether `RestartSec × (burst − 1) <
interval`, which is the sum Session 39 did by hand for `sysadmin.service`
(600s against 40s) and which `alfred-backend.service` also passes on a
hand-written `StartLimitIntervalSec=60`.

Both signals are **pure**, so `scan.py` keeps its no-subprocess promise:
`enabled` is an enablement symlink under a `*.wants/`/`*.requires/`
directory the sweep already walks (matched on link *name*, so a dangling
link left by an `rm` without a `disable` still counts), and the restart
keys are text it already parses. Agreed with `systemctl is-enabled` on
every unit on this box. What purity costs is `NRestarts` and `activating
(auto-restart)` — this says "armed to loop", never "has looped 34,517
times".

Five rules, three of them the opposite of the obvious implementation:

1. **Arming is orphan-only.** Every healthy service here is enabled and
   most restart unboundedly; an `armed` that meant "enabled" would alert
   on all of them. A *disabled* orphan is debt and stays in the roll-up
   — four of this box's six carry the PersonalAssistant shape exactly
   and are harmless only because someone disabled them.
2. **The sweep's exclusion set is what the run judged, not what it
   raised** — `sysadmin/estate/agent.py`'s rule, for its reason. Against
   a raised set a deduplicating family writes nothing on run two, has
   its still-true row swept, re-raises on run three, and each flip clears
   the tray's `{severity}:{title}` fingerprint.
3. **Escalation resolves the quiet row and raises a louder one**, and
   `step_for` refuses the reverse — an orphan whose `Restart=` is
   *softened* stays `critical` until it is actually removed, because a
   softer restart policy does not fix a start job that cannot succeed.
4. **`alert_threshold` does not govern this family.** That knob is
   patience for accumulated debt; an armed orphan is a unit failing on
   every trigger, and one of them is worth saying.
5. **A folded oneshot is armed by its *timer*.** Reading only the
   service's own enablement reports a live schedule as dormant.

`armed` is a **subset of `orphaned`** on `UnitScanSummary`, deliberately
outside the sum the model exists to make auditable, and its count is a
scalar in the `findings` blob rather than `len()` over the stored list —
that list is truncated at 200.

What this deliberately does **not** do is the general case:
`SNAG-UNITS-002` records that 15 of the 18 units on this box with a
`Restart=` policy cannot reach `failed`, including every live service
except `sysadmin`, `alfred-backend` and `alfred-frontend`. Fifteen rows
on the first run is the pile-up shape wearing a new hat.

**Three registries claim a port and only one of them cannot lie**
(Session 26c). `sysadmin/units/ports.py` is a sibling of `scan.py`, not
part of it — that module's no-subprocess promise is load-bearing and was
re-verified in Session 46. The three are the estate's markdown table in
`monitorable-project.md` (18 rows, project granularity, no units), this
repository's `services.yaml` (11 entries carrying **both** `port:` and
`systemd: {unit, scope}`, a hand-declared pair nothing had ever checked),
and the kernel via `ss -H -ltnp` → `/proc/<pid>/cgroup`.

estate-manager compares the first against the third and **stops one
join short of the interesting half**: its `live_listeners()` ran `ss`
deliberately without `-p` until 2026-09-13, on the stated grounds that
*"process names need privileges for other users' sockets"* — true, and
true only of *other users'*. Measured as `gaddi` on 2026-08-15: every
registry-relevant port on the box came back with a pid, and the cgroup
path names the unit **with scope in it** (`…/user@1000.service/app.slice/`
against `/system.slice/`) — the scope-aware identity `services.yaml`
already keys on, for free. Blank only for root-owned and containerised
sockets: 5432, 1883, 631, 139/445 and 8601.

**They added `-p` on 2026-09-13 and the answer did not move, which is
`SNAG-PORT-006`.** A test pinned their `ss` invocation on the reasoning
that *if the estate ever adds `-p` this module is a second implementation
of their check* — a **conjunction** (`-p` **and** attributes ports
itself) of which only the first limb landed. Their ADR-0166 joins the pid
to `/proc/<pid>/cwd` and resolves a registry **tree**; this module joins
it to `/proc/<pid>/cgroup` and resolves a **unit with its scope**, and
their `working_directory` refuses ours in writing (*"reading either as
ground truth would make this check verify its registry against another
repository's document"*, their §4). The two separate on this box: **21 of
the 29** ports `ss` names a process for have a unit here and no tree
there. So a flag was pinned where the claim is about a **verb**, and the
instrument is `tests/test_estate_port_join_live.py` now: it blinds their
directory reader and requires their whole check to resolve nothing,
driven at both `attribute` and `run_check` and controlled against a
stand-in that models the fix.

**Four comparisons in two families, and the split decides the surface.**
`wrong_unit` (services.yaml says port P is unit U; the cgroup says V) and
`port_shared` (two units, one port) are the box disagreeing with itself
now — one alert row each, port in the title. `duplicate_claim` (two
registry rows, one port — invisible to the estate until 2026-09-13,
because `claimed_ports` is a `set` and the fold came first; their
ADR-0168 asks the rows before folding and files `claimed_by_more_than_one_row`
at `warn`, which `JUDGED_AUDIT_CHECKS[PORTS_CHECK] = "breach"` does not
read, so the surface is unmoved and only its reason changed) and
`wrong_project` (the table's project against the one the
sweep matched the holding unit to) are a document being wrong while the
box is right — ranked advice, last in `KIND_ORDER`. That is the
armed-orphan split applied a third time, and `COLLISION_KINDS` lives in
`ports.py` rather than in the agent so the alert family and the advice
list cannot come to disagree about which findings are faults.

Six rules, four of them the opposite of the obvious implementation:

1. **Not-knowing is never a finding, and this fails _open_** — the
   `collation.py` posture, not `schema_guard`'s. An unattributed listener
   is compared against nothing; 8601 alone would otherwise produce a
   false positive on every sweep. A registry row naming something that is
   no project here (`_syncthing_`, and today `sysadmin-service` for 8500)
   lands in `unknown_registry_projects` as evidence: "wrong project" and
   "not a project" are different faults and only the first is ours.
   Filed as `SNAG-ESTATE-005` for the owner, never fixed here.
2. **A failed observation is not an empty one.** `ss` missing yields a
   report carrying the error and no findings, and `_maintain_port_alerts`
   then neither raises nor sweeps — the estate judge's rule 2, because a
   sweep scoped to a payload nobody received closes every row on the
   strength of not having looked. The registry half degrades separately:
   an unreadable document costs the two document comparisons and leaves
   the two live ones working, carried as `registry_error` beside `error`.
3. **A dual-stack listener is one holder.** A port bound on v4 and v6
   prints twice with the same pid, so `(port, pid)` is deduplicated —
   without it `port_shared` fires on every dual-stack server on the box
   and the family's first live run is entirely false positives.
4. **The port is the identity, never the kind.** Two kinds on one port
   are one thing to go and look at; a title carrying the kind forks the
   row the day a second kind arrives. Session 46's rule and
   `judgements.py` rule 5 meeting from opposite directions.
5. **The sweep's exclusion set is what the run judged**, not what it
   raised — the third time this repository has written that down.
6. **No escalation ladder, deliberately.** `critical` is what the tray
   leaves on screen and is reserved for a fault costing something now;
   this family has never had a member on this box, and a ladder tuned
   against zero observations is a guess with a number on it.

Verified live rather than only against fixtures, because the family
ships with **zero rows** — the same starting position as the estate
judge's. The whole agent path was driven against the real database in a
rolled-back transaction: the sweep stored `ports` with 31 listeners, 24
attributed and 12 units holding an audited port; a synthetic `wrong_unit`
then gave raise → hold → resolve across three runs, with **0 rows of
residue** after rollback.

`GET /api/units/status` gains `port_findings`, `port_collisions` and
**`ports_checked`**. The last one is the point: a sweep whose `ss` call
failed reports zero findings, and zero-because-clean must not be served
as the same answer as zero-because-blind. Every sweep stored before
Session 26c reports `false`, correctly.

The estate judge reads the sweep's attribution rather than running `ss`
itself, and that is a deliberate cross-domain read: two calls at two
moments (hourly judge, six-hourly sweep) would give two answers to one
question with neither surface saying which it used. The holder goes in
`details` and **never** in the title or message — the row's identity
belongs to the producer — and carries `observed_at`, so a five-hour-old
attribution says so. Absent attribution changes nothing; the enrichment
must never become a dependency of the alert.

`UnitRecommendationInfo` carries **no score or size field**, unlike its two
siblings. `RecommendationInfo` ranks by health-score points and
`FileRecommendationInfo` by reclaimable megabytes — both directly
measurable. Nothing makes two host units meaningfully "twice" one orphan,
so ranking is by `kind` (`orphan` → `unmonitored` → `host`) and no number
is invented to sort on. The one sub-ordering, added in Session 46, is
`armed` orphans ahead of dormant ones — a measured fact about whether
systemd starts the unit, not a score, and it does not make the tiers
comparable to each other.

**Advice has to be executable, and Session 48 was the first sitting to
carry it out.** Sessions 46, 47 and 26c made the diagnosis speak; nobody
had run what it says. Two defects surfaced inside an hour, both the same
root cause — `recommendations.py` under-reading a `UnitFinding` the sweep
had already filled in (`SNAG-UNITS-004`).

**A snippet is offered only for a unit something starts.** `kind:
systemd` asserts the unit is *active* and `kind: timer` that the schedule
is armed, so wiring up a disabled unit declares a check that fails on
every poll for ever — measured: the two suppressed snippets would each
have written a `critical` **every 300 s**, the pile-up Sessions 41–45
spent themselves deleting, arriving through this module's own remediation
text. The gate is **"nothing enables it", not "it is not running"**:
`enabled` is an enablement symlink `scan.py` already walks and
`classify_units` folds a oneshot's timer enablement into it, so the
no-subprocess promise survives where an `ActiveState` test would have
cost it. `manual` is a subset — no `[Install]` means it cannot be
enabled — so it is tested first and keeps its wording.

**A folded oneshot's timer is removed with its service.** `monitor_unit`
names the timer, and the timer is the half carrying `[Install]`, so it
holds the enablement symlink `removal_command`'s docstring exists to
avoid orphaning. Removing only the service leaves a `Requires=` pointing
at nothing, which the next sweep cannot see — a timer with no service is
not a finding shape this module has.

Both imply the rule that closes the family: **a row offering no snippet
must never say "paste the snippet below"**. `sysadmin-failed.service`
shipped exactly that, which is an item an execution sitting *cannot
close*, so it returns on every sweep for ever — `SNAG-ESTATE-001`'s
roll-up defect wearing a single unit's name. Every no-snippet row now
names its real next step, and for a disabled unit that step is a fork.

Note the polarity trap the fix exposed: `UnitFinding.enabled` defaults to
`False`, which is right for `armed` (absent evidence reads as "not
armed", quiet) and the **opposite** of what this gate wants (absent
evidence suppresses advice, loud). One field, two consumers, opposite
safe defaults — fixed in the fixtures, because flipping the default would
quietly arm every orphan.

**The snippet knows a port now** (SNAG-UNITS-001, fixed in Session 26c).
A `kind: systemd` check asserts only that the unit is *active*, so a
backend running while every request 500s is active, healthy, and broken.
The snag reasoned that a comment was the only honest fix *because* "this
scan does not know the unit's port" — true of the sweep, and no longer
true of its siblings. The entry now emits `kind: http` with `url:` and
`port:` whenever the unit holds **exactly one** port in the audited
range, and keeps `kind: systemd` plus the comment otherwise: zero ports,
two ports (picking one is a guess), or a timer, which holds no socket.

Two honest limits, both measured rather than assumed. Its **population
is empty today** — all 12 units holding an audited port are `monitored`,
which `classify_units` drops before they become findings, the same
two-thirds-invisible shape SNAG-UNITS-002 hit; driven as a
counterfactual it reproduces the hand-written `alfred-backend` entry
exactly. And the **health path is a guess**: `/api/health` is the
contract's, right for 4 of the 11 declared entries here and wrong for 7.
Kept anyway (`SNAG-UNITS-003`) because a wrong url fails loudly within
one poll while `kind: systemd` under-monitors silently for ever — the
trade `schema_guard` makes by refusing to boot.

Three rules the detector encodes, each learned from the live estate:

1. **Distro units are filtered by `is_symlink()`, not a package query.**
   `systemctl enable` installs a symlink into `/usr/lib/systemd/system`, so
   every packaged unit under `/etc` is a link and every hand-written one is
   a real file. No subprocess, and it works off Arch.
2. **A `Type=oneshot` service is reported under its timer.** A oneshot is
   `inactive (dead)` between runs by design, so monitoring the service
   alerts continuously — the rule config.yaml already records by hand for
   `alfred-evaluate`. The finding is keyed on the *service* (which holds
   `WorkingDirectory` and `ExecStart`) with `monitor_unit` naming the
   timer, and the timer suppressed, so one schedule yields one finding.
3. **Scope is part of a unit's identity.** `deadlock-api-ingest.service` is
   installed as both a user unit and a system unit here, running two
   different binaries; wiring one says nothing about the other, and the
   generated config.yaml `name:` gains a `-user`/`-system` suffix so two
   tray tiles cannot share one label.
