# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-10-22
>
> **Archive**: Sessions 344 and earlier are in [archive/completed_2026-10-19.md](archive/completed_2026-10-19.md).

---

## Session 405: SNAG-TEST-014's disposition is readable again (2026-10-21)

The published next action: the highest-ranked open snag a session can
start now. None could be started: every entry is decided, blocked or
delegated, `SNAG-LOG-021` still waits on a boot (the box last booted
2026-10-18, before the estate's fix), and `SNAG-LOG-012`'s pre-staged
check still holds. The preflight's one warning was `SNAG-TEST-014`.

- [x] **`SNAG-TEST-014`'s status line uses the comma form**:
      `Open — decided:` read as the token `decided:` and the sweep
      reported it as declaring no disposition. Now `decided, P3:`;
      the open tally reads decided 31, blocked 4, delegated 3, with
      no unknown.

## Session 406: the preflight reads only `## Scheduled action` (2026-10-22)

The published next action: fix the preflight's scheduled-section match,
recorded by Session 404.

- [x] **The awk matches the heading whole**: `/^## Scheduled action[[:space:]]*$/`
      in place of any heading containing "scheduled". Fixed in `622cd92`.
- [x] **2 tests** in `tests/test_handoff_shape.py` lift the awk out of
      the script and run it on forged handoffs; both go red against the
      old match.
- [x] **`SNAG-ESTATE-012`'s check reads `mismatch`** (found this session,
      not worked): `check_unmarked_sentence_invisible` reports that
      STATUS.md's unmarked sentence *"ask estate-manager the Session 33
      question"* now reaches the report, *"the report quotes the sentence
      (estate-manager)"*. Two tests in `tests/test_snag_claims.py`
      (`test_it_holds_against_the_live_reader`,
      `test_a_figure_that_merely_moves_is_unknown_not_a_mismatch`) are red,
      already at `2f98465`, so the pre-push suite is red. The postflight
      also reads STATUS.md's block as 3 unresolved alerts against 5
      measured.

## Session 407: the quotation instrument matches tokens (2026-10-22)

The published next action: find why `check_unmarked_sentence_invisible`
reads `mismatch`.

- [x] **Tokens on both sides**: the baseline's words were subtracted as
      tokens and the second drive searched as a substring, so the live
      alert `estate-manager-audit-timer critical` held the specimen's
      `estate-manager`. Fixed in `a68ab33`; Session 406's item above is
      ticked by it.
- [x] **1 test** injects the hyphenated title into both drives; it goes
      red against the substring search.
- [ ] **`SNAG-LOG-022`: baloo's crash loop rotates the journal** (found
      this session, not worked): three premise failures in
      `tests/test_services_registry.py` find no journal records for
      estate-manager units, so the pre-push suite stays red on them. The
      owner ran `balooctl6 disable` on 2026-10-22 and parked it. The tests
      recover at the next boot and after `estate-manager-review`'s
      2026-10-26 run; tick this when they pass.

## Session 408: the blip row reads the service's own log (2026-10-22)

The published next action: the highest-ranked open snag a session can
start now. None could be started; `SNAG-SVC-001` (P3) waited only on an
owner ruling, which the owner gave this session: (b), give the row
evidence.

- [x] **Blip times leave the scorer**: `ReliabilityScore.episode_starts`,
      dropped by `as_dict` so the wire shape is unchanged.
- [x] **`fetch_blip_logs`** reads the service's `error`/`critical`
      lines within 60 s of each blip, only for blip-shaped scores; a
      live test drives the real query inside a rolled-back transaction.
- [x] **The row's three readings**, correlated one blip at a time
      through `log_actions.correlate`; 14 tests, and the one-call-per-blip
      rule goes red under a whole-window call. Closed `SNAG-SVC-001` and
      retired its check in `d604dfd`.
- [x] **Daemon restarted** onto `d604dfd` at 21:08:24 (PID 2577593).
- [ ] **STATUS.md's Alerts paragraph is stale** (found this session, not
      worked): it names 3 open rows and the box holds 5. The two it
      does not name are `Estate audit checks errored` and
      `estate-manager-audit-timer critical`, both opened today and
      estate-manager's to fix. Rewrite the paragraph to name all five so
      the `alerts` and `open_titles` claims read `ok`.

## Session 404: venture-embed stops declaring holds_vram (2026-10-21)

The published next action: the highest-ranked open snag a session can
start now. Every open entry is decided, blocked or delegated except
`SNAG-GPU-008` and `SNAG-LOG-021`, and both had moved: the race
`SNAG-GPU-008` waited on was settled by venture-assistant on
2026-10-17, and estate-manager answered `571f2f12` at 15:51 today.

- [x] **`venture-embed` drops `holds_vram`** in `services.yaml`; the
      shipped-declaration test expects two services and goes red with
      the old line restored. Closed `SNAG-GPU-008` in `1687713`.
- [x] **ADR-0007 §2.5**, and the comments in `gpu_context.py`,
      `gpu_residency.py`, `services.py`, `CLAUDE.md` and
      `docs/design/gpu.md` moved to the past tense.
- [x] **Daemon restarted** onto `1687713` at 17:40:06 (PID 565829).
- [x] **Estate message `571f2f12` logged**: closed by estate-manager,
      taken as asked (their `69b11db`, ADR-0259). Recorded on
      `SNAG-LOG-021`, which is now blocked on the next boot.
- [ ] **At the next boot, confirm the mosquitto gate's wait**: the boot's
      journal shows `listener address assigned after N s; starting
      mosquitto` and `sysadmin.alerts` holds no `Log error:
      mosquitto.service — Failed to start` row for it; then close
      `SNAG-LOG-021`.
- [x] **The preflight's scheduled-section match is too wide** (found
      this session, not worked): the awk in
      `scripts/claude-preflight.sh` takes the first `## ` heading whose
      text contains "scheduled", so with no `## Scheduled action`
      section it printed `## Session 392: the scheduled-section assert
      is declared` and its bullets as a scheduled action. Likely fix:
      match the heading `## Scheduled action` itself.

## Session 403: the route's condense pass waits out its own first pass (2026-10-21)

The published next action: the highest-ranked open snag a session can
start now. Every P3 entry is still decided, blocked or delegated;
`SNAG-API-006` is decided, `SNAG-GPU-008` waits on a restart and
`SNAG-LOG-021` on estate message `571f2f12`, so `SNAG-GPU-007` was
first.

- [x] **The condense call waits for its own tail**: `generate` takes
      `follows_own_inference` and polls the counter for up to 1 s
      before its single read. Closed `SNAG-GPU-007` in `baa48ca`.
- [x] **5 tests** in `tests/test_llm_client.py` and
      `tests/test_word_limit.py`; 3 go red with the wait removed.
- [x] **Restarted `sysadmin.service`** onto `baa48ca` at 16:53:03
      (PID 271346); `/api/health` answers `healthy`.

## Session 402: mosquitto's boot refusal is asked of the estate (2026-10-21)

The published next action: the highest-ranked open snag a session can
start now. Every P3 entry is still decided, blocked or delegated, and
`SNAG-API-006` and `SNAG-GPU-008` are as Session 398 left them, so
`SNAG-LOG-021` was first. Its preferred fix is in estate-manager's
drop-in, so the work here was a measurement and a filing.

- [x] **Re-measured the refusal**: 5 boots under the gate, one
      self-closing `warning` each; `eno1` arrives 3.9–4.6 s after the
      refusal on the four readable boots.
- [x] **Asked estate-manager for a waiting gate**, estate message
      `571f2f12-f7fc-46d6-89ae-5d9488c67e5e`, with the start-limit cost
      a wait inside each attempt adds.
- [ ] **Act on estate-manager's answer to `571f2f12`.** If they change
      the gate, check the next boot logs no `Failed to start` and close
      `SNAG-LOG-021`. If they decline, price shape (b), pairing the two
      lines of one start job in the aggregator.

## Session 400: the advice reads stream in partitions (2026-10-21)

The published next action: the highest-ranked open snag a session can
start now. Every P3 entry is still decided, blocked or delegated, and
`SNAG-API-006` and `SNAG-GPU-008` are as Session 398 left them, so
`SNAG-SVC-008` was first.

- [x] **Both advice reads stream through a server-side cursor**, 2,000
      rows a round trip, on the session's Core connection. Worst
      `/ping` wait behind `/actions` 0.66 → 0.27–0.35 s under the
      unit's quota. Closed `SNAG-SVC-008` in `e35fd40`.
- [x] **3 tests** in `tests/test_off_loop.py`, and `StreamedResult` in
      `tests/conftest.py` for the routes' existing tests.
- [x] **Restart `sysadmin.service`** so the daemon runs the streamed
      reads: `kill -TERM` on its main PID, no sudo while it is up. The
      owner's step under auto mode. Done by Session 401 on the owner's
      prompt; the daemon came back at 15:25:08 on 2026-10-21.

## Session 398: a run of an agent already running is declined (2026-10-21)

The published next action: the highest-ranked open snag a session can
start now. Every P3 entry is decided, blocked or delegated;
`SNAG-API-006` is decided and `SNAG-GPU-008` waits on a reset after a
boot start, so `SNAG-AGENT-014` was first.

- [x] **`BaseAgent.run` declines an overlapping run** (`99f52ab`): a
      per-name `threading.Lock`, taken without blocking. Closed
      `SNAG-AGENT-014`.
- [x] **8 tests** in `tests/test_agent_run_overlap.py`, falsified by
      removing the check and the release.
- [x] **Restart `sysadmin.service`** so the daemon runs `99f52ab`:
      `kill -TERM` on its main PID, no sudo while it is up. The
      session's attempt was refused by the permission check, so it is
      the owner's step. Done by the owner at 12:33:27 on 2026-10-21,
      recorded by Session 399.
- [x] **STATUS.md's alerts sentence** names the fourth open row,
      `venture-chat unreachable`, opened 10:55 today.

## Session 397: go-to-market's API on 8950 is watched (2026-10-21)

Estate message `495f072e`: go-to-market committed its own
`services.yaml` entry (`970ba50`) the day `go-to-market-api.service`
was made. Applied by reload, no restart.

- [x] **`go-to-market-api` applied** by `POST /api/sysadmin/reload` at
      09:32:10 UTC, which reported that one entry added and nothing
      needing a restart. A scan stored it `ok` at 09:32:15 UTC, 4 ms;
      `/api/health` answered `healthy` with the database connected.
- [x] **Estate message `495f072e` closed**, with a note naming the
      commit and the first stored check.

## Session 396: the roll-up sat unread five days, not eight (2026-10-21)

The published next action: the highest-ranked open snag a session can
start now. Every P3 entry is decided, blocked or delegated; `SNAG-GPU-008`
waits on a reset after a boot start, so `SNAG-DOCS-033` was first.

- [x] **Measured** the roll-up's life in `sysadmin.alerts`: open from
      2026-08-07 10:20 to 2026-08-12 16:08 under four titles, five days.
      The snag's "one day" was the `17 findings` title's age alone.
- [x] **Corrected** twelve sites and the `SNAG-ESTATE-001` bullet
      (`2ec118d`), two of them outside the snag's sweep. Closed
      `SNAG-DOCS-033`.
- [x] **Removed** a stray `Status: Open` line Session 395 left under
      the closed `SNAG-TEST-017`.

## Session 395: the idle-queue assert is declared (2026-10-21)

The published next action: give `SNAG-TEST-017`'s idle-queue assert a
witness or a declaration, the shape `SNAG-TEST-016` closed with.

- [x] **Declared** (`74b919d`): a `# may-not-evaluate:` comment above
      `tests/test_arbitrated_stops_live.py:210`, the reverse of the
      granted branches' declarations in the same file, naming the
      recorded half's `test_no_active_lease_is_idle_and_not_unread` as
      the witness. Closed `SNAG-TEST-017`.
- [x] **Checked** at the gate's reader with the assert marked
      unexecuted: undeclared before, declared after.

## Session 394: the alerts sentence names four rows; the off-loop assert has a witness (2026-10-21)

The published next action: rewrite STATUS.md's alerts sentence, then
the highest-ranked open snag a session can start now. Every P3 entry is
decided, blocked or delegated; of the P4 entries with no disposition,
`SNAG-TEST-016` is the one the vacuous-guard gate reports at every close.

- [x] **Rewrote the alerts sentence**: 4 open rows, all named, and both
      `alerts` and `open_titles` checks read `ok`. The new row is
      `Project clyde-automation-site next action idle`; the ProductHunt
      429 Session 393 saw had resolved.
- [x] **Closed `SNAG-TEST-016`**: the comprehension moved into
      `_dependency_calls`, and a new test drives it on
      `/api/units/status`, which does take the request session. The
      gate's line now turns, and the assert is shown able to fail
      (`7881ca3`).

## Session 393: the GPU-context reader fired on real resets (2026-10-21)

The published next action: the highest-ranked open snag a session can
start now. Session 392 passed over `SNAG-GPU-001` (P2) as decided, but
its rank was waiting on a reading, and the resets it waited for had
already happened on 2026-09-30. Taking that reading needed nothing from
the owner.

- [x] **Read and closed `SNAG-GPU-001`**: 3 resets, 3 of 3 stored;
      `venture-chat` flagged before both of its aborts and served nothing
      while flagged; `llama-server` was flagged 2 h 41 m and was never
      submitted to; both `degraded` alerts opened 53 minutes before the
      first abort. Docs only, so no restart is owed.
- [x] **STATUS.md's alerts sentence is stale**: the block names 3
      unresolved rows; the preflight measured 4 at this session's start
      and 5 at its close. A second concern, named and not worked here.
      Rewritten by Session 394 to name all 4 open rows (the ProductHunt
      429 had resolved by then).

## Session 392: the scheduled-section assert is declared (2026-10-20)

The published next action: the highest-ranked open snag a session can
start now. `SNAG-TEST-018` (P4) was the only entry declared owed; the
P2 and P3 entries are decided or delegated.

- [x] **Declared** (`0b5a39b`): a `# may-not-evaluate:` comment above
      `tests/test_handoff_shape.py:133`, naming the test class that
      drives the same pattern at forged documents. The gate lists it as
      declared. Closed `SNAG-TEST-018`.
- [x] **Left as found:** the gate still exits 1 on
      `tests/test_off_loop.py:99`, which is `SNAG-TEST-016`, open and not
      worked here. `SNAG-TEST-017` did
      not show on this run because the GPU queue was idle.

## Session 391: the API token is a systemd credential (2026-10-20)

The published next action: the highest-ranked open snag a session can
start now. `SNAG-GPU-001` (P2) waits on a real GPU reset, so the first
startable one was `SNAG-API-005` (P3), the only entry declared owed.

- [x] **Daemon half** (`4ef799f`): `sysadmin/core/api_token.py` reads
      `$CREDENTIALS_DIRECTORY/api-token`; `require_auth` prefers it over
      `api.auth_token`.
- [x] **Tray half and unit line** (`17701c9`): `LoadCredential=api-token:`
      on `sysadmin.service`; the tray sends systemd's delivered copy, per
      request, to the daemon's origin only.
- [x] **Installed by the owner** (20:25:27) and probed live: 401 without
      the token, 200 with it, the tray's worker 200 with the header on
      8500 and without it on 8400.
- [x] **Closed `SNAG-API-005`; opened `SNAG-API-006`** for what a token
      the tray can read cannot stop: the owner's own processes.

## Session 390: the token surface becomes a standing rule (2026-10-20)

The owner asked this session to act on estate message
`21860cb6-753f-42f5-954c-7ea872a4be83`. Docs only; no restart owed.

- [x] **Drove the recipe once.** Minted a `sysadmin-assistant` token,
      `/auth/whoami` read *"Claude Code session in sysadmin_assistant"*,
      revoke answered 204 and the token then got 401. No block written.
- [x] **Wrote it into CLAUDE.md** ("Writing to Alfred's planner"), which
      every session here loads; Alfred's own mint hook does not reach this
      repository, so this is the prompt the message asked for.
- [x] **Closed the message** as `sysadmin-assistant`.

## Session 389: Alfred's `sysadmin-assistant` token surface (2026-10-20)

Estate message `21860cb6-753f-42f5-954c-7ea872a4be83` from Alfred
(ADR-0176). Docs only; no code, no restart owed.

- [x] **Read and logged the message.** Alfred now accepts
      `{"surface":"sysadmin-assistant"}` on `POST /auth/session`
      (loopback, port 8100), so a session here no longer borrows `cv`,
      `claude` or `web`. Nothing was minted: no task needed it.
- [x] **Use the surface when a task needs Alfred's planner for downtime
      or sudo** (the owner's stated use). *(Moved by Session 390 into
      CLAUDE.md, "Writing to Alfred's planner", as a standing rule; the
      message is closed.)* Mint with
      `curl -s -X POST http://127.0.0.1:8100/auth/session -H 'Content-Type: application/json' -d '{"surface":"sysadmin-assistant"}'`,
      send `Authorization: Bearer <token>`, and revoke at session end with
      `DELETE /auth/device-tokens/<id>`. The token reads and writes every
      domain; the server restricts nothing about changing blocks this
      session did not create (Alfred row 387). Close message
      `21860cb6-753f-42f5-954c-7ea872a4be83` as `sysadmin-assistant`
      once that has been done.

## Session 388: `ops_claims.py` stops calling the region append-only (2026-10-19)

Session 387's next action. Comments only; no restart owed.

- [x] **Close `SNAG-DOCS-034`.** Three present-tense statements in
      `sysadmin/ops_claims.py`, not two: rule 10's heading, the
      `daemon_start` comment, and `check_open_titles`' docstring, which
      the snag did not list. Each now says the region *was* append-only
      and names `docs/roadmap/archive/status_opening_block_2026-10-19.md`.
      Code in `f8ce7ce`.
- [x] **The same tense in the tests.** `tests/test_ops_claims.py` still
      says the region *is* append-only at lines 1571, 1977, 2486 and
      3558 (docstrings). Lines 1195, 1611 and 3047, and
      `tests/test_claude_md_registry.py:402`, speak of the past or of
      append-only documents in general and stay. Left out to keep this
      sitting to the file the snag named.
- [x] **STATUS.md carries `**Last Updated**` twice** (2026-10-19 and
      2026-10-18, lines 2 and 3). Seen in passing; older line deleted in
      `d75e751`.

## Session 387: STATUS.md's opening block is archived (2026-10-19)

Session 386's next action. Docs and tests only; no daemon code changed,
no restart owed.

- [x] **STATUS.md went from 8,310 lines to 110.** The opening block,
      Sessions 10 to 384's dated announcements, moved unedited to
      `docs/roadmap/archive/status_opening_block_2026-10-19.md`, newest
      first. Only its 15 relative links changed, re-based on the
      archive's directory; every other line was compared with the
      original and matches.
- [x] **A current block replaces it, one paragraph per standing claim.**
      Nine markers moved into it: `deploy`, `daemon_start`, `health`,
      `schema`, `alerts`, `open_titles`, two `flapping` and the
      `expires` prediction for 2026-10-27 03:00. The tenth,
      `migration_head`, marked a prose sentence that still said head
      019; the Quick Status table already states head 021 beside its own
      marker, so the stale sentence went to the archive rather than
      being restated. The block's first paragraph asks for claims to be
      rewritten in place from now on, not added as dated paragraphs.
- [x] **The alert claim was already stale and is corrected: 2 → 1.**
      `Unusual disk / usage` resolved at 11:33:32 today. The open row is
      `Project InvestingAssistant next action idle`.
      `check-ops-claims.sh` reads all `ok` after the move.
- [x] **Four tests assumed the block only grows, and now read the
      archive as history.** `tests/test_ops_claims.py` gains
      `with_history()`, which puts the archived block's prose, markers
      blanked, ahead of the live region. The clock-collision drives, the
      `05:45` zone-fault drive and the superseded-restart count use it.
      The unmarked-figure scope test now anchors on the current
      paragraph's "7-day window" instead of the archived "11.3 %".
      Rejected: lowering the 86-clock floor, which empties the hazard
      drive, and `git show` of the old commit, which skips on a shallow
      clone. Side gain: the "pinned by its own sentence alone" drive was
      going to skip on the lean block and now runs.
- [x] **Nothing else reads the moved text.** `check-snag-claims.sh`
      reports the same as before the move apart from live readings, and
      estate-manager's `estate_service` has no reader of STATUS.md.
- [x] **Fix `SNAG-DOCS-034`**: `sysadmin/ops_claims.py` still says in
      the present tense that the printed region is append-only (rule 10
      at line 179, the `daemon_start` comment at line 402). Comments
      only. Done by Session 388.

## Session 386: STATUS.md's Recently Completed is archived (2026-10-19)

Session 385's next action. Docs only; no code changed, no restart owed.

- [x] **STATUS.md went from 14,615 lines to 8,310.** Sessions 10 to 344
      moved, newest first as they stood, to
      `docs/roadmap/archive/status_completed_2026-10-19.md`. Kept:
      Sessions 349 to 374, the same two-week cut Session 385 made in
      this file. One pointer line replaces the old one.
- [x] **No check reads the moved text.** `ops_claims.printed_region`
      ends at the first `## ` heading after `## Quick Status`, which is
      `## Recently Completed`, and that heading stays. Lines 1 to 8,302
      are byte-identical to HEAD; `check-ops-claims.sh` reads all
      `ok`. No live reader in estate-manager's code; its ADR citations
      of STATUS.md line numbers are dated history.
- [x] **Moved text is unedited except for 10 relative links**, re-based
      on the archive's directory, found with `tests/test_doc_links.py`'s
      own regex. A first sweep with a hand-written `grep` found none;
      the link test caught all 10.
- [x] **A separate archive file, not an appendix to
      `completed_2026-10-19.md`**: that file's header says it came from
      tasks.md, and the same sessions would have stood in it twice.
- [x] **STATUS.md's opening block, lines 1 to 8,242, is left as found.**
      It is about 300 dated announcements, and it is the region
      `ops_claims.py` parses. Ten live check markers sit in it, from
      line 14 (`alerts`) to line 8,136 (`migration_head`), so archiving
      it means moving those claims into a current block first. Three
      more `<!--check:` strings at lines 2,423, 2,520 and 4,341 are
      quoted in backticks and are not markers. Done by Session 387.

## Session 385: the roadmap and the handoff are archived (2026-10-19)

The owner's request: archive old tasks, snags and handoff items. Docs
only; no code changed, no restart owed.

- [x] **tasks.md went from 18,831 lines to about 1,270.** Sessions 24
      to 344, the 2026-08-13 cutover notes and the completed Maintenance
      items moved, in their original order, to
      `docs/roadmap/archive/completed_2026-10-19.md`. Kept: Sessions 345
      to 384 (the last two weeks), Session 286 for its one unticked item,
      and the Backlog, which holds the other.
- [x] **Moved text is unedited except for 44 relative links**, re-based
      on the archive's directory so `tests/test_doc_links.py` stays
      green. Checked by comparing every line before and after: the only
      lines lost are those 44.
- [x] **The two "⚠️ Pending" Maintenance notes from August were moot**
      and moved with the rest. The daemon was last started 2026-10-18
      22:03:29. `sportsanalyser-backend.service` is disabled and inactive
      on purpose: the owner stopped the sports analyser (Session 352).
- [x] **snag_list.md: only the Session 34 and 37 write-ups moved**, to
      the same archive file. Their one-line rows stay in the Fixed
      table. Open entries were not touched: closing one is a judgement
      about the box, not housekeeping. Fixed `SNAG-ESTATE-*` rows also
      stay, because `tests/test_snag_estate_series_is_closed.py` and
      estate-manager's "Also minted" markers read them in this file.
- [x] **HANDOFF.md went from 418 lines to about 150.** Sessions 369 to
      379 moved to the top of `HANDOFF-archive.md`, newest first.
- [x] **`docs/README.md`'s roadmap figure re-measured**: about 37,000
      lines, up from 32,000 on 2026-09-26. The archive move does not
      change it: `tests/test_docs_index.py` counts tracked files matching
      `docs/roadmap/*.md`, and git's pathspec `*` matches the `archive/`
      subdirectory too. The first attempt wrote 19,500, measured while
      the new archive file was still untracked; the full suite caught
      it at 48 % adrift.
- [x] **STATUS.md is 14,615 lines and was left as found.** Lines 1 to
      8,242 come before `## Quick Status`, and Recently Completed runs
      from 8,267 to 14,611. `sysadmin/ops_claims.py` re-measures that
      file's opening block, so moving any of it is a sitting of its
      own, after reading `docs/design/status-claims.md`. Done by
      Session 386.

## Session 384: a VRAM resident evicted to GTT reads degraded (2026-10-18)

Estate message `af170afe-54d0-4997-8a10-42267c6a2214`: a game had
pushed 1.0 GiB of `alfred-inference` into GTT, nothing moves it back,
and the estate's queue will not publish the per-resident split.
Commit `08a2235`; the rules are in `sysadmin/monitor/gpu_residency.py`
and `docs/design/gpu.md`.

- [x] **A third term on the `holds_vram` check.** It reads the unit's
      `MainPID`, sums `drm-total-vram` less `drm-resident-vram` over
      its distinct dGPU clients in `/proc/<pid>/fdinfo`, and reads
      `degraded` at 128 MiB or more. The figures go in
      `details['gpu_residency']`. A lost GPU context keeps its own
      reason. No main PID, an unreadable `/proc` or no client on the
      card leaves the status alone.
- [x] **Driven live before the restart**: `alfred-inference` degraded,
      1,048,320 KiB evicted; `venture-chat` ok, resident 8,448 KiB
      above total, so clamped to 0; `venture-embed` ok, no client on
      the card.
- [x] **Rejected `amd-evicted-vram`**: it read 0 KiB beside the 1.0 GiB
      shortfall.
- [x] **Daemon restarted 22:03:29.**
- [x] **The suite was red at HEAD, and the push needed it green.**
      Session 383 took out the empty `## Scheduled action` heading,
      as the estate's handoff rule asks when nothing is gated. Three
      tests in `tests/test_handoff_shape.py` assumed it always stood.
      They now skip when it is absent. Rejected: putting the heading
      back empty, which the estate refuses ("absent beats fake").
- [x] **Read back from the daemon.** `alfred-inference` was restarted
      at 22:05:33, not by this session, so the first stored row
      (22:08:29, service `llama-server`) reads `ok`, 2,349,364 KiB of
      2,349,364 resident. No stored row carries `degraded` yet; that
      arm was proved by the live drive above.

## Session 383: the game detector's first evenings, and the disk (2026-10-18)

Session 370's scheduled check, read after four evenings of play. No
code.

- [x] **One span per launch.** 24 spans since 2026-10-15 (21 Deadlock,
      3 Slay the Spire 2), each keyed on the Steam AppId, none open.
      Three are one-poll sightings with no duration: a Deadlock launch
      replaced five minutes later (2026-10-16 10:28), one at
      2026-10-18 16:22, and a Slay the Spire 2 seen at the same poll a
      Deadlock span opened (2026-10-18 17:59).
- [x] **Focused stretches while the game was in front.** 163
      `game_focus` rows, all `focused`; 22 of the 24 spans have at
      least one. The gaps between stretches are the game being behind
      another window. No `unknown` row exists, so the KWin probe
      answered on every poll.
- [x] **`agent_runs.details->>'focus'` reads `known`** on all 1,483
      `game_detector` runs that fell inside a span. It is `null` only
      on runs with no game open (3,426), where there is nothing to ask.
- [x] **`/` under 90 %.** The owner's uninstalls took it from 95 % to
      79 % (337 GB free) at 21:56, and the critical disk alert opened
      2026-10-14 resolved itself at 21:56:56. No warning opened after it.

---

## Session 381: estate.snags reads an ASCII priority digit (2026-10-17)

Estate message `67138a9d-3adf-45a5-a409-f4f844b0b0d9` (estate-manager:
`estate.snags` now reads `[P0]`-`[P9]` with `[0-9]`, not `\d`). No
code.

- [x] **Our `PRIORITY_RE` keeps `\d`.** It sets `Entry.priority` in
      `sysadmin/snag_claims.py`, and nothing reads that field: no
      reader in `sysadmin/`, `sysadmin_tray/` or `scripts/`, and the
      only test use builds an `Entry` by hand. No database column takes
      it either, so the estate's failure (a CHECK refusing a full-width
      `[P３]` and failing their nightly scan) cannot happen here.
  - Both patterns find the same 177 priorities in our snag list, all
    ASCII.
  - Rejected: switching to `[0-9]` to match the estate. That changes a
    field with no reader, so nothing would change. If someone ever
    adds a reader, the estate's pattern is the one to copy.
  - Our `read_snags` call counts entries and open entries, and the
    estate says this change does not move either count.
- [x] **Closed `67138a9d-3adf-45a5-a409-f4f844b0b0d9`** with that note.
- [x] **Close notes on two messages we sent, logged.**
  - `4f851ae8-01c9-4656-bffa-3bc1547ab10e` (to Alfred: will it keep
    the game spans it reads?): Alfred confirmed the endpoint answers,
    with 12 spans at 22:50 on 2026-10-16. Its Part 6 is unblocked. It
    noted that focus stretches also carry `state` and `last_seen_at`.
    Nothing is owed.
  - `89d1c61c-2e1b-4993-84a2-5592acbe8ef6` (to estate-manager: on
    2026-10-16 something wiped this session's unstaged edits twice):
    no session ran git or pre-commit in this tree in that window. The
    estate thinks it was the owner's push from project-manager's
    Review tab. Their reasoning: pre-commit stashed the unstaged
    edits, the session reapplied them, the restore then failed and
    fell back to `git checkout -- .`, which was the second wipe. That
    is their reading, unconfirmed; nothing is owed here.

---

## Session 380: ADR-0016 §4 from Alfred's answer (2026-10-16)

Session 379's next action. One ADR amendment and one estate close; no
code.

- [x] **§4 now says the 30 days are the only raw record.** Alfred
      keeps one `Downtime: <game>` entry per run with no expiry and
      stores no spans; it never rebuilds a day older than our window.
  - Chosen: amend §4's retention bullet in place. It named the
    condition it waited on ("until Alfred confirms it"), so an
    amendment section would have left §4 saying "unconfirmed".
  - Retention stays 30 days. Keeping raw spans longer is a new ruling
    for the owner; nothing asks for it.
- [x] **Closed `36903d39-5793-47c9-a8df-eb71fd591cee`.** The close note
      tells Alfred the endpoint has been live since 2026-10-15
      (checked: 200, 12 spans, Deadlock and Slay the Spire 2), since its
      message said Part 6 still waits on it. Our `4f851ae8` stays open
      until Alfred closes it; that is theirs.

---

## Session 379: venture-embed declares holds_vram (2026-10-16)

Estate message `d2b70567-0cc4-42ba-916c-546f0540d94d`: estate-manager
measured that `venture-embed` puts a compute buffer on the card despite
`-ngl 0`. Code in `125bbc9`; ADR-0007 §2.4.

- [x] **Re-measured, and the estate's figures hold.** From
      `journalctl --user -u venture-embed.service`, the first
      `compute buffer size` after each `main: loading model`: 12 boot
      starts on CPU (564 MiB), 10 later starts on Vulkan0 (504 MiB),
      2026-09-03 to now. The live process (10:09:22 BST) is on Vulkan0.
- [x] **Every reset on record hit a CPU-only process.** The 14 resets
      in the kernel journal (2026-09-03 → 09-30) all fell after a boot
      start. So ADR-0007's "267 of 823 served while flagged" measured
      processes no reset could touch. No reset has landed while the
      unit held the card; its abort is inferred, not measured.
- [x] **`holds_vram: true` on `venture-embed`** in `services.yaml`.
      Reloaded live at 17:36; the 17:37:25 check recorded
      `gpu_context.evaluated: true, context_lost: false`.
  - Chosen: declare it. Leaving it absent reads `ok` after a reset in
    the state the unit is in after any restart.
  - Rejected: deciding per start from the unit's `compute buffer` log
    line. Exact, but a new reader for a case never seen. Reopen if a
    boot start's false `degraded` is ever seen.
  - Cost: after a boot start and a later reset, it reads `degraded`
    while it could still serve, until its next restart. Filed as
    `SNAG-GPU-008`.
- [x] **Prose corrected** where it said `venture-embed` holds no VRAM:
      `services.yaml` (three comments), `gpu_context.py` rule 1,
      `ServiceEntry.holds_vram`'s comment, `tests/test_gpu_context.py`
      (the shipped-file pin now names three), ADR-0007 §2.4, CLAUDE.md.
      The rule (a declaration, not a role) stands; its evidence changed.
- [x] The start-order race (no `wait-for-dgpu` gate on the unit) is
      venture-assistant's; the estate filed it there as `d07f4176`.
- [x] **Amend ADR-0016 §4 from Alfred's answer**, estate message
      `36903d39-5793-47c9-a8df-eb71fd591cee` (Alfred, 2026-10-16, in
      reply to our `4f851ae8`). Alfred keeps one "Downtime: <game>"
      entry per run in its own table, with no expiry, and does not
      store the raw spans, so our 30 days are the only raw record.
      Record that in §4, then close the message.
      *(Done by Session 380, 2026-10-16: §4 amended in place, message
      closed.)*

---

## Session 378: the estate should poll for games (2026-10-15)

Session 377's next action, from Session 369's open item. Roadmap,
handoff and one estate message; no code, ADR-0016 unchanged.

- [x] **Recommended: the estate polls `GET /api/games/spans`.** No
      `estate/…` event. The decision is estate-manager's and the
      owner's, because rung 2 is theirs to build. Sent to them as estate
      message `2d24843e-de87-481e-81a4-6a3ee72d675d`, which also tells
      them the "nothing detects a game" blocker in their `ideas.md` is
      gone.
- [x] **Why polling.**
  - **Latency is the detector's, either way.** A game is seen at most
    60 s after launch whatever carries the news. Polling from the
    arbiter's 5 s tick adds seconds. A faster eviction needs a shorter
    detector interval, not MQTT.
  - **A poll is a level reading; an event is an edge.** The estate's
    ADR-0007 Decision 3 re-derives reality every tick. An event is lost
    across an estate restart or a broker outage. Making it safe needs a
    retained topic plus a last will, so a dead daemon does not leave
    "game running" standing.
  - **MQTT's cost is the estate's.** `sysadmin-publisher` can already
    publish on `estate/#` (estate `mqtt/dynsec.yaml`), but the `:8400`
    service has no subscriber. It would need a dynsec client, a
    credential and a reconnecting loop. It already reads `:8500` over
    HTTP (`scan.yaml`, `audit.yaml`).
- [x] **Checked live**: a five-minute window at 17:34 BST answered
      200 in 5 ms, with Deadlock open (`ended_at: null`) since 14:52
      UTC. The reader's test is `ended_at` null and `last_seen_at`
      within about two `poll_seconds` of now; both are served.
- Chosen: poll. Rejected: a game-start event, for the three reasons
  above. The estate's ADR-0001 called MQTT "the obvious carrier"; that
  predates both the detector and the arbiter's tick loop.
- **Reopen when** something needs the push itself (a phone buzz on game
  start). Then publish a retained state topic with a last will, not a
  bare event.
- If the estate polls, it becomes the route's second measured reader
  after Alfred, so a change to the route's shape files at both first.
- [x] **Answered** (2026-10-15, closed by estate-manager): polling is
      recorded as the route in their `ideas.md` gaming-ladder entry, and
      the no-detector blocker is struck. Rung 2 is not built, so they
      are not yet a reader of `/api/games/spans`.

---

## Session 377: the memory index under 140 lines (2026-10-15)

Session 376's next action. The memory directory is outside the
repository, so only the roadmap and handoff are committed.

- [x] **`MEMORY.md` from 175 lines to 123, 21,717 bytes to 19,064.**
      Every link resolves; the old file and the new list the same
      memories bar three.
- [x] **Three lines dropped under the index's own rule** (a memory
      four or more others link to is surfaced by them):
      `estate-messages-the-receiver-closes`,
      `snag-parser-lives-in-estate-service`,
      `exit-status-cannot-see-polkit`. Each is linked from at least
      four memories that stay indexed.
- [x] **34 memories folded into 16 family lines**, each member keeping
      its own link and a short cue, placed at its newest member.
      Rejected: raising the excused threshold to three links, which
      would hide 14 cues with nothing checking they still surface; and
      merging memory files into hubs, which rewrites 30-odd bodies.
- [x] **The header states the line budget** beside the byte budget,
      since the line limit is the one that bit.

## Session 376: no PostgreSQL service for CI, yet (2026-10-15)

Session 375's next action, from Session 368's open item. Roadmap and
handoff only; `ci.yml` unchanged.

- [x] **Recommended: leave `ci.yml` without a PostgreSQL service.**
      Both tests already run on every push, at the `pre-push` stage
      that runs the full suite on the box since 2026-10-14. CI would
      add a second run of the same tests, at a cost.
- [x] **Rehearsed, not reasoned.** The 14 non-`box` test files that
      skip without a database were run against an empty PostgreSQL 18
      on `localhost:5432` (user `gaddi`, database `projects`) inside a
      network namespace. Today, all 14 skip in CI, not just the two.
  - **Service alone: 36 red** (14 failed, 22 errors). Every guard
    sees a reachable database and finds no `sysadmin` schema.
  - **Service plus `alembic upgrade head` first: 2 failed, 154
    passed, 18 skipped.** Both failures assert the live table already
    holds rows (`test_logs_routes.py`
    `test_the_table_holds_rows_to_be_declared`,
    `test_arbitrated_stops_live.py`
    `test_the_deployed_path_has_annotated_at_least_one_row`), so they
    would need the `box` mark.
  - `test_schema_build.py` passes either way. `test_schema_drift.py`
    passes only after the upgrade, and then it diffs a database just
    built from empty, which `test_schema_build.py` already does. The
    drift guard's own job is the box's long-migrated schema, which CI
    cannot have.
- Chosen: no service. Rejected: service plus upgrade plus two `box`
  marks, because its only coverage the pre-push stage lacks is a
  fresh cluster, and the build test already starts from an empty
  database each push.
- **Reopen when** a push can come from anywhere other than this box
  (a second machine or committer), because then nothing guarantees
  the pre-push stage ran. The rehearsal's two-failure list is the
  starting point.

---

## Session 374: the 05:41 power-off was the dark-screen wake again (2026-10-15)

Session 373's next action. Read the journal of boot `1f080b26` (ended
2026-10-14 05:41:15). Roadmap and handoff only; no code changed, no
restart owed.

- [x] **The box had not hung.** Services, the tray's 30 s polls,
      Postgres and the estate API logged normally up to 05:41:15.207,
      27 s after the press. No amdgpu fault in the whole boot.
- [x] **The press was handed to KDE and did nothing visible.** logind
      logged "Power key pressed short" at 05:40:48.6 and took no action,
      because PowerDevil holds the `handle-power-key` block inhibitor.
      Nothing from KDE followed. The journal then stops with no shutdown
      sequence, and the next boot recovered ext4's journal and found
      the ESP's dirty bit: the key was held until the power went.
- [x] **The cause is Session 349's failure, on 7.2.9.** Steam quit at
      21:27:23 on 2026-10-13, the monitors went off at 21:51, and the
      card then slept all night, waking only about hourly (`:37:48` or
      `:42:48`). At 05:19:10, off that pattern and so most likely the
      owner's input, it resumed cleanly with a `drm` change of
      `prop_connector: (null)`. No `card1-DP-2` event followed in the
      21 minutes before the press. Every earlier morning in this boot
      that worked had one within seconds (10-10 10:42, 10-12 09:01,
      10-13 06:43).
- [x] **7.2.9 lets the card sleep; 7.2.7 did not.** Boot `797b83cd`
      (7.2.7, 2026-09-30 to 10-07) logged 0 card resumes. Boot
      `1f080b26` (7.2.9) logged 1,797, the first at 2026-10-08 23:00.
      So Session 349's "7.2 keeps the card awake", which the owner's
      2026-10-08 ruling rests on, held for 7.2.7 and stopped on the
      upgrade. The current boot reads `control=auto` with 0 resumes,
      because Steam is running.
- [x] **Pin the card awake** *(For: owner, ~5 min)*. The 2026-10-08
      ruling already says a sleeping card is not wanted. Two commands,
      run once:
      `echo 'ACTION=="add", SUBSYSTEM=="pci", KERNEL=="0000:03:00.0", ATTR{power/control}="on"' | sudo tee /etc/udev/rules.d/80-dgpu-awake.rules`
      and `echo on | sudo tee /sys/bus/pci/devices/0000:03:00.0/power/control`.
      Check: `cat /sys/bus/pci/devices/0000:03:00.0/power/control`
      reads `on`, and again after the next boot. **Chosen:** a udev
      rule. Rejected: `amdgpu.runpm=0` on the kernel line, which needs
      a boot-entry edit and a reboot, while the rule takes effect at
      once and does not depend on which kernel entry boots.
      **Done 2026-10-15 (Session 375)** through `pkexec`, because
      `sudo` wants a terminal password the session cannot give. The
      rule as written matches `ACTION=="add|bind"`, not `add` alone:
      `add` fires when the card is enumerated, before amdgpu binds,
      and the driver re-enables runtime PM while it loads, so an
      add-only write would likely be undone each boot. Not measured;
      the after-boot check settles it. `udevadm verify` passes, and
      `power/control` reads `on` and `runtime_status` `active`.
- [x] **After the next boot, `power/control` still reads `on`.** If
      it reads `auto`, the rule lost to the driver: try matching
      `DRIVER=="amdgpu"` on the bind event, else fall back to
      `amdgpu.runpm=0`.
      **Held 2026-10-18 (Session 382):** boot `b6bb4935`, the first
      since the rule, reads `on` and `runtime_status` `active`.
- [x] **Compact the memory index under 140 lines.** A hook flagged
      `MEMORY.md` at 175 of its 200-line read limit on 2026-10-15.
      Done by Session 377: 123 lines.

---

## Session 372: idx_alerts_open_by_agent dropped (2026-10-15)

Session 371's next action, Session 359's open task. Migration 021,
applied live the same day; no restart owed.

- [x] **Measured before the drop**: 100,000 open `log_aggregator` rows
      and the index dropped in one rolled-back transaction; `sysadmin`'s
      open-row read took `uq_alerts_open_agent_title`, 4 buffers,
      0.013 ms.
- [x] **Migration 021** drops it; `downgrade` recreates it as 017 did.
      The pointer is migration 017's docstring. Not filed at the
      estate: rule 5 covers schemas and tables holding data.
- [x] **`test_an_open_index_leads_on_agent`**, falsified by reordering
      the unique index's columns.

---

## Session 371: ADR-0016's second half (2026-10-15)

Session 370's next action. Code: `sysadmin/games/focus.py` (the KWin
probe), `sysadmin/games/router.py` (`GET /api/games/spans`), three
models in `contracts.py`, the agent's default probe, the router in
`main.py`; `tests/test_games_api.py`, more in `tests/test_games.py` and
`tests/test_game_spans_db.py`; the registry row in `CLAUDE.md`.

- [x] **The KWin focus probe.** Loads a two-line script, runs it,
      unloads it, reads its line from the user journal by a per-call
      token. A name left loaded by a killed probe is unloaded and loaded
      again. Driven live under the daemon's stripped environment.
- [x] **Found: the daemon is a system unit** with no session bus in its
      environment, which ADR-0016 §3 assumed it had. The probe sets
      `XDG_RUNTIME_DIR` with `build_env`, as `systemctl --user` does.
- [x] **`GET /api/games/spans`**, `response_model=GameSpansResponse`,
      with its registry row. Overlap over `[start, end)` tested against
      the scratch PostgreSQL; a naive timestamp is a 422.
- [x] **ADR-0016 §8** records the five changes from this build.
- Falsified: deleting the leftover-load branch reds its test; matching
  on `started_at >= start` instead of `ended_at >= start` reds the
  overlap test.

---

## Session 370: ADR-0016's first half (2026-10-15)

Session 369's next action. Code: migration 020, `sysadmin/games/`
(`detect.py`, `agent.py`, `models.py`), wiring in config, jobs, main,
self-monitor, retention and metadata; `tests/test_games.py` and
`tests/test_game_spans_db.py`.

- [x] **Migration 020**: `game_spans`, `game_focus`, 30-day retention
      on `last_seen_at` (focus rows go by `ON DELETE CASCADE`), and
      `game_detector` added to the alerts agent whitelist. Applied live.
- [x] **The detector**: a Steam launch by the adjacent argv pair
      `SteamLaunch` `AppId=<n>`, keyed on the AppId; the owner's
      `games:` list under `agents.game_detector`, never counted twice
      inside a Steam launch; names from each library's manifest, else
      `steam:<n>`.
- [x] **The spans**: end at the last sighting; a gap over 3 polls breaks
      a span; startup closes every open span. Falsified: setting
      `ended_at` to the noticing poll, or dropping the gap rule, reds
      three tests.
- [x] **Found by the scratch-database test**: without an ORM
      relationship the focus row was inserted before its span. Fixed by
      a relationship on `GameFocus`.
- [x] **ADR-0016 §7** records the two departures (AppId keying, the
      `state` column) and the gap rule.
- Chosen: one code commit carrying `tasks.md`, which the commit hook
  demands for 5+ code files. Rejected: four 4-file code commits for one
  concern.

---

## Session 369: the game-spans ADR (2026-10-14)

Session 368's next action. Docs only: `docs/adr/0016-game-spans-are-raw-and-alfred-reads-them.md`.

- [x] **ADR-0016 drafted with the owner.** Four rulings: detect by
      Steam `SteamLaunch AppId=<n>` plus an owner-kept `games:` list in
      `config.yaml`; focus by a one-shot KWin script, run only on polls
      that found a game; 30 days kept; spans served raw, Alfred merges.
- [x] **Focus measured, not assumed.** KWin 6.7.5 has no D-Bus call
      for the active window. A loaded, run and unloaded KWin script
      printed the active window's PID and class to the user journal.
- [x] **Replied to Alfred** (message
      `4f851ae8-01c9-4656-bffa-3bc1547ab10e`, in reply to `4dc2b8bc`)
      with the shape. It asks whether Alfred keeps the spans it reads,
      which the owner left for Alfred to answer. `4dc2b8bc` stays open
      until the endpoint exists.
- [x] **Build ADR-0016, first half** (Session 370, 2026-10-15):
      migration 020, `sysadmin/games/`, the agent's six places, 26
      tests. Applied live; daemon restarted 2026-10-15 08:52:12.
- [x] **Build ADR-0016, second half** (Session 371, 2026-10-15):
      `GET /api/games/spans`, its `contracts.py` model, the registry
      row and the KWin focus probe. Then close `4dc2b8bc`.
- [x] **A game-start event for the estate's gaming ladder** (rung 2:
      evict models when a game starts). Recorded as a second concern,
      not worked: whether the detector publishes under `estate/…` or the
      estate polls the route is open (ADR-0016 §6).
      Recommended by Session 378: the estate polls, so nothing is built
      here (estate message `2d24843e-de87-481e-81a4-6a3ee72d675d`).

---

## Session 368: the §2.7 test exists (2026-10-14)

Session 367's next action. One new test file.

- [x] **`tests/test_schema_build.py`**: an empty scratch database is
      built by `alembic upgrade head` through `alembic/env.py`
      (`get_config` patched to its URL), read by `schema_status`, diffed
      against `Base.metadata`, and dropped `WITH (FORCE)`. Two premises:
      it started with no revision, and the comparison reaches every
      mapped table. 4 tests, 0.3 s.
- [x] **Falsified at migration 019**, file restored after each: a read
      of a table no migration created errors all 4 tests; an upgrade
      that skips its index fails the drift test while the head test
      still passes, which is why both are asserted. 0 scratch databases
      left behind either time.
- Chosen: an Alembic `Config` with no ini file, because `env.py` then
  skips `fileConfig`, which would disable every logger already created
  in the pytest run. Rejected: running Alembic in a subprocess, which
  would make the `get_config` patch impossible.
- [x] **Decide whether `ci.yml` gets a PostgreSQL service**, so this
      test and `test_schema_drift.py` run in CI instead of skipping.
      Recorded, not worked: a choice about CI, not about this test.
      Recommended no by Session 376, with the rehearsal behind it.

---

## Session 364: Steam filled /, not the backups (2026-10-14)

Session 363's next action. Docs only: STATUS.md's ops block.

- [x] **pgBackRest's lead ruled out.** The 2026-10-11 02:05 run took the
      second full and expired the March chain (`20260307-141905F` and
      its 33 incrementals), and `/` fell from 1,490 to 1,374 GB that
      morning: 116 GB, as the estate's `1ed64da3` expected. The 0 ms
      expires since have nothing to remove. Nothing to file.
- [x] **What filled `/`, read from `resource_snapshots`.** Two steps:
      +142 GB on 2026-09-22 between 17:00 and 19:00 BST, which is Path
      of Exile 2's install (its directory was born 17:53); and +21.5 GB
      today between 06:07 and 06:17 BST, which is Steam updating Last
      Epoch (manifest `LastUpdated` 06:14). The alert opened at 06:12:46
      on that step. Steam's library is 891 GB of the 1.4 TB used.
- [x] **Ops block refreshed**: 4 open rows named, and the daemon start
      moved to 2026-10-14 05:42:46. That start was a boot: the power key
      was pressed at 05:40:48 and the previous boot's journal ends at
      05:41:15 with no shutdown sequence. `check-ops-claims.sh` reads
      12 of 12 `ok`.
- [x] **Why the box was powered off uncleanly at 05:40:48** on
      2026-10-14. *(Answered by Session 374: it had not hung. The
      screens had not come back after the card woke at 05:19:10.)*
      A second concern, not worked: the journal shows the
      key press and then nothing, so whether the box had hung first is
      unread. Start at `journalctl -b -1 --since 05:30`.
- Left for the owner: the alert stays open until `/` is under 90 %,
  and only uninstalling games gets it there. Not tried: reading each
  game's last-played date, because Steam's `localconfig.vdf` nests its
  app blocks and a flat regex found none.

---

## Session 363: clydeautomation.co.uk is watched (2026-10-14)

Session 362's next action. One declaration in `services.yaml`.

- [x] **`clyde-automation-site` declared** as `kind: http` on
      `https://clydeautomation.co.uk/`, no unit, the `internet` entry's
      shape. Reloaded live (`services_added` named it, 47 services); the
      first poll at 16:57:46 UTC read `ok` in 170 ms. Estate message
      `6db6bf4c` closed with that note.
- Known and accepted: when this box loses its connection the site reads
  down beside `internet`, two alert rows for one fault. Nothing here
  suppresses one check on another's failure; the entry's comment says
  `internet` is the one that names the cause.

---

## Session 362: the thirteen open estate messages triaged (2026-10-14)

Session 361's next action. Docs only. Eight messages were already acted
on or asked nothing and are closed. Three asked nothing but leave a
decision of ours: each is recorded here or in the snag list and closed.
Two are requests whose senders want a close note when the work is done,
so they stay open until then.

- [x] **Closed, already acted on or nothing asked**: `6aa1fbc7`
      (`healthy` and `ok` are one status), `0db3617a` (handoff bound
      done by Session 350, the sports analyser entries by Session 351's
      task, Alfred's `bind:lan` row is Alfred's; §2.7 is the item
      below), `8e1e23bb` and `8c5d026c` (both go-to-market timers
      declared, reading `ok`), `5faf8e47` (`venture-model-probe`
      declared, reading `skipped`), `9c40b495` (the `owners` check is not
      in `JUDGED_AUDIT_CHECKS`), `1ed64da3` (pgbackrest installed: the
      unit carries the estate's Description and ExecStart, the timer
      entry reads `ok`), `99f11c1f` (`_FOR_MARKER` already matches the
      timed marker).
- [x] **Watch `https://clydeautomation.co.uk/` with a `kind: http`
      entry** (estate message `6db6bf4c`, closed by Session 363). clyde-automation-site's
      suggested entry follows the `internet` precedent: project and name
      `clyde-automation-site`, role `frontend`, the https root, since
      http:// and www. answer 301. About 288 requests a day at no cost to
      the owner. Add it, reload, and close the message saying it was
      added.
- [x] **A read-only endpoint for the spans a game was running, for a
      date range** (estate message `4dc2b8bc` from Alfred, closed by Session 371; the
      owner's ruling of 2026-10-11 routed it here). A feature that wants
      its own session and an ADR: nothing here records processes today.
      Detection by full `/proc/<pid>/cmdline` (`SteamLaunch AppId=<n>`)
      or an owner-kept executable list, Discord never; focus via KWin
      if it can be had, else say presence only; 7 days of history; say
      whether spans arrive merged or raw. estate-manager's gaming
      ladder rung 2 waits on the same detector. Close the message once
      the endpoint exists.
      *(2026-10-14: decided in ADR-0016 by Session 369; the build is
      that session's two open items.)*
      *(2026-10-15: built by Sessions 370 and 371 and live;
      `4dc2b8bc` closed with the served shape.)*
- [x] **Decide whether to judge `publish_errors`** on
      `GET :8400/api/estate/messages-invariants` (estate message
      `653e9ae9`, closed). Decided by Session 365: not judged, and not
      added to `SURFACE_PATHS`. Why, with the reopen trigger, is the
      last paragraph of `docs/design/estate.md`: 0 of 750 messages ever
      failed, a failure costs a phone buzz and not a message, a broker
      outage is already the `mosquitto` entry's, and a counter that never
      falls cannot close a row.
- [x] **Amend `SNAG-AGENT-005`'s host-fault paragraphs** (estate
      message `c86f83f9`, closed). Done by Session 366: a dated
      amendment under `SNAG-AGENT-005`, which the message named
      correctly (this line used to say `SNAG-ESTATE-001`). It also found
      the Wi-Fi half now bound to `mt7925e` and the adapter on USB port
      `8-11`. An estate session installed the
      MT7927 Bluetooth firmware into `/usr/lib/firmware/updates/` on
      2026-10-10 and parked the `0489:e13a` udev rule as `.disabled`, so
      the paragraphs saying the blob is unpublished and the device is
      de-authorised no longer describe the box. Re-measure first: `ls /usr/lib/firmware/updates/mediatek/mt7927/`
      and `journalctl -k -b | grep -E 'hci0|Failed to load firmware'`,
      then add a dated amendment rather than rewriting the history.
- [x] **Decide whether contract §2.7's empty-database test applies
      here** (estate message `0db3617a`, closed). monitorable-project.md
      §2.7 now says a service with a database carries one test that
      builds an empty database to head on real PostgreSQL by the startup
      path. This repository owns the `sysadmin` schema and has no such
      test (`tests/test_schema_guard.py` reads the head, it builds
      nothing). The estate named only itself as backfill and nothing
      checks it, so this is a choice, not a breach.
      **Decided by Session 367: it applies, to the `sysadmin` schema.**
      §2.7 names sysadmin_assistant among the services that adopt it in
      their own sequence; the shared `projects` database being
      grandfathered is a different rule (where a schema lives, not who
      builds it), so it is no exemption. The scope is our schema, never
      the whole `projects` database, whose other schemas are not ours.
      *The one-owner half is met*, measured: the Alembic chain is the
      only mechanism (no `create_all` or `CREATE TABLE` anywhere in
      `sysadmin/`, `sysadmin_tray/`, `scripts/` or `tests/`). *The test
      half is owed*, and the chain already passes it: a scratch database
      built by `alembic upgrade head` through `alembic/env.py` reached
      `019` (the packaged head) in 0.1 s with 13 tables, autogenerate
      against `Base.metadata` read 0 differences, and the empty-metadata
      witness read 13 `remove_table` and 13 `remove_index`, identical to
      the live `projects` database. Scratch database dropped after.
      "The startup path" is read as: the service never migrates at
      startup, it refuses unless at head (`verify_schema_revision`), so
      the build is the operator's `alembic upgrade head` and the
      startup's half is that check. Rejected: *not applicable because the
      database is shared* (above); *`test_schema_drift.py` already covers
      it* (it diffs the live schema, so it cannot see a chain that fails
      from empty, which is the estate's `gpu_leases` defect exactly).
- [x] **Write the §2.7 test** (done by Session 368,
      `tests/test_schema_build.py`): create a scratch database, run `alembic
      upgrade head` through `alembic/env.py` with
      `sysadmin.core.config.get_config` patched to the scratch URL (env.py
      reads no other source), then assert `packaged_head()`, 0 drift
      against `Base.metadata` with the empty-metadata witness, and drop
      the database. Skips without PostgreSQL as `test_schema_drift.py`
      does, so CI (no PostgreSQL service) will not run it; adding one to
      `ci.yml` is a separate choice. The probe Session 367 drove is this
      test's body.
- [x] **`Critical disk usage on /` is open and STATUS.md's ops block is
      stale** (done by Session 364: Steam, not pgBackRest; block
      refreshed). Found by Session 362's postflight and not worked, as a
      second concern. `/` read 91 % (146 GB free) on 2026-10-14, the
      alert opened 05:12 UTC, and the block still says 3 open rows and a
      daemon start of 2026-10-10 16:52 (measured 4 and 2026-10-14 05:42).
      One lead, unchecked: pgbackrest's 02:03 run today logged `expire`
      in 0 ms, though the estate's `1ed64da3` expected the March chain
      (about 120 GB) to go a week after the 2026-10-03 install. If it
      did not, that is the estate's to know, by filing. Find what filled
      the disk, then refresh the block.
- [x] **`SNAG-DOCS-033` opened** for portfolio's `a56e0bc4` (closed):
      "unread for eight days" is said of the alert, which was open one
      day.

---

## Session 361: the suite runs at push, once installed (2026-10-14)

Session 360's next action. Config in `1848546`.

- [x] **`.pre-commit-config.yaml`**: pytest, ruff check and mypy at
      `pre-push`, each `verbose: true`, run from `.venv/bin`. Measured
      149.6 s, all passed, pytest 149.32 s of it.
- [x] **CLAUDE.md states the time** under "Step 4: Test".
- [x] **The owner installed the stage** (2026-10-14 13:11); the
      installed hook, driven with a simulated push, ran all three green.
      Estate message `732a62cb` closed.

---

## Session 360: venture-manager's two services.yaml asks are declared (2026-10-13)

Session 359's next action. Config in `e765164`; reloaded live, no
restart owed. Suite 4,612 passed, 2 skipped.

- [x] **`expect: { path: status, equals: healthy }` on `venture-manager`**
      (estate message `bc8d87c1`). First poll after the reload read `ok`;
      the loaded entry, driven at `{"status": "degraded"}`, reads `unmet`.
- [x] **`venture-manager-traffic-timer` declared** (estate message
      `33503d0e`), venture-manager's proposed entry. First poll read
      `ok`, last run `success`.
- [x] **Both messages closed.**
- [x] **Estate Rule 7's backfill** (estate message `732a62cb`), named
      by Session 360 and done by Session 361: declare the suite at the pre-push
      stage of a new `.pre-commit-config.yaml` with `verbose: true`,
      state the stage's measured time in CLAUDE.md, and ask the owner to
      run the install line the message gives.

---

## Session 359: one open alert per (agent, title), held by the schema (2026-10-13)

Session 358's next action, `SNAG-DB-007`. Code in `b7568bf` (a test
stand-in) and `861f742` (migration 019, the model, the tests); applied
to the live database the same day, no restart owed.

- [x] **The identity**: `(agent, title)`, the pair every insert site
      deduplicates on. `details['source']` narrows one resolve and no
      raise; `title` alone would refuse a raise the code allows.
- [x] **Migration 019**: the partial unique index and the two
      flag/timestamp CHECKs, falsified red against the old schema and
      green after, in `tests/test_open_alert_constraints_live.py`.
- [x] **Drop `idx_alerts_open_by_agent`**, found by Session 359 and not
      worked. Migration 019's index leads on `agent` under the same
      predicate, and the planner already takes it for "this agent's open
      rows" (`Index Only Scan using uq_alerts_open_agent_title`). Its
      own migration, and a dropped object leaves a pointer: a note in
      migration 017's docstring is enough, since the index is ours alone.

---

## Session 358: Alfred's Telegram health is watched from the day the bot exists (2026-10-11)

Estate message `d01b0798`, at the owner's request. Test in `ba81bb2`,
the entry in `c056ee9`; reloaded live, no restart owed.

- [x] **The decision**: watch Alfred's new `telegram` health field on
      its own `alfred-telegram` entry, `expect: { path: telegram,
      equals: ok }`, the shape of `alfred-bus` — but not before the
      bot exists, because it reads `disabled` until then.
- [x] **The trigger**: `tests/test_alfred_telegram_wiring.py` skips
      while `~/.config/alfred/telegram.env` is absent and fails from
      the day it exists until the entry is declared. Its gate is
      driven against a temporary path, so it runs in CI too.
- [x] **Declared the same evening** (`c056ee9`). The owner installed the
      token file at 20:58 BST, the test went red, and `alfred-telegram` was
      added beside `alfred-bus` and reloaded in without a restart. First
      poll at 21:17:34 BST read `ok`.

---

## Session 357: a critical service draws a red dot (2026-10-11)

Session 356's next action: `SNAG-TRAY-012`. Code in `902176a` and
`8fb5564`. Nothing is deployed until the tray restarts.

- [x] **One map**: `STATUS_COLOURS` in `sysadmin_tray/styles.py` holds
      exactly the seven `chk_health_status` values, and `status_colour()`
      is the one grey fallback. The overview row, the services-tab card
      and the projects-tab card all read it. The private map in
      `widgets/service_grid.py` is gone.
- [x] **The check**: `tests/test_tray/test_status_colours.py` pins the
      keys to the constraint's `sqltext` in both directions and drives
      all three sites through every value. Falsified: 13 of its 25 tests
      turn red against the pre-fix map.
- [x] **Two code commits, not one.** The pre-commit hook blocks five or
      more code files without docs, and code and prose go in separate
      commits, so the change split at a green point: map and tests
      first, then the two tabs' switch to the helper.

---

## Session 356: a foreign Origin is refused on every mutating route (2026-10-10)

Session 355's next action: the half of `SNAG-API-005` that needs no
secret. Code in `381cfdb`. The owner restarted the daemon at 16:52:34.

- [x] **`require_auth` refuses a foreign `Origin` with 403**, before the
      token check and with or without a token. The allowed list is the
      one `CORSMiddleware` holds, kept on `app.state.cors_origins`.
- [x] **A test per route**: `TestCrossSiteRefused` refuses all 13, and
      `TestRouteCensus` keeps that list equal to the routes that carry
      `require_auth` on `create_app()`. Falsified: 16 red with the check
      disabled.
- [x] **Probed live** after the restart: 403 for a foreign origin and
      for `Origin: null`, 200 for a read with a foreign origin.
- [x] **Recorded, not worked: `SNAG-TEST-017`.** Postflight flagged
      `test_arbitrated_stops_live.py:205`, an idle-queue-only assert with
      no `may-not-evaluate` declaration, while lease 161 was held.

---

## Session 355: the October design review's five defects are recorded (2026-10-10)

Session 354's next action: estate message `dca21976`, in which
estate-manager passed on five defects that the owner's October design
review read in this tree. Roadmap and handoff only; no code changed, no
restart owed. Each claim was re-read at its file and line, and measured
where the box could answer.

- [x] **R4, the empty API token: `SNAG-API-005` (P2).** Confirmed at
      `config.yaml:21` and `core/auth.py:32`. All 13 mutating routes
      are open when the token is empty, and 9 of them take no body, so a
      browser can send them cross-site without a preflight. The old task
      "Set a real `api.auth_token` in the local config.yaml" cannot be
      done as written, because that file is public.
- [x] **R5, the tray palette: `SNAG-TRAY-012` (P2).** Confirmed: two
      maps (`sysadmin_tray/styles.py:50-59`,
      `widgets/service_grid.py:21-26`) and three readers, none mapping
      `critical`, `warning` or `skipped`. 311 `critical` rows in the last
      7 days showed as grey dots.
- [x] **R35, duplicate open alerts: `SNAG-DB-007` (P3).** Confirmed in
      the schema (`core/models/alert.py:30-76`), and empty on the live
      table: 0 duplicate open `(agent, title)` pairs and 0 flags that
      disagree with their timestamps.
- [x] **R36, a unit that never applies migrations: no entry, because
      this is the design `SNAG-DB-005` chose.** That entry, about the
      23-hour outage of 2026-08-23, rejected applying migrations at
      start-up, because it would run an unreviewed migration with nobody
      watching. It chose to block the commit instead:
      `scripts/claude-precommit.sh:95` still runs
      `check-migrations.sh`, which refuses a commit while the database is
      behind the checkout. The review itself noted it was by design.
- [x] **R43, two stale lines in `CLAUDE.md`.** Found by Session 355;
      done by Session 373 (2026-10-15), both lines removed. `CLAUDE.md:8` still holds the template placeholder
      `_Update this as your project evolves_`, and `CLAUDE.md:104` says
      "~360 tests" where Session 354's run counted 4,540. Remove the
      placeholder line, or replace it with a real phase if the owner has
      one, and drop the count (`pytest` prints it) instead of updating it.
- [x] **Not recorded: the review's two closing remarks.** The 24 direct
      `select`/`execute` calls in `sysadmin/files/router.py`, and the
      package being 48% docstrings and comments. The message lists them
      outside the five and calls neither a defect.
- [x] **README's line counts re-measured.** This block's own prose took
      the tree's Markdown total to 61,824, 15.2% beyond the README's
      "52,400", and `test_readme_claims` turned red at postflight. Now
      36,300 roadmap lines of 61,800, measured 2026-10-10.

## Session 354: this repository's two failure units are declared (2026-10-09)

Session 353's next action. `services.yaml` changed; applied by reload,
no restart.

- [x] **Why they were unmonitored.** Both units are this repository's
      (`systemd/`), and neither ever had an entry. Each is a oneshot that
      an event starts: `sysadmin-failed.service` by `sysadmin.service`'s
      `OnFailure=`, and `sysadmin-replay-failures.service` by each
      login's `graphical-session.target`. No kind polls such a unit, and
      the sweep offers no snippet for one, so nothing suggested an entry.
- [x] **Declared as `kind: static`, `monitor: false`**, each with its
      reason, the shape of the arbiter-started units. Both are
      `controllable: false`: starting the first by hand announces a
      failure of `sysadmin.service` that has not happened. The reload
      reported exactly the two added; a sweep run by hand at 13:34:16 UTC
      reads 0 unmonitored and 2 `host`.
- [x] **STATUS.md re-counted 3 → 4.** The new row is
      `Project InvestingAssistant next action idle` (opened 2026-10-08
      22:50:11), which is InvestingAssistant's to move.

## Session 353: go-to-market's reply watcher is watched (2026-10-08)

Session 352's next action. `services.yaml` changed (`f3e7ffe`); applied
by reload, no restart.

- [x] **`go-to-market-watch-replies-timer` declared**, `kind: timer`
      beside `go-to-market-draft-check-copy-timer`, as estate message
      `b00baf51` asked. The reload reported that one entry added, and
      the 21:04:11 UTC poll stored it `ok`. The sweep folds the oneshot
      service under its timer, so the service leaves the unmonitored
      findings too.
- [x] **The units roll-up resolved, not re-raised.** A sweep run by
      hand at 21:05:52 UTC found four findings, under
      `alert_threshold: 5`, so `Unmonitored systemd units: 5 findings`
      resolved. STATUS.md re-counted 4 → 3.
- [x] **Estate message `b00baf51` closed**, with a note naming the
      commit.

## Session 352: the sports analyser's stopped units are no longer polled (2026-10-08)

Session 351's next action, and the task it recorded below. `services.yaml`
changed (`069174b`); applied by reload, no restart.

- [x] **Three entries `monitor: false`, each with the ruling as its
      reason.** `sports_analyser`, `sports_analyser-frontend` and
      `sportsanalyser-pipeline-timer`. Applied with
      `POST /api/sysadmin/reload` rather than a restart, so STATUS.md's
      claimed daemon start stays true; the reload reported exactly those
      three as changed. The 21:39:11 poll stored all three `skipped`
      with the reason, and their alerts resolved at 21:39:14.
- [x] **Estate message `fd376758` closed.**

## Session 351: STATUS.md's opening block is current again (2026-10-08)

Session 350's next action. STATUS.md, roadmap and handoff only; no code
changed, no restart owed.

- [x] **Four starts recorded, not two.** The owner restarted the daemon
      by hand at 2026-10-05 20:29:16 (`sudo`, `pts/4`) and 21:33:50
      (`pts/19`); no session transcript holds either. Then the reboot
      into `linux-lts` (2026-10-07 21:42:10) and the boot after the hard
      reset (2026-10-08 08:49:11), which the block now claims.
- [x] **Seven open alerts named, not two.** The three sports analyser
      rows, Alfred's `Estate port 8100 registry breach` and the
      recurring `Unmonitored systemd units: 5 findings`, each with its
      cause in the re-count note.
- [x] **The 2026-10-08 03:00 prediction measured and replaced.** The
      2026-09-07 specimen cleared, but 53 newer shared instants keep the
      test passing. Their clearing is derived from the real
      `purge_statement` (1 of 53 left on 26 October, 0 on 27 October)
      and is the block's new `expires` marker.
- [x] **Stop polling the sports analyser's stopped units.** Found by
      Session 351 and not worked, as a second concern. An estate session
      stopped and disabled `sportsanalyser-backend.service`,
      `sportsanalyser-frontend.service` and
      `sportsanalyser-pipeline.timer` on the owner's ruling of
      2026-10-07 (estate message `fd376758`), and `services.yaml` still
      declares all three, so three `critical` alerts stay open. Set
      `monitor: false` on the three entries, with the `reason` that key
      requires citing the ruling, restart the daemon, and close the
      message.
- [x] **Trace the recurring `Unmonitored systemd units: 5 findings`.**
      Found by Session 351 and not worked. The same set has opened and
      resolved four times since 2026-09-09. Two of the five are this
      repository's own units (`sysadmin-failed.service`,
      `sysadmin-replay-failures.service`); two are the system-scope
      `deadlock-api-ingest` units, filed `host`. The fifth,
      go-to-market's `go-to-market-watch-replies.service`, was declared
      by Session 353, and the row resolved at four findings, under the
      threshold of five. The four remain findings, and one more new
      unit re-raises it.
      *Done by Session 354 (2026-10-09):* this repository's two units are
      declared. The two `deadlock-api-ingest` system units stay `host`
      findings: they are disabled, and whether to enable or remove them
      has been recorded as the owner's decision in `services.yaml` since
      Session 48 (2026-08-15).

## Session 350: the handoff is archived (2026-10-08)

Session 349's next action. Handoff and roadmap only; no code changed, no
restart owed.

- [x] **HANDOFF.md is under estate rule 2's 500-line bound.** Sessions
      343 and older (lines 188 to 14,361) moved unedited, newest first,
      to `HANDOFF-archive.md`, whose header follows the one `dotfiles`
      wrote the same day. HANDOFF.md keeps Sessions 344 to 349 and is
      221 lines. The kept top plus the archive body reconstructs the
      original byte for byte.
- [x] **Found: 10 live tests red, not caused here.**
      `tests/test_arbitrated_stops_live.py` and
      `tests/test_estate_surface_payloads.py` fail because 8400's
      `/api/queue/invariants` answers `503`, `queue not ready: database
      unavailable`; the same 10 fail with the original handoff restored.
      The estate's queue is theirs; the next sitting reruns them before
      reading a red as its own.

## Session 349: on linux-lts the card sleeps, and the screens do not come back (2026-10-08)

Session 348's scheduled action, brought forward by the owner reporting
an overnight "crash". Read
`~/.local/state/sysadmin/dgpu-pin-witness-lts-2026-10-08.jsonl` (657
minutes, 2026-10-07 21:51 to 2026-10-08 08:47) and the journal of boot
`f616db54`. Roadmap and handoff only; no code changed, no restart owed.

- [x] **The 7.2 kernel is what keeps the card awake.** On
      `6.18.55-1-lts` with Steam quit, both DP monitors went off at
      21:53 and the card reached `suspended` 21 s later. It was
      suspended in 551 of 657 minutes, waking only for `llama-server`
      (the enrichment job, about hourly) and dropping back within a
      minute each time. `kwin_wayland` submitted nothing after 21:53.
      Every other night measured on 7.2 had it `active` in every second.
- [x] **On this kernel the screens did not come back after the card
      slept.** The card resumed at 08:00:01 and 08:20:27, almost
      certainly the owner's input: PSP, SMU and DMUB came back cleanly
      and powerdevil saw a `drm` change on `card1` with
      `prop_connector: (null)`, but every connector stayed
      `disconnected` in the witness and no client drew. The card went
      back to `suspended`. The owner saw the monitors power up to their
      logo and then go black: they woke and found no signal, so the
      card never trained the DP links.
- [x] **It was not a crash.** Services, the tray, Postgres archiving
      and the witness itself logged normally up to 08:47:50, when the
      journal stops mid-stream with no shutdown sequence: a hard reset.
      The reset left the witness's last line as 281 NUL bytes; the 656
      lines before it are whole. The box came back on `7.2.9-arch1-1`.
- [x] **The one earlier suspending night may have gone the same way.**
      27 to 28 September (6.18 LTS, 283 resumes) shows the same
      `prop_connector: (null)` resumes at 08:30:36 and 08:31:39 and a
      last one at 08:56:40. Not settled: that boot ended in a clean
      shutdown at 11:48:34, so the screens may have come back then; the
      journal holds nothing saying either way.
- [x] **Owner ruling: is a sleeping dGPU still wanted?** *(Ruled 2026-10-08:
      no. The hunt is closed; the box stays on 7.2.)* The hunt began
      with the card never sleeping (Session 324). The answer is now that
      7.2 keeps it awake, and the one night it slept, the screens it
      drives did not wake. Recommended: close the hunt and treat 7.2's
      always-active card as the working state, because a lower idle draw
      is not worth a reset. The alternative is to keep chasing it as a
      kernel display-wake bug, which belongs upstream rather than here.

## Session 348: the linux-lts witness is scheduled (2026-10-07)

Session 347's next action, the owner's, done a day late. Roadmap and
handoff only; no code changed, no restart owed.

- [x] **The owner booted `linux-lts` and scheduled the root witness.**
      Booted 2026-10-07 21:41:53 into `6.18.55-1-lts` (not the 6.18.54
      named below; still the LTS line, so the night still separates it
      from 7.2). Steam was not running at 21:43. The 21:30 start had
      passed, and a transient `--on-calendar` timer set in the past never
      fires, so `sysadmin-dgpu-pin-witness-lts.timer` fires at 21:50:00
      instead, with `--duration 43200`, writing
      `~/.local/state/sysadmin/dgpu-pin-witness-lts-2026-10-08.jsonl`.
      Checked with `systemctl list-timers` and `systemctl cat`. The
      Session 347 item stays open until the log has been read, after
      09:50 on 2026-10-08.
- [x] **Bring HANDOFF.md under estate rule 2's 500-line bound.** *(Done
      by Session 350.)* Found
      by Session 348 and not worked, as a second concern. The estate
      added the bound on 2026-10-07 (their message 0db3617a, which also
      announced a `bind:lan` marker and other contract changes still to
      read); HANDOFF.md is 14,316 lines. Move the sections older than the
      recent few into `HANDOFF-archive.md` beside it, leaving the top
      blocks the board, hook and audit read.

## Session 347: as root, kwin goes quiet with the monitors off (2026-10-06)

Session 346's scheduled action. Read
`~/.local/state/sysadmin/dgpu-pin-witness-root-2026-10-06.jsonl` (720
minutes, 2026-10-05 21:31 to 2026-10-06 09:30). Roadmap, STATUS.md and
handoff only; no code changed, no restart owed.

- [x] **Root sees nearly everything.** `unreadable` is 0 to 2 a minute
      all night, against 488 to 527 when run as the user. The card read
      `active` in all 43,200 seconds and `suspended_ms` totals 0.
- [x] **kwin is not the holder.** Both DP monitors were `disconnected`
      from 21:53 to 05:50, 477 minutes. `kwin_wayland` submitted work in
      one of them, the 21:53 minute the monitors went off (19 s), and in
      none after. No root process appears among the clients at all.
- [x] **Steam was running, so this night cannot say more.** Steam was
      started at 2026-10-05 08:41, after Session 346 checked at 07:52.
      In the off window `steamwebhelper` submitted in 28,614 and
      `Xwayland` in 28,616 of 28,620 seconds, so `longest_quiet_s` is 0
      in all 477 minutes: a visible holder the whole night.
      `llama-server` worked in 202 minutes (the enrichment job).
- [x] **What is left, read across both nights.** On 2026-10-04 (Steam
      quit, as the user) every visible client was quiet for whole minutes
      and the card still never slept; kwin and root processes were the
      invisible ones. Tonight shows both quiet with the monitors off. The
      two facts come from different nights, but nothing about kwin's
      idle behaviour should depend on Steam. What remains is the driver
      or firmware, or a process that holds the card's power reference
      without submitting work (fdinfo counts submitted work only; a
      frequent sensor read through sysfs is one such reader, not checked).
- [x] **Owner: one night on `linux-lts`, Steam quit, witness as root.**
      *(Run 2026-10-07 21:50 on `6.18.55-1-lts`, cut short by a reset
      at 08:47; read by Session 349, which records the result.)*
      *(Needs a reboot and `sudo`.)* Quit Steam, reboot and choose
      `linux-lts` (6.18.54, installed) at the boot menu, then schedule
      the witness. A transient timer does not survive a reboot, so
      schedule it after booting:
      `sudo systemd-run --unit=sysadmin-dgpu-pin-witness-lts
      --on-calendar='YYYY-MM-DD 21:30:00' /usr/bin/python3
      /home/gaddi/projects/sysadmin_assistant/scripts/dgpu-pin-witness.py
      --log /home/gaddi/.local/state/sysadmin/dgpu-pin-witness-lts-<next day>.jsonl
      --duration 43200`. If the card suspends, the 7.2 kernel is the
      cause. If it still never sleeps with every client quiet, the kernel
      is cleared and the firmware or a non-submitting reader is left.
      Read the log after 09:30 the next day.
- [x] **Record the owner's 2026-10-05 21:33:50 restart in STATUS.md.**
      *(Done by Session 351, with three more starts it found.)*
      Found by Session 347 and not worked, as a second concern:
      `check-ops-claims.sh` reads the block's daemon start time
      (06:20:53) as out of date. The system journal has `sudo systemctl
      restart sysadmin.service` at 21:33:48 from `TTY=pts/19` in this
      repository's directory, and `NRestarts=0`, so it was a clean manual
      restart, most likely to take the services.yaml entries other
      repositories committed that day. Session 345's block shows how to
      record one.

## Session 346: the root witness is scheduled (2026-10-05)

Session 345's next action, which was the owner's. Roadmap and handoff
only; no code changed, no restart owed.

- [x] **The owner scheduled the root witness for tonight.**
      `sysadmin-dgpu-pin-witness-root.timer` fires at 2026-10-05
      21:30:00 and runs for 43,200 s, writing
      `~/.local/state/sysadmin/dgpu-pin-witness-root-2026-10-06.jsonl`.
      Checked with `systemctl list-timers` and `systemctl cat` at
      07:52. Steam was not running then. The Session 338 item stays
      open until the log has been read.

## Session 345: the owner's deploy recorded, one restart (2026-10-05)

Session 344's next action. No code changed: STATUS.md, the roadmap and
the handoff, plus one daemon restart.

- [x] **Whose 20:50:41 restart it was.** The owner's, from a terminal
      (`TTY=pts/19`): the system journal has `sudo ./scripts/setup-systemd.sh`
      at 20:50:40 and `sudo systemctl restart sysadmin` at 20:50:41, and
      no session transcript holds either command. Active at 20:50:43,
      the `READY=1` instant under `Type=notify`.
- [x] **Restarted once** at 2026-10-05 06:20:53 (`kill -TERM` on the
      main PID, back in 12 s, `/health` 200) after a green suite (4,540
      passed, 2 skipped). `/api/files/trends` now reads 117.1 MB/day
      over 81 scans, 50 GB on 2026-12-30, 100 GB on 2028-03-11.
- [x] **STATUS.md re-recorded**: a new entry carries the bold restart
      time and both check markers; Session 339's entry keeps its time
      unbolded. Every `check-ops-claims.sh` row reads `ok`. The
      `venture-chat unreachable` row the last block flagged opened and
      closed three times overnight and is closed, so the count of 2 holds.

## Session 286: the `box` marker, and three CI causes that were not the box (2026-09-28)

`SNAG-TEST-015`, second half. Tests, `pyproject.toml`,
`.github/workflows/ci.yml` and the roadmap files; no `sysadmin/` change,
no restart owed.

- [x] **104 tests that read the box carry a registered `box` marker, and
      CI runs `pytest -m "not box"`.** Classified by each failure's reason
      on the real runner and in a rehearsal, never by file. On the class
      where every test reads the box, on the function otherwise.
- [x] **Three failures the marker must not hide were fixed in the
      workflow instead:** `fetch-depth: 0` (the briefing guards walk
      history, 4 tests), `TZ: Europe/London` (ops-claims times, 12) and
      `UV_PYTHON: "3.12.12"` (coverage arcs differ from the runner's
      3.12.3, 4).
- [x] **Push `main` and read the run.** Pushed at the owner's word. Run
      36467479237, Python 3.12.12: 36 failed, 4,124 passed, 124 skipped,
      104 deselected. All 36 are in the set that fails only on
      estate-manager's pushed estate-lib, exactly as rehearsed; nothing
      else fails.
- [ ] **When `UV_PYTHON` in `ci.yml` stops matching the box's
      interpreter, move it.** The coverage-arc tests are sensitive to the
      CPython patch release; `uv run --no-sync python -V` on the box is the
      value.

## Backlog

**Carried-forward follow-ups** — small items noted by the sessions that
deferred them. Hoisted here 2026-08-05 when Sessions 10–23 were archived,
so nothing was buried with them.

Conformance (noticed 2026-09-05, Session 175):
- [x] **This service does not serve the health path it enforces on
      everyone else.** `GET :8500/api/health` answers **404**; the
      contract in `monitorable-project.md` §2.2 requires it, and
      `units/recommendations.py` emits `url: http://localhost:<port>/api/health`
      into every `services.yaml` snippet this repository recommends —
      so the monitor tells other projects to serve a path it does not.
      Measured while restarting for an unrelated reason: `/health`
      answers 200, `/api/health` 404, and this repository's own
      `services.yaml` row points at `/health`
      *(Re-read by Session 266, 2026-09-27, and left open: measured today: `:8500/api/health` returns 404 and `/health` 200. Since estate message `3f2a0e0a` (2026-08-29) the estate's registry marks 8500 `health:legacy`, so the contract records the gap, but the route is still not served.)*
      *(Chosen by the owner on 2026-09-27, Session 267, as the next work: the cheaper half only, adding `/api/health` beside `/health`. The snippet generator's half stays with `SNAG-UNITS-003`.)*
      *(Done 2026-09-27, Session 268: `GET /api/health` is served by the same handler as `/health`, measured 200 on the restarted daemon, and this service's own `services.yaml` row polls it. `/health` stays for the tray's liveness probe. The access-log exclusion covers both paths. Announced to estate-manager so its registry can drop `health:legacy` from 8500.)*
- **It is already counted and not separately filed.**
      `SNAG-UNITS-003` measured every hand-written entry on 2026-08-16
      and found `/api/health` correct for **4** of the 11 declaring a
      port and a unit and wrong for **7**, naming `sysadmin-service`
      itself among them. So this is a *decision* owed rather than a new
      finding, and the decision has two shapes that are not the same
      question: whether the snippet generator should probe rather than
      guess (that entry's own candidate fix), and whether this service
      should add `/api/health` beside `/health` so the party enforcing
      the contract conforms to it
      *(Checkbox removed by Session 266, 2026-09-27; the bullet stays because it is a standing note, not work owed. An observation that the gap is already counted under `SNAG-UNITS-003`. Nothing to complete.)*
- **Nothing here should be done unilaterally.** The path is the
      estate's contract, so changing what this repository *emits* is a
      recommendation to every other project; adding a second route here
      is ours alone and is the cheaper half. Not started, and recorded
      so the next sitting to notice the 404 finds the measurement rather
      than repeating it
      *(Checkbox removed by Session 266, 2026-09-27; the bullet stays because it is a standing note, not work owed. A directive about how the health-path item above may be acted on, not work owed.)*

Notifications (from SNAG-CFG-001, 2026-08-11):
- [x] **The daemon announces an outage's start and never its end.**
      `sysadmin/monitor/desktop.py` notifies on `alert.raised` only,
      because `alert.resolved` carries a *match pattern* rather than a
      subject — `BaseAgent.resolve_alerts` publishes
      `{"agent", "match", "count"}`, and the project organiser's `match`
      is `"Project % health critical"`. A recovery toast needs the
      resolve events to name what recovered, which means changing the
      three resolve paths, not the notifier
      *(Re-read by Session 266, 2026-09-27, and left open: `sysadmin/monitor/desktop.py` still subscribes to `alert.raised` only, and its docstring still says recovery is deliberately not announced.)*
      *(Done 2026-10-03 by Session 336, without touching the resolve paths: the sweep announces the end of a fault it spoke for once its row closes after the sweep's previous look. See the Session 336 block.)*
- [x] **The presence signal cannot tell the tray from any other client.**
      Any GET of `/api/sysadmin/alerts` counts as "somebody is watching",
      including a `curl`. It errs towards silence, which is the safe
      direction and the pre-existing behaviour, but a tray that
      identified itself (a header set in `sysadmin_tray/client.py`) would
      be exact. Deferred because an older tray build would then go
      unrecognised and both would toast — the duplicate this design
      exists to prevent
      *(Re-read by Session 266, 2026-09-27, and left open: `tray_presence.mark_seen()` fires on any GET of `/api/sysadmin/alerts`, and the tray's client sends no identifying header, only `Authorization`.)*
      *(Done by Session 337, 2026-10-04: the tray sends `X-Sysadmin-Client: sysadmin-tray` and the route marks presence only on that. The older-build risk was met by restarting the tray before the daemon.)*
- **The tray re-announces the open alert set on every start**, because
      `NotificationPolicy`'s fingerprint state is in-memory. Now that
      `sysadmin-tray.service` starts at login this happens every login.
      Measured 2026-08-11 against the live set — six distinct
      fingerprints fold into **one** coalesced summary and the next poll
      is silent, so it is currently a feature ("here is what is
      outstanding") rather than noise. It stops being one if the distinct
      count ever drops below `coalesce_threshold` while the volume stays
      high. No action while the numbers hold; recorded so the next
      "why did it just announce everything?" is a lookup, not an
      investigation
      *(Checkbox removed by Session 266, 2026-09-27; the bullet stays because it is a standing note, not work owed. The item says "no action while the numbers hold": expected behaviour, recorded. The tray's policy state is still in memory.)*
- [ ] **Page-1 churn can re-notify a standing alert.** The tray fetches
      the newest 50 unresolved alerts; with 547,814 of them, a burst of
      new rows pushes an older title off the page, `_close_inactive`
      closes its episode, and the title notifies again as a *new* episode
      when it reappears. Harmless at the current rate (one alert in 90
      minutes) and unbounded when the log aggregator is noisy — which
      makes it a second consequence of SNAG-AGENT-002 rather than a tray
      defect. A fix belongs on the volume, not on `limit=50`
      *(Read 2026-09-14 by Session 235 and **left open**, which is the reading this item most needed. Its own remedy — *"a fix belongs on the volume"* — landed as `SNAG-AGENT-005` on 2026-08-12 and did **not** remove the mechanism: replaying `created_at`/`resolved_at` as a running open-row count, the table held **95** unresolved rows at once on 2026-08-13, peaking the day **after** that fix and staying over the 50-row page for 2 h 41 m. It has been clear since — max **34** between 08-14 and 08-29, **19** in the last seven days — but clear is a property of today's fault load, not of the code: `GET /api/sysadmin/alerts` still defaults to `limit=50` newest-first (`sysadmin/monitor/routers/sysadmin.py:288`) and `_close_inactive` still resets a fingerprint absent from a poll (`sysadmin_tray/notifications.py:913`). Naming a closed entry was not proof this was done.)*
      *(Re-read by Session 266, 2026-09-27, and left open: re-read by Session 235 on 2026-09-14 and still unchanged: `limit=50` on the route and `_close_inactive` in the tray's notifications module.)*
- [x] **547,814 unresolved `Log error: kernel` rows** were found in the
      table while measuring notification volume. That is SNAG-AGENT-002's
      damage rather than a new defect, and the notifier's incident gate
      makes it harmless to *notifications*, but nothing has ever purged
      or resolved them — retention purges resolved rows only
      *(Closed 2026-09-14, Session 235: the backlog was reached after all. `SNAG-AGENT-005`'s `_resolve_quiet` closes a row unobserved for `alert_quiet_minutes`, and it keys on `COALESCE(details->>'last_seen_at', created_at)` — which is what made rows written before that fix reachable at all, the one thing this item said nothing would do. Measured live rather than inferred: `Log error: kernel%` holds **607,148** rows and **0** of them unresolved. The table-wide unresolved total is not pinned here — it moved 6 → 5 during the sitting that read this — so the claim rests on the family's zero.)*

Tray / UI:
- Wire Session 18's file-action endpoints (`/api/files/organise`,
  `clean/duplicates`, `clean/downloads`) into Session 19's Files tab — the
  tab is deliberately read-only because the endpoints landed in a parallel
  session. Each view already holds its parsed rows, so the work is
  per-row/selection buttons plus a confirmation dialog reusing
  `quick_wins.clean_confirmation_text`'s pattern. Remove the
  "display-only until the file-action endpoints land" note at the same time
- Tray consumes Session 17's SSE stream (`GET /api/sysadmin/events`)
  instead of polling `/health`. Note from the live run: the log aggregator
  currently raises one alert *per* error line (SNAG-AGENT-002, fixed by
  Session 27), so a poll can emit dozens of `alert.raised` events — the
  consumer must coalesce. Once this lands, a file-organiser `agent.run`
  event should refresh the Files tab instead of the user pressing Rescan
- Projects tab could show the branch-prune dry-run manifest behind a
  confirmation dialog (name the branches, state the count, say what is
  recoverable via `git branch <name> <sha>`). Contract is already shared,
  so this is presentation only
- Visual sanity-check of the Files tab and trend charts on a real Plasma
  session — built and screenshotted headless only

Backend:
- `response_model=` on the `/api/files/*` GET routes (contracts exist and
  are parse-side enforced; the routes aren't annotated yet)
- `git remote prune origin` for gone-upstream remote-tracking refs — read
  but never deleted by Session 20; a separate, safer action
- A repo-wide "branch report" GET (no auth, no mutation) so the score can
  explain *which* branches cost it points, not just the count already in
  `findings.stale_branches`
- Config loader could warn when a managed project's `path` doesn't exist —
  would have caught SNAG-CONF-001 immediately (also in ideas.md and
  snag_list.md)

Config / ops:
- Set a real `api.auth_token` in the local config.yaml — auth ships
  disabled because config.yaml is committed. *Superseded by
  `SNAG-API-005` (2026-10-10): this repository is public now, so a token
  in that file is a published token. The entry describes two routes that
  do not need one.* *Done another way 2026-10-20 (Session 391): the token is the
  `api-token` systemd credential, never in config.yaml.*
- PA-auto's 224 branches will take 12 confirmed calls at the current
  `max_deletions: 20`; raising it for a one-off sweep is a config change,
  deliberately not a request parameter

---

## Maintenance

_Not numbered sessions — config/upkeep work that doesn't warrant one.
Completed maintenance is in the archive._

