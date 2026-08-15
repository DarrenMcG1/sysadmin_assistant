# Handoff — 2026-08-15

## Next action

Run `sudo systemctl restart sysadmin.service` and the five orphan-removal commands listed under "Blocked on sudo" below, then take `SNAG-AGENT-006` — bounding the service and threshold alert families, the last two on this box that raise one row per run for as long as a fault is true.

## This session — Session 48, the execution sitting

Three sittings (46, 47, 26c) went into making the diagnosis *speak*. This
one **carried out what it says**, and that is the finding: **two defects
surfaced inside an hour**, neither visible by reading the code, both the
same root cause — `sysadmin/units/recommendations.py` under-reading a
`UnitFinding` the sweep had already filled in.

Suite **1708 passed** (from 1701), ruff and mypy clean, **no migration**.

### What was executed, and what it proved

- **`garmin-sync.service` removed** — the armed orphan, enabled since
  February, alerting since 14 Aug. The endpoint's emitted command ran
  **verbatim** and worked. First end-to-end proof an orphan action is
  correct as written.
- **`sysadmin-tray.service` start limit bounded** with the emitted
  snippet. `LoadError=` empty, `systemd-analyze verify` silent, and
  systemd's own reading matches the advice's arithmetic exactly —
  `StartLimitIntervalUSec=1min`, `StartLimitBurst=5`, `RestartUSec=10s`,
  so the 5th start lands 40 s after the first, inside the window.
  **`restart_bounded` flips `False → True`** on the same `load_unit` the
  sweep calls, so the family drops 13 → 12 on the next sweep. That was
  the second half of the sitting's brief and it is answered.
- **Three host units wired into `services.yaml`** —
  `ethernet-optimise`, `paccache-timer`, `deadlock-api-ingest-user`. The
  first entries in that file produced by pasting endpoint output. All
  three parse, resolve, and check **`ok`** against the live box.

### The two defects (`SNAG-UNITS-004`, fixed)

1. **The advice never asked whether the unit is meant to be running.**
   `grep -n "enabled" recommendations.py` returned *nothing*, while every
   finding carries a measured `enabled` the orphan family has trusted
   since Session 46. Two of five host snippets named units that are
   **disabled and inactive**; pasting them declares `kind: systemd` /
   `kind: timer` checks — which assert *active* and *armed* — returning
   `critical` **every 300 s for ever**. Verified against the box:
   `ActiveState=inactive → CRITICAL`, both.
2. **`removal_command` left a folded oneshot's timer installed.**
   `ticktick-sync.timer` declares `Requires=ticktick-sync.service` and
   the emitted command removed only the service — leaving a `Requires=`
   pointing at nothing, and orphaning the enablement symlink that
   command's own docstring exists to avoid. `monitor_unit` already named
   the timer. Now removed **timer first**.

And the rule both imply: **a row offering no snippet must never say
"paste the snippet below"**. `sysadmin-failed.service` shipped exactly
that — an item an execution sitting *cannot close*, so it returns for
ever. Every no-snippet row now names its real next step.

### Decisions taken, and options rejected

- **The gate is "nothing enables it", not "it is not running".**
  `enabled` is an enablement symlink the sweep already walks, so
  `scan.py`'s no-subprocess promise survives; an `ActiveState` test is
  sharper and would have cost it. On this box the two agree exactly.
- **The two disabled deadlock units were *not* declared `monitor: false`.**
  Tempting — `searxng-upstream` in `services.yaml` exists precisely to
  close permanently-unactionable findings — but that unit is healthy and
  checked elsewhere, so no decision is outstanding. These have a real
  pending decision (enable or remove) that is the box owner's, and
  declaring them would hide the day someone enables them.
- **The 20 failing tests were fixed in the fixtures, not the default.**
  `UnitFinding.enabled` defaults to `False`, correct for `armed` where
  absent evidence must read as "not armed" (quiet) and the **opposite
  polarity** from this gate (loud). Flipping the default would quietly
  arm every orphan.
- **Eleven cross-repo restart units left as advice** (Alfred 1,
  estate-manager 3, SportsAnalyser 2, venture-assistant 1, five unowned).
  The monitor must not own what it monitors, and the endpoint's own
  `detail` says the edit is that repository's to make.

### Blocked on sudo (`SNAG-UNITS-005`)

No agent session can supply a password. **All six unit files are backed
up** under the session scratchpad. The user-scope orphan was removed, so
the command shape is proven; only the privilege is missing.

```
sudo systemctl restart sysadmin.service          # deploys the 3 new entries + the fix

sudo systemctl disable --now offline-agents-dashboard.service \
  && sudo rm /etc/systemd/system/offline-agents-dashboard.service
sudo systemctl disable --now personalassistant-backend.service \
  && sudo rm /etc/systemd/system/personalassistant-backend.service
sudo systemctl disable --now personalassistant-frontend.service \
  && sudo rm /etc/systemd/system/personalassistant-frontend.service
sudo systemctl disable --now ticktick-sync.timer ticktick-sync.service \
  && sudo rm /etc/systemd/system/ticktick-sync.timer \
            /etc/systemd/system/ticktick-sync.service
sudo systemctl disable --now ticktick-sync-db.service \
  && sudo rm /etc/systemd/system/ticktick-sync-db.service
sudo systemctl daemon-reload
```

Note the fourth: **the timer is in that command because of this
sitting's fix**. Before it, the emitted command removed the service and
left the timer behind.

### The collation half of the brief was already closed

All **12 databases report `datcollversion = 2.44`** against a live 2.44,
and all 8 alert rows are `resolved` — one row each, so the dedup rule
held. "8 stale collations" was a stale reading. The symptom was tested
rather than assumed: for all five collation-sensitive indexes in the
`sysadmin` schema, an index-driven count and a seq-scan count **agree
exactly** (626,632 rows on the largest), and `alerts` carries **no text
B-tree at all**, so the snag's stated symptom has no index behind it here.

**What survives is the interesting half**: nothing distinguishes a real
`REINDEX` from `ALTER DATABASE … REFRESH COLLATION VERSION`, which clears
the warning without rebuilding anything — the trap
`monitor/collation.py` rule 4 already puts in `details['remedy']`. If
that is what happened, a loud known risk is now silent and this monitor
can never raise it again. Finding out which, across `venture` (100 MB)
and the five `alfred*` databases, is the residual task.
