# Handoff — 2026-08-27

## Next action

Write the snag-claim check for `SNAG-PORT-003` — it is the only entry opened today with no instrument, and it is the one where an instrument earns its keep most obviously, because the entry's whole argument for not fixing it is that a rule tuned against a single observation is a guess and this box currently has exactly one D-Bus activated listener, so a check that sweeps `observe_listeners` for units whose name carries a bus-unique id and asks whether `Listener.transient` recognises them is a check whose verdict flips on the day a second instance appears, which is precisely the evidence the entry says it is waiting for and cannot otherwise be told has arrived.

## Session 106 is complete — the band moved, nothing was raised, and the parse underneath it was wrong

`SNAG-PORT-001` is **closed**, `SNAG-PORT-002` opened and closed in the
same sitting, and `SNAG-PORT-003` **opened**. The live parser reads
**95 → 97 entries with open unmoved at 23**. Suite **2732 → 2737**, all
green — the two red on a clean tree when this sitting opened are the two
that closed. Daemon restarted **22:26:57**, `/health` 200, all ten ops
claims check out. No migration; the change is one constant, one parse and
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
