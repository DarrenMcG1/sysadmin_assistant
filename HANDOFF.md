# Handoff — 2026-08-12

## Next action

Restart `sysadmin.service` with `sudo systemctl restart sysadmin.service` — it is a system unit serving start-time code, so the running daemon is still on the old raise rule and has written 800 new alert rows in the four minutes since the backlog was cleared.

## Read this first: the fix is written and tested but not deployed

`sysadmin.service` is a **system** unit (`systemctl`, not `--user`) running
from this working tree, and `sudo` on this box wants a password, so the
session could not restart it. Everything else is done: the code is in, the
suite is green at 1,956, and the 598,091-row backlog is resolved. The
daemon is adding roughly **200 rows a minute** until it picks up the new
code.

Nothing needs cleaning up afterwards. The new `_resolve_quiet` sweep
closes those rows on its own — they fall back to `created_at`, which is
older than the 15-minute quiet window within a quarter of an hour of the
restart.

## Session 42 (2026-08-12): SNAG-AGENT-005, and the option that was not on the list

The handoff asked which of two options to take — alert on a **burst** and
resolve when the source goes quiet, or **drop alerting** from the log
aggregator entirely. The answer was neither as written, and the reason is
worth keeping because the data refuted the obvious implementation *before*
any of it was written.

Burst-alerting suppresses a single genuine critical until it repeats.
Dropping alerting means a first-ever critical from a service reaches
nobody, and `GET /api/logs/stats` is a surface nothing polls. So: **dedup
plus a quiet-resolve** — one open row per fault, resolved when the fault
goes quiet.

### The part that had to be measured

Deduplicating on the existing alert title is the obvious reading of
"dedup", and it is wrong. The title is `Log {severity}: {source}`, so
every kernel error shares one. The live 30-day kernel population:

| Message | Rows |
|---|---|
| `Bluetooth: hci0: Failed to set up firmware (-2)` | 297,390 |
| `Bluetooth: hci0: Failed to load firmware file (-2)` | 297,389 |
| `usb 1-11: device descriptor read/64, error -110` | 66 |
| `usb 1-11: device not accepting address 9/10, error -71` | 44 |
| `usb usb1-port11: unable to enumerate USB device` | 22 |
| `rcu: … expedited stalls` / `INFO: task … blocked on a mutex` | 8 |

Dedup on the title and the Bluetooth storm holds the one open row while
**the RCU stall and the USB enumeration failure go silent** — all three
are in the same window, so this is measured rather than argued. Half a
million rows traded for a mask over every other kernel fault is not a fix.

So the key is `sysadmin/monitor/log_signature.py`: the message with digit
runs and hex literals replaced. It collapses 594,779 Bluetooth lines to 2
signatures and 110 USB lines to 2, and leaves all six faults distinct. The
signature goes **in the title**, because dedup, the resolve and the tray's
`{severity}:{title}` fingerprint all key on title already — and four rows
all reading `Log error: kernel` are indistinguishable to whoever is
looking at the tray.

Verified against the live storm:

```
2000 kernel error lines in 10 min -> 2 alert rows
  x1000  Log error: kernel — Bluetooth: hciN: Failed to load firmware file (-N)
  x1000  Log error: kernel — Bluetooth: hciN: Failed to set up firmware (-N)
```

### Three things caught on the way, two of them mine

**`_open_alerts` would have OOMed on the backlog it exists to end.** It
was written the natural way — every unresolved row this agent owns — which
against the live table is 593,814 ORM objects on the first run. Bounded to
the titles the run is about to raise before deployment, not after. An
unbounded `SELECT` over the table whose unboundedness is the bug is an
easy one to write.

**`details` has to be reassigned, not mutated.** SQLAlchemy does not track
mutation inside a plain JSONB dict, so bumping `occurrences` in place
looks like it worked, writes nothing, and freezes `last_seen_at` while the
fault fires — which would resolve the row on the next quiet sweep with the
storm still running.

**The cursor must advance over entries the severity filter discards.**
Advancing only past *kept* entries leaves the resume point behind a run of
info-level noise, and the next read parses it all again — the
duplicate-ingest defect rebuilt one layer down.

### The two smaller defects, both fixed

Journal reads resume from `__CURSOR` rather than re-reading a two-minute
window on a sixty-second poll. A cursor rather than a narrower window,
because narrowing trades the duplicate for a **gap** whenever a run runs
long, and a gap is the worse failure for a monitor. Back-to-back runs
ingested **96 entries then 0**, where every entry used to be stored twice.
The cursor is in memory, so a restart falls back to the newest `logged_at`
already stored for that source, passed as `--since @<epoch>` — journalctl
reads a bare datetime as **local** time and everything here is UTC.

The `-n 500` cap stays, because 8.5 messages a second makes a ceiling
unavoidable, but hitting it is now `details['truncated_sources']` and it
**names** the sources rather than counting them. It was invisible before:
`findings_count` sat at exactly 200 on every single run.

## The host fault is untouched, and the reversible stop is gone

`BT_RAM_CODE_MT6639_2_1_hdr.bin` is still absent from
`/lib/firmware/mediatek/mt7927/`, the `btusb`/`btmtk` retry loop is still
running at ~8.5 lines a second, and **`rfkill list` now prints nothing at
all** — the adapter no longer registers a soft-block switch, so the
one-line workaround the last handoff recorded is no longer available.
Neither disabling `bluetooth.service` (userspace; the loop is in the
kernel) nor `rfkill` is on the table.

That is deliberately not this repository's problem to solve, and the point
of this session is that it no longer has to be: the storm costs 2 alert
rows instead of 43,000 a day.

**The fix this entry recorded does not exist, and that was checked rather
than assumed.** The snag concluded that installing
`BT_RAM_CODE_MT6639_2_1_hdr.bin` from upstream linux-firmware was the real
fix. Upstream ships only `WIFI_MT6639_PATCH_MCU_2_1_hdr.bin` and
`WIFI_RAM_CODE_MT6639_2_1.bin` for the MT7927, and `WHENCE` declares
nothing else — **MediaTek has not published the Bluetooth firmware at
all.** A vendor publication gap, not a distribution one, so there is no
package to wait for and no way to date a fix. The original reasoning — the
driver names the file, every sibling chip has one, therefore it is merely
missing here — is sound and wrong: a `modinfo` firmware line is a
*request*, not evidence of existence, and the upstream tree was never
checked.

What does stop it, at no cost, is de-authorising the device so nothing
probes it. Bluetooth does not work either way. The rule is written and
ready at
`scratchpad/99-mt7927-bt-no-firmware.rules` (matching `0489:e13a` on port
`1-11`); it needs `sudo install` into `/etc/udev/rules.d/`, so it belongs
to the owner. Blacklisting `btusb`/`btmtk` is the blunter fallback.

Worth doing even now: the alert table is bounded, but the lines are still
ingested. `log_entries` holds 610,941 rows / 622 MB and took on 64,047
today against 30-day retention; journald is at 4 GB with 165,670 kernel
lines today.

The Wi-Fi half of the same MT7927 is the mirror image — firmware present,
no driver bound at all — which is the genuinely unsupported part.

## Open, in order

1. Restart the daemon (above), then confirm with
   `SELECT title, details->>'occurrences' FROM sysadmin.alerts WHERE
   agent='log_aggregator' AND resolved=false;` — expect a handful of rows,
   not a page.
2. `SNAG-DB-002` — every database on this box has a stale collation
   version, and a text-index lookup can miss a row that is present. Still
   the only open defect that could silently corrupt a result rather than a
   count.
3. `SNAG-SYSD-003` — `sysadmin.service` still orders itself after
   `ollama.service`, retired three weeks ago. The honest question is
   whether it should order against `alfred-inference.service` at all
   rather than which name to substitute.
