# v2 proposals, 2026-11-11

Written after the bug review beside this file
([bug-review.md](bug-review.md)); finding numbers such as H1 and M9
refer to it. The repository is under a feature freeze until 2027-02-01,
when the owner reads the v2 list, so nothing here is a plan to start
now. The exception is the bug fixes, which the freeze already admits.

## What the project is for, as the repository shows it

The README states the purpose plainly: on a single-user workstation
running about 48 declared services, nothing pages anyone when one dies,
so this service exists to make quiet failures loud. It polls systemd
units, HTTP and TCP health, disk, RAM and the GPU every five minutes,
ingests the journal every minute, stores readings in PostgreSQL, raises
alerts, and speaks them through a PyQt6 tray. Around that core it has
grown a file organiser that audits and tidies the home directory, a
systemd unit sweep, a judge for the sibling `estate-manager` service's
published surfaces, a game detector for another application, three
weekly LLM-narrated reviews, and about 13,300 lines that re-measure the
repository's own documents. The README also names a second purpose, the
written record of how each rule was reached.

The purpose is clear. What the data questions is whether the alerts
reach it. The `alerts` table holds 646,166 rows and not one was ever
acknowledged; the last 30 days raised 575, of which 493 were warnings;
the two buttons on every toast have never worked (H4) and no entry in
the snag list noticed. That is the evidence most of the proposals below
start from.

## Proposals

### 1. Fix what is live and delete what is dead (conservative consolidation)

- **What changes:** fix the four high findings and the cheap mediums,
  and remove code whose purpose left: the `/clean/stale-caches` route,
  its tray button and the cache concept (H1, M10); the Projects tab's
  scan button and dead score display (L14); the `strategy: "largest"`
  option (L12). Add savepoints and subprocess timeouts where the code
  already states the rule for a neighbour (M14, M15, M3). Correct the
  stale prose (L4, L17).
- **Problem it solves:** the tray stops offering a button that can break
  another project's database, the journal read stops losing the lines
  that explain a crash, and toast buttons do what they say.
- **Findings addressed:** H1 to H4, M3, M4, M5, M6, M7, M8, M12, M14,
  M15, M18, M19, and most of the lows.
- **Size:** small. Each fix is a few lines plus a test; split by area it
  is five or six reviewable changes under 400 lines each.
- **Risks:** low. H3's fix changes which kernel lines arrive after a
  reboot, so the first boot afterwards may raise a burst of rows for the
  previous boot's tail. Worth doing if the service keeps running at all.
- **Breaks or retires:** the stale-caches endpoint and its
  `CleanResultResponse` contract; nothing else reads them.

### 2. An alert budget: fewer alerts, each one answered

- **What changes:** treat an alert as a request for the owner's action
  and measure it that way. Give the two flapping titles (`High VRAM
  usage`, `Unusual CPU usage`, 428 and 250 rows) hysteresis so they open
  once per episode. Put an acknowledge and a working snooze in the tray.
  Record for each alert whether anything followed it (an ack, a restart,
  a resolved fault) and publish the weekly ratio in the health review.
  Demote to the weekly review any title that was never acted on in 90
  days.
- **Problem it solves:** today the owner receives about 19 alerts a day
  and answers none through the system. A monitor whose alerts are not
  answered is the quiet failure the README describes, one level up.
- **Findings addressed:** H4, M1, M2, M5, the unused acknowledge path in
  L17.
- **Size:** medium, a week or two. Hysteresis and the ack control are
  small; the "was it acted on" measure needs a definition first.
- **Risks:** demoting a title that later matters. It is worth doing only
  if the owner wants to act on alerts from the desktop at all; if the
  morning briefing in Alfred is where they are read, do proposal 4
  instead and put the ack there.
- **Breaks or retires:** the `flapping` declarations in STATUS.md's
  opening block, which exist to excuse what hysteresis would remove.

### 3. Make the file organiser read-only

- **What changes:** keep the disk forecast, the large-files list and the
  weekly disk review. Remove the three remaining mutating actions
  (`organise`, `clean/duplicates`, `clean/downloads`) and the duplicate
  and similar-folder scans that feed them, or leave duplicates as a
  report computed with a full hash.
- **Problem it solves:** the audit's counts have been pinned at their
  caps for weeks (M9), its duplicate test is wrong (H2), its organise
  rule would scatter application trees (M11), and its nightly walk is
  the likeliest reason the daemon sits at its memory ceiling (M17). The
  one real disk event in the record, a 75 GB game install on 2026-11-04,
  was diagnosed from `resource_snapshots` and file birth times, not from
  this agent.
- **Findings addressed:** H1, H2, M9, M10, M11, M17, L11, L12, L13.
- **Size:** small to medium. Deletion plus contract and tray clean-up.
- **Risks:** losing a tidy-up feature the owner uses. It would have to
  be true that the actions are in fact unused; I could not measure
  that, since the daemon keeps no record of confirmed action calls.
- **Breaks or retires:** four routes, `FileActionResponse` and its
  relatives, about 850 lines of `files/actions.py`, and 92 tests.

### 4. Move the dashboard into Alfred and shrink the tray to an icon

- **What changes:** the five-tab PyQt6 dashboard becomes a page in
  Alfred's frontend, which the owner already opens every day and where
  the briefing already lands. The tray keeps the status icon and the
  notifier. `docs/roadmap/ideas.md` already carries this idea under
  "Rebuild the sysadmin web UI inside Alfred's frontend".
- **Problem it solves:** the dashboard is where four of this review's
  findings live (M5, M6, L14, and four modules no test names), it
  duplicates a view the estate's board and Alfred partly give, and it
  can only be seen at the desk.
- **Findings addressed:** M5, M6, L14, L17's missing ack control.
- **Size:** medium for a read-only page, large if every action moves
  too. The work is mostly in Alfred's repository, not this one.
- **Risks:** it is a cross-repository change, so it needs Alfred's
  agreement and a filing at the estate first. Worth doing only if the
  Alfred page would be read more than the tray dashboard is; ask that
  before building.
- **Breaks or retires:** `sysadmin_tray/dashboard/` and `widgets/`,
  roughly half the tray's 6,160 lines, and the "parse-side only"
  contract rows that exist for the tray alone.

### 5. Separate the record-checking tools from the daemon

- **What changes:** `sysadmin/snag_claims.py` (9,528 lines),
  `ops_claims.py` (2,845) and `vacuous_guards.py` (929) check the
  repository's documents and tests, not the workstation. Move them out
  of the daemon's package into a `tools/` directory with their own test
  run, and stop them growing: a new claim check needs an incident that
  it would have caught.
- **Problem it solves:** a quarter of the "backend" and about 13,800
  lines of tests guard prose. They ship in the daemon's wheel, run at
  every push (the box half of the suite takes about three minutes), and
  make the monitor look four times harder to review than it is. The
  owner's own audit of 2026-10-29 found process growing faster than
  product; this is where that shows in the code.
- **Findings addressed:** none directly. It answers a structural
  weakness: this review could not read those 13,300 lines and found the
  live defects elsewhere, in code those checks do not cover.
- **Size:** small to move. No module in `sysadmin/` or `sysadmin_tray/`
  imports them (checked by search); they are reached only as the three
  `sysadmin-check-*` console scripts in `pyproject.toml`.
- **Risks:** the README says the written record is the point of
  publishing. This proposal keeps the record and its checks and only
  stops them counting as the product. It is worth doing if the owner
  agrees the monitor is the product.
- **Breaks or retires:** import paths in `scripts/check-*.sh` and the
  tests; the README's line counts.

### 6. Rethink: judge standard collectors instead of being one

- **What changes:** stop collecting what standard tools collect. Let
  node_exporter, a blackbox prober and systemd's own `OnFailure=` hooks
  gather resources, health checks and unit failures, with Alertmanager
  or a small rules file deciding thresholds. This repository shrinks to
  what nothing off the shelf does for this box: the estate judge, the
  journal fault signatures and incident folding, the GPU-context
  predicate, and the briefing for Alfred.
- **Problem it solves:** about 2,700 lines of `monitor/agent.py` and its
  dedup, escalation and flapping rules re-derive what alerting tools
  already model (grouping, inhibition, hysteresis, silences), and each
  rule was learnt here by incident. The owner would also be operating
  tools that job adverts for database and data-engineering roles name,
  which the bespoke agent is not.
- **Findings addressed:** the class behind M1, M2, M12, M13 and the
  flapping titles: alert-lifecycle rules written by hand.
- **Size:** large, several weeks, and it adds three or four services to
  a box that this repository exists to keep quiet.
- **Risks:** the highest here. The README says outright that this is
  not trying to be Prometheus, and the bespoke rules encode real
  measurements from this box that a migration would have to carry over
  or lose. It would have to be true that the owner wants the monitoring
  stack as a learning build with an outside date attached; without one
  it is new building in place of the aims it would serve.
- **Breaks or retires:** `service_health`, `resource_snapshots` and
  most of `alerts` as they stand, the tray's status contract, and the
  reliability scores computed from them.

## Recommended order

1. **Proposal 1 now**, as bug fixes under the freeze, starting with H1.
   It is the only item with a live hazard, and it is days of work.
2. **Proposal 3** when v2 opens. It removes more risk and more code per
   day than anything else, and it takes M17's memory pressure with it.
3. **Proposal 2** next. It is the one that moves the project toward its
   stated purpose, and it needs the owner's answer to one question
   first: where should an alert be answered, the desktop or Alfred?
4. **Proposal 5** alongside either, since it is a move, not a rewrite.
5. **Proposal 4** only if the answer to step 3 is Alfred.
6. **Proposal 6** last, and only against a date someone else set.

The reasoning: the review found the core sound and the edges unsafe or
unused, so the cheapest gains are subtraction (1, 3, 5), then making
the remaining alerts count (2). None of these moves the owner's stated
aims of health, income or game making directly; this repository keeps
the machine working for the projects that do. That argues for the
smallest v2 that removes the hazards and the noise, and against 4 and 6
unless something outside the repository asks for them.
