# ADR-0007: a poisoned GPU context is a predicate, not a state — so the check that already writes the row owns it

Decided 2026-09-08 by Session 199, answering the next action Session 197
filed and Session 198 carried forward, and closing the design half of
[`SNAG-GPU-001`](../roadmap/snag_list.md).

**The question was "who owns the state a GPU reset opens, and who closes
it". It has no answer, because there is no state.** "This service holds a
GPU context created before the last reset" is a predicate over two
instants the box already publishes durably and independently. Nothing
opens it, nothing closes it, and every poll recomputes it from scratch.

So the owner is **the service check that already writes the
`service_health` row** — `SysAdminAgent._check_http_and_unit`, which
already calls `get_unit_status` on the unit `services.yaml` names. No
second writer, no new agent, no new table, no lifecycle. The second-owner
defect this repository has now found at seven scales is avoided **by
construction rather than by argument**, which is the strongest form the
avoidance comes in.

The recorded reading is **`degraded`** — a fault, and it deducts.

---

## 1. Why the question dissolves

The filed line presupposed a state machine: something raises a flag when
the card resets, something else lowers it when a submission proves the
card usable, and the two must not be different owners. Both facts the
flag would encode are already durable:

| fact | where it already lives | how it is read |
|---|---|---|
| when this unit's current process started | systemd | `systemctl [--user] show <unit> --timestamp=unix -p ActiveEnterTimestamp` → `@1788753615` |
| when the card was last reset | `log_entries` | the newest row whose `(source, signature)` is a key of `CRITICAL_SIGNATURES` |

The predicate is `unit_started_at < last_declared_reset_at`.

Nobody closes it. `alfred-inference.service` carries `Restart=on-failure`
with a five-second `RestartSec`, so the first submission after a reset
aborts the process and systemd moves the first instant past the second —
and the next poll reads `False` with nothing having been told anything.
That is `message_backfill.py` rule 4, *idempotence is a property, not a
flag*, arriving in a third family; and it is `_resolve_recovered`'s move
of asking the inverse question rather than hunting for an observer of the
recovery.

**A reboot needs no special case, and that was checked rather than
assumed.** `log_entries` retains a reset row for 30 days, so the newest
declared reset can belong to a previous boot — but every unit start
instant is necessarily after the boot that follows it, so the comparison
already answers `False`. No boot id is read, and reading one would be a
second statement of an ordering the two instants already carry.

### 1.1 What that makes the ownership question

`services.yaml` declares the service, the sysadmin agent checks it, and
the check writes one row per poll. Adding a term to that check adds no
owner. The three candidates `SNAG-GPU-001` enumerated are all *second*
owners and all three stay refused:

- **restarting `alfred-inference` on the signature** — refused by the
  estate rule that the monitor must not own what it monitors, and that
  unit is Alfred's. Unchanged.
- **a probe submission before each review takes the lease** — refused:
  it spends a GPU submission to answer a question the submission itself
  answers, outside the lease the probe is checking for.
- **a reader that marks the service unwatched** — refused here, on §3.

---

## 2. The predicate, falsified against 34 days of the live journal

Driven over 2026-08-05 → 2026-09-08 — the whole retained journal — with
12 `VRAM is lost due to GPU reset!` events, sourced through
`journalctl _TRANSPORT=kernel` rather than `journalctl -k`, which implies
`--boot=0` and would have seen four.

| unit | `-ngl` | aborts the predicate anticipated | successful requests served **while flagged** |
|---|---|---|---|
| `alfred-inference` | 99 | **6 of 6** | **0 of 3,020** |
| `venture-chat` | 99 | **10 of 10** | **0 of 8,545** |
| `venture-embed` | 0 | 0 of 0 | **267 of 823** |

An "abort" is `radv/amdgpu: The CS has been cancelled because the context
is lost` followed by `code=dumped, status=6/ABRT`; a success is a
`done request: POST /v1/chat/completions … 200` (or `/v1/embeddings`).

On the two units that hold VRAM the separation is **total in both
directions**: every abort was preceded by a true predicate, with a lead of
**0.06 h to 9.78 h**, and not one of 11,565 successful requests was served
while the predicate was true. Across the twelve resets the flag would have
stood **79.9 hours** for `alfred-inference` — 9.8 % of the window.

### 2.1 The declaration's own reason is wrong in words, and one live service says so

`_GPU_RESET.reason` reads *"Every GPU client's memory was destroyed — the
foreground application and any resident inference server alike."* Measured,
the second half is false. `venture-embed` runs `llama-server … -ngl 0` —
no offloaded layers, no resident VRAM — and served **267 of its 823
successful embeddings while the predicate was true**, across the same
twelve resets, with **zero** aborts in the unit's whole retained history.

That is the measurement that decides the population, and it refutes the
cheapest rule available. `role: inference` names four services in
`services.yaml`; keyed on it, this reading ships **267 false alarms** about
a server that was working the entire time.

**The population is therefore a declaration and not a role**, which is
`unwrap_json_message`'s rule — honouring a statement rather than
recognising an application — met from a new direction. Reading `-ngl` out
of the unit's `ExecStart` is the other cheap rule and is refused for the
same reason plus a stronger one: it makes this repository a parser of a
command line another repository owns, free to drift on any edit, and
`scan.py`'s no-subprocess promise does not extend to interpreting one.

**The prose is corrected rather than the rule narrowed.** The declaration
still speaks for the *event* — the card was reset and clients lost VRAM —
and it is a log family, which is right for an event. What is wrong is a
clause claiming which clients; that clause is now the business of a
declaration in `services.yaml`, and the reason will say so.

### 2.2 The one precision question, and which direction it errs

`--timestamp=unix` renders `@<epoch>` at **second** granularity, which is
`since_timestamp`'s own form and needs no parse at all. `--timestamp=us+utc`
renders `2026-09-07 04:00:15.580415 UTC` — microseconds with the zone
written out. Neither is the ambiguous local wall clock `timer_stale`
refuses to parse and `SNAG-LOG-009` removed.

Second truncation moves a unit's start instant **earlier**, which makes the
predicate more likely to be true — it errs toward over-reporting. So the
comparison is strict and a tie is **not** flagged, which corrects exactly
the direction the truncation errs in. That is `SNAG-LOG-009` rule 2's
`int` → `math.ceil` lesson read the other way round, and it is why the
cheaper rendering is also the safe one. `us+utc` is recorded here as the
measured alternative if a sub-second case is ever produced; none exists
today, the shortest observed gap between a reset and the abort it explains
being 3.4 minutes.

### 2.3 Every way of not-knowing is not a flag

`ActiveEnterTimestamp` is **empty** for an inactive unit — measured against
`venture-chat-large.service`, which is `monitor: false` and inactive by
design. A unit whose start instant cannot be read, or whose `systemctl`
query raises `SystemdQueryError`, yields *no reading* rather than a false
one: the term is skipped, the existing status stands, and the fact that it
was not evaluated is recorded beside it. `ports_checked`'s rule — zero
because nothing was wrong must never be served as zero because nobody
looked — at the size of one term in one check.

---

## 3. The reading is `degraded`, and `unwatched` is false in both halves

The filed next action proposed marking the affected service **unwatched**.
Measured against the code that owns the vocabulary, that value is wrong
twice over.

`STATUS_READINGS` classifies `skipped` as `unwatched` and its comment says
what the value means: *"A declared non-check… somebody decided not to look,
and recorded the decision."* Here the check **did** look, and no
declaration says not to. Both halves of the value's meaning are false.

The cost is not only a wrong word. `reliability.UNMEASURED_STATUSES` holds
`("error", "skipped")`, so a `skipped` row is dropped from the rates
entirely — the 79.9 hours would cost the service **nothing**, and
`GET /api/services/reliability` would go on scoring a server that could not
serve as perfectly available. That is `SNAG-SVC-001`'s defect run in
reverse: that entry was a `skipped` row wrongly *charged* as an outage for
eighteen days, and this would be a genuine outage wrongly *excused* as a
declaration.

`error` was considered and is false for a third reason: it means the check
failed and the state is unknown. Here the state is known, and known
precisely.

**A waiver was considered and refused.** `reliability.py` already computes
deductions and reports them `waived: true` for a muted service, and the
argument for reaching for it is real — the cause is a desktop process
wedging a shared card, and 11 of the 12 resets in the window are attributed
by the kernel to `GameThread`, `MainThrd`, `spotify` and `kwin_wayland`,
not one a member of the arbiter's four profiles. It is refused because the
score's question is availability and not blame: `internet` is charged for
three incidents that are the router's fault or the ISP's, and
`reliability.py` rule 4 excuses a *gap in the series* — this monitor's own
downtime — which is a different thing from a service that was measured and
was down. Adding a second waiver trigger beside `mute` would make "not the
service's fault" a thing this repository judges, and it has no evidence for
that judgement beyond the kernel's attribution of a reset it did not watch.

So: **`degraded`, and it deducts.** The `details` blob carries the reset
instant, the unit's start instant and the signature that declared it, so a
reader can see the whole derivation in the row.

---

## 4. What this changes about `SNAG-GPU-001`

Two corrections, both from the measurement rather than from re-reading the
entry.

**The population is at least two monitored services, and the entry names
one.** `venture-chat` is a `services.yaml` entry, is watched, aborted on
this exact signature **ten** times in the window — more than
`alfred-inference`'s six — and reported `ok` throughout every one of them.
The entry's framing, that the 05:00 health review is the structural victim
because it is the first GPU consumer to touch a server idle overnight, is
correct and is *about the discovery*, not about the population: two servers
were poisoned each time and only one had a review pointed at it.

**The entry's shape-of-fix asked for an owner for a state, and the state
does not exist.** Its third candidate — *"it needs an owner for a state the
reset opens and a submission closes"* — is the premise this document
refuses. Nothing needs to close it, because the closing fact is systemd's
restart and that fact is already published.

---

## 5. What is deliberately not decided here

**The estate's question is untouched and is not a blocker.** Message
`bc5f6a09` asks estate-manager what a granted GPU lease is *meant to
promise*, and it is still open on 2026-09-08. It bears on whether the
arbiter should validate the card before admitting work — a producer-side
mechanism this repository may not build. The reading decided here is local,
needs no lease semantics, and would be correct under either answer. If the
estate rules that a grant does promise a usable card, this reading becomes
a second, cheaper witness of the same fact rather than becoming wrong.

**No code is written by this decision, and that was the scope.** The
implementation owes a declaration leaf in `services.yaml`, the extra
`systemctl show` property, the term in `_check_http_and_unit`, tests
falsified against the record measured in §2, and a restart. The measurement
is recorded here in full precisely so that sitting re-runs it rather than
re-deriving it.

**How to re-run §2.** Reset instants:
`journalctl _TRANSPORT=kernel --since <date> -o json --output-fields=MESSAGE,__REALTIME_TIMESTAMP | grep 'VRAM is lost due to GPU reset'`.
Per-unit starts, aborts and successes: the same read against
`journalctl --user -u <unit>`. `-k` must not be used: it implies
`--boot=0` and reported 4 of the 12 resets.
