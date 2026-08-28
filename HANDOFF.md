# Handoff — 2026-08-28

## Next action

Decide `SNAG-AGENT-009` by measuring its population first — drive `_maintain_port_alerts` and `EstateJudgeAgent._execute` across a run where the *state* moves under a held title and count how many open rows on this box currently carry a message that no longer describes what they are about, because the entry is `P3` on a guess and the three candidate remedies it names are not comparable until that number exists.

## Session 108 is complete — the blocker was gone, the family was three times bigger, and the name never carried the fact

`SNAG-PORT-003` is **closed** and `SNAG-AGENT-009` opened; the live
parser reads **97 → 98 entries with open unmoved at 23**. Suite
**2755 → 2750** (2755 − 18 + 13), ruff and mypy clean, all nine ops
claims ok. Daemon restarted **10:37:40**, `/health` 200 — owed this
time, unlike Session 107's. No migration.

### What the sitting settled

- **The entry's own framing was the smaller half of its defect.** It is
  filed as a *D-Bus* fault with a population of one, deferring itself
  for want of *"a second instance to tell a rule from a coincidence"*.
  `$XDG_RUNTIME_DIR/systemd/transient` holds **eight** runtime-created
  services: three bus-named and **five** `app-*@<32-hex>`. The second
  instance was there when the entry was written and was a **different
  shape**, which is precisely what makes a rule tuned to the first the
  coincidence.
- **Both named fixes are refuted by the count, and by which units were
  listening.** A `dbus-` prefix reaches 3 of 8; `:N.N` reaches 2,
  because `dbus-:1.21-org.a11y.atspi.Registry@0.service` sits beside
  `:1.2` and refutes the entry's own spelling of the pattern it
  rejects. Both leave `app-steam@455b2e51….service` (27036, 34223,
  46847, 57343) and `app-appimagekit_…@….service` (36577) — `.service`,
  colon-free, and holding ports on the day the entry recorded a
  population of one.
- **No name rule could have worked, which is the durable half.**
  `app-steam@455b….service` and `syncthing@gaddi.service` are the same
  shape. Separating them means deciding a 32-hex instance is special —
  `systemd-run`'s convention, which is the format-someone-else-owns
  objection the entry raised against `:N.N`, met from the other side.
  The name does not carry the fact, so the fix had to stop reading it.
- **The third fix is systemd's own answer and it is added, never
  substituted.** `runtime_unit_names` lists both managers' transient
  directories — the same class of signal `discover_units` reads for
  enablement, no second subprocess — and `observe_listeners` stamps
  `Listener.runtime_created`. The obvious reading is to *replace* the
  suffix test; `init.scope` refutes it, reporting `Transient=yes` from
  both managers while appearing in **neither** directory. So the listing
  is a proxy that under-reports, and additive cannot subtract.
- **Stamped at observation, not derived in the property**, so
  `judge_ports` stays pure below `observe_listeners` — the promise this
  module makes in its first paragraph. Nothing in production rebuilds a
  `Listener` from storage, so the stamp cannot go stale in a consumer.
- **The handoff's second question answered: no.** The entry predicted a
  new title every login; `port_alert_title` is keyed on the **port**, so
  the row dedups and what churns is the message. That makes the entry
  *less* urgent and the fix **no smaller** — a message-refresh reaches
  one of the eight by accident and none correctly, and Session 57's rule
  for a per-launch holder is to quieten it, not to describe it better.
  Fixing `transient` closes the staleness here outright, because no such
  finding is raised at all.
- **The retired check reported `match` against the fix that closed its
  entry.** `transient_misses_bus_name` asked
  `Listener(port=0, unit=name).transient` — a *synthetic* listener — so
  it assumed transience is a function of the name. It was built to be
  neutral between the two fixes the entry named, and both were
  name-based, so it inherited their shared assumption and the fix
  refuting both is invisible to it; read off the *observed* listener the
  same property returns `True`.
  `a-control-a-fix-breaks-is-not-a-control`, a third time, and the first
  where the coupling came from the entry's framing rather than the
  check's construction. It retired with the entry per the registry's own
  rule, and the reading is recorded in the entry rather than lost.
- **Live either side, through the production path.**
  `unit_ports(audited_only=True)` **13 keys → 12**, findings **0 → 0**,
  and the degraded path driven at `XDG_RUNTIME_DIR=/nonexistent`: one
  warning logged, `ok: True`, and the `.scope` holder still recognised.

### Two mistakes the sitting made, recorded

- **A cross-repo filing was nearly made against our own error.** The
  first drive of `estate.snags.read_snags` returned **0 entries,
  format unrecognised**, at HEAD *and* the working tree — which reads
  exactly like a regression in their parser between `1e7a9a9` and
  `516116f`. It was ours: the function takes the document *text* and was
  handed a *path*. Reading their signature before writing the message is
  what stopped it.
- **A falsification harness that reverts with `git checkout` deletes the
  fix it is testing.** The first pass restored `sysadmin/units/ports.py`
  from HEAD between stand-ins; the fix was uncommitted, so it went too,
  and only the next stand-in's missing anchor showed it. Re-applied, and
  every later revert came from a copy in the scratchpad.

### Left deliberately

- **`SNAG-AGENT-009` is filed, not fixed, and its `P3` is a guess.** The
  population is unmeasured — that is the next action above. Its three
  candidate remedies are not comparable until the number exists, and the
  obvious one (refresh every held row) is `SNAG-AGENT-006`'s per-run
  write arriving by the back door.
- **Two open entries now carry no check** (`SNAG-DOCS-006` and the new
  `SNAG-AGENT-009`), up from one, which is the cost of closing an entry
  whose check retired with it.
- **`app-signal-2308871.scope` and five other runtime units bind no
  port**, so the fix's effect on them is unobservable today and is not
  claimed. What is claimed is the four that do.

## Session 107 is complete — the instrument for an entry that argues for its own postponement

`SNAG-PORT-003` has a check and **stays open at `P3`**; nothing was
fixed, which is what the entry asked for. Open entries carrying no check
go **2 → 1**. Suite **2737 → 2755** (2737 + 18), ruff and mypy clean, all
nine ops claims ok. Daemon restarted **09:30:18** — see below, because it
did not need to be. No migration; no entry opened or closed, so the
parser still reads 97 with open at 23.

### What the sitting settled

- **The handoff's own proposed verdict rule was refuted by the first
  run.** It asked for a check "whose verdict flips on the day a second
  instance appears". The second instance was already here:
  `$XDG_RUNTIME_DIR/systemd/transient` holds **three** D-Bus activated
  units, so a verdict keyed on the population would have printed
  *refuted* against a live, untouched defect on day one — rule 1's
  reading, and the one Session 83 refused for `SNAG-LOG-013`. So
  `mismatch` is reserved for the entry being **dead**, and the blocker's
  disappearance rides in the note, which `render` prints on a `match`
  line too. `SNAG-TRAY-008`'s rule reached from the other side: an entry
  whose fix has become *buildable* must stay open, and one reported
  `mismatch` sits in the bucket with the ones to close.
- **The second instance is discriminating, not merely present.** The
  entry spells the rejected pattern `:N.N`, and
  `dbus-:1.21-org.a11y.atspi.Registry@0.service` sits beside
  `dbus-:1.2-org.kde.kdeconnect@0.service`. That is strictly the evidence
  the entry says is missing — a pair that tells a rule from a
  coincidence — and it is why the candidate pool is the **union** of the
  listener and runtime sets: only `:1.2` binds a TCP port, so a pool
  taken from `ss` alone reports the anchored naive fix complete, which is
  the one verdict this check exists to be able to refuse.
- **Two of the entry's own claims were corrected by the instrument built
  to measure it.** Its *"no consumer reaches it"* names
  `recommendations.py` and the estate judge and **not** `judge_ports`,
  whose `holders` map admits the listener because its guard is the
  property under test — one synthetic `DeclaredPort` produces a
  `wrong_unit` naming the per-session unit verbatim. And its predicted
  *"new title every login"* is not what it would get: `port_alert_title`
  is `Port collision on 1716`, keyed on the port, so the row deduplicates
  and what churns is the message. Both are recorded in the `Check`
  bullet rather than by rewriting the bullets they correct, because a
  check that edits the entry it reads is the second author
  `ops_claims` rule 6 exists to keep out.
- **Two of the eighteen tests passed against deliberately broken code, in
  one shape.** Both decided their `pytest.skip` from a value the break
  itself empties — the partial-rule test read `reading.candidates`, which
  a narrowed pool empties, and the failure-mode test read
  `reading.reach_title`, which removing that instrument nulls. Both
  decide from the box now.
  `a-control-a-fix-breaks-is-not-a-control`, found twice in one class.
- **The restart was not owed and was taken anyway.**
  `sysadmin/snag_claims.py` is reached from the `sysadmin-check-snags`
  console script and from nothing in `create_app()`, so the daemon's
  imported code did not move. The deploy check compares the newest `.py`
  on disk and its docstring already prices this: *"a file the daemon
  never imports reports a restart owed, and that fails in the direction
  that costs a needless `kill -TERM`"*. The alternative was a red claim
  at every preflight until an unrelated sitting restarted.

### Left deliberately

- **`SNAG-PORT-003` is not fixed and its priority is unchanged.** No
  family can raise on it today and its own first escalation trigger — a
  bus-named unit declared in `services.yaml` — has not fired. What
  changed is only that its argument for staying unfixed no longer holds.
- **The registry's second trigger is unmeasured and the check says so.**
  Whether the registry claims a bus-named holder's port *under a project
  name* needs the project join `wrong_project` already owns; 1716 is
  claimed as `_kdeconnectd_`, which folds to a name matching no project
  on disk. Reproducing that join would be a second implementation of an
  existing comparison, so the silence is stated rather than left to be
  read as an oversight.
- **One open entry still carries no check** (`SNAG-DOCS-006`).
- **Both estate messages are closed** (`8c1706d3`, `153c1c96`), and the
  bullet that stood here said the opposite — that they were
  estate-manager's to close. That was Session 106's clause carried
  forward unchecked. The brief says *"the receiver closes it when dealt
  with; the sender may withdraw it"*, and the close endpoint refuses a
  bystander with **409**: we are the receiver on both, so a receiver
  declining to close leaves the row open for nobody. Neither asked
  anything of us — *"Cost to us: none"* and *"Nothing is asked of you"*,
  in their own words.
- **Closing `8c1706d3` caught a live instance of what it warns about.**
  It asks that entry counts be re-derived rather than compared; this
  sitting's first pass carried `97 entries` forward from the previous
  handoff, and only drove `estate.snags.read_snags` when it came to write
  the close note. Re-derived at their committed `1e7a9a9`, clean tree:
  **97 entries, 23 open**. Said in the note rather than quietly fixed.
- **`estate.provenance.checkout()` is filed in `ideas.md`, not adopted
  and not declined.** It reports the commit of the code that *answered*
  where `estate_module_state` infers it from the tree, and they measured
  it would have read `DIRTY` at 14:12 inside a window we were driving
  them. Adopting it changes what four cross-repo checks report and the
  falsifications pinned to that wording, so it is its own sitting.

## Session 106 is complete — the band moved, nothing was raised, and the parse underneath it was wrong

`SNAG-PORT-001` is **closed**, `SNAG-PORT-002` opened and closed in the
same sitting, and `SNAG-PORT-003` **opened**. The live parser reads
**95 → 97 entries with open unmoved at 23**. Suite **2732 → 2737**, all
green — the two red on a clean tree when this sitting opened are the two
that closed. Daemon restarted **22:26:57**, `/health` 200, all ten ops
claims check out — **nine**, not the ten the previous handoff said, which nobody had counted. No migration; the change is one constant, one parse and
their guards.

### What the sitting settled

- **The widening raises nothing, and that had to be driven rather than
  reasoned.** `ServiceDiscoveryAgent._check_ports` was run through its
  own code path against the real `ss`, the real `services.yaml` and the
  real registry document at both bands: **findings 0 → 0, collisions
  0 → 0, advice 0 → 0**. The single observable difference is
  `unit_audited_ports`, 12 units → 13. So the entry's stated reason for
  deferring — *"widening the band changes what an alert family raises"* —
  had an empty population, which is `SNAG-LOG-002`'s shape for the fourth
  time here. The deferral was still correct: the only way to know it is
  zero is to drive it, and driving it is a sitting.
- **The entry's blast radius was wrong and both sides of the copy got it
  wrong the same way.** It names four comparisons; `in_range` has **two**
  production call sites and one of them is not a comparison —
  `judge_ports`' `wrong_project` gate, and
  `PortReport.unit_ports(audited_only=True)`. `port_shared`, `wrong_unit`
  and `duplicate_claim` never consult the band at all. estate-manager had
  already caught and corrected the identical overstatement on their side
  the same day (their ADR-0054 §5 → their `SNAG-ESTATE-070`).
- **1883 could never have contributed.** Root-owned socket, so `ss -p`
  names no holder, so it is `unattributed` and compared against nothing
  by construction. Widening a band over a port nobody can attribute buys
  jurisdiction and no observation — the distinction `ports_checked`
  exists to keep visible. `SNAG-ESTATE-009` is untouched, because the
  estate judge reads the holder out of `unit_ports`, which was never
  gated on the band.
- **`SNAG-PORT-002` is what the drive found underneath.**
  `_unit_from_cgroup` took the path from the *last* colon; `cgroup(5)` is
  `hierarchy:controllers:path` and only the first two fields are
  colon-free. A D-Bus activated unit
  (`dbus-:1.2-org.kde.kdeconnect@0.service`) lost its prefix and, with
  it, the `/user@1000.service/` that decides scope — a **user** unit
  stamped `system` since Session 26c. 1 of 30 attributed listeners, 4 of
  694 processes. No live consequence today; what the fix buys is that the
  next such listener is compared against the right identity.
- **The scope half needed its own witness.** The live specimen breaks the
  unit name and the scope together, so it cannot say which half a
  candidate fix repaired. A second test uses a shape where the colon is
  in the *slice* and not the leaf, where `rpartition` returns the right
  unit and loses only the scope. Three falsifications; a fourth stand-in
  (`split(":", 2)[-1]`) passes, correctly, because behind the
  colon-count guard it is the same code — recorded because an
  unexplained green in a falsification list reads as a gap.
- **The band has three statements and all three are pinned now.**
  `ports.DEFAULT_AUDITED_RANGES` gives `judge_ports`' fallback a name a
  test can address, because the pure module may not read `config.yaml`
  and so cannot derive what it governs. Without it a widening applied to
  `config.py` alone leaves every bare `judge_ports` call in the suite
  judging the old band while production judges the new one — green in
  both places.
- **Both of the producer's statements are read.** The check now parses
  their shipped `audit.yaml` — what the running audit actually reads — as
  well as the `config.py` default it was reading before. Their own test
  pins the two together, and one repository's guard is not this
  repository's evidence. Empty population today; witnessed against
  doctored copies in both directions.

### Not done, and named

- **`SNAG-PORT-003` carries no check**, so open entries without one go
  1 → 2 (`SNAG-DOCS-006` is the other). That is the next action above.
- **The stored sweep still carries the old band.** `service_discovery`
  runs six-hourly and the row in `unit_audits` was written 20:02, before
  the restart; the next run picks the widening up. Normal operation, not
  residue — the same fact `ports_checked` already reports as `false` on
  any pre-26c sweep.
- **Both estate messages stay open.** `8c1706d3` was honoured by
  re-deriving the entry counts rather than comparing them against
  yesterday's, but it is not this repository's to close. `153c1c96` — the
  `SNAG-ESTATE-*` namespace having two minters and no owner — was routed
  around by minting today's ids into `SNAG-PORT-*`, which is not the same
  as answering it; renaming this repository's 14 colliding ids is a
  sitting of its own and the ownership question is estate-manager's.
