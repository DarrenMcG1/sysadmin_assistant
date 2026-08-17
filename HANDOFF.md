# Handoff — 2026-08-17

## Next action

Take `SNAG-LOG-002` and give `log_trends._confidence` a per-source truncation reading in place of the binary global flag it has now, because 119 of 10,063 log-aggregator runs truncated across **nine** different sources in the last seven days rather than the two Session 60 recorded, so `GET /api/logs/trends` and the entire `noise` recommendation family report `confidence: low` far more reliably than any single kernel storm explains, and neither waiting for the 2026-08-12 spike to leave the window nor Session 61's fix to this service's own volume can recover it.

## Two sub-session items, neither of them a session

**One to run, and it is what makes today's work real.**

```bash
sudo systemctl restart sysadmin
```

uvicorn serves start-time code, so **both halves of `SNAG-AGENT-008` are
waiting on this one restart** — Session 60's duplicate access line and
Session 61's level prefix. Until it runs, `log_entries` holds **0 rows**
for `sysadmin-service` (checked again at 13:30 today) and this daemon
still cannot see its own `ERROR`s. Two minutes, and it needs `sudo`.

**One still outstanding from yesterday morning.** The two `Estate port …
registry breach` rows still need resolving so Session 57's `info` rung
can reach them (`SNAG-ESTATE-010`) — both confirmed still open today:

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

The 03:00 retention purge has still not deleted anything —
`log_entries` read **626,917** at 13:30. Tonight's run is the first that
will, and it happens by itself.

## This session — Session 61: the priority half, and a premise that did not survive one command

The handoff's `## Next action` line stood and was taken as written. It
named the fault correctly. **The snag entry it came from named the
trade-off incorrectly, and one `systemctl show` settled it before any
code was written.**

### The premise, checked first

The entry said `SyslogLevelPrefix=` and `JournalHandler` "both need a
unit edit and sudo", leaving the reader-side hack as the only cheap
option. `SyslogLevelPrefix=` **defaults to true** in systemd:

```
$ systemctl show sysadmin.service -p SyslogLevelPrefix
SyslogLevelPrefix=yes
```

So the prefix remedy needs no unit edit and no `sudo` either — the same
footing the entry credited only to the option that couples a fourteen-
source reader to this one application's log format. Two of the three
clauses in that sentence were wrong. A trade-off written from
documentation rather than from the box had sent the choice toward the
weakest of the three.

Verified end to end against a transient unit rather than read off the
manual: `<4>{…}` on stdout arrives as `PRIORITY=4`, and journald
**strips the prefix**, so `MESSAGE` is byte-identical and
`log_signature`, `alert_title` and the stored `raw_line` need no change.

### What was built

`JournalLevelPrefixFormatter` in `sysadmin/core/logging_setup.py`
prefixes each JSON line with `<N>`, gated on `log_format == "json"`.
That gate is a **precondition, not a proxy for the destination**: a
level prefix marks one line, and only the JSON formatter guarantees one
line per record. Under the text formatter a traceback's first line would
be stamped `ERROR` and its body left at `info` — one fault across two
priorities, worse than the uniform `6` because it looks fixed.

`syslog_priority` is a module-level function rather than formatter
internals so a test can drive it against `journal.PRIORITY_MAP` directly.
Two maps that can disagree about one fact is this repository's recurring
defect, and the round trip is pinned for all five levels.

**The second emitter was the one carrying the errors.** `uvicorn.error`
has no handler and propagates only as far as `uvicorn`, which keeps a
plain-text stderr handler with `propagate = False` — `uvicorn.access`'s
shape exactly, one logger over. So `Exception in ASGI application` and
the traceback of every unhandled 500 went out as plain text at
`PRIORITY=6`, and no prefix on *this application's* logger could have
reached them. It is **rerouted, not silenced**, deliberately the
opposite verb from its sibling three lines up in the same function: the
access line duplicates a structured line the middleware already writes,
so the second copy is waste; uvicorn's error line has no second copy
anywhere, so silencing it would delete the only record an ASGI crash
leaves.

### Session 60's own guard was asserting the opposite, and passing

`test_only_the_access_logger_is_silenced` claims `uvicorn.error` reaches
the root handler. Its fixture rebuilds `uvicorn.access` and **not** its
parent, so `uvicorn` was left with no handler and `propagate = True` and
the record fell through. Driven against uvicorn's real `LOGGING_CONFIG`:

```
test env  (no uvicorn dictConfig): root='{"timestamp":…,"level":"ERROR",…'  uvicorn_own=''
production (uvicorn dictConfig)  : root=''                                  uvicorn_own='ERROR:    address already in use'
```

True in CI, false on the box. That is `test_excludes_health_endpoint`'s
defect one logger over, shipped by the session that found it. The new
class drives the real `dictConfig`; the old test is kept as a cheap
guard with its docstring now saying what it does not cover.

### Verified live, without the sudo the deploy needs

A transient user unit ran the real `configure_logging` and emitted four
records. journald recorded `INFO→6`, `WARNING→4`, `ERROR`+traceback→`3`,
`uvicorn.error→3`; the **real `read_journal`** at `severity_filter:
warning` returned **3 entries where it has always returned 0**, prefix
stripped, cursor set. Both new guards were falsified against restored
pre-fix code: reverting the formatter fails 12 tests, removing the
reroute fails exactly the two that name it.

Full suite **1,965 passed**, ruff clean, mypy clean.

### Decisions taken, and what was rejected

- **Producer over reader.** Parsing `"level"` in `read_journal` fixes
  this repository's view and leaves the artefact lying — and puts a
  special case for one source into a reader serving fourteen.
  `sysadmin.service` is the only JSON-writing journal source on this box,
  measured, so the branch could never pay for itself.
- **`systemd.journal` rejected on measurement**, not argument:
  `ImportError` in the venv, so it is a new native dependency, and it
  replaces stdout-JSON rather than repairing it.
- **The JSON-blob message was measured and deliberately not fixed.**
  `alert_title` will produce a 252-character title made of JSON. Filed as
  `SNAG-LOG-003` because the obvious remedy is the coupling just
  rejected, and the honest one — `format: json` declared per source in
  `services.yaml` — is a schema change that deserves its own sitting.
  Detection is unaffected: two distinct faults gave two distinct titles.

### Filed and corrected

- **`SNAG-AGENT-008` closed**, both halves.
- **`SNAG-LOG-003` opened** — the JSON document where the message should
  be. Not observable until the restart.
- **`SNAG-LOG-002` re-measured.** Session 60's "kernel 103,
  sysadmin-service 14" is 2 of **9** sources: 119 runs of 10,063, 164
  source-truncations, eight of the nine sources affected. This is what
  moved it from third to first in the recommendation.
- **`SNAG-ESTATE-001`'s units confirmed gone** from the box; its
  remaining half is a retirement checklist, a process rather than code.
- Live parser **42 → 43**, measured either side of the edit.
