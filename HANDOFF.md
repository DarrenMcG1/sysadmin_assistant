# Handoff — 2026-08-28

## Next action

Judge `SNAG-PORT-003` now that its own blocker is measured gone, choosing between the two fixes it names and the third it does not — systemd's `Transient=`, whose unit files sit in `$XDG_RUNTIME_DIR/systemd/transient` and are a directory listing away, which is the same class of signal `scan.py` already reads for enablement and is therefore not a guess at all, and decide at the same time whether the fix it actually needs is the smaller one this sitting's fourth instrument found, since `port_alert_title` is keyed on the port so the row deduplicates and what churns per login is the message rather than the title the entry predicts.

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
- **Both estate messages stay open** — `8c1706d3` and `153c1c96` are
  estate-manager's to close and neither is this repository's to answer.

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
