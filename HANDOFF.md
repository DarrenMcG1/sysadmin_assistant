# Handoff — 2026-08-17

## Next action

Take the priority half of `SNAG-AGENT-008` — every line this daemon writes is journald `PRIORITY=6` regardless of the `"level"` inside the JSON, so `read_journal`'s severity filter discards the lot, `log_entries` holds zero rows for `sysadmin.service`, nine consecutive nights of `ERROR` raised no alert, and it is also what keeps `_resume_floor` returning `None` for this source for ever.

## Two sub-session items, neither of them a session

**One to run, and it needs `sudo`.**

```bash
sudo systemctl restart sysadmin
```

uvicorn serves start-time code, so the duplicate access line is still
being written. The tray half is already deployed and measured; this is
the other half of the same fix. Two minutes.

**One still outstanding from this morning.** The two `Estate port …
registry breach` rows still need resolving so Session 57's `info` rung
can reach them (`SNAG-ESTATE-010`) — a write to the live `alerts` table,
still left for the owner:

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

The 03:00 retention purge item from the last handoff is unchanged and
happens by itself: **207,566 rows**, `log_entries` 626,906 → 451,888.

## This session — Session 60: the volume half, and what the table said instead

The handoff's `## Next action` line stood and was taken as written. It
named a fix and a reason. The fix was worth doing. **The reason was
wrong, and finding that out cost twenty minutes of measuring.**

### The volume, measured before anything was changed

`sysadmin.service` wrote **673 journal lines per 5 minutes** — 676 over a
30-minute sample, so steady rather than bursty. Two causes, neither of
them the one the snag named.

**Every request was logged twice.** `configure_logging` clears the
**root** handlers, and that does not reach `uvicorn.access`: uvicorn's
default dictConfig attaches a handler to that logger *directly* and sets
`propagate = False`, so it sat outside every switch the module throws.
Over ten minutes, **662 plain lines against 640 JSON access lines** — and
662 − 640 is exactly the **22 `/health` polls** the middleware excludes
and uvicorn's did not.

That second clause is the part worth keeping. `_EXCLUDED_PATHS` is
`SNAG-API-002`'s fix and **it has never worked**. The test that guards it
patches `sysadmin.core.middleware.logger` — the emitter that was already
honouring the exclusion — so no amount of strengthening it could have
caught the one that was not. An exclusion a second emitter ignores is not
a quieter log; it is a decision with nothing enforcing it.

**The tray was polling a tab nobody was looking at.** `ServicesTab` is
constructed eagerly at tray startup and wired to `status_updated`
unconditionally, so it issued one `GET …/details` per systemd-backed
service on every status poll whether or not the dashboard had ever been
opened — **1,160 of the 1,347 lines, 86 %**. `DashboardWindow`'s own
docstring promised the opposite: *"no background polling when hidden"*.
Every other tab keeps that promise; `LogsTab` stops its timer in
`hideEvent`, and this tab had no timer to stop, which is how it escaped
notice. The polling was never scheduled — it was inherited from a signal
that fires anyway.

### What the live table said about the justification

The handoff's reason was that 118 truncated runs make
`GET /api/logs/actions` report `confidence: low`, and that those runs are
overwhelmingly this service. Measured over the same 7-day window in
`agent_runs`:

| source | truncated runs |
|---|---:|
| kernel | **103** |
| mosquitto | 14 |
| **sysadmin-service** | **14** |
| sports_analyser | 12 |
| venture-assistant | 11 |

118 out of **10,064 runs — 1.2 %**, not "essentially every read". And
**104 of the 118 landed on one day**, 2026-08-12, as kernel reads.

`log_trends._confidence` is `if coverage.runs_truncated > 0: return LOW`
— **binary, not proportional**. So taking this service to zero leaves 103
kernel runs and `SNAG-LOG-002` does not close. It will clear by itself
around **2026-08-19** when 08-12 leaves the window, and return on the
next kernel storm. Both snag entries have been corrected in place.

### The finding worth carrying forward

**The two halves of `SNAG-AGENT-008` are multiplicative, not
independent.** `_read_journal_source` falls back to a five-minute window
only when there is no cursor **and** `_resume_floor` is `None`. For
`sysadmin-service` the floor is *always* `None`, because the priority
half means no rows are ever stored — so the durable resume mechanism is
permanently disabled, every restart re-reads five minutes, and five
minutes at 673 lines overflows a 500-line ceiling. Fixing **either** half
stops the truncation; only the priority half stops the re-read. That is
why it is the next action.

### Decisions taken, and what was rejected

- **The middleware is the copy kept**, not uvicorn's — only it carries
  `method`/`path`/`status`/`duration_ms` as structured fields. Rejected:
  deleting the middleware, which loses the fields *and* the exclusion.
- **Disabled, not re-levelled.** uvicorn logs access at INFO and nothing
  else, so `setLevel(WARNING)` is silence spelled indirectly and would
  start emitting again the day uvicorn adds a warning-level access line.
- **Silenced, not redirected.** Removing the handler and letting the
  record propagate keeps the duplicate and re-dresses it as JSON — the
  same line count, which is the number being moved. A test asserts it.
- **In code rather than `--no-access-log` on `ExecStart`** — the owner's
  choice. No `sudo`, and it keeps logging configuration in one file.
- **Rejected: raising `max_entries_per_read`**, the snag's third
  candidate. It treats the ceiling rather than the volume, and the
  volume turned out to be two defects.
- **`isVisible()` rather than a flag.** It is false both when the window
  is hidden and when another tab is selected — both cases where nobody
  is looking — so a second flag would be a second statement of the same
  fact, free to disagree with Qt about it.
- **Fixed in place, not abstracted.** `ServicesTab` is the *only* tab
  that issues a request from a client signal handler; every other one
  confines them to `refresh()` or a user action. Checked rather than
  assumed.

### Verified live, not only against fixtures

Both guards were **falsified against the restored pre-fix code** before
being trusted: `test_access_line_is_not_emitted` fails with production's
exact line, `127.0.0.1:53994 - "GET /health" 200`, and 4 of the 7
`test_services_tab.py` tests fail with the whole service list.

The logging half was additionally driven against uvicorn's **real**
`LOGGING_CONFIG` rather than a reconstruction of it — `dictConfig` then
`configure_logging` gives `INFO:     127.0.0.1:53994 - "GET /health
HTTP/1.1" 200 OK` before and `''` after, with nothing rerouted to root.

The tray was deployed and the journal measured over a five-minute window
six minutes after the restart: **673 → 93 lines per 5 minutes, an 86 %
reduction, `details = 0`.** The residual 41 plain lines are uvicorn's
duplicate, still being written until the backend restart above; removing
them leaves ~52, against a 500-line ceiling.

**1948 green** (from 1937), ruff and mypy clean.

### Filed rather than implied

Nothing new opened. Two entries **corrected**: `SNAG-AGENT-008`'s volume
half is fixed and three of its claims were wrong (the ceiling is hit on
the first read after a restart and at no other moment; the cause was a
duplicated line and a tray fan-out, not "an access-log line per request
nobody revisited"; the composition was never measured before being
asserted). `SNAG-LOG-002`'s cause is the kernel, its gate is binary, and
per-source confidence is now the only fix that reaches it.
