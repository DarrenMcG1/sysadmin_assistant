# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-25

---

## After the Session 4 cutover (estate-manager, 2026-08-13)

_Project state left this repository — [ADR-0005](../adr/0005-project-state-leaves.md).
`sysadmin/projects/` and `sysadmin/registry/` are both gone: the first to
the estate's 8400 service, the second to `estate-lib` as `estate.registry`,
which `units/` and `monitor/` now import from there. These three are the
debts that landing deliberately left behind._

- [x] **Session 46 — three snags.** *(2026-08-14.)* `SNAG-AGENT-006`
      (the raise-side pile-up), `SNAG-TRAY-006` (the untested 8400 seam)
      and `SNAG-ESTATE-002` (recorded in estate-manager, fixed nowhere,
      per its ADR-0002). The first entry's stated remedy was **wrong** and
      is flagged as superseded in `snag_list.md`: removing the service and
      threshold families from `RESOLVABLE_TITLE_PATTERNS` would have undone
      `SNAG-AGENT-004`. The patterns stayed and the exclusion set changed
      from what a run raised to what it **judged** — `sysadmin/estate/agent.py`'s
      pattern, reused rather than rediscovered. Verified live and rolled
      back: 10 sustained runs of one fault → 1 row, was 10. Filed on the
      way: `SNAG-AGENT-007`
- [x] **The judging session.** *(2026-08-13, Session 45.)* Landed as a
      new agent, `estate_judge` — `sysadmin/estate/` with a client, a
      pure `judgements` module and the lifecycle. It judges **four**
      surfaces, not the two this entry named: the scan's invariants and
      attention as planned, plus `GET :8400/api/audit/invariants` (which
      estate ADR-0009 requires sysadmin to judge — "the estate never
      grades its own audit") and `GET :8400/api/queue/invariants` (ADR-0007,
      already live and named in `services.yaml`'s own comment as ours to
      judge). Hourly, since the producers change twice a day and
      `/attention` re-walks ~26 manifests from disk per request.
      Migration 012 widens `chk_alert_agent`
  - **Nudge severity is taken verbatim** from the producer, which
    computes it on the ladder that moved with the domain; re-deriving it
    here would be two implementations in two repositories. Health
    breaches carry no published severity — that machinery was deleted
    rather than ported — so they are `warning`, one rung, never `critical`
  - **Reachability is deliberately not judged**: `estate-manager-api` is
    already an `http` entry in `services.yaml` and both estate timers are
    `kind: timer` beside it. A second owner of one lifecycle closes a row
    while the first still holds it true
  - **The cumulative queue totals are reported and never judged**
    (`dropped_total` is already 1), because a rule on a lifetime
    `count(*)` raises a row no future state can clear
  - Follow-ups filed: `SNAG-ESTATE-002` (the producer's nudge title never
    reaches the wire) and `SNAG-ESTATE-003` (no escalation for these
    families)
- [x] **Watch and judge the estate's audit agent** *(both parts done 2026-08-13, Session 45)* (delegated requirement
      from estate-manager Session 5, 2026-08-13 — its
      [ADR-0009](../../../estate-manager/docs/adr/0009-audit-agent-shape.md) §8).
      Two parts, and the first is overdue by the estate's own contract:
      1. **Add `estate-manager-audit.timer` to `services.yaml`** (user
         unit, alongside the scan and review timers already there). The
         monitorable-project contract says a new unit is wired the same
         day it is created — but estate ADR-0002's bounded exception
         closed on 2026-08-13, so that repository may no longer edit this
         one's runtime-read config, and it recorded the requirement here
         instead of making the edit. **Until this lands the audit timer
         runs unmonitored**: a silent failure is visible only in the
         retained `estate/audit/status` timestamp.
      2. **Judge `GET :8400/api/audit/invariants`** beside the scan's and
         the queue's — audit age, `checks_errored`, and `publish_error`
         (non-null means the audit's findings stopped reaching the bus,
         which is invisible *from* the bus by construction: nothing
         arrives to say nothing is arriving). Findings themselves are at
         `/api/audit/findings`, each carrying how long it has stood. The
         estate publishes and grades nothing; this repository judges —
         the same swap as the scan above
  - **Part 1 landed**: `estate-manager-audit-timer` is in `services.yaml`
    beside the scan and review timers, `kind: timer`, user scope.
  - **Part 2 landed** in `sysadmin/estate/judgements.py` as
    `judge_audit_invariants` — audit age (26 h: one daily interval plus
    the briefing's existing two-hour margin), `checks_errored` (which
    **names** the erroring checks from the `checks{}` map, because a
    check that errored produced no finding, so a clean-looking result for
    that dimension means nothing *looked*), `publish_error` and `error`,
    each its own alert family.
  - **`findings_total` is deliberately not judged**, and that is why this
    entry's wording is right to name only the three: the estate files
    findings about *other* repositories, and 8 of today's 10 are the
    collation family `monitor/collation.py` already holds eight open rows
    for. A rule on the total would announce this service's own alerts a
    second time through a different producer.
  - **The two parts catch different faults and both are needed**: the
    `services.yaml` entry catches a timer that stops firing, and
    `estate_judge` catches an audit that runs and goes wrong. Neither
    sees the other's.
- [x] **Drop the frozen tables** — `sysadmin.project_snapshots`,
      `sysadmin.project_reviews` and `log_summaries`, in migration
      **014** (Session 74, 2026-08-24). With them went their
      `retention_config` rows, their `TABLE_TIMESTAMP_MAP` and
      `KEEP_LATEST_PER` entries, the `FROZEN_TABLES` exclusion in
      `sysadmin/metadata.py` (now empty, and kept — see the constant)
      and the `LogSummary` model. Table count **14 → 11**, verified by
      `sysadmin-check-claims` rather than asserted.
  - **This entry was marked blocked, and the number it was blocked on
    was wrong by four orders of magnitude.** It said the 26 rows the
    estate's copy lacks — the final organiser sweep at
    `2026-08-13 07:35:03` — cost "a day of history for 26 projects".
    Re-measured 2026-08-24 by comparing `(project_name, scanned_at)`
    across both databases: the estate's own **first scan lands at
    07:35:46**, forty-three seconds later, and **all 26 projects appear
    in it**. The gap is 43 seconds, not a day, and nothing was ever
    missing from the estate's series.
  - **The history it was protecting was being deleted nightly by the
    row this migration removed.** The entry counted **3,739** rows here
    on 2026-08-16 and there were **3,447** on 2026-08-24 — the
    `retention_config` row thinning a frozen table on a 90-day window,
    so waiting cost history rather than preserving it. The estate now
    holds **4,155** snapshots reaching back to **2026-05-10** against
    this schema's **2026-05-20**: a superset in both directions.
  - **`log_summaries` was one row describing 29 seconds**, its
    `entry_count` and `error_count` both **100** and both the retired
    query's own `LIMIT`. Migration 013 recorded why its shape could not
    be carried into `log_reviews`, and left the note this migration
    acts on: *a table is destroyed once.*
  - **The estate's database was read once, by hand, and never from
    code.** The comparison above is the first estate rule's business
    ("no application reads or writes another application's database"),
    so it was done from a shell by a human deciding whether to destroy
    data and recorded in the migration's docstring rather than left to
    be re-derived. No copy was requested from estate-manager because
    the measurement showed there was nothing to copy
- [ ] **Trim the `agents.project_organiser` config block.** The last
      limb of the entry above, deliberately not taken with it: it is
      parsed by pydantic here and read by nothing since ADR-0005, which
      records it as knowingly untidy. It is `SNAG-CFG-001`'s shape and
      is a config change rather than a schema one — config classes fan
      out into defaults tests, so it is its own sitting's edit and does
      not belong in a migration
- [x] **Pin the tray's parse of the estate's responses.** The tray reads
      `/api/projects/overview` and `/{name}` from **8400** now but parses
      them with *this* repository's contract classes
      (`ProjectOverviewResponse` and friends), which the estate also
      defines in `estate_service/projects/contracts.py`. That is one
      shape maintained in two repositories — the copy-drift pattern the
      estate exists to remove, surviving here because the consumer's
      parse and the producer's contract are genuinely different jobs.
      **Decided 2026-08-14 (SNAG-TRAY-006): a contract test, and the
      shapes stay in two repositories.** `estate-lib` was rejected
      because the two are not duplicates — this side is a tolerant
      consumer parse (`extra="ignore"`, every field defaulted, a
      `ValidationError` meaning "connection lost" to the tray *by
      design*) and the estate's is a producer guarantee enforced as
      `response_model=`. One class makes the tray's defensiveness the
      producer's problem and the producer's strictness a way for the
      tray to crash on an unknown field — the exact defect
      `extra="ignore"` exists to prevent. It would also have *appeared*
      to close this while proving nothing about whether the producer is
      reachable or still populating the routes.
      `tests/test_estate_project_contracts.py` is the consumer-driven
      test instead: a recorded 8400 payload the suite always parses,
      plus a reachability-gated live pair sharing one set of assertions

- [x] **Monitor SearXNG — the estate's first self-hosted third-party
      service** (delegated requirement from estate-manager, recorded
      2026-08-14 at the owner's request; the deploy decision was the
      owner's on 2026-08-12, in venture-assistant's phase 7 sign-off).
      **The deploy is not this repository's** — SearXNG is shared
      infrastructure and gets an owner that is not an application, so
      estate-manager hosts it and this repository watches it, the same
      split as everywhere else. **Recorded before the deploy rather than
      after, deliberately**: the estate's own backlog item raised the
      sequencing question and the owner answered it this way, because
      two of the three parts below are decisions that *block* the deploy
      rather than follow it, and because the estate-manager-audit.timer
      precedent (`fa51aac`) shipped a unit that ran unmonitored until
      this repository's next session. **Trigger:** estate-manager
      deploys SearXNG and claims its port in the registry.
      1. **Add it to `services.yaml`.** `kind: http`, an explicit `url`
         with SearXNG's own health path, and `systemd.scope: user` (the
         default) once the unit is named per the monitorable-project
         contract.
      2. **The `/api/health` worry in the estate's item does not apply
         to this side — checked, not assumed.** That item warns against
         "silently grandfathering a fifth exception" because the
         contract's `GET /api/health` shape was written for our own
         apps. But `services.yaml` has never required that shape: it
         polls whatever `url` says, and already carries
         `http://localhost:8081/health`,
         `http://localhost:8200/api/v1/health` and
         `https://1.1.1.1/cdn-cgi/trace`. **No shim is needed here.**
         What remains is a contract question for estate-manager — whether
         a third-party service is held to `/api/health` at all — not a
         monitoring one. Worth telling the estate so its item can shrink.
      3. **It needs no `project:` id, and that is the precedent to
         follow.** Five entries already omit it — `postgresql`,
         `mosquitto`, `NetworkManager`, `internet`,
         `pgbackrest-backup-timer` — all infrastructure rather than
         projects, and an id that names nothing **fails at load**, so
         inventing one for a service with no repository and no
         `.project.yaml` would break the file. **Project-less is not
         ownerless**: `mosquitto` has been estate-owned since that
         repository's Session 2 and carries no `project:` here, which is
         the exact shape SearXNG should take.
      4. **Judge it like any other service** once it is declared — no
         new invariant endpoint, nothing estate-specific. SearXNG is
         third-party software the estate hosts, not another estate
         surface that publishes its own numbers.
      **Note for whoever writes this:** the estate's backlog item and the
      global `~/.claude/CLAUDE.md` both still say to wire new services
      into `projects.yaml` with `user: true`. Both are gone — this
      file's own header records that `services.yaml` replaced
      `projects.yaml`'s runtime half and that `systemd.scope` replaced
      the `user: true` opt-in. The estate-side copies are being
      corrected; flagged here so the stale wording is not followed.
      **Pre-staged 2026-08-14 at the owner's request, and it stays
      unchecked.** The trigger has not fired — no searxng unit on either
      bus, nothing listening, and no row in the estate's port registry —
      so the entry cannot be written: `url` and `port` are the two fields
      the deploy decides, and *"claim ports in the registry, don't
      guess"* is the rule `services.yaml` exists to enforce. What was
      done instead:
      - **A commented block in `services.yaml`**, in the host section
        beside `mosquitto`, carrying every decided field with the port
        and health path left as `<PORT>`. **Commented rather than live**:
        the loader has no "declared but absent" state, so an entry naming
        an uninstalled unit checks as down every 300 seconds for as long
        as the deploy takes — this repository's own alert-storm shape.
      - **`tests/test_searxng_wiring.py`**, which is the part that makes
        pre-staging worth more than a note. The failure mode this whole
        item was written against is *"the unit ships and nobody
        notices"*, and a comment does not fix that — nobody reads it
        until they already know. The guard skips while no searxng unit
        exists and fails from the moment one does, so the red appears on
        the day the gap opens. Its gate is the **unit file**, not a port
        probe: a probe flips off exactly when SearXNG is down, which is
        the state monitoring exists for. It matches the substring
        `searx`, because a container deploy names its unit
        `podman-searxng.service` and a gate that knows one spelling fails
        open on the others. Nine ungated tests drive the gate against a
        fake estate under `tmp_path`, because a gate that has never
        fired and a gate that cannot fire look identical from outside.
      - **A finding that shrinks part 1 and files a snag.** The Session
        26 unit sweep will catch a hand-written searxng unit unaided and
        classify it `host` — hand-written, mapping to no project — and
        its snippet already omits `project:`, so **part 3 is enforced
        mechanically and needs nobody to remember it.** But that snippet
        says `kind: systemd`, because the scan cannot know a port
        (`sysadmin/units/recommendations.py`), and a unit check passes a
        SearXNG that is running while every search errors. So the sweep
        would *appear* to close this item while leaving the one check
        worth having unwritten. Filed as `SNAG-UNITS-001` for the
        general case; pinned for this one service by the test above.
      - **Stale file names in the sweep's own output**, fixed in passing:
        an `unmonitored` finding's `reason` read *"no projects.yaml or
        config.yaml entry monitors it"* — two files that no longer
        exist, in a string the operator reads. Four category docstrings
        in `sysadmin/units/scan.py` and two in `agent.py` said the same.
      **What is left when the deploy lands** is three lines: fill in the
      port, confirm the health path against the deployed version
      (upstream serves `/healthz`; venture's seam calls
      `/search?q=…&format=json` — neither taken on trust here),
      uncomment, restart. The guard turns red until that happens.

      ---

      **THE TRIGGER HAS FIRED — SearXNG went live 2026-08-14, and
      `tests/test_searxng_wiring.py` is RED as of now.** Recorded here by
      an estate-manager session under
      [estate ADR-0002](../../../estate-manager/docs/adr/0002-delegation-not-command.md)
      (documents into other repositories, never their code, units or
      runtime-read config), the same shape as `c890a52`. The estate's
      record is
      [ADR-0010](../../../estate-manager/docs/adr/0010-searxng-deploy-shape.md).
      **Every value this row was waiting on is now decided**, and one of
      them is not what the commented block currently says:
  - `url: http://localhost:8600/api/health`
  - `port: 8600`
  - `systemd: { unit: estate-manager-searxng-shim.service }` —
        **not `searxng.service`**, which is what the pre-staged block
        names. This is the one field that changed shape rather than
        just gaining a value
  - `kind: http`, no `project:`, `scope` omitted — all three exactly as
        this row already determined
  - **The health path is `/api/health` after all, and that is a
        ruling, not a coincidence.** This row and `f5b37e6` in the estate
        both recorded the routed question — *is a third-party service
        held to `/api/health` at all?* — as answered **no**. The owner
        was then put the question directly during the deploy, with
        exemption as the *recommended* option, and **chose the
        opposite**: the contract binds it, and the estate owns a thin
        shim that makes it true. So there are two units, and the split
        is the point:
  - **`estate-manager-searxng-shim.service`, port 8600** — an
        estate-owned FastAPI process. It serves `/api/health` and proxies
        everything else. **This is the one to monitor.**
  - **`estate-manager-searxng.service`, port 8601** — the upstream
        SearXNG container, bound to loopback, reachable only through the
        shim. No health surface of its own worth watching; it has a
        registry row because sidecars count, not because it needs a
        check
  - **The health check is not a liveness restatement, which matters for
        how its states should be judged.** It reports **503** when
        SearXNG is not answering at all, and **424 Failed Dependency**
        when SearXNG is up but *searching* is broken — engines
        captcha'd, all upstreams failing. Under this file's own ladder
        that lands as `critical` and `degraded` respectively, which is
        the intended reading: a dead container is this box's problem, a
        captcha'd engine is not, and venture degrades past the second
        cleanly. `SNAG-UNITS-001` is the general form of exactly this
        distinction — a unit check passes a SearXNG whose every search
        errors
  - **Expect `degraded` to appear legitimately.** The instance runs two
        engines (`duckduckgo`, `seznam`) chosen by measurement, not
        reputation — `brave` returns 429 on every request from this box,
        `mojeek` answers nothing, and DuckDuckGo issued a CAPTCHA during
        the deploy session itself. Two engines exist so that one
        captcha is degradation rather than an outage. **A 424 here is
        usually upstream having a bad day, not a fault on this box** —
        worth an alert only if it stands
  - **Verified from the estate side rather than reported**: the guard
        was run there and fails naming both units, the audit re-run
        after the deploy raises no new finding, and both ports answer.
        What is left here is genuinely the four lines above plus
        `sudo systemctl restart sysadmin.service`

      ---

      **WIRED 2026-08-14.** `services.yaml` carries the entry, the guard
      is green, and the check was driven against the live shim before
      the file was trusted: `ok` in 23 ms, body `status: healthy`, probe
      153 s old with 20 results and no unresponsive engines. Every value
      the estate handed over was confirmed here rather than copied —
      port, unit name, health path and the status ladder.

      **Two things this session found that the handover did not say.**

      - **`/healthz` on 8600 is a trap, and it is the path the
        pre-staged block named.** The shim proxies unknown paths
        upstream, so `http://localhost:8600/healthz` reaches SearXNG's
        own liveness ping and returns 200 whenever the container runs —
        *including when every search fails*, which is the one case this
        entry exists to catch. It answers 200 right now, so a wiring
        that took the pre-staged value would have looked correct on the
        day and been blind on the day it mattered. `/api/health` is the
        only path that knows whether searching works. The guard's
        failure message now names the trap.
      - **The 424/503 ladder was verified, not assumed.** Both
        repositories describe it in prose; `_check_http` was driven
        against a real socket returning each code — 200 → `ok`,
        424 → `degraded`, 503 → `critical`. And `_handle_status`
        requires **three consecutive** degraded checks before raising,
        so the estate's "worth an alert only if it stands" is already
        the behaviour: a captcha'd engine is silent for 15 minutes, a
        standing search outage is not.

      **A second entry was added that the plan did not call for.**
      `searxng-upstream` declares `estate-manager-searxng.service`
      (the 8601 container) with `monitor: false` and a reason. It is
      deliberately *not* checked — a dead container already shows up as
      the shim's 503, and two entries would give one fault two alert
      rows — but leaving it out of the file entirely put it in the unit
      sweep's `host` findings **permanently**, where it could never be
      actioned and where "watched through the shim on purpose" is
      indistinguishable from "nobody wired it up". That is the shape
      `venture-chat-large` already carries. Measured: host findings went
      9 → 8, and no searx unit is left unaccounted for.

      **Item 3's rationale was narrowed rather than inherited.** This row
      said no `project:` because SearXNG is "third-party software with no
      repository". What shipped puts an estate-manager-owned shim in
      front of it, and *that* module has a `.project.yaml` — so the field
      would now resolve and the loader would not object. The owner was
      put the question and kept the omission on the narrower ground: what
      this entry judges is whether **searching works**, and a 424 means
      upstream engines are failing off this box, which is not the
      estate-manager repository's fault to carry. The guard's docstring
      records the narrowing so the next reader does not re-derive it.

      **The guard changed shape rather than being deleted.** Its gate now
      separates *environments* rather than dates — CI has no searxng
      unit, so the three assertions skip there and run here against the
      live box, where before the deploy they skipped everywhere and the
      file was unfalsifiable. The self-retiring
      `test_the_pre_staged_block_is_still_commented_out` was deleted per
      its own failure message. The `kind: http` assertion is now
      **stronger**, not merely narrowed to skip the unmonitored entry:
      it asserts *exactly one* searx entry is checked before asserting
      that one is HTTP, because a filter alone would let someone silence
      the family by muting the shim and still pass. And the two real unit
      names are pinned into the gate's parametrised cases — **neither is
      any of the three spellings it guessed**, so the substring match is
      the only reason it fired at all, and it must not be "tidied" into
      an exact one.

## Active Sessions

## Session 77 — SNAG-DOCS-002, the registry describes only what it serves (2026-08-25) ✅

`sysadmin/core/contracts.py` carried eight project response models
describing routes that left for estate-manager on 2026-08-13 (ADR-0005) —
a pydantic model that validates and no caller consumes, which is
`SNAG-CFG-001`'s shape in the file `CLAUDE.md` calls the contract
registry. The entry had been measured twice and was wrong three times,
always with the same instrument.

- [x] **Measure it a third way, and stop using a grep.** A grep answers
      "does anything mention this". The question is whether anything
      *reaches* it, and the two differ in both directions at once: **17**
      models have no mention anywhere and are field types of a served
      payload, while `RecommendationInfo` looked alive off one line of
      prose in `units/recommendations.py`. Session 76 put
      `ProjectHealthInfo` in the dead set on the first kind of evidence;
      it is a field of `ManagedProjectInfo`, the `response_model` of the
      one `/api/projects` route this service still serves. **15**
      classes are unreachable — the 8 responses plus exactly their 7
      exclusive members — and the re-export count is **five**
- [x] **Take the decision the entry deliberately left open**, which is
      the owner's and was put to them: delete from the registry,
      deprecate on the tray. Ten classes go outright; the five
      `sysadmin_tray/models.py` re-exports move to
      `sysadmin_tray/_deprecated_contracts.py`, because `sysadmin_tray`
      ships in the wheel and an import list is a published surface
- [x] **Resolve them lazily, warning on access and never at import.** A
      PEP 562 module `__getattr__` runs only after normal lookup fails,
      so the live re-exports pay nothing; warning at import would fire on
      every tray start whether or not anything touched a deprecated name,
      which teaches the reader to filter the category rather than act on
      it — `judge_audit_findings` rule 3, one package over
- [x] **Make membership a property a test computes**, not a claim a
      document makes. `tests/test_contract_reachability.py` walks field
      annotations and base classes from every root, where a root is a
      name **used** and never a name **imported** — the distinction
      Session 58 stated in prose and then measured with a tool that
      cannot draw it. Skipping `ast.Import`/`ast.ImportFrom` draws it;
      docstrings are `ast.Constant` and fall out for free;
      `response_model=` needs no special case, being an `ast.Name` in a
      keyword already
- [x] **Falsify it at the real pre-fix file, not only at a synthetic
      one.** A fresh unreachable model trips the guard and is reported
      exactly. Driven at the pre-fix registry it reports **12** of the
      15: `tests` is a consumer package on purpose, so the shim's own
      annotations and `models.PortfolioActionsResponse` in the new test
      make three of them roots. Stated in the file, and covered by
      `test_none_of_them_are_defined_in_contracts` — two tests composing
      rather than one doing both. The synthetic falsification passes
      cleanly, which is how that would have shipped unseen
- [x] **Verified on the box.** 83 classes → 68, 1,846 lines → 1,460.
      Suite **2238** green, `ruff` clean, `mypy sysadmin` clean;
      `create_app()` serves 52 routes with `/api/projects/managed` still
      the only one under `/api/projects`; daemon restarted 07:58:56,
      `/health` 200, 11 jobs scheduled
- [x] **Two costs filed rather than implied.** `SNAG-DOCS-003`: the five
      deprecated names are removable only once someone confirms nothing
      outside this repository imports them, which is an operational fact
      rather than a code question. `SNAG-ESTATE-013`: found by *running*
      `check-ops-claims.sh` at the top of the sitting — `check:expires`
      takes a naive instant, the block copied `03:32` off a producer that
      publishes `+00:00`, and the row cleared at 05:32 local. The check
      correctly said `unknown`; what it cannot notice is a marker written
      in the wrong zone. `SNAG-LOG-009` one document over

## Session 76 — SNAG-ESTATE-011, every claim names the check that closes it (2026-08-24) ✅

`SNAG-ESTATE-008` shipped the query half of its own proposal and left the
convention — *"every ops action names the check that closes it"* — unbuilt,
because that half had no enforcement point. The entry that recorded the
gap contained its own contradiction: it named `<!-- check: … -->` as the
cheap next move and refused a marker in the next clause. Both are right
about **different markers**, and the distinction is the fix. Suite
**2194 → 2229**, ruff and mypy clean, verified live at exit 0 on the real
document and exit 1 on a copy broken four ways.

- [x] **A marker names a check, never a value.** `<!-- routes=46 -->` can
      agree with the box while the prose beside it disagrees and nothing
      notices — `SNAG-DB-003` in a document, which is `ops_claims.py` rule
      1. `<!--check:routes-->` states no fact, so the figure in the prose
      stays the only statement of itself and there is nothing to drift
      from
- [x] **The marker is additive and cannot subtract.** Every
      pattern-bearing claim runs whether or not a line names it, so
      deleting a marker is a way to be *told*, never a way to retire a
      check — a gating marker would make "edit the document" a switch,
      which is rule 2's silent retirement inside the fix for it
- [x] **`check_markers` is the enforcement point**: a figure this module
      can test that no line claims, and a marker naming a check nobody
      implements. First run against the real block reported **five
      unclaimed figures**. A typo fires from **both** sides —
      `<!--check:helth-->` gave the unknown name *and* the now-unclaimed
      `health` beside it, which was not designed
- [x] **`expires` — a prediction is timed, not measured.** The founding
      instance ("the row clears at 03:32", written at 00:30) was not wrong
      when written and not measurable when written. It is the one family
      whose members the **document** declares; after its moment the claim
      is `unknown`, never `mismatch`, because the prediction may have come
      true and "nobody went back" is what rule 2 reserves `unknown` for
- [x] **The instant is pinned, being the one fact stated twice.** The
      marker carries a date the prose has no room for, so the wall clock
      it renders must appear in the block. **The pin was broken and only a
      live run said so**: it searched the flattened region, which contains
      the marker, so it matched the marker's own copy and passed whatever
      the sentence said. Three fixture tests of that pin were green either
      side of the fix
- [x] **`check_open_titles` and `check_health`.** The first is the finer
      half of the alert count, which holds still through a swap; one
      direction only, the other being `check_alerts`'s *fall* note. The
      second is a different fact from the deploy check's — `active` says
      the process is up, `/health` says it is serving, and `SNAG-DB-005`
      is the 23 hours where those parted company
- [x] **8400 deliberately unchecked**, with the reason in the block's own
      prose: `estate/judgements.py` rule 3 declines to judge its
      reachability here, and a claims-checker that alerted on it would
      re-import the second owner that rule prevents
- [x] **19 new tests, five falsified** — the unclaimed half removed,
      `mismatch` for a passed prediction, a hand-written `CHECK_KEYS` (which
      fired **twice**, having forgotten `health`), the pin without
      `prose_without_markers`, and the marker read unflattened. All five
      fired
- [x] **Filed on the way**: `SNAG-ESTATE-012` — a sentence with no pattern
      *and* no marker is still invisible, because deciding that an English
      sentence is a claim is a human's job. Today's block carries three

## Session 75 — SNAG-LOG-011, a deleted route stops answering 200 (2026-08-24) ✅

Session 69 removed `GET /api/logs/summary` and `/summary/history` with
the producer behind them, and Session 74 dropped the table. The path went
on answering `200` with `{"source":"summary","entries":[],"count":0}`,
because `GET /api/logs/{source}` matched `summary` as though it were a
log source. Suite **2195 → 2206**, routes **46 → 48**, ruff and mypy
clean, verified live after a restart.

- [x] **Two `410 Gone` tombstones above the catch-all.** `410` rather
      than `404` because "was a route and was removed" and "never was a
      route" are different states a caller cannot otherwise tell apart —
      `ports_checked`'s rule one status code up. `/summary/history`
      already 404'd (the catch-all takes one segment) and is named
      anyway, so the pair answers with one voice
- [x] **`/{source}` validates its argument, which is what removes the
      class.** The tombstones patch two paths; any single-segment path
      added and later removed acquired the same behaviour, and
      `/{source}` has been last in the router since it was written —
      which is what makes it work at all, so it cannot simply move. An
      unknown segment is now a 404
- [x] **The key is not one field, and this is the part reading the route
      could not have given.** `log_entries.source` holds the **unit** for
      a journal source and the **name** for a file source, because
      `_read_journal_source` and `_read_log_file` stamp different things.
      `services.stored_source_name` mirrors the ingestion loop's dispatch
      rather than restating it from the data — every declared source here
      is `type: journalctl`, so a rule derived from the live table would
      have omitted the file branch, stayed green in every test, and
      404'd the first file source's own rows
- [x] **Both configuration files, measured.** `kernel` is declared in
      config.yaml because it belongs to no service, and it is **451,319
      of the 451,569 rows** in `log_entries`. A services.yaml-only set
      passes every fixture and rejects 99.9 % of the data. So
      `LogAggregatorAgent._sources` was lifted to
      `services.composed_log_sources` and shared — the set the route
      admits must *be* the set the agent ingests, not merely agree with
      it. `_sources` stays as the seam the tests patch
- [x] **Passing a source *name* was the same defect one level down**, and
      the entry did not name it: `/api/logs/alfred` returned an empty
      list, indistinguishable from a quiet service. It now 404s with the
      fifteen declared units in the detail
- [x] **Eleven tests, where there were none.** Nothing asserted
      `/{source}` before this sitting, which is how a route describing a
      dropped table stayed green through the sitting that dropped it.
      Each was falsified against the behaviour it replaces; the one worth
      naming is **ordering** — declaring the tombstone *below* the
      catch-all produces the same `200` as deleting it, so only a
      behavioural test separates a future alphabetical sort from a
      working fix. The live half is skipped when postgres is unreachable,
      `test_schema_drift.py`'s shape
- [x] **Cost stated rather than implied.** A source removed from
      services.yaml keeps 30 days of rows this route no longer serves.
      Empty population today — all 9 distinct values in
      `log_entries.source` are declared — and
      `GET /api/logs/recent?source=` still reaches them

## Session 73 — SNAG-ESTATE-008, the block that opens a sitting gets a reader (2026-08-24) ✅

Six consecutive sittings were spent on claims that had stopped being
true: an ops action done three days earlier by another repository, a
restart method that needed no `sudo`, and — the day before this one —
this file asserting a retention boundary three hours before it happened.
The previous ranking demoted the fix for having "no obvious enforcement
point, since these claims live in prose". `claude-preflight.sh` already
runs at the start of every sitting and already prints those claims; it
just prints them *from the prose*.

- [x] **`sysadmin/ops_claims.py`, `sysadmin-check-claims` and
      `scripts/check-ops-claims.sh`**, wired into preflight (where a
      stale claim is *caught*) and postflight (where one is *made* —
      the numbers are written at the close, so a wrong one is caught
      before it is committed rather than one sitting later)
- [x] **Seven checks in two kinds, and conflating them would have you
      edit the wrong artefact.** Five *claims* parsed out of the block
      itself — routes, tables, the documented Alembic head, unresolved
      alerts, the daemon's start time — where a mismatch means the
      **document** is stale; and two *state* checks — the live schema
      against the packaged head, and whether the daemon is serving the
      code on disk — where a mismatch means the **box** is
- [x] **The entry understated its own defect by a whole surface.** It
      says preflight prints the priorities "without checking either
      against `sysadmin.alerts`"; measured, the banner never printed the
      sub-session block at all, because the blockquote sits *above* the
      `## Quick Status` heading its extract is anchored on. The one
      surface the global rules require to be read first was the one it
      omitted. It prints now, bounded and stopped at the ranked
      recommendation
- [x] **The obvious deploy check is wrong on this box, and was wrong
      today.** Daemon start 09:58:28 against the newest commit touching
      `sysadmin/` at 10:05:22 reports a restart owed on identical
      content — this repository restarts to verify and commits
      afterwards. The newest `.py` on disk, **09:57:46**, answers it
      correctly. Measured both ways before either was written down
- [x] **`systemctl show` answers for a unit that does not exist**, exits
      `0`, and prints `ActiveState=inactive` — this snag's own shape
      found inside its own fix. `LoadState` is the gate, pinned by a
      test that drives the real binary rather than a stub
- [x] **A *fall* in the alert count is the founding case.** Equality or
      a rise is the rule anyone would write; this entry exists because
      eight collation rows resolved themselves and four documents went
      on asking for the `REINDEX` for three days. Both directions
      reported, worded differently, open titles named rather than
      counted
- [x] **35 tests, six falsified against the behaviour they replace** —
      first-match parsing, `len(app.routes)` (which is 50 against the
      documented 46, FastAPI's four docs routes), no `LoadState` gate,
      `max()` over the exit map, an unbounded parse region, and the
      missing `flatten()`. All six fired. Suite 2159 → 2194
- [x] **The check refuted its author within a minute of being wired up.**
      The first rewrite of the block under it wrapped `holds **2**` and
      `unresolved` across two lines with a `>` between them, and the
      claim came back `unknown` — correct by the rule that not-knowing
      is never agreement, and useless, because a paragraph reflow must
      not be able to retire a claim. `flatten()` matches against prose
      rather than markdown
- [x] **Driven against a document made false on purpose.** All five
      claims in today's real block hold; a copy with the route count set
      to 44, the alerts to 9 and the restart backdated produces three
      `no` lines and reproduces the founding case from the outside
- [x] **`SNAG-ESTATE-011` filed for what is left** — the block's other
      claims are prose no pattern can reach, and the *convention* the
      entry proposed (every ops action names the check that closes it)
      has no enforcement point yet

## Session 72 — SNAG-LOG-010, a row's identity is the fault (2026-08-24) ✅

`GET /api/logs/actions` served two rows reading exactly
`kernel: 39885 occurrences, unchanged`, correct and impossible to tell
apart. `SNAG-AGENT-005` moved the signature *into* `alert_title` for that
reason in 2026-08-12; the advice endpoint never got the same treatment.

- [x] **Every title builder names the signature, not just the one the
      entry filed against.** `quoted_signature()` on all four; the entry
      scoped this to `noise` and ranked it last on a population of zero,
      and driving the real `recommend()` against the live table put
      **14 of 21 rows in five collision groups** at the 2026-08-12 anchor
      and **7 of 9** at the live one — where the `noise` population is
      genuinely zero and every colliding row is `severity: risk`
- [x] **`capped_signature()` bounds at `SIGNATURE_DETAIL_CHARS` with
      `truncate_at_word`.** It was a bare slice, so **12 member
      signatures per request** were cut mid-word with no marker — one
      ending `"message": "alert_raised", "service"`. That is the
      unmarked cut `log_review._quoted_signature`'s docstring calls
      `SNAG-BRIEF-002`, and calls *worse* on a signature, in the module
      that lent it the constant
- [x] **`log_review._quoted_signature` keeps only its `figure_free`
      gate** and borrows cap, marker and quoting, so a review line and a
      title name one signature one way. `SAMPLE_DETAIL_CHARS` names the
      other bare slice, which was written twice
- [x] **The noise title no longer claims a direction.** `unchanged` was
      asserted for all four change kinds `_is_noise_candidate` admits,
      and both live rows classify **`FALLING` — 39,885 this window
      against 77,496 last**, contradicted by the row's own `detail`. The
      count stays: volume is the reason to act
- [x] **Nine tests, all falsified against the behaviour they replace**,
      and one strengthened before it could be — it compared the two
      modules' quoting on a *short* signature, where a slice and a
      marked cut agree, so it passed against the broken code. The whole
      module's titles had been pinned by one `startswith`
- [x] **Verified on the route.** 7 collisions among 9 rows at 09:57, **0
      among 9** after the restart at 09:58; the specimen pair driven
      through the real `build_report` → `recommend()` over the storm
      window, 18 days before those rows age out
- [x] **`SNAG-LOG-013` filed for what the cap leaves.** 9 of 55
      signatures share their capped prefix, and one live incident row
      already lists **7 members that are identical after capping** — the
      roll-up naming nothing, one level below the titles

## Session 71 — SNAG-LOG-009, the window journalctl actually opens (2026-08-24) ✅

Nine of nine rows `GET /api/logs/actions` served carried
`--since '2026-08-22 17:10'` for an event stored at
`2026-08-22 18:10:16.115268+01`. journalctl reads a bare datetime as
**local**, so the window opened an hour early here — and past the
incident west of Greenwich, where the row loses its whole purpose.

- [x] **`journal_command` takes a `datetime`, not a rendered string.**
      The rendering belongs to `journal.since_timestamp`, which has
      emitted `@<epoch>` and stated this reason since the module was
      written. Three callers were each implementing a fact a fourth
      function already owned — the `-k` bullet in `journal_command`'s own
      docstring, met from a third direction
- [x] **The entry's remedy was the weaker of two and is recorded as
      such.** `astimezone()` renders a local wall clock: correct on this
      box, verifiable, green, and still ambiguous — it holds only while
      the writer and the reader share a zone, and an autumn-fold local
      time names two instants
- [x] **`since_timestamp` refuses a naive datetime.** `timestamp()` reads
      one as local, which is the reading being removed, so accepting it
      would rebuild the defect inside its own fix with the right-looking
      type. Empty population by construction
- [x] **Prose labelled `UTC`** in `detail` and the incident line, so the
      fix leaves no row disagreeing with its own command. Not converted
      to local: the command had a timezone taken *out* of it
- [x] **Tests model the consumer, not the rendering.**
      `TestTheWindowJournalctlOpens` resolves the emitted `--since` the
      way journalctl does in London, New York and UTC. The old
      assertions pinned the string, which is how a wrong command stayed
      green across three sittings. All four falsified; the
      truncation-direction one needed `int` → `math.ceil`
- [x] **Verified by running both forms at two timezones.** Epoch form
      opens on the event; the old form lost one line here and **8,749**
      under `TZ=America/New_York`, where it opens four hours past the
      incident

## Session 70 — SNAG-DB-005, the migration that nothing applies (2026-08-24) ✅

Session 69 restarted the daemon to serve a new route and found it had
already been dead 23 hours: migration 013 was written, committed and never
applied, `schema_guard` refused to serve (correctly), and
`StartLimitBurst=5` made the restart loop terminal. Nothing on this box
applies migrations and nothing checked either.

- [x] **`sysadmin-check-schema`** — a console script over
      `schema_guard.packaged_head()` and a new `live_revision_sync()`,
      wrapped by `scripts/check-migrations.sh`
- [x] **Blocking in `claude-precommit.sh`, advisory in
      `claude-postflight.sh`** — the commit is the last scripted moment
      before the hand-typed `kill -TERM`; there is no deploy script
- [x] **The failure names its own remedy** —
      `unit_failure._schema_diagnosis()` into `details['schema']` and the
      alert message, and `notify-unit-failed.sh` into the toast
- [x] **`sudo systemctl status` corrected to `systemctl status`** in the
      toast, measured as `gaddi` (wheel): both it and `journalctl -u` exit 0
- [x] **45 tests** (2101 → 2146), each falsified against the behaviour it
      replaces; ruff and mypy clean

**What the sitting found that was not written down.**

- **The entry ranked its own candidates by cost and never asked what each
  buys.** `ExecStartPre=` was ranked cheapest-that-works and buys
  **nothing** — a check there fails identically to the lifespan guard, one
  process earlier: same refusal, same `failed`, same 23 hours. And
  postflight alone would **not have caught this outage**, because Session
  69's restart happened *mid-sitting*; a session-end check runs after the
  box is already down. Both errors are the same shape.
- **Prevention owns almost none of the 23 hours.** `sysadmin-failed.service`
  fired *correctly*, with a persistent critical toast, and said only
  `result=exit-code, exit=1, restarts=5`. The cause was one revision number
  and the remedy one command — both sitting in `schema_guard._REMEDY`,
  reaching the journal and nothing else. The entry named three candidates
  and none of them shortens this.
- **The one duplication accepted is the connection, never the rule.** Both
  new callers run outside a running application, so `get_engine()` would
  raise and a sync reader is unavoidable. The schema-qualified table name,
  the none/one/many interpretation and the mismatch wording moved into
  `_qualified`, `_interpret_version_rows` and `describe_mismatch`, and a
  live test drives **both** readers against the real `alembic_version`.
  Falsified by pointing the sync one at `public.alembic_version` — the
  stranger's copy `schema_guard`'s rule 2 exists to keep out — and it fires.
- **This is the one place the guard family fails _open_.** Exit 2 (the
  comparison could not be made) warns and never blocks: a commit refused
  because PostgreSQL happens to be down teaches the operator to reach for
  `--no-verify`, which disarms the check for the case it exists for. Three
  verdicts, three exit statuses, because a check that could not look must
  not report what a clean check reports.
- **The counterfactual was driven by moving the checkout, not the
  database.** A temporary migration file raises the packaged head and
  leaves `alembic_version` untouched, so a crash mid-test cannot leave the
  box in the state the snag describes. Stamping down would have.
- **`uv sync` prunes this repository's extras.** `dev` and `tray` are
  `[project.optional-dependencies]`, not dependency groups, so a bare
  `uv sync` removed pytest, ruff, mypy and PyQt6 — and `uv run pytest` then
  silently fell through to `/usr/bin/pytest`, which fails on `import
  estate`. `uv sync --all-extras` is the command.

## Session 68 — SNAG-LOG-001, the correlation rule (2026-08-18)

Session 67 named this session and named the specimen to measure against.
The specimen refuted the entry's proposed rule, as predicted — and then
refuted two things the entry stated as fact.

- [x] **Measure whether the declared graph suffices.** It does, and the
      framing was wrong: the risk was never declared-versus-effective
      (which would cost `scan.py`'s no-subprocess promise), it was
      *which directories*. **Parsing `/usr/lib/systemd/system` reads 629
      further unit files and yields zero further relations** among the
      fourteen declared log sources, because the unit that *depends* is
      always the hand-written one. The sweep's own two directories are
      enough
- [x] **`sysadmin/units/scan.py`** — `UnitRelation`, `RELATION_DIRECTIVES`,
      `UnitFile.relations`, `qualify_unit()`, `declared_relations()`.
      Symmetric map keyed on `(scope, unit)`; `Conflicts=` excluded as the
      one *negative* relation; self-edges refused
- [x] **`sysadmin/monitor/log_actions.py`** — `group_incidents()`,
      `INCIDENT_WINDOW_SECONDS`, `SIGNATURE_DETAIL_CHARS`,
      `IncidentMember`, `_incident_recommendation()`; `journal_command()`
      gains `others` so one command reads the whole incident
- [x] **`sysadmin/monitor/routers/logs.py`** — `_unit_relations()`, which
      resolves scope per declared log source *before* flattening.
      `deadlock-api-ingest.service` exists in both scopes here running two
      different binaries, so a name-only key would merge them
- [x] **`sysadmin/core/contracts.py`** — `LogIncidentMemberInfo`, and
      `members` on `LogRecommendationInfo`. Additive; `source`/`signature`
      stay the **anchor's**, so a consumer ignoring `members` still reads
      a correct row about the fault that happened first
- [x] **Tests** — `tests/test_unit_relations.py` (18, new) and 26 more in
      `tests/test_log_actions.py`. **2067 green**, ruff and mypy clean
- [x] **Ten guards falsified deliberately.** Ignoring the graph reproduces
      the entry's own proposal and breaks 8; single-linkage breaks the
      anchor test; dropping the first-sighting filter breaks 16; dropping
      the tie-break breaks 1; bypassing the noise filter breaks 2; and
      five on the graph builder (asymmetry, self-edges, scope, empty-reset,
      `Conflicts`) break one each
- [x] **Driven live, not only against fixtures** — the real trend report
      from the real database, the real unit files, and the **emitted
      `journalctl` command actually run**. 24 recommendations → 11

**What the specimen refuted, beyond the rule.**

- **The entry's mechanism was backwards.** It said mosquitto "took the
  `estate-broker-provision` oneshot with it". systemd started the oneshot
  **2 ms after** mosquitto had already failed (`12:32:51.284877` then
  `.286928`), because the declared relation is `Wants=`, which does not
  propagate failure; the provisioner failed on its own connect
  (`mosquitto_ctrl dynsec listClients: Error: Bad file descriptor.`)
- **The window is a boot.** Boot `0` begins **12:32:39**, twelve seconds
  before the crash. Nothing in three sittings had noticed, and it is
  exactly why a same-window rule is dangerous here
- **The false positive is real and 1.2 s away.** `alfred-backend.service`
  failed at `12:32:52.487` because PostgreSQL was still starting up
  (`asyncpg.exceptions.CannotConnectNowError`). It is a **user** unit and
  mosquitto a **system** one, so systemd could not order them even if
  someone declared it

**Left undone deliberately, and named.**

- **`SNAG-LOG-009`** — every emitted `journalctl --since` is an hour early
  here and would be five hours *late* west of Greenwich. One
  `astimezone()`, but every existing `TestJournalCommand` assertion pins
  the current rendering, so it changes what the tests call correct rather
  than what is underneath them. **Fixed 2026-08-24 (Session 71)** — and
  the `astimezone()` named here was the weaker of two fixes: it renders a
  local wall clock, correct on this box and still ambiguous. The
  assertion problem was real and the answer was to assert what the
  command *means* rather than what it renders
- **`SNAG-UNITS-006`** — drop-in directories are invisible to
  `discover_units`, so `restart_bounded` and now `declared_relations`
  share one blind spot. Empty population today: **zero** of the 38 units
  the sweep sees has a drop-in
- **`SNAG-LOG-008` is not closed**, though the rule collapses its ten rows
  to three. That entry is about the signatures being unreadable, not about
  how many rows they occupy

---

## Session 67 — the purge (2026-08-17)

Session 66's fix stopped new duplicates and deleted none of the old ones.
This sitting deleted them, reversibly, and measured the two endpoints
either side.

- [x] **Prove the identity before deleting anything.** `raw_line` differs
      in **all 339** duplicate groups, which reads as evidence they are
      distinct journal entries. It is journalctl's JSON key ordering
      varying between reads. Settled against journald's own identity:
      **338 of 339 groups carry exactly one distinct `__CURSOR`, and none
      carries more than one**
- [x] The 339th is the mosquitto coredump, whose `raw_line` is truncated at
      2000 characters so the cursor fell off the end — its three
      `ingested_at` stamps (12:34:14, 14:12:00, 19:50:19) are the three
      restarts, which is the same evidence by another route
- [x] **Key the purge on `(source, logged_at, message)`** — exactly what
      `_is_unstored()` uses to decide an entry is already stored, so the
      surviving table holds no shape the running code refuses to re-create
- [x] **Keep the earliest `ingested_at`, not the earliest `id`.** Session
      66's plan said `id`; `UUIDPrimaryKeyMixin` is `uuid.uuid4` /
      `gen_random_uuid()`, so ordering by it is arbitrary and would have
      kept a random copy — falsifying when the service first observed the
      entry while leaving `logged_at` correct, a row disagreeing with itself
- [x] **Assert no source's resume floor moves.** Deleting the last
      surviving row at a floor moves `_resume_floor()` backwards and the
      next poll re-reads the window — the purge re-opening `SNAG-LOG-007`
      by hand. Measured 0 before the delete, and asserted inside the
      transaction
- [x] Back up first: `raw_line` is truncated at 2000 characters and these
      entries may have rotated out of the journal, so a wrong delete is not
      recoverable from source
- [x] **Rehearse with `ROLLBACK`, then falsify both guards** — the count
      guard and the floor guard each abort, and the `DELETE` never executes
      in either falsified run
- [x] Purge: **497 rows deleted**, 626,976 → **626,479**, duplicate groups
      339 → **0**
- [x] **Verify the restore path rather than claiming it.** Re-inserting the
      CSV inside a transaction gives back 626,976 rows and all 339 groups,
      then rolls back
- [x] **Re-read both endpoints.** `GET /api/logs/actions` **28 → 24**
      recommendations, `confidence: medium` unchanged, **no new
      recommendations**; `GET /api/logs/trends` 47 signatures unchanged,
      `truncated: false`
- [x] **Four recommendations were fabricated, not inflated** — both
      `alfred-backend` surges (21 vs 5, ratio 4.2; genuine **4 vs 5**) and
      both `sportsanalyser-frontend` surges (19 vs 6, ratio 3.17; genuine
      **1 vs 3**). The second pair is a **decline that was being reported
      as a surge**: duplication inverted the direction, which "counts are
      overstated by up to 19×" does not predict
- [x] Worst surviving inflation: `estate-broker-provision` **18 → 1**,
      `kernel` "failed to reset" **17 → 1**, `estate-manager-api`
      **23 → 11**, `venture-assistant-backend` surge **48 → 27**, the
      mosquitto coredump **3 → 1**. The two `noise` rows moved
      39,922 → **39,885** — tens of thousands of genuine occurrences, 37
      duplicates
- [x] **Confirm the aggregator is alive before claiming no re-ingestion.**
      91 completed `log_aggregator` runs since the restart, latest
      21:16:38, and **0 rows stored since 20:06:38** — a dead agent would
      have produced the same zero
- [x] Full suite **2,031 passed**; no code changed

**Left undone, deliberately:**

- [x] **Four permanent `running` rows in `agent_runs` — measured, and
      benign.** Carried forward from Session 66 as "unmeasured", answered
      here while ranking rather than as a session. `summarise_agent` takes
      `last_run_at` from `runs[0].started_at` **regardless of status**, so a
      permanent `running` row is the newest row only when the agent
      genuinely has not started one since — in which case flagging it
      stalled is correct, not a false negative. `_failure_streak` *skips*
      `running` rows rather than letting them break a streak, and says why
      in its docstring: a run still going has not failed yet. `durations`
      filters on `duration_seconds IS NOT NULL`, which they are. The rows
      are cosmetic; the two from 2026-08-14 and the two the Session 66
      restart created are all superseded by newer completed runs
- [ ] **Ten `sysadmin.service` signatures still read as raw JSON**
      (`SNAG-LOG-008`) in
      `GET /api/logs/trends` (`{"timestamp": "N-N-N ...", "level":
      "WARNING", ...}`). `unwrap_json_message` applies at *read* time, so
      rows stored before the Session 64 declaration keep the **raw** form
      for ever. **Historic, and measured rather than assumed**: all 10 were
      ingested 14:12–14:22, and the 17 readable rows for that source begin
      at 19:50:19 — nothing is creating new ones. Found by reading the
      purge's before/after, not looked for; filed rather than fixed because
      a backfill is a second data migration and this sitting had already
      made one

## Session 66 — the verification sitting (2026-08-17)

Three consecutive sittings shipped green and unrun. This one restarted the
daemon and measured the four claims, then fixed what the measuring found.

- [x] Restart the daemon — **no `sudo` needed**, `kill -TERM` + `Restart=always`
- [x] Pre-check `alembic current` against the packaged head before restarting,
      because `schema_guard` refuses to boot on a mismatch and that is the one
      failure mode a restart can introduce with no warning (`012 (head)`, clean)
- [x] **Claim 1** — `-p` efficiency: **40.0 %** reproduced on the real
      2026-08-12 storm window (122,531 raw → 49,012 storable)
- [x] **Claim 2** — `GET /api/logs/actions` serves **2 `noise` rows** at
      `confidence: medium`, the family's first in its life
- [x] **Claim 3** — a 700-character JSON journal line yields a **46-character**
      readable title; stored messages read as prose
- [x] **Claim 4** — `covered_by` observed on an induced `service_discovery`
      failure: `info`, `covered_by` naming `failures.py`, `noise_reason` `NULL`
- [x] Resolve the two `Estate port % registry breach` rows owed since Session 63
- [x] **`SNAG-LOG-007` found and fixed** — the resume boundary was re-read on
      every restart; 339 duplicate groups / 497 surplus rows / 19 copies worst
- [x] 8 new tests, each falsified against the old behaviour **and** against both
      wrong fixes (the gap-creating one and the untruncated-comparison one)
- [x] Full suite **2,031 passed**, ruff clean, mypy clean

**Left undone, deliberately:**

- [x] **Purge the 497 historic surplus rows in `log_entries`** — done
      2026-08-17 by Session 67. The key it proposed was right and its
      tie-break was wrong: `id` is `gen_random_uuid()`, so "keeping the
      earliest `id`" keeps an arbitrary copy. See Session 67 below
- [x] **Four permanent `running` rows in `agent_runs`** — **measured
      2026-08-25 (Session 77) and dismissed, with the answer recorded.** Two
      from 2026-08-14 predate the sitting that filed this; two
      `file_organiser` rows were created *by* it, in the documented Session
      41 way — a process killed mid-run leaves the row behind, and the file
      organiser's scan outlives a restart. The open question was whether
      `summarise_agent` mistakes such a row for liveness, and the item was
      **honest that it was unmeasured**. It is now measured against the live
      endpoint: `GET /api/sysadmin/self` reports `last_status: completed` for
      **all five** agents, and `stalled: false` for all five. The rows reach
      nothing — not `last_status`, not the stall path — because `runs[0]` is
      the *newest* run and a ten-day-old row is never newest for an agent
      that ran ninety seconds ago. Cost is four table rows that retention
      clears.
      **What is worth carrying is what happened to the claim in between.**
      Session 76 demoted this by measuring the stall path and then kept a
      residual — *"only `last_status` is wrong"* — which was reasoned from
      the same `runs[0]` fact that refutes it, and it was inherited verbatim
      into a `## Next action` line and a STATUS.md ranking. So an item filed
      as **unmeasured** was ranked first on a cost nobody had measured, which
      is the failure this repository names one document over: a stated cost
      inherited rather than measured. Curling the endpoint settles it in one
      command and nobody had


### Session 65 — SNAG-LOG-005, one owner for agent-run health (2026-08-17) ✅

- [x] **Count the collision before choosing a fix, rather than reasoning
      about the mechanism.** 713 `ERROR`/`CRITICAL` lines from this daemon
      resolve to **249 incidents** and 5 signatures — and the entry's "one
      fault, two rows" was **four**: 215 of 215 fired `agent_run_failed`,
      `scheduler_job_error` and apscheduler's `Job "…" raised an exception`
      in the same second
- [x] Establish the population is **historic**: all 215 fall on 2026-08-08
      → 08-10, the `SNAG-DB-001` window, and `agent_runs` holds **zero**
      `failed` rows across 7,816 sysadmin runs — the same fact twice, since
      `run()` raised out and `_record_outcome` died with it (Session 41)
- [x] **Refute candidate (b) on measurement.** 34 of the 249 incidents
      carry no `agent_run_failed` at all — `file_organiser_scan` ×27 and
      `retention_purge` ×7 — and `retention_purge` is not an agent, so
      excluding `OWN_UNIT` from the alert half deletes the only witness
      those failures have
- [x] Promote the literal in `BaseAgent.run` to
      `core/agent.py::AGENT_RUN_FAILED_EVENT`, so the exclusion keys on
      the producer's own constant rather than a copy of it
- [x] Add `COVERED_SIGNATURES` to `log_aggregator.py`, keyed
      `(OWN_UNIT, AGENT_RUN_FAILED_EVENT)` → the owning family, quietening
      to `NOISE_SEVERITY` with `details['covered_by']` **naming** it
- [x] Keep `noise_reason` and `covered_by` as **separate keys** — an
      operator's judgement and a structural fact are different claims, and
      one field holding both is `UnitFinding.enabled`'s trap
- [x] Carry the quietening through `_record_recurrence` so a **deploy**
      reaches a row the previous release raised loudly — the case
      `known_noise` does not have, since its entries arrive by a config
      edit the next poll re-reads
- [x] Six tests, each falsified deliberately: emptying `COVERED_SIGNATURES`
      breaks five, re-keying the lookup on the signature alone breaks the
      sixth (the negative assertion, which an empty set cannot break)
- [x] Pin the derivation end to end — a real failing `BaseAgent.run`, with
      the assertion keyed on what the logger **emitted**, not on the
      constant against itself
- [x] Verified live: real historic journal lines through the real
      `unwrap_json_message` and the real `_execute` against the live
      database in a rolled-back transaction — `info` + `covered_by` for
      `agent_run_failed`, `warning` for `scheduler_job_error`, **0 residue**
- [x] File `SNAG-LOG-006` — the manual-run path, where `asyncio.create_task`
      means no scheduler listener and so no loud fallback

### Session 64 — SNAG-LOG-003, and the P0 found underneath it (2026-08-17) ✅

- [x] Drive `SNAG-LOG-003` against the **real rows** the 14:10:58 restart
      made available, rather than against a reconstruction — which is what
      found the rest of this session
- [x] **`SNAG-LOG-004`, unplanned and the larger half.** `read_journal`
      passed no `-a`, so `journalctl -o json` returned `MESSAGE: null` for
      every record over ~4096 bytes; `entry["message"][:5000]` raised
      `TypeError` and took the whole run down. Self-sustaining, because
      the failure it logs is itself a 12.8 kB line — all 215 historic
      `agent_run_failed` lines are 12,837–12,845 bytes
- [x] Establish it was **armed and not sprung**: 0 error lines and 146
      clean `log_aggregator` runs since the restart, against 40,228 runs
      that have never failed because `-p 4` excluded these lines until
      Session 61's level prefix
- [x] `message_text()` behind `-a` for the one shape `-a` introduces — a
      non-UTF-8 field rendered as an array of byte values. **Empty
      population** measured (205,298 kernel records over seven days, all
      `str`), kept because the shape is journalctl's to choose
- [x] Check rather than assume that `journal_command` needed no change:
      the field cap is the **JSON serialiser's**, and the same records
      print in full under the default text output at 11,572 and 12,164
      characters
- [x] `LogFormat = Literal["text", "json"]` on `LogSource` and `LogRef`,
      `log_format` through `read_journal` → `unwrap_json_message`, and
      `format: json` declared on this daemon's entry in `services.yaml`
- [x] Measure the title change over the **723 real `ERROR` lines**: 6
      distinct titles of 242–253 characters of JSON → 5 of 46–151
      readable characters
- [x] Decide `logger` goes to `metadata` and **not** into the title, on
      the evidence that the old key's sixth title was a fork produced by
      truncation (`sysadmin.core.scheduler` vs `sysadmin.services.scheduler`,
      one fault under a renamed module)
- [x] Establish the fail-open rule from the box rather than from caution:
      systemd's own plain-text error lines live in a unit's journal, 668
      of them for one unit — verified by reading `sportsanalyser-frontend`
      with `format: json` forced on
- [x] Pin `service.log_format` and `log.format` together by test, keyed on
      `OWN_UNIT`, plus a test that no other source declares a format
- [x] Fix the **fixture** rather than soften the read when twelve tests
      broke on `source.format`: `SimpleNamespace` → the real `LogSource`
- [x] Falsify all four guards independently; 2017 tests green, ruff and
      mypy clean

### Session 63 — SNAG-LOG-002, proportional confidence (2026-08-17) ✅

**The handoff's `## Next action` line stood and named the right change.
It was wrong about the mechanism, and measuring that is what made the
change safe rather than merely permitted.**

- [x] Measure what the 120 truncations actually are before touching the
      gate: **103** are the 2026-08-12 kernel storm (one source, one per
      60 s poll); **16** are the first poll after a restart, each naming
      **four or five sources at once**
- [x] Correct the stated mechanism. The handoff said `_resume_floor()`
      "sizes by daemon downtime"; it returns the newest stored `logged_at`
      **for that unit**, so it sizes by *how long since that source last
      stored a row* — days for a quiet source, against the two seconds a
      restart takes. That is why four sources truncate together
- [x] Verify the consequence: Session 62's `-p` **does** reach the
      catch-up read, against the expectation that no ceiling could.
      Same box, same day — **13:17:05 restart → 13:18:08 poll truncated 4
      sources**; **14:10:58 restart → 14:12:00 poll clean**
- [x] Fix the denominator in `_trend_coverage`: count runs carrying
      `details['truncated_sources']` (`has_key`), not every run. **120 of
      7,006 (1.71 %)**, not 120 of 17,730 (0.68 %)
- [x] `WindowCoverage` gains `runs_instrumented` and `truncated_fraction`,
      which **fails closed** — no denominator returns `1.0`, so every
      un-migrated caller keeps the binary behaviour
- [x] `_confidence` gates on `truncated_fraction > TRUNCATION_LOW_FRACTION`
      (0.05, invented and saying so). **`HIGH` untouched** — only the floor
      beneath it moved
- [x] `LogTrendCoverageInfo` gains both fields, additive and defaulted
- [x] Falsify the guards: `TRUNCATION_LOW_FRACTION = 0.0` restores the
      binary rule **exactly** and breaks precisely the four new tests
- [x] Live run against the real database: confidence **`medium`**, **25
      recommendations including the 2 `noise` rows** — both Bluetooth
      firmware signatures at 39,921. `SNAG-LOG-002` closed
- [x] Full suite **1,984 passed**, ruff clean, mypy clean
- [ ] **The name/unit seam is still open** — `details['truncated_sources']`
      keys on the `services.yaml` name while `log_entries.source` keys on
      the unit, and only `kernel` collides. Anything joining the two must
      map first. Untouched here because the gate is global by run, not by
      source, so it never needs the join

### Session 62 — SNAG-LOG-002, the ceiling half (2026-08-17) ✅

- [x] Refute the handoff's per-source-confidence plan **by measurement**,
      driving the real `_build_trend_report` → `recommend()` against the
      live database: it produces **zero** noise rows, because kernel holds
      both noise-eligible signatures and 103 of the 120 truncations
- [x] Correct the denominator: `details['truncated_sources']` first appears
      **2026-08-12 17:31**, so it is 120 of **6,974 instrumented** runs, not
      119 of 10,063 — 33,090 earlier runs have no such key
- [x] Find the real defect: `-n 500` bounds **raw** journalctl output while
      `severity_filter` runs in Python afterwards — **40 %** of the budget
      useful across the storm, 208 of 210 storm minutes truncated
- [x] Pass `-p` to journalctl, derived from `PRIORITY_MAP` by
      `max_priority_for` rather than restated beside it
- [x] Verify live that the stored multiset is **identical** (81,216 either
      way) and efficiency goes **40 % → 100 %**
- [x] `tests/test_journal.py` — `read_journal`'s **first direct tests** (14)
- [x] Full suite **1,979 passed**, ruff clean, mypy clean
- [x] **Proportional confidence** — `_confidence` was `runs_truncated > 0`
      over 14 days, so one post-restart catch-up read pinned the report
      `LOW` for a fortnight. **Done by Session 63 above**, which also found
      that this session's `-p` already removes the catch-up truncation
      itself, leaving only its history to gate against
- [ ] **The name/unit seam** — `details['truncated_sources']` keys on the
      `services.yaml` name while `log_entries.source` keys on the unit, and
      only `kernel` collides. Anything joining the two must map first

### ✅ Session 61: The priority half, and a premise settled by one `systemctl show` (done 2026-08-17)

**The handoff's `## Next action` line stood and was taken as written.** It
named the priority half of `SNAG-AGENT-008` and it was right about the
fault. It was wrong about the choice — and so was the snag entry it came
from, which said the two unit-file remedies both need `sudo` and that
reading the `"level"` key in `read_journal` is *"the only one needing no
unit-file edit"*. `SyslogLevelPrefix=` **defaults to true in systemd** and
already reads `yes` on this unit, so the prefix remedy needs no unit edit
and no `sudo` either.

- [x] Check the premise before choosing: `systemctl show sysadmin.service
      -p SyslogLevelPrefix` → **`yes`**. Two of the trade-off's three
      clauses were wrong, and one command settled both
- [x] Verify the mechanism against a **transient unit** rather than the
      documentation — `<4>{…}` arrives as `PRIORITY=4` and journald
      **strips the prefix**, so `MESSAGE` is byte-identical and
      `log_signature` / `alert_title` / `raw_line` need no change
- [x] Rule out `systemd.journal` on measurement: `ImportError` in the
      venv, so it is a new native dependency
- [x] Rule out the reader-side fix on measurement too: `sysadmin.service`
      is the **only** JSON-writing journal source of the 14 declared, so a
      special case in a reader serving fourteen could never pay for itself
      — and `journalctl -u sysadmin -p err` would still print nothing
- [x] `JournalLevelPrefixFormatter` in `sysadmin/core/logging_setup.py`,
      gated on `log_format == "json"` — a **precondition**, not a proxy:
      only JSON guarantees one line per record, so a traceback travels on
      the line whose level describes it
- [x] **The second emitter, and it is the one carrying the errors.**
      `uvicorn.error` propagates only as far as `uvicorn`, which keeps a
      plain-text handler with `propagate = False` — `uvicorn.access`'s
      shape exactly. **Rerouted, not silenced**, the opposite verb from
      its sibling three lines up: the access line duplicates a structured
      line, uvicorn's error line has no second copy anywhere
- [x] **Session 60's own guard was asserting the opposite and passing.**
      `test_only_the_access_logger_is_silenced` rebuilds `uvicorn.access`
      and not its parent; driven against the real `LOGGING_CONFIG` the
      record went to uvicorn's own handler and root stayed **empty**. The
      new class drives the real `dictConfig`; the old test's docstring now
      says what it does not cover
- [x] Falsify both guards against restored pre-fix code — reverting the
      formatter fails 12 tests, removing the reroute fails exactly the two
      that name it
- [x] **Drive the whole loop live without the `sudo` the deploy needs**: a
      transient user unit running the real `configure_logging`, read back
      by the real `read_journal` at `severity_filter: warning` — **3
      entries where it has always returned 0**
- [x] Re-measure `SNAG-LOG-002`'s composition: **119 of 10,063 runs, across
      9 sources**, not the two Session 60 named
- [x] Full suite **1,965 passed**, ruff clean, mypy clean
- [x] **Restart done 2026-08-17 by Session 66** — and it needed **no
      `sudo`**: the unit runs `User=gaddi` with `Restart=always`, so
      `kill -TERM <MainPID>` is a deploy the owner can perform and systemd
      brings the daemon back on the new code in `RestartSec=10`. Both
      halves of `SNAG-AGENT-008` verified live off that restart

**What the fix will look like when it lands, measured in advance.** With
the priority half in, `entry["message"]` is the whole formatted JSON line,
so `alert_title` produces `Log error: sysadmin-service — {"timestamp":
"N-N-N N:N:N,N", "level": "ERROR", "logger": "sysadmin.core.retention",
"message": "retention_purge_failed", …` at 252 of 255 characters, and that
reaches a notification body verbatim. **Detection is unaffected** — two
distinct faults gave two distinct titles — so it is filed as
`SNAG-LOG-003` rather than fixed here, because the obvious remedy is the
very coupling this session rejected and the honest one is a `format: json`
declaration in `services.yaml`.

### ✅ Session 60: The volume half, and what the table said instead (done 2026-08-17)

**The handoff's `## Next action` line was taken as written, and the live
table refuted its justification within twenty minutes.** The line said
to stop `sysadmin-service` flooding its own journal read *because* 118
truncated runs suppress `GET /api/logs/actions`'s `noise` family. The
first half was worth doing. The second was wrong.

- [x] Measure the composition of `sysadmin.service`'s journal before
      changing anything — **673 lines per 5 minutes**, 676 over a
      30-minute sample, steady rather than bursty
- [x] **Cause 1: every request was logged twice.** `configure_logging`
      clears the *root* handlers, which does not reach `uvicorn.access`
      — uvicorn's dictConfig attaches a handler to it directly with
      `propagate = False`. 662 plain lines against 640 JSON access lines
      in ten minutes, and 662 − 640 is exactly the 22 `/health` polls
      the middleware excludes. So `SNAG-API-002`'s exclusion **has never
      worked**, and the test that guards it patches the middleware's
      logger — the one that was already honouring it
- [x] **Cause 2: the tray fanned out `/details` for a tab nobody was
      looking at.** `ServicesTab` is built eagerly at tray startup and
      wired to `status_updated` unconditionally: one request per
      systemd-backed service per poll, dashboard open or not. **1,160 of
      1,347 lines, 86 %.** `DashboardWindow`'s own docstring promised
      *"no background polling when hidden"*
- [x] Fix both: `uvicorn.access` disabled in `configure_logging`;
      `_on_status` gated on `isVisible()` with `refresh()` covering the
      warm tab so it does not sit blank for a poll interval
- [x] Falsify both guards against the restored pre-fix code — 1 logging
      test and 4 of 7 tray tests fail, with production's exact line
- [x] Drive the logging half against uvicorn's **real** `LOGGING_CONFIG`
      rather than a reconstruction of it
- [x] Deploy the tray and measure: **`/details` = 0**
- [x] Correct `SNAG-AGENT-008` (volume half fixed; three claims in it
      were wrong) and `SNAG-LOG-002` (its cause is the kernel)
- [x] **Done 2026-08-17 by Session 66** — and "the restart needs `sudo`"
      was wrong: `User=gaddi` + `Restart=always` makes `kill -TERM` a
      no-sudo deploy path. `systemctl restart` needs `sudo`; a restart
      does not

**What the table said instead, and it is the more useful half.** The 118
truncated runs are **kernel 103, sysadmin-service 14**, out of **10,064
runs — 1.2 %**, not "essentially every read"; and **104 of the 118
landed on one day**, 2026-08-12. `log_trends._confidence` is
`runs_truncated > 0`, i.e. **binary**, so taking this service to zero
leaves 103 kernel runs and `SNAG-LOG-002` does not close. It will clear
by itself around 2026-08-19 when 08-12 leaves the window, and return on
the next kernel storm.

**The two halves of `SNAG-AGENT-008` turned out to be multiplicative,
not independent.** `_read_journal_source` falls back to a five-minute
window only when there is no cursor *and* `_resume_floor` is `None`. For
this service the floor is *always* `None`, because the priority half
means no rows are ever stored — so the durable resume mechanism is
permanently off, every restart re-reads five minutes, and five minutes
at 673 lines overflows a 500-line ceiling. Fixing either half stops the
truncation.

**Checked for a pattern rather than assuming one.** `ServicesTab` is the
only tab that issues a request from a client signal handler; every other
one confines them to `refresh()` or a user action. One instance, so it
is fixed in place rather than given an abstraction.

### ✅ Session 58: The document catches up with the box (done 2026-08-17)

**The recommendation, taken on the fourth attempt.** `SNAG-DOCS-001` was
named at the close of Session 55, re-stated by 56 and displaced twice on
merit; the argument that displaced it — a detector's first live data
beats the document backlog — was spent, and no fourth such opportunity
was queued.

- [x] **Measure before editing.** `GET :8500/openapi.json` serves **one**
      route under `/api/projects`. The Contract Registry held **twelve**
      `/api/projects` rows, not the fifteen the snag claims, and the
      population splits **three** ways rather than two — served here
      (`/managed`), consumed from 8400 (`/overview`, `/{name}`), and
      neither (nine). The entry's own remedy, applied literally, would
      have deleted a live route's contract and relabelled a live seam
- [x] **Nine narrative blocks, not the five the entry named** — found by
      grepping the tree instead of counting the paths it lists:
      `snapshots.py`, `build_narrative_history`, `/next`, `momentum.py`,
      `nudges.py`, `/stale`, `status: archived`, the marker scan and
      `branch_actions.py`
- [x] **Six further sentences**, each correct in isolation and wrong
      together: "the file-organiser mirror of `/api/projects/actions`",
      "the third scorer, after the project organiser's repositories",
      "the two weekly reviews" (there is one), "both project sections
      read **one** snapshot query" (there are none), the retention
      narrative's example route, and the manifest parser named as
      `sysadmin/registry/`. That is the residue a block-level sweep
      leaves
- [x] **Two blocks rewritten rather than pointed away**, because the
      argument is still this repository's: `SysAdminAgent._resolve_recovered`
      (the project organiser made the case, we still run the statement),
      and `core/escalation.py`'s placement, whose stated reason —
      `monitor` may not import `projects` — **expired with the domain**
      and has been replaced with the four climbers it actually has
- [x] **ADR-0005 was not linked from `CLAUDE.md` at all**, nor 0003 nor
      0004. The pointer target of the entire fix was missing from the
      index the fix points through; all three are now listed, with 0001's
      open question marked answered against this repository
- [x] Suite **1866** green, `CLAUDE.md` 1,774 → 1,684 lines

#### What measuring the box found on the way

- [x] **`SNAG-AGENT-002` was fixed on 2026-08-12 and nobody closed it.**
      Its stated fix — group by unit plus a normalised signature, one
      alert carrying an occurrence count — is `log_signature.py`
      verbatim. Live table: **8 unresolved rows**, five log signatures,
      every one carrying `occurrences` and `last_seen_at`, against
      547,814 for one title on 2026-08-11. **Session 27 is therefore not
      "fix the pile-up then build the tiers"; it is only the tiers**
- [x] **`SNAG-ESTATE-010` filed**: Session 57's quietening is live in the
      daemon and cannot reach the two rows it was written for, because
      the family dedups on an open title. Escalation has a path for
      getting louder (resolve the quiet row, raise a loud one) and
      nothing has the reverse
- [x] **`SNAG-DOCS-002` filed**: eight project contract models with zero
      readers, four of them re-exported to the tray — the `SNAG-CFG-001`
      shape, left for a sitting that is allowed to touch code
- [x] **The snag parser went 36 → 38** across a sitting that closed two
      and opened two, because it cannot see a closure that stays in
      place under "Open". `SNAG-ROADMAP-002` demonstrating itself, and
      still filed here though the parser left on 2026-08-13

### ✅ Session 57: The holder decides how loud (done 2026-08-17)

**Not the recommendation.** Session 56 named `SNAG-DOCS-001`; the sitting
opened on the ports family's first live rows instead, which is the third
consecutive time a detector's first real data has been worth more than
the document backlog — and, like Sessions 52 and 54, it found a defect no
hand-written fixture held.

- [x] Measure the two open rows rather than read about them —
      `Estate port 3110` and `Estate port 8110`, `warning`, open since
      2026-08-16 12:07, one minute after the daemon last entered active.
      Both listeners still up: `nuxt dev` and `uvicorn --reload`, all
      three pids in `app-code-oss-26348.scope`
- [x] Find why `details['holder']` is `null` when
      `Listener.transient` has named these listeners since Session 26c.
      **The signal was collected, named, and then dropped**:
      `PortReport.unit_ports` skips `attributed and transient` for
      `recommendations.py`'s correct reason, and `unattributed_ports`
      never held them because a session scope *is* attributed. The port
      fell out of the stored blob entirely
- [x] `PortReport.transient_ports()` — a **separate blob key**, not a
      flag inside `unit_ports`. One field whose two consumers want
      opposite safe defaults is Session 48's `UnitFinding.enabled` trap,
      caught this time before it shipped
- [x] `PortAttribution.transient_holders` + `of()` returning
      `transient` as a bool that is **always present**, so
      `holder.get("transient")` cannot read every service on the box as
      non-transient by accident
- [x] The ambiguity rule spans both maps: a port held by a dev server
      *and* a real service is attributed to neither, because naming one
      would answer here a question `judge_ports` reports as a
      disagreement
- [x] `judge_audit_findings` rule 5 — a transient holder is **quietened,
      never suppressed**. `TRANSIENT_HOLDER_SEVERITY = "info"`, derived
      from `tray.notify_min_severity` and guarded by a test that reads
      the live `config.yaml`
- [x] The roll-up takes the loudest rung it swallows (Session 52's
      rule), so six dev servers plus one genuine unclaimed listener
      still speaks at `warning`
- [x] 12 tests: 5 in `test_unit_ports.py` driving `ss` output → blob →
      attribution end to end off the real 2026-08-17 lines, 7 in
      `test_estate_judgements.py`. 1866 green, ruff and mypy clean
- [x] Verified **live, in-process**: the real `ss` (37 listeners), the
      real `:8400/api/audit/findings` (2 breaches + the standing 3300
      `warn`), and the same two rows coming out `info` with
      `holder=app-code-oss-26348.scope` where they had come out
      `warning` with `holder=None`
- [x] `SNAG-ESTATE-009` filed for what this does **not** cover: the
      sweep is six-hourly and the judge hourly, so a dev server started
      inside a sweep window is unattributed and speaks at `warning`

**Rejected: dropping the row.** It is the obvious implementation and it
rebuilds this family's founding defect — Session 26b-A exists because a
ports breach was detected, correct, machine-readable and never said out
loud. A consumer that silently declines to judge a published finding is
that shape one layer over, with the extra property that nothing records
the decision, which is `SNAG-CFG-001`'s.

**Rejected: running `ss` in the judge** to close the sweep-window gap.
`EstateJudgeAgent._attribution` refuses it in writing — two answers to
one question at two moments, with neither surface saying which it used —
and the gap is a lower bound of the kind this repository already
publishes (`at_window_edge`, `observed_from`, `standing_days`).

**Rejected: raising the sweep cadence** from six-hourly to hourly. It
narrows the same gap with one config line, and pays six times the
sweep's cost across every consumer of `unit_ports` for the benefit of
one annotation.

**Known and not fixed here.** The two rows standing today were raised at
`warning` and the agent deduplicates on title, so they are *not*
re-raised at `info` — they stay loud until they resolve, which happens
when the editor closes. A de-escalation path (resolve the loud row,
raise the quiet one) is the inverse of the ladder in
`core/escalation.py`, which `step_for` explicitly refuses in that
direction, and it is a design question rather than this session's.

### ✅ Session 56: The snag that was already fixed (done 2026-08-17)

**Not the recommendation.** Session 55 named `SNAG-DOCS-001`; the sitting
opened on `SNAG-DB-002` instead, and closed it without changing a line of
code — because the box had closed it three days earlier and nothing here
had noticed.

**What the session actually was**: `SNAG-DB-002`'s remedy half —
`REINDEX` then `REFRESH COLLATION VERSION` across the stale databases —
was carried out by **estate-manager** on 2026-08-13, in two passes
(`eb51ff6` at 18:03, `52b312c` at 20:29). The remedy is their
`scripts/refresh-collations.sh`, and it encodes this entry's own trap:
never `REFRESH` unless that database's `REINDEX` has just succeeded.

**The verification is the deliverable, and the first method was
insufficient.** Index file mtimes show the two bursts and prove nothing
about an actively-written index, whose file carries a recent mtime
regardless of whether its contents were rebuilt. The exact test is
`pg_class.relfilenode` against `pg_class.oid` — a rebuild draws a fresh
relfilenode from the cluster-wide counter, so an index never rewritten
retains `relfilenode = oid`. **0 of 125 collation-sensitive user indexes
across all eight databases** retains its original. Filtering on
`indcollation NOT IN (0, 950, 951)` is what makes the count mean
anything: `0` is not collatable, `950`/`951` are `C`/`POSIX` and are
byte-order, so immune to a glibc change.

**Four numbers in the entry were corrected, three of them having been
true when written.** 16 GB (real, and mostly index bloat the reindex
reclaimed, before the estate dropped `personal_assistant` on 2026-08-14
taking it to 1,094 MB); eight databases (the estate audits eleven); "25
indexes, several on text" (58 collation-sensitive in `projects`, 125
across the cluster, **0** in `pg_catalog`); and a quiet window of hours
that was 30 seconds, because `REINDEX` rebuilds indexes and the database
size was never the governing figure.

**The durable finding is `SNAG-ESTATE-008`, and it is not the estate's
fault.** This application *observed* the remedy land — the eight alerts
resolved at `18:01:48` on the next five-minute poll — and recorded it
where nothing reads back. Meanwhile `snag_list.md`, `tasks.md`,
`STATUS.md` and `HANDOFF.md` each independently restated the action as
pending for three days and five sittings, `STATUS.md` as a standing
sub-session item at the top of the block that opens every sitting. An
unread fault is a missed alarm; an unread **recovery** is an instruction
to redo finished work on a live 16 GB database, which is the worse
polarity. The cause is structural: `EstateJudgeAgent` is narrowed to
`check == "ports"` for two good reasons, neither of which anticipated
shared infrastructure remedied by the estate.

**Also corrected**: this file's sibling header claimed
`count_open_snags` reports 47, measured 2026-08-14. Driven against the
current parser it reports **35** — the function was rewritten around
`read_snags` since, so the number went stale because the code that
measures it moved. `SNAG-ESTATE-008` in miniature.

**No code changed. No tests were added, and that is a finding rather than
an omission** — there is nothing here to test. The gap is that no
document or script reconciles an ops action against the alert row behind
it, and the candidate fix is one `psql` query in
`scripts/claude-preflight.sh`, deliberately left unpriced in the snag.

### ✅ Session 55: The understudy gets a clock (done 2026-08-16)

**Session 54's recommendation, taken as written**, and the last unclosed
hole in the arc Sessions 39, 53 and 54 built. `SNAG-TRAY-007`:
`monitor/desktop.py` is subscribed to `alert.raised`, speaks once per
incident, and has no moment at which it could notice that a fault it
announced six hours ago is still open — Session 39's original defect,
surviving in the one component that exists for the case where the tray
is down. Suite **1854 passed** (from 1834), ruff and mypy clean, **no
migration**, **no route**, one new config leaf and one new scheduled job.

- [x] `DesktopNotifier.sweep_reminders` — the clock the module never had
- [x] `desktop_reminder_sweep` in `core/jobs.py` + `main.py`'s `JOB_TARGETS`
- [x] `notifications.desktop.reminder_hours`, defaulted to the tray's 24
- [x] 20 tests in `tests/test_desktop_notifier.py`
- [x] Verified live against the real `alerts` table and a real scheduler
- [x] `SNAG-TRAY-008` filed for what the fix deliberately does not cover

**The deliverable was a decision, and it came out in two halves.**

*Precedence.* `tray_grace_seconds` is the same window on both paths and
the **action is different**. The raise path *skips*: the tray is about to
show this. The repeat path **stamps the clock forward**, because a skip
leaves `last_spoken_at` at the opening notification, and the first sweep
after a tray outage would then restate a fault the tray itself restated
ten minutes earlier. Session 54's doubt — "the two answers are not
obviously the same" — was right, and the difference is only observable in
the middle window, which is what the test pins. The first version of that
test asserted the wrong arithmetic and passed for the wrong reason.

*Ownership.* A `JobSpec`, not a call bolted to the end of
`SysAdminAgent._execute`. The agent version is cheaper wiring and makes an
agent responsible for a lifecycle `monitor/desktop.py` owns — the
second-owner defect this repository has now found at four scales, and the
reason the snag refused a patch in the first place.

**Nothing here is a new number.** `reminder_hours` is the tray's, for the
tray's reason, and because two speakers with different cadences make the
interval depend on which of them was running — the thing the understudy
exists to hide. The sweep's own cadence has no leaf at all: it is
`max(60, tray_grace_seconds)`, since the sweep asks the two questions that
window already answers.

**The honest limit is filed rather than implied.** The population is what
*this process* announced, so a fault raised while the tray was up is never
adopted, and a daemon restart forgets everything. Widening it to
`resolved IS false` is `SNAG-AGENT-005`'s unbounded `SELECT` wired to a
notification each — that is `SNAG-TRAY-008`, with the shape of a fix
recorded so it is not re-derived.

**Live, because the unit tests mock every session.** The `title IN (…)`
clause had never reached PostgreSQL. Driven against the real table: the
query selected the live title and refused one never raised, the sweep
restated once then held, a synthetic row was restated inside a roll-up of
2, resolved, and dropped — residue **0** after rollback. `apply_jobs`
against a real `BackgroundScheduler`: added at `interval[0:03:00]`,
re-apply retimed nothing, grace 600 retimed it to ten minutes, and
`enabled: false` removed it.

### ✅ Session 54: The other three surfaces, against data (done 2026-08-16)

**Session 53's recommendation, taken as it was written.** The estate
judge's remaining three surfaces — `judge_projects_invariants`,
`judge_audit_invariants`/`judge_audit_findings` and
`judge_queue_invariants` — driven against payloads made by the
producer's own code the way Session 52 did for `attention`. Suite
**1834 passed** (from 1802), ruff and mypy clean, **no migration**, **no
route** and **no config change**; the two code changes are in
`sysadmin/estate/`, which the daemon serves from its start-time copy, so
they deploy on the restart already owed.

**The method, and that it is one notch weaker than Session 52's.** There,
26 real snapshots and 5 real streaks went through the producer with two
thresholds forced, and the fixture was an observation. Here the unhappy
states have never occurred — **0 of 7 `scan_runs` and 0 of 22
`audit_runs` carry an error**, no `ports` finding has ever reached
`breach`, and the queue has never had a waiter — so the *rows* are
synthetic. What is borrowed is everything downstream of them: the ORM
models (which reject a shape the estate cannot store), `scan_invariants`,
`audit_invariants`, `findings` including its `_streak_starts` age walk,
`CheckResult.as_summary`, `Arbiter.invariants` and `api._public`. Run in
estate-manager's venv against the live `estate` database inside
transactions that were rolled back, verified afterwards at 7/22/92 rows
unchanged. The port breaches are **not** synthetic: real listeners on
3900–3905, inside the registry's own audited range, through
`ports.run_check` against the real `monitorable-project.md` — Session
26b-A's method.

**The defect, and it is exactly what a one-condition-at-a-time literal
cannot show.** `_scan(error=...)` and `_scan(estate_written=False)` are
two separate tests here and were never in one payload. The producer
cannot separate them: `ScanOutcome.estate_written` starts `False` and is
set near the end of a run, so **every failing scan carries both**, and
the judge raised two rows for one fault — the second reading *"The last
project scan completed without rewriting estate.json"* of a scan that
did not complete. Under Session 53's `reminder_hours` that is a false
sentence restated every 24 hours. The `estate_written` rule is now
narrowed to a scan that did not error, which makes the two families
mutually exclusive by construction — `failures.py`/`stalls.py`'s shape,
one domain over.

**A second, latent one, fixed because it is invisible either way.**
`EstateJudgeAgent._execute` read `open_titles` once and never updated it,
so two judgements sharing a title in one run insert two rows and
deduplicate only from the second run onwards. Reachable through
`judge_audit_findings` rule 4, which keeps the finding's `code` out of
the title on purpose: two `breach` codes for one port are two findings
and one row. Unreachable on today's estate, pinned because a run that
raises twice looks exactly like one that raises once until somebody
counts.

**Two producer-side gaps found and delegated rather than worked around.**
`SNAG-ESTATE-006` — `AuditFinding` has no `code` column, so
`details['code']` is `None` on every payload the estate can serve, and
`judge_audit_findings`' rule 4 claimed otherwise. Not fixed here: the
only workaround is splitting `fingerprint`, which is parsing a format the
estate owns. `SNAG-ESTATE-007` — the arbiter's pool omits the `-c
timezone=utc` its sibling engine sets and documents, so `active_lease`
stamps render `+01:00` against three surfaces' `+00:00`. Costs nothing
here and is filed for whoever parses it next.

**Two rules recorded as unreachable rather than deleted**, having been
measured: the scan's `finished_at is None` (the producer writes its row
once, *after* the scan, so a mid-flight death writes no row and surfaces
as staleness) and the audit's `error` (`_record` builds `AuditRun` with
no `error=`, and the path that sets one writes no row). Both kept —
their columns are nullable and the producer may yet fill them — and
named in the docstrings so their silence is not read as health.

**Also corrected**: `1 data sources were unreachable`, in a message that
reaches a notification body verbatim; and the `"code"` key an existing
agent-test literal invented, which is the same defect this session was
about, in the fixtures rather than the code.

**Verified live**, as this family always is because it ships with almost
no rows: the whole agent path against the real database in a rolled-back
transaction, raise 7 → hold (0 raised, 0 resolved) → resolve 7, **0 rows
of residue** — and the failed-scan payload producing one row where it
used to produce two.

### ✅ Session 53: A fault that stands keeps speaking (done 2026-08-16)

**`SNAG-ESTATE-003`, and the entry's own "what would settle it" was
answered in the negative before anything was built.** It asked for a
third rung, or a `warning`-that-repeats mechanism that is not
`critical`; STATUS.md sharpened that to *a third rung in
`sysadmin/core/escalation.py` with three callers*.

**The rung cannot be heard, and that measurement is the session's first
deliverable.** `NotificationPolicy.fingerprint` is `{severity}:{title}`
and an episode only closes when that pair is **absent from a poll** —
which a resolve-and-re-raise inside one agent run never produces. Driven
against the real policy: a resolved row replaced by a fresh one carrying
a new message produced **no notification at all**; the same fault
escalated to `critical` spoke; a forked title spoke. Two audible
repeats, and a forked title is forbidden by four separate rules here.

So the repeat is a **notification** decision and went where notification
policy already lives: `reminder_hours` in
`sysadmin_tray/notifications.py`, default **24 h, derived** from
`self_monitor.escalate_after_hours` so a laddered family reaches its loud
rung as news rather than as a repeat. It covers every deduplicating
family, not the estate's five surfaces alone — which matters, because
`estate_judge` has produced two rows in its life and the live instance
was `service_discovery`'s, the only unresolved row on the box, open 24 h
and spoken once.

- [x] Measure whether a same-severity repeat can reach the desktop
- [x] `reminder_hours` + `_reminder` + `FP_REMINDER`, reminders folded apart from new alerts
- [x] Plumb the knob through `config.py` → `tray_icon.py` → `app.py` → `config.yaml`
- [x] Correct `estate/agent.py` and `core/escalation.py`, whose docstrings said the omission was deliberate and now say why the alternative was refused
- [x] 12 tests; suite 1802 green, ruff and mypy clean
- [ ] Deploy: `systemctl --user restart sysadmin-tray.service` (no `sudo`; re-announces the open row as new, which is the in-memory-state limit working as documented)

**Follow-up opened**: `SNAG-TRAY-007` — the desktop understudy
(`monitor/desktop.py`) is event-driven off `alert.raised` and shares
none of this, so on a box where the tray is down a standing fault is
still announced once. Not patched here: it needs a decision about
precedence, not a copy.

### ✅ Session 52: judge_attention, against data (done 2026-08-16)

**`SNAG-ESTATE-002`'s half that needed nothing from estate-manager.**
The entry's closing paragraph: `judge_attention` had never been run
against a payload with anything in it, so an entire alert family could
not be shown to work. `GET :8400/api/projects/attention` has answered
`{"health": [], "nudges": []}` on all four occasions anyone has looked —
including once after an overnight scheduled scan of 26 projects with no
parse failures, which is what made the negative result worth recording.

**How a populated payload was made, since the wire cannot supply one.**
The producer's own code, driven read-only in its own venv against the
live estate database with two thresholds forced: `effective_threshold`
raised to 101 so live scores breach, and `nudges.evaluate(…,
default_days=0)` so live streaks qualify. Everything else is the
estate's — 26 real snapshots, 26 real manifests, 5 real streaks, and
`dataclasses.asdict` over the producer's own `Nudge`, which is the point:
the field names are exactly what an unforced payload would carry.
Committed as `tests/fixtures/estate_projects_attention.json` with its
provenance on the test that owns it, and the two forced numbers are
visible in the data (`threshold: 101`, `threshold: 0`) rather than
hidden.

**Two defects, both rules this repository had already written down
elsewhere and never applied here.**

- **31 rows from one poll.** 26 health breaches and 5 nudges, each its
  own alert row and its own tray `{severity}:{title}` fingerprint.
  `judge_audit_findings` has had `port_breach_max_rows` for exactly this
  since Session 26b-A and `judge_attention` had nothing. Now
  `attention_max_rows` (5), applied to **each family separately** —
  they have separate producers inside the estate, fail separately, and
  collapsing the working half because the other broke would hide the
  half that still names its projects. The recording lands on both sides
  of the cap without being made to: 26 collapses, 5 does not.
- **A 469-character message.** The live next actions on this estate run
  to 469 characters and `alert.message` reaches a notification body
  verbatim, so the daemon cuts it at a point nobody chose — which is
  `SNAG-BRIEF-002` exactly. Now cut with `truncate_at_word`, which
  always marks it, at `NEXT_ACTION_CHARS = 120`; the full text stays in
  `details['next_action']`.

**A roll-up takes the loudest rung it swallows.** Collapsing rows must
not also quieten them: `info` is below `tray.notify_min_severity` on
this box, so an escalated `warning` nudge folded into an `info` row
would have made the fix for noise the reason the one entry that earned a
toast never got one.

**The seam is now guarded where the two other 8400 routes already were.**
`tests/test_estate_project_contracts.py` gains `/api/projects/attention`
as its third route rather than a new file: recorded half asserts the
keys the consumer reads are present in the populated payload, live half
asserts the envelope and **pre-stages** the per-entry assertions, which
begin running by themselves the first day the estate publishes anything.
It also asserts `title`/`message`/`details` are *absent* from a nudge,
so the day estate-manager closes its `SNAG-ESTATE-010` the suite says so
and names the next move.

Verified live and rolled back, the family having never had a row: three
runs against the real database gave raise (1 roll-up + 5 nudges) → hold
(dedup, 0 raised) → resolve (6 closed when the estate goes quiet), with
**0 rows of residue**. Suite **1792** (from 1776), ruff and mypy clean,
no migration, no new route.

### ✅ Session 51: One copy of the autogenerate rules (done 2026-08-16)

**`SNAG-DB-003`, closed by settling the placement question the entry
deliberately left open.** Session 43 filed it with the design call
unmade — `env.py` cannot import from `tests/`, and a shared constant in
`sysadmin/` looked like pushing a testing concern into the shipped
package. It is not, once the direction of ownership is stated the right
way round: `include_object` is what `alembic revision --autogenerate`
uses whether or not a test suite exists, so it is **production
configuration the drift guard borrows**.

**Where it went, and why not a new module.** `sysadmin/metadata.py`,
beside `Base` — that file's docstring already argues this exact case for
the *model set* ("a table missing from one copy and not the other is
exactly the silent drift the drift test exists to catch"), and which of
the live schema's tables the metadata is authoritative for is the same
question one step further. `COMPARISON_OPTS` travels as one dict;
`alembic/env.py` and `tests/test_schema_drift.py` splat it and configure
nothing of their own.

**Widened from the exclusion list to the whole comparison**, because the
flags fail the same silent way: `compare_type` set in `env.py` and
absent from the guard leaves the guard green *while blind to the drift it
certifies*. Six option names, one statement.

**Not moved, deliberately**: the `SET search_path TO public` both
callers issue. It is connection setup rather than comparison — `env.py`
pairs it with `CREATE SCHEMA`, DDL the guard must never run — and its
drift fails **loudly** (double reflection, phantom diffs) rather than
green.

**`tests/test_autogenerate_config.py` (5) stops the copy coming back**:
an AST sweep over every module for a second `include_object`,
`include_name` or `FROZEN_TABLES`, and for any of the six option names
passed by hand. Textual because `env.py` cannot be imported — it runs
the migrations at module scope. Two of the five exist so the detector
can be seen to fail: one runs the walker at the owner (which must trip
every rule), one feeds it the deleted code. A third asserts both callers
still *import* the options, since a file that configures nothing would
pass an absence check while quietly taking alembic's defaults.

**Verified live.** With the exclusion removed autogenerate proposes
`remove_table` for both frozen tables against 3,739 and 4 rows; after
the change `alembic check` reports no operations (exercising `env.py`
itself), offline mode still renders, and re-adding a test-only exclusion
makes the sweep fail by file and line. Suite **1776 passed** (from
1771), ruff and mypy clean, **no migration**, **no new route**.

**Found while measuring, and it blocks the drop task below**: the
estate's copy of `project_snapshots` holds **3,713** rows in the window
this repository's table covers, against **3,739** here — the **26 rows
dated 2026-08-13**, one per project from the final organiser run at
07:35, were written after the copy was taken.

### ✅ Session 50: The reload re-times the scheduler (done 2026-08-15)

**`SNAG-RELOAD-001`, closed by removing the divergence rather than
reporting it better.** Session 49's own follow-up, and the only candidate
on STATUS.md's runner-up list that was *worse for that session having
happened*: before the reload existed, the config object and the running
scheduler were built from one read and could never disagree.

**The entry offered two mitigations and named a third option in its last
line. The third is what shipped.** Storing the last `ReloadReport` and
serving it is a field nobody polls (`SNAG-CFG-001`'s shape); raising it as
an alert row needs a settled dedup and resolve lifecycle before it is
written, which is a session of its own and would still be *describing* a
divergence this repository can simply not have.

**Shipped**:

- `sysadmin/core/jobs.py` — `plan_jobs(config)` maps an `AppConfig` to the
  nine jobs it asks for, and `apply_jobs(host, config, targets)`
  reconciles a scheduler with that plan. `core` rather than a fourth
  composition root: it imports no domain and knows no agent, because the
  callables are handed in as `JOB_TARGETS` from `main.py`.
- `Scheduler.sync_interval` / `sync_cron` / `remove_job` — **converging**
  rather than additive. There is deliberately no separate "add" entry
  point left: a caller with both has a decision to take, and taking that
  decision away from the two composition roots is the point.
- The lifespan and the reload now call the same function, so the schedule
  at startup and the schedule after a reload cannot be produced
  differently — the rule `_reload_configuration` already applied to its
  two triggers, one layer down.
- `RESTART_ONLY` went from **fifteen leaves to two prefixes**: `service`
  and `database`, covering the socket, the logging setup and the engine.

**The obvious implementation is wrong in the direction that matters.**
Re-applying every job on every reload is a line shorter and breaks the
schedule: `reschedule_job` recomputes the next fire from *now*, so a
24-hour job would sit permanently 24 hours from the most recent reload —
`agent_first_run_delay_seconds`'s failure with a reload standing in for a
restart. An unchanged trigger is therefore left alone, decided by
comparing against the **live** job rather than a remembered plan.

**Two decisions with a stated cost:**

- **A job being *added* gets the first-run delay; a job being *re-timed*
  does not.** Added means this process has never scheduled it (a cold
  start, or an agent just re-enabled) and `IntervalTrigger` alone would
  put the first fire 24 hours out. Re-timed means it already has a next
  fire, and pulling that forward would turn an unrelated threshold edit
  into a 118-second filesystem scan nobody asked for.
- **The plan is total — a disabled job is emitted disabled, never
  omitted.** Only a plan that still names a job can *remove* it;
  otherwise `enabled: false` is a restart-only field wearing a live
  one's name. Rule 5 bounds the other side: only planned ids are removed,
  so a job this module did not schedule is never swept.

**The guard test was rescued rather than lost.** `tests/test_reload.py`
walks the lifespan and requires every config path it reads to be
classified; moving fifteen of those reads into `core/jobs.py` would have
hollowed it out silently. It now walks both, and gained a second half —
each `JobSpec`'s declared `config_paths` must equal the paths `plan_jobs`
actually reads. Writing it found a real defect in the walker itself:
`delay = schedules.agent_first_run_delay_seconds` is syntactically
identical to an alias assignment and semantically the opposite, and the
original helper dropped it, which is the guard failing in exactly the
direction it exists to catch. Three source-grep tests elsewhere
(`test_scheduler`, `test_self_monitor`, `test_estate_judge_wiring`) were
converted from substring matching on `main.py` to real assertions
against the plan.

**1771 tests pass** (from 1733), ruff and mypy clean, no migration.

**Verified live** against the real `config.yaml` and a real
`BackgroundScheduler`, in-process, touching neither the daemon on 8500
nor the file: 999 s became `interval[0:16:39]`, `retention_purge` moved
03:00 -> 04:00, a disabled `estate_judge` had its job **removed** and
re-enabling **added it back with the first-run delay**, and
`requires_restart` came back `[]` where Session 49 reported three leaves.
The same reload run twice re-timed nothing.

**What it does not fix, and says so**: `service` and `database` are
genuinely immutable in-process, so a port or database URL change still
needs `sudo systemctl restart` — and the report still names it.

### ✅ Session 49: A reload path for services.yaml (done 2026-08-15)

**`SNAG-UNITS-005`'s durable half.** STATUS.md had this as a runner-up,
demoted as *"a sub-task rather than a session"* — a judgement made on two
data points, where the third consecutive sitting owing a restart was the
one that made it session-sized. It removes the class of blocker rather
than the instance.

**The design question it carried was settled by measurement, and the
measurement moved the answer.** The question as filed was whether
config.yaml is safe to reload *"which holds thresholds the running agents
have already read"*. They have not: every agent calls `get_config()`
inside `_execute`, because SNAG-AGENT-003 forbade agents a startup hook —
a constraint written for event-loop safety that bought per-run
configuration for free. So the reloadable half is nearly everything, and
the start-time-read half is small enough to enumerate.

**Three decisions taken, all three the recommended option:**

- **Both files, naming what was ignored** — rather than refusing the
  config half. Refusing blocks a threshold fix on an unrelated edit in the
  same file, and the operator then restarts anyway, so it delivers nothing
  the restart did not. Half-success is dangerous when *silent*; this names
  the changed leaves in the body and in a `WARNING` log line.
- **`SIGHUP` and an authenticated `POST`, one shared function** — the
  signal is the path that needs no `sudo` (the unit is system-scope but
  runs `User=gaddi`); the endpoint is the only one that can *return* the
  report, and the only one that is straightforwardly testable.
- **Prune per-service in-memory state, never reset it** — resetting
  re-arms the three-poll degraded streak at the moment an operator is
  most likely to be reloading because something is failing.

**Shipped**: `sysadmin/reload.py` (a composition root beside `main.py`,
now enforced by `tests/test_import_boundary.py`), `parse_config`/
`set_config`/`set_services` split out of the loaders so validation
precedes installation, `forget_unknown()` on the two agents holding
name-keyed state, `ReloadResponse`, the endpoint and the signal handler.
**1733 tests pass** (from 1708), ruff and mypy clean, no migration.

**Verified live on the instance that motivated it**: with Session 48's
three new entries removed to stand in for the running daemon, a reload of
the real `services.yaml` reports them `added`, installs all three, and
reports `requires_restart: []`.

**One follow-up filed**: `SNAG-RELOAD-001` — after a reload the config
object can hold a scheduler setting the running scheduler does not obey,
and `requires_restart` says so once rather than continuing to. The real
fix is a `reschedule_job` on `Scheduler`, which would shrink
`RESTART_ONLY` to the socket, the engine and the logging setup.
**Taken as Session 50 the same day** — see below.

**Still owed, and not addressable by any reload**: the five system-scope
orphan removals under `/etc/systemd/system`. `SNAG-UNITS-005` conflated a
deploy blocker with an ops blocker; only the first is gone.


_Sessions 24–27 promoted from [ideas.md](ideas.md) on 2026-08-05. They are
**independent of each other** — take them in any order. 24 and 26 are done,
and 25's Tier 1 landed 2026-08-07; **25b/25c (reliability Tiers 2–3) and
27 (log aggregator tiers) remain**, plus 26b (port-registry
reconciliation), split out of 26 on 2026-08-07._

All four repeat the **tier pattern** proven by Sessions 21–23:

- **Tier 1 — measure**: structured findings; a score whose deductions are
  individually attributable.
- **Tier 2 — advice as data**: a *pure* module (no DB, no FastAPI) mapping
  each finding to ranked advice with an exact payoff, pointing at existing
  safe dry-run executors where one exists, naming the config change where
  one doesn't.
- **Tier 3 — periodic LLM narrative**: facts and deltas computed
  deterministically in code, bounded prompt, model writes only the
  qualitative sections, digest fallback when inference is unavailable,
  persisted with its inputs in `stats` for auditability, surfaced via
  endpoint + cron + briefing section.

**Two hard-won rules any Tier 3 must follow** (both cost a live debugging
session in Session 23): commit the read transaction *before* calling the
LLM — this host sets `idle_in_transaction_session_timeout=1min` and
inference takes longer — and never let the 3B model produce numbers; it
fabricated the numeric section under two different prompts.

### Session 24: File organiser tiers — disk instead of portfolio

**Complete 2026-08-06 (all three tiers).** Tier 1 already existed, so
this was Tiers 2 and 3 plus the module move. The currency is **reclaimable
megabytes** — MB, not bytes, because every source field is `size_mb` and
bytes would be fake precision on a value rounded to 1 dp at scan time.

- [x] **Promote the forecast maths out of the tray** →
      `sysadmin/services/forecast.py`. Not a pure move: `disk_series()`
      took a `ResourceHistoryResponse`, which the backend never has, so
      the primitive is now `disk_series_from(entries, mount)` over
      `(timestamp, disk_usage)` pairs — an ORM row and a parsed contract
      both produce that shape — with the contract version a one-line
      adapter. Tray imports it the way `models.py` already imports
      `contracts`; verified no FastAPI/SQLAlchemy leaks in. Added
      `most_urgent_projection()` (imminent crossing beats an exceeded
      lower threshold; exceeded beats a distant crossing) and deduped
      `_compute_reclaimable_forecast`'s hand-rolled least-squares against
      `linear_fit`
- [x] **Tier 2** — pure `sysadmin/services/file_recommendations.py`.
      **The currency only applies to three finding types.** Duplicates,
      old downloads and stale caches free space; misplaced files, empty
      dirs and similar folders free *nothing* — they price at 0.0 MB and
      rank by `item_count` beneath anything with real megabytes. Large
      files are a fourth case: measurable but not reclaimable, since only
      the user knows which are junk. Split stale project dirs into
      caches (executor exists) and rebuildable dirs (`node_modules`,
      `.venv` — 25 GB here, no executor, advice names the manual step)
- [x] `GET /api/files/actions`, risk-first. The risk needs a **second
      table**: `filesystem_audits` tracks junk accumulation, only
      `resource_snapshots` knows disk occupancy, and occupancy is what
      answers "when does the disk fill up"
- [x] Separate `FileRecommendationInfo`, **not** a reuse of
      `RecommendationInfo` — one `points` field meaning "score recovered"
      or "megabytes" depending on the producer would be unreadable at the
      call site
- [x] Contracts + tray re-exports; 48 new tests (1099 → 1147)

**Two Tier 2 bugs only the live run caught** — both invisible to the mocked
tests, which is the Session 23 lesson repeating:

1. **`findings` is truncated before storage** (50–100 entries per
   category). The real audit row lists 200 misplaced files against an
   actual **11,877**, and 100 downloads against **11,400** — up to 60×
   understated. Fixed by passing the audit row's own count columns as
   `true_counts`; sizes summed from a truncated list are now labelled a
   lower bound ("at least 25 GB"), and the note says "largest N" only for
   the lists the agent actually sorts by size before truncating.
2. **Duplicates and old downloads recorded no sizes at all**, so the
   currency was uncomputable. `FileOrganiserAgent._scan` now stores
   `size_mb` per download and `size_mb`/`reclaimable_mb` per duplicate
   group (priced at "delete all but one copy"), and sorts both lists
   before truncating so the cap keeps the biggest wins. Reading is
   tolerant: pre-existing rows say "sizes were not recorded — rescan to
   price it" rather than claiming 0 MB.

- [x] **Tier 3 complete 2026-08-06** — `sysadmin/services/disk_review.py`
      plus a `disk_reviews` table (migration 005, kept separate from
      `project_reviews` so neither migration can disturb the other's
      rows). Facts come from **two tables**: occupancy delta from
      `resource_snapshots`, junk deltas and per-kind reclaim from
      `filesystem_audits` via Tier 2. Four surfaces, mirroring the
      project review: `GET /api/files/review`,
      `POST /api/files/review/generate`, a Monday 05:45 cron (staggered
      after the 05:30 portfolio review so only one generation is in
      flight) and a "Weekly Disk Review" briefing section —
      `_build_review_section` is now parameterised by model, so the
      8-day freshness rule exists once. 55 new tests (1147 → 1202)
- [x] **Rescan happened 2026-08-06 12:05** as a side effect of live
      testing (the test server's file_organiser first-run fired). The
      new audit records sizes, so reclaim now prices at 43.6 GB instead
      of "unrecorded"

**The Session 23 numbers rule needed strengthening, not just obeying.**
First live generation reproduced the failure in a worse form: given a
prompt listing "25.0 GB across 50 directories" *and* an explicit "do not
restate any figure", dria-agent-a-3b restated them and then invented
**"each consuming 5GB"** — a quotient it derived from data the prompt had
supplied. Instructing a model not to use a number it can see is a
request; not showing it one is a constraint. `build_review_prompt` is now
figure-free by construction — sizes become bands ("very large"),
categories become named phrases (`KIND_PHRASES`, because Tier 2 titles
like "Clear 11400 stale downloads" carry counts), occupancy becomes a
direction and a horizon — guarded by a test asserting no digit reaches
the model outside API paths. Re-verified live: zero figures in the
model's prose. It also ignored "no markdown, no headings, no lists" on
both attempts, so `strip_markdown` removes those deterministically.

Still open:

- [ ] The model ignores the 150-word limit (final live narrative ran
      ~350 words). Harmless — it is honest prose with no invented
      figures — but the briefing section is longer than intended.
      Truncating mid-sentence would be worse; a summarise-again pass or
      a smaller `n_predict` would be the fix
- [ ] A single large cleanup flattens the 30-day disk fit for a month
      (usage fell 92.8 % → 67.3 % in late July, so every threshold reads
      `not_growing` and no risk can fire). Inherent to a least-squares
      fit over a fixed window; a shorter secondary window, or fitting
      only since the last sharp drop, would catch a resumption sooner

### Session 25: Service reliability scoring

Nothing scores *services*, yet the history is already in the DB:
`health_checks` streaks, `alerts`, `resource_snapshots`, `agent_runs`.

**Tier 1 complete 2026-08-07.** Tiers 2 and 3 remain — take them as
Sessions 25b and 25c.

- [x] **Tier 1** — `sysadmin/services/reliability.py` (pure, scores a list
      of `HealthPoint`) + `reliability_history.py` (the DB adapter) +
      `GET /api/services/reliability` + `reliability_scores` table
      (migration 008) + a 02:00 daily snapshot cron. 82 new tests
      (1359 → 1441). Live: `venture-assistant` 68, `internet` 77,
      `alfred-frontend` 95, 14 others 100
- [x] Score is `100 − downtime − instability`, both attributable:
      downtime = `round(100 − uptime%)` capped 60, instability = 5 per
      outage **episode** from the first, capped 25. Separate terms
      because they are separate failures — `internet` lost 7.5 % of its
      checks across *three* incidents (−15 instability, −8 downtime)
      while `venture-assistant` lost 27 % in *one* (−27, −5), and retry
      logic survives the second shape but not the first
- [x] The mute waiver landed as specified: `mute: true` **or** a name in
      `notifications.tray.mute_services` (the only way to mark a
      projects.yaml service, which has no `mute` field) → deductions
      computed and reported with `waived: true`, not applied. Required
      modelling `notifications.tray` backend-side for the first time;
      the tray still parses it independently

**Three departures from the plan, each forced by the live data:**

1. **"Mean time between alerts" was uncomputable as specified.** The
   `alerts` table records one row *per failed check*, not per incident:
   one internet outage wrote **123 rows in 7 days**, one
   `venture-assistant` outage wrote **81**. The mean of those measures
   `health_check_interval_seconds`. Incidents now come from consecutive
   non-ok runs in `service_health`, which collapse into episodes by
   construction — and it avoids a join on `details->>'service_name'`,
   the only (unindexed) link `alerts` has to a service.
2. **Restart frequency was dropped.** Nothing on this host records
   restarts: `NRestarts` is a live cumulative counter never sampled into
   the DB, and `agent_runs` records agent executions. Three measured
   metrics beat four where one is invented. Sampling `NRestarts` into
   the systemd check's `details` would make it computable in ~30 days if
   it is ever wanted.
3. **Coverage became a confidence flag, not a deduction.** The estate
   records ~81 % of expected checks (the monitor's own downtime), and
   services added on 2026-08-06 have 1 day of history against a 7-day
   window. Deducting for a gap would charge the service for *this
   application's* downtime, so it lowers `confidence` instead — and
   ordering deliberately ignores confidence, because a thinly-observed
   failing service is still the most interesting row on the page.

**One design call worth re-reading before Tier 3:** the endpoint
recomputes live (~28 ms) rather than serving the stored row, unlike
`/api/units/status`. The table exists for trending only, written at
02:00 — an hour *ahead* of the 03:00 retention purge, so the day's score
is written before the checks behind it can be deleted.

Also surfaced: `venture-chat` and `pgbackrest-backup-timer` are in
config.yaml with **zero health checks ever** (both added 2026-08-07,
backend not yet restarted). They score 100 at low confidence rather than
vanishing — "configured but never checked" is a finding, not an absence.

- [x] **Tier 2 — complete 2026-08-25** (Session 78).
      `sysadmin/monitor/service_recommendations.py` (pure) +
      `GET /api/services/actions` + `ServiceRecommendationInfo` /
      `ServiceActionsResponse` + `ServiceActionsConfig`. 55 new tests
      (2,238 → 2,293). Live on first run: **6 rows, 213 recoverable
      points** across 30 services. Both scoped examples were built as
      written and both conflicts filed rather than decided —
      `SNAG-SVC-001` (the interval advice) and `SNAG-SVC-002` (the timer
      staleness question `stalls.py` already owns for agents)
- [x] Its own `ServiceRecommendationInfo`, **not** a reuse of the
      `RecommendationInfo` deleted the day before by `SNAG-DOCS-002` —
      `FileRecommendationInfo`'s argument for the third time, plus a
      fourth twist the siblings do not have: the currency differs in
      **tense**. Megabytes are freed when the duplicate is deleted;
      reliability points are charged for failures already inside the
      window and lapse only as those age out. So `recoverable_points`
      is a forecast, and every points-bearing `detail` says so in words

**Four things the live data settled that no fixture could**, which is
Session 24's lesson arriving in the fourth advice endpoint:

1. **The confidence gate had to be asymmetric or the endpoint shipped
   empty.** All 30 services were `confidence: low` on the build day — the
   box was off 08-18 → 08-22 and `SNAG-DB-005` killed the daemon a
   further 22 h on 08-23, so a 7-day window held `observed_days: 1.07` at
   `coverage_percent: 15.13`. A `confidence == "high"` gate is the
   obvious implementation and would have been `SNAG-LOG-002`'s
   measured-empty population for the **third** time. What rescues it is
   that a gap is **one-directional**: it can hide an outage and never
   invent one, so `outage`/`flapping`/`timer_failed` are floors and
   survive it, while `check_interval`/`timer_stale` argue from a rate or
   an absence and do not. `log_trends.py` rule 4's `NEW` asymmetry, one
   domain over
2. **Timer staleness needed no clock parsing, and the obvious approach
   would have rebuilt `SNAG-LOG-009`.** `service_health.details['last_run']`
   is systemd's `LastTriggerUSec` rendered as a **local wall clock with a
   zone abbreviation** (`"Tue 2026-08-25 08:00:00 BST"`) — ambiguous
   between zones, and two instants at an autumn fold. The token is
   instead treated as **opaque** and compared only for inequality, with
   `checked_at` as the clock. Live, that derives **24.0 h** for all five
   daily timers, `alfred-evaluate-timer` included despite 15 holes in its
   series
3. **A 7-day window cannot observe a weekly cadence**, so
   `timer_lookback_days` is 30 and deliberately not
   `reliability.window_days`. `estate-manager-review-timer` fires once
   inside 7 days — zero intervals, no cadence — and a staleness rule
   built on the scoring window would be structurally blind to every
   weekly timer on the box. Both weekly timers correctly derive `None`
   today at 2 observed firings each
4. **Two of eight guards passed against deliberately broken code**, and
   both were the memory's own warning. The `waived` test set `muted=True`
   as well, so the muted skip returned before the filter it named was
   reached; the cadence test passed one firing where it claimed to test
   two. Both repaired, plus an invariant test pinning
   `reliability._deductions`' `waived=muted` at its owner, since this
   module leans on it
- [ ] **Tier 3** — weekly system health review: flappiest services, alert
      volume delta, anomaly summary, resource trend direction. Sits beside
      the project review in Monday's briefing and reuses the
      `project_reviews` table design (facts in `stats`, hybrid narrative)

### ✅ Session 26: Service discovery — the unmonitored-unit detector (done 2026-08-07)

**Directly requested 2026-08-05**: hand-registering each new project's
systemd units is tedious and rots silently. The contract this enforces is
written up in [guides/monitorable-project.md](../guides/monitorable-project.md);
this session is its mechanical backstop. Delivered Tiers 1 and 2; there is
deliberately **no Tier 3** (see below).

- [x] `sysadmin/services/units.py` — pure sweep of
      `~/.config/systemd/user/*.{service,timer}` and
      `/etc/systemd/system/*.{service,timer}`, findings **both ways**
- [x] **Unmonitored unit**: maps to a live project, nothing wires it.
      Path first (`WorkingDirectory`/`ExecStart` under the project dir),
      then normalised name-prefix, longest project wins
- [x] **Orphaned unit**: dead `WorkingDirectory`, or a project declared
      `archived`. Ranked `risk`, above everything else — this is not an
      unwatched unit, it is a broken one
- [x] **Host unit** — a *third* category the original plan did not have.
      `pgbackrest-backup` (the estate's only DB backup) and
      `ethernet-optimise` are hand-written, real, unmonitored, and map to
      no project, so the path-match filter would have dropped them
      alongside genuine distro units. They get a **config.yaml
      `services:` snippet**, not a projects.yaml one, because
      projects.yaml models only backend/frontend
- [x] Tier 2 `sysadmin/services/unit_recommendations.py` with
      ready-to-paste snippets, `user: true` for user units, oneshot→timer
      applied
- [x] **Advice-only.** No executor, and both endpoints are GET-only —
      asserted by a test
- [x] `sysadmin/agents/service_discovery.py`, `unit_audits` (migration
      006), `GET /api/units/status` + `GET /api/units/actions`
- [x] 109 new tests — suite 1276 → 1385

**Four things the plan got wrong, all found by running it:**

1. **The `pacman -Qo` ownership query is unnecessary.** Every distro unit
   in `/etc/systemd/system` is a *symlink* into `/usr/lib/systemd/system`
   (that is what `systemctl enable` installs) and every hand-written one
   is a real file. `is_symlink()` is the same test with no subprocess,
   and it works off Arch.
2. **Three of the four named validation targets are orphans, not
   uncovered units.** `~/projects/MCP` and
   `~/Documents/Programming/MCP` no longer exist, so `ticktick-sync`,
   `ticktick-sync-db` and `offline-agents-dashboard` point at dead
   directories — as does `garmin-sync` (`projects/PersonalAssistant`
   moved to `archive/`). They have been failing every start, silently,
   for as long as nothing watched them.
3. **`sportsanalyser-pipeline` was already wired** — in config.yaml, not
   projects.yaml. SportsAnalyser comes back completely clean, which was
   the predicted negative test.
4. **Adding an agent touches four places, not one.** `sysadmin.alerts`
   has a `chk_alert_agent` CHECK constraint enumerating the four known
   agents, so the first live run was rejected by the database *after* the
   scan succeeded (migration 007 widens it, and a test now pins the
   constraint list to `self_monitor.AGENT_NAMES`). The self-monitor's
   own hardcoded `AGENT_NAMES` is the fourth — without it the new agent
   would run entirely unwatched.

**Live result on this box (2026-08-07)**: 44 units seen, 6 distro/template
excluded, 38 scanned → **12 monitored, 8 timers folded into their oneshot
service, 11 orphaned, 0 unmonitored, 7 host**. The counts are exhaustive
by construction (`scanned = monitored + folded + findings`) after the
first draft inferred "monitored" and reported 20 where the truth was 12.

**Zero `unmonitored` findings is the real headline**: every live project's
units are already wired. The estate's actual debt is 11 dead units and 7
unwatched host services — including `pgbackrest-backup`, which nothing
would have noticed going quiet.

**No Tier 3.** Sessions 22 and 24 rank by health-score points and
reclaimable megabytes — both directly measurable. There is no equivalent
currency here, nothing makes two host units meaningfully "twice" one
orphan, and a weekly LLM narrative over 18 findings that change maybe
monthly would be prose about nothing. `UnitRecommendationInfo` carries no
score field at all.

**Pending ops action** (advice, not automation — decide before acting):
11 orphaned units are removable with the exact commands in
`GET /api/units/actions?kind=orphan`, and the 7 host units have
ready-to-paste config.yaml snippets.

### Session 26b: Port-registry reconciliation

**Split out 2026-08-07.** Was folded into Session 26 on 2026-08-06 on the
grounds that "the unit sweep already parses every `ExecStart`, so the
ports are free to extract". Half true: the sweep does parse ExecStart, but
`ss -ltnp` joining, collision detection and the registry migration are a
sitting of their own.

**Decided 2026-08-07 — option (b), and *reversed 2026-08-14*.** The plan
was to move the port allocation into `config.yaml` as structured data,
with the guide's table rendered from it. That decision predates
`estate-manager` (created 2026-08-11) by four days and predates its
conformance audit (2026-08-13) by six. Three of the four checkboxes below
have been overtaken, and re-checking them against the live estate was
most of Session 26b-A.

**What changed, and it inverts item 1.** The guide moved to
`~/projects/estate-manager/docs/guides/monitorable-project.md` on
2026-08-11, and the estate's audit
(`estate_service/audit/checks/ports.py`) now parses that markdown table
as its source of truth — with a guard that *errors* rather than reporting
zero findings if the parse comes back empty. Mirroring the registry into
this repository's `config.yaml` would break that check and would have the
monitor own a cross-repo convention document, against the estate rules.
**Item 1 is dead, not deferred.**

- [x] ~~Move the registry into `config.yaml`~~ — **killed 2026-08-14**,
      see above. The registry stays in estate-manager's markdown and this
      repository never mirrors it
- [x] **Unregistered listener** — **already built**, in estate-manager, as
      the `unclaimed_listener` breach. It has earned its keep: it is how
      syncthing's 8384 got a registry row on 2026-08-13
- [x] **Judge the estate's port findings** (Session 26b-A, 2026-08-14) —
      not on the original list, and it turned out to outrank everything
      that was. The detection above worked and **nothing on this box ever
      said it**: the estate files findings and never alerts, and
      `judge_audit_invariants` deliberately judged only whether the audit
      *ran*. `judge_audit_findings` now judges the `ports` check per
      finding. See CLAUDE.md for the five rules
- [ ] **Contended default** — a project on a well-known default (8080,
      3000, 5000, 8888, 9000). **Delegated to estate-manager 2026-08-14**
      (`SNAG-ESTATE-004` here): it is pure conformance against a rule
      written in *their* guide ("Never take a tool's default port"), it
      needs no privileges, and detecting it is *filing a finding* rather
      than alerting — squarely the audit's remit, beside
      `unclaimed_listener` in the check that already exists
- [ ] **Collision / near-miss** — two registry rows claiming one port, or
      a configured port already held by a different cgroup. **The one
      genuinely-ours remainder, and now Session 26c.** The estate is
      *structurally* blocked from the interesting half: its
      `live_listeners()` runs `ss -H -tln` deliberately **without** `-p`
      ("process names need privileges for other users' sockets"), so it
      can say a port is taken and never by whom. Duplicate registry rows
      also slip through it — `claimed_ports` is a `set`

### ✅ Session 26c: Port collision detection (done 2026-08-15)

**Done. `sysadmin/units/ports.py` ships four comparisons in two
families**, the alert half with zero rows on this box and the advice half
with zero too — which is the honest result and was the expected one.
Suite **1701 passed** (from 1653), ruff and mypy clean, **no migration**
(the block rides in `unit_audits.findings['ports']`).

- [x] `ss -H -ltnp` → `/proc/<pid>/cgroup`, unprivileged, scope from the
      path. 31 listeners, **24 attributed**, 12 units holding a port in
      the registry's range. Blank only for root-owned and containerised
      sockets (5432, 1883, 631, 139/445, 8601)
- [x] **`wrong_unit`** — a `services.yaml` entry whose declared
      `systemd.unit` does not hold the `port:` it checks. 11 declared
      pairs on this box, **all 11 agree**; the pair has been in the file
      since Session 35 and had never been checked, so an `http` probe
      could be green against a process the tray's restart button would
      never touch
- [x] **`port_shared`** — two distinct units on one port. Dual-stack
      dedup on `(port, pid)` first, without which this fires on every v4
      +v6 server on the box
- [x] **`duplicate_claim`** — two registry rows claiming one port. This
      is the one the estate cannot see: `claimed_ports` is a `set`, so a
      shared parser would have to return what their check discards
- [x] **`wrong_project`** — the table's project against the one the
      sweep matched the holding unit to, through an alias map (directory
      name *and* manifest id, which differ for a third of the repos).
      Found one thing on a clean box: 8500's row says `sysadmin-service`,
      which is neither. Recorded as evidence, filed as `SNAG-ESTATE-005`
      for its owner
- [x] **One alert row per contested port**, port in the title, dedup +
      resolve on the judged set, no escalation ladder. Verified live in a
      rolled-back transaction: raise → hold → resolve, **0 residue**
- [x] **Advice for the document half**, ranked last in `KIND_ORDER` —
      the only kind where nothing here is broken or unwatched
- [x] **`SNAG-UNITS-001` folded in**: the snippet emits `kind: http` with
      a real url and port when the unit holds exactly one audited port.
      Population is empty today (all 12 are `monitored`); the
      counterfactual reproduces the hand-written entry exactly
- [x] The estate judge's port breaches carry the holder in `details`,
      read from the stored sweep rather than a second `ss` call
- [x] Conformance tests against estate-manager's checkout: audited
      ranges, the document path, and that their `live_listeners()` still
      runs `ss` without `-p` — if it ever does not, this module is a
      duplicate and should go

**Original entry, kept because its route survived contact.**

**Nothing on this box has ever collided** — every listening
port appears exactly once, and 8080 is the only contended default and is
already annotated in the registry. That is the honest argument for it
being a session of its own rather than folded into 26b-A, which gave
voice to a detector that has already found real things.

**The route is decided and measured** (2026-08-14), because the estate's
premise does not hold on this side of the fence:

- `ss -ltnp` **unprivileged, as `gaddi`, attributes every
  registry-relevant port** — 8080, 8300, 8400, 8500, 8600 and the rest
  all come back with a pid. The estate's "needs privileges" is true only
  for *other users'* sockets, and almost everything in the registry is
  our own process. Blank for root-owned listeners: 5432, 1883, 631,
  139/445, and **8601** (the SearXNG container, podman)
- `/proc/<pid>/cgroup` then names the unit **with scope in the path** —
  `…/user@1000.service/app.slice/alfred-backend.service` against
  `/system.slice/…`. That is the scope-aware identity the old last
  checkbox asked for, for free
- Rejected: `/proc/net/tcp` + inode→fd scan (same permission wall, ~50
  lines to reproduce what `ss` prints); `systemctl show -p MainPID` per
  unit (a subprocess each, misses forked workers, and **requires knowing
  the scope before you ask** — `sysadmin.service` returns `MainPID=0` on
  the user bus because it is a system unit); `ExecStart` alone, which the
  original entry already rejected and 8601 proves right
- **It cannot live in `sysadmin/units/scan.py`** — that module's
  no-subprocess promise is load-bearing and was re-verified in Session
  46. A sibling module

*Corrected 2026-08-14: the old last checkbox said "reuse
`sysadmin/services/units.py`", which has not existed since Session 35's
module split — it is `sysadmin/units/scan.py`. Same stale-path defect as
commit `ce71bef`.*

### ✅ Session 28: Roadmap findings + the estate board (done 2026-08-06)

Directly requested: surface "what needs doing / where is this project at"
in Alfred, without Alfred ever reading a directory. Delivered:

- [x] Global **SessionEnd hook** (`~/.claude/hooks/generate-handoff.sh`,
      wired in `~/.claude/settings.json`) writes `docs/sessions/handoff.md`
      in whatever repo the session ran in. Replaces the instruction in
      CLAUDE.md that postflight "generates handoff" — it never did, which
      is why `docs/sessions/` sat empty for months.
      **Superseded 2026-08-10 by Session 37**: right that an instruction is
      a request and a hook is executed, wrong about what follows. SessionEnd
      cannot block, so the file it guaranteed contained only what `git`
      already knew — and by always existing, it removed the signal that a
      real handoff was missing
- [x] `sysadmin/services/roadmap.py` — pure parser for handoff / tasks /
      snag documents, resolving a **next action** (handoff → tasks → git)
- [x] `findings["roadmap"]` recorded by the organiser; **no score
      deduction** — that would move every active project at once and could
      trip alert thresholds as a side effect
- [x] `kind: "roadmap"` recommendations at 0 points (the `no_remote`
      precedent), waived for dormant/archived
- [x] `GET /api/projects/board` + `"Pick This Up"` briefing section
- [x] [guides/alfred-projects-page.md](../guides/alfred-projects-page.md)
      specs the consumer side

48 new tests (1202 → 1250). Two live-only findings, both fixed: Alfred
keeps its handoff at `docs/roadmap/handoff.md` not `docs/sessions/`, and
its tasks file uses a status **table** rather than checkboxes — so
`open_tasks` now reports `None` ("not measurable") rather than `0` for
the busiest project on the box.

**Same-day follow-up (2026-08-06), from the first real use.** The user
looked for ImbaBots — an ongoing project — and concluded it had not been
flagged. It had: `top_action: "Write a README.md"` plus a roadmap item.
Two presentation faults hid it, both fixed:

- [x] **The board defaulted to neglect order**, so an actively-developed
      project sat at row 12 of 18 while abandoned ones led. `?sort=` now
      takes `activity` (default — the working view, recently touched
      first) or `neglect` (the weekly triage view). ImbaBots is now row 2
- [x] **`/api/projects/actions` is saturated**: 11 projects share one
      `no_remote` risk, risk sorts first, and roadmap advice is worth 0
      points, so the default limit of 10 showed nothing but "Add a git
      remote" — 68 available, 10 returned, no indication of *what kind*
      was hidden. Response now carries `dropped_by_kind`
- [x] Roadmap + hygiene written into Contract 1 of
      [guides/monitorable-project.md](../guides/monitorable-project.md),
      waived for dormant/archived

**Open decision — should missing roadmap docs cost health-score points?**
Currently no (findings recorded, advice at 0 points). Deducting would
move every active project's score at once and could fire alerts as a side
effect. Worth taking deliberately once the status triage below has run.

**Estate triage, ranked (not started).** 26 repos, 4 genuinely active;
the dozen showing `days=1` are the `~/projects` reorganisation commit,
not work. In order of value: (1) declare `status:` for ~16 repos in
projects.yaml — one file, ~20 min, and the board drops from 18 rows to 4;
(2) the **11 repos with no git remote**, `sysadmin_assistant` among them;
(3) give this repo a README and a remote — the monitor is currently the
worst-scoring live project it monitors; (4) roadmap docs for whatever
survives (1) as active. An agent fan-out was considered and rejected:
after triage there are ~4 repos left, and the work that remains is
judgement, not volume.

**Follow-up worth taking:** the git fallback is weak where the
`~/projects` reorganisation touched every repo — a dozen projects report
`days_since_commit=1` and a next action of "WIP snapshot before
~/projects reorganisation", which is bulk housekeeping, not work. Either
ignore known bulk-commit subjects, or weight staleness by commits that
touched source rather than by the last commit date.

### ✅ Session 27: Log aggregator tiers — complete 2026-08-24 (all three)

Thinnest of the four, and it was deliberately coupled to `SNAG-AGENT-002`
because error **signature fingerprinting** was the fix for both. **That
half is done** and the session is now only the tiers — re-scoped
2026-08-17 by Session 58, which is also when the snag was closed on
paper.

- [x] Fix [SNAG-AGENT-002](snag_list.md) — group by unit + normalised
      message signature within a poll, raise one alert carrying an
      occurrence count (mirroring Session 16's "X flapped N×").
      **Shipped 2026-08-12** as `sysadmin/monitor/log_signature.py` under
      `SNAG-AGENT-005`, against 598,091 rows. Measured 2026-08-17: eight
      unresolved rows on the whole box, five of them signatures, each
      carrying `occurrences` and `last_seen_at`. Everything below now has
      the grouping it was scoped to need and did not have
- [x] **Tier 1** — `GET /api/logs/trends`, computed live (88 ms) off a
      pure `sysadmin/monitor/log_trends.py`. **The signature is applied in
      Python over SQL-grouped rows**, never re-implemented in
      `regexp_replace`: measured 2026-08-17, 626,906 rows collapse to
      **44 distinct messages in 91 ms**, so the honest version is
      affordable — and a second normaliser would drift from the identity
      the alert family is keyed on
- [x] **"New" is a first sighting, not an empty previous window.** The
      obvious `previous == 0` test was refuted by the live table in one
      row: the Bluetooth firmware signature reads `current=39,919,
      previous=0` today and has been storming since 2026-07-15, so it
      would have headed "new errors this week" on its fifth outbreak. It
      comes out `returned`; the 8 genuinely-new signatures are a mosquitto
      core dump, `estate-broker-provision` failing, and
      `Bluetooth: hciN: failed to reset (-N)` — a *distinct* signature the
      firmware storm would have masked under a source-level key
- [x] **A gap lowers confidence and never becomes a trend** —
      `reliability.py`'s rule 4 reused. But **truncation is the signal and
      poll count only the proxy**, which is the opposite of the obvious
      ordering: a missed poll is caught up by the journal cursor, so data
      is lost only when a catch-up read hits `max_entries_per_read`. Live:
      118 truncated runs across the window, so the real report is
      `confidence: low` at 88 % poll coverage
- [x] **Tier 2** — `GET /api/logs/actions`, ranked `new_signature` →
      `surge` → `noise`, kind before volume with no invented number
      merging them. 13 recommendations on live data
- [x] **`known_noise` built rather than named** — Tier 2's scoped example
      ("add to known-noise or fix it") named a mechanism that did not
      exist, which is Session 48's defect in advance. It is
      `agents.log_aggregator.known_noise`, keyed on **(source, signature)**
      because `Failed with result 'exit-code'.` is logged by six services
      here, and it **quietens rather than suppresses** (`info`, below
      `tray.notify_min_severity`) per Session 57
- [x] **The quietening reaches a row that is already open**, which
      `SNAG-ESTATE-010` says nothing does. Session 39's ban on in-place
      severity changes is **asymmetric** and that is what rescues it: an
      escalation must be *heard*, so an in-place bump keeps a fingerprint
      the tray has suppressed; a quietening must be *silenced*, and
      `{severity}:{title}` becoming `info:…` is dropped by `_consider`
      before it notifies. One-directional by construction
- [x] **Three of the emitted commands did not work, and only a live run
      said so** — `journalctl -u kernel` (the kernel is not a unit), no
      `--user` for the **7 of 14** sources that are user units (measured:
      2,170 lines with the flag, 1 without), and a `--grep` on the
      normalised signature, whose `N` placeholders match no real line.
      Fixed and re-verified by executing them
- [x] **Tier 3** — `GET /api/logs/review`, `POST /api/logs/review/generate`,
      a Monday 05:15 job and a "Weekly Log Review" briefing section, off a
      new `log_reviews` table (migration 013). **Done 2026-08-24 by
      Session 69, and this row's own premise was false.** It said the
      overnight LLM summary "already runs in the briefing"; measured,
      `LogAggregatorAgent.summarise()` had **no caller anywhere** — not in
      production, the scheduler or a test — `log_summaries` held **one
      row** dated 2026-07-24, and the briefing's 12-hour freshness window
      meant the section had been absent from every briefing for 25 days.
      So "extend rather than duplicate" was not available: there was
      nothing running to extend
- [x] **The dead producer is the argument against extending it.** Its one
      row covered **29 seconds** (13:16:47 → 13:17:16), because its window
      was the newest 100 rows and the box was mid-Bluetooth-storm, and it
      reported `entry_count = error_count = 100` — both the query's own
      `LIMIT`. Handed a hundred raw timestamped lines it answered "1.
      Repeated failures 2. Pattern of failures" plus the invented rate
      "every 1-2 seconds". There is no edit that makes that a Tier 3,
      because the direction of flow *is* the design. `summarise()`,
      `SUMMARISE_PROMPT_SYSTEM`, `summarise_with_llm` and the two
      `/api/logs/summary*` routes are gone; `log_summaries` is left
      **frozen** rather than dropped, the treatment ADR-0005 gave
      `project_snapshots` — *dropped by migration 014 on 2026-08-24
      (Session 74); the routes went on answering `200` until Session 75,
      which is `SNAG-LOG-011`*
- [x] **Built on the recommendations, not the trend** — Session 23's
      choice, for a sharper reason here: until 2026-08-17 one mosquitto
      crash was **six** recommendations, so a narrative written then would
      have described one crash six times. That is what three sittings of
      deferral were waiting for, and it is why this tier could not have
      been built before Session 68
- [x] **Rule 3, which the other two Tier 3s could not have found: the
      normalised signature may go into the prompt verbatim, because
      normalisation is the operation that makes it figure-free.**
      `signature()` maps every digit run to `N` — measured 2026-08-18,
      **0 of 46 live signatures contain a digit**. The disk review had to
      invent `KIND_PHRASES` to keep numbers away from the model; here the
      safe form already existed and is the same string the reader matches
      against `GET /api/logs/actions`. Still filtered through
      `figure_free`, because `_HEX` produces `0xN` and that `0` is a
      digit by construction — empty population today, reachable the
      moment a driver logs an address
- [x] **Two band edges borrowed, one invented and saying so.**
      `RATIO_MIN_COUNT` (10) and `NOISE_MIN_OCCURRENCES` (100) are
      already Tier 1's and Tier 2's own thresholds, so the narrative's
      sense of "loud" cannot drift from the ranking's. `STORM_OCCURRENCES`
      (10,000) is invented: the live counts are `1, 1, 2, 4, 6, 7, 11,
      16, 26, 39885, 39885` — bimodal with a **1,534× gap** and nothing
      inside it, so every value between 27 and 39,884 gives identical
      output, which makes it safe rather than derived
- [x] **`direction_phrase` is asymmetric, and that is the new rule.**
      Truncation is one-directional — it drops entries, so it can only
      make a count too low — so a *rise* is trustworthy at any
      confidence and a *fall* is not, because a source that went quiet
      and a source whose reads truncated produce the same smaller
      number. Session 63 used one-directionality to justify a threshold
      on the input; this decides what the narrative may claim on the way
      out. Verified reaching the reader: the live generation wrote "the
      kernel service was reported less frequently, which could be due to
      the reading rather than the actual fault"
- [x] **Two defects only the live LLM run found, both fixed and
      re-verified live.** The model **invented `kernel.service`** —
      reproducing in prose the exact `journalctl -u kernel` error Tier 2
      removed from the emitted commands — and it nominated
      `alfred-backend.service` and `kernel` for "look at first" although
      neither had a recommendation, having merged the faults list with
      the movement list. Labelling the two lists `OUTSTANDING FAULTS` and
      `VOLUME CHANGES` and scoping each instruction to one fixed both.
      Every fixture was green throughout
- [x] **The overnight block is now a live count, and that is what closes
      the mechanism that hid the defect.** `_gather_logs` counted no
      rows; it read the newest `log_summaries` row, and `_logs_clause`
      returns `None` for a missing block — so a quiet night and a dead
      producer rendered *identically*, as nothing at all. It now counts
      `log_entries` over the briefing's own period (via a `_period_start`
      extracted so the count and the declared window cannot disagree),
      is **unconditional**, and distinguishes three outcomes: no entries
      at all is a statement about the aggregator, not about the box
- [x] **2101 tests green** (+34), ruff and mypy clean. Six guards
      falsified deliberately and **two of them failed to fail**: the band
      test asserted `NOISE_MIN_OCCURRENCES in thresholds`, which a
      hardcoded `100` satisfies, and the prompt-label test asserted
      `label in prompt`, which the instructions satisfy by quoting
      themselves. Replaced by an AST sweep and a facts-half scope
      respectively, then re-falsified

---

## Momentum sessions (29–32) — moving projects along, not monitoring them

Requested 2026-08-06. Sessions 24–27 make the service a more complete
*monitor*; these four are the other axis — changing what happens on a given
morning. Everything built so far reports; nothing acts.

**The design constraint they share:** each one must make the output
*shorter*. The obvious way to add features here is more surfaces and longer
lists, and that is the failure mode — 400 TODOs and 51 routes have not moved
a project yet. Success is measured in what stops being shown.

Take 29 first: 30 consumes its ranking, and 31/32 are more useful once one
project at a time is the unit.

### Session 29: The one-thing endpoint — done 2026-08-10

- [x] `GET /api/projects/next` — **one** project, one action, one sentence
      of why it is that one. Not a filtered board: a different object, with
      a `reason` field the consumer must render. `NextProjectInfo` carries
      four fields the board has no use for (`days_unchanged`,
      `unchanged_since`, `unchanged_scans`, `at_window_edge`), which is what
      stops it reading as `/board?limit=1`
- [x] **The open design question, and it is the whole feature: what decides
      when two projects both have a live next action?** Decided 2026-08-10:
      **stuckness** — how long the stated next action has stood unchanged —
      with the most recently committed project breaking a tie. Rejected:
      longest-idle (ranks by guilt), nearest-to-finishing (reads
      `done_tasks`/`open_tasks`, which are `None` for three of five active
      projects, so it would be blind to most of the population while looking
      authoritative), smallest-next-step (unmeasurable — nothing records the
      size of a step and every proxy is invented)
- [x] **The unit is elapsed days, not scans.** The cadence is irregular by
      construction (6-hourly until Session 35, daily from the timer since,
      plus manual scans — two live scans 17 minutes apart on 2026-08-08), so
      a run length in scans ranks by how often the organiser happened to
      run. Run length in observations is reported as evidence, not ranked on
- [x] Honour `?exclude=` so a deferred suggestion can be skipped without
      re-rolling the same answer. Repeatable; exclusions are counted in
      `skipped` and echoed in `excluded`, so a caller that excluded its way
      to an empty answer can tell that from an estate with no work in it
- [x] Contract-pinned; feeds alfred-glance, whose whole premise is glance
      then act
- [x] Eligibility: active, `next_action_source` in (`handoff`, `tasks`), and
      not a handoff stating there is nothing queued. `roadmap.looks_like_no_action`
      catches the two live cases ("No unchecked task found — set one before
      the next session"); conservative like `is_placeholder`, since a false
      positive hides real work
- [x] Empty is `200` with `project: null` and a reason, never `404` — a 404
      would collapse "every project is up to date" into "no scan has run"
- [x] Deliberately **not** in scope: a resume/deep-link command. Considered
      and dropped 2026-08-06

**Left for a later session** (found while building, deliberately not fixed):

- [ ] The eligible population is **2 of 23** fresh projects — 20 inactive,
      1 with no stated action, 2 stating there is nothing queued. The
      endpoint is correct and the estate is the constraint; whether
      `says_no_action` should itself become a nudge ("write a next action")
      belongs with Session 31, not here

### Session 30: Next action → an Alfred work item — declined by the consumer 2026-08-11

**Not blocked, not deferred: refused, by the repo that would build it.**
Alfred accepted [ADR-0064][adr64] on 2026-08-07 — three days *before*
Session 29 shipped — declining the whole projects-page arc for v1 and
putting it behind two named triggers. This row said "nothing here blocks
it beyond Session 29" and was wrong when it was written; the block was
never on this side.

The decline is not a rejection of the endpoints. ADR-0064 §1 finds the
estate's momentum data **already ships**, as the daily digest's
`Pick This Up` section, rendered with this guide's own honesty treatment.
A second surface over the same data is the failure mode ADR-0063 was
written to avoid — the ADR names it "a surface that exists because its
data exists".

**The triggers, and where they stood when this was checked (2026-08-11):**

| Trigger | Fires at | Live |
|---|---|---|
| (a) Stall returns | `stalled_count ≥ 2` on `?sort=neglect`, sustained across two consecutive weekly reads | **0** |
| (b) Estate outgrows the five-row cap | `count ≥ 12` active | **5** |

Neither is close, and (b) moved the wrong way: 6 active when the ADR was
written, 5 now. The board carries 3 stalled projects among the 20
inactive ones, which the trigger deliberately does not count — declaring
a project dormant *was* the decision, so it cannot also be a stall.

- [ ] **Do not build this here or in Alfred until a trigger fires.** Both
      are one `curl` against an endpoint that already ships, which is the
      point of writing them as numbers:
      `curl -s 'localhost:8500/api/projects/board?sort=neglect' | jq '{count, stalled_count}'`
- [ ] When one does fire, ADR-0064 §2 says the build instruction is
      [guides/alfred-projects-page.md](../guides/alfred-projects-page.md)
      as written — "good and should be followed rather than redesigned".
      The `sysadmin_name` column on `trackables.Project` belongs to *that*
      triggered ADR, not to this row and not to ADR-0064
- [ ] The boundary survives either way and is now recorded on both sides:
      sysadmin stays read-only, the write happens in Alfred pulling, and
      the board is never written into `trackables.projects` — a curated
      list of life projects against every directory on disk carrying a
      marker (§3 here, ADR-0064 §3 there)

**One premise of the decline has since expired, and it fires nothing.**
ADR-0064 §3 declines to design against `GET /api/projects/next` because
"it returns 404 today" and its ranking policy is "undecided by its own
author". Session 29 shipped it on 2026-08-10: it returns 200, and the
ranking (stuckness in days, tie-broken by the most recent commit) is
decided, documented and argued. That removes a *stated reason* without
touching either *trigger*, and the distinction is the whole discipline —
a deferral with countable triggers is re-opened by the count, not by an
argument. Recorded here so the next reader of ADR-0064 does not have to
re-derive that the endpoint now exists.

[adr64]: file:///home/gaddi/projects/Alfred/docs/adr/0064-estate-board-consumption.md

### Session 31: Idle nudges — a commitment, not hygiene ✅ 2026-08-11

- [x] Distinct from the staleness score, which asks "is this repo tidy".
      This asks "**you have a stated next action and have not touched it in
      N days**" — a broken commitment, not a dirty directory. The score is
      never consulted: `venture-assistant` scores 100 and can still be sat
      on the same action for a fortnight
- [x] Rides plumbing that already exists: severity thresholds, DND windows,
      desktop notifications, the tray. No new delivery path — and **no new
      endpoint**, so the daemon needs no restart; the organiser is a oneshot
      timer that picks this up on its next run
- [x] Only for `active` projects with a non-null `next_action`. Eligibility
      was **not re-implemented** — it was extracted out of
      `GET /api/projects/next` into `next_action.eligible_candidates`, which
      both now call. Two copies of "what counts as a commitment" drift in
      the direction nobody notices: the endpoint stops offering a project
      while the nudge goes on reminding you about it
- [x] Threshold per project (`idle_nudge_days` in `.project.yaml`, beside
      `alert_threshold`), defaulting globally to **7 days**

**Decisions taken, with what was rejected:**

- **7 days, quiet; 14 days, loud.** The live estate turns its next actions
  over in 1–4 days, so 7 fires on nothing today and that is the intended
  shape — the threshold is "long enough that standing still is a fact".
  5 was rejected as within normal turnover; 14-as-first-rung was rejected
  because a feature that can never be observed firing cannot be trusted
- **The `info` rung is silent on this host and that is deliberate**, but
  not for the reason first written down: the gate is
  `tray.notify_min_severity`, **not** `notifications.desktop.min_severity`,
  which is parsed by `DesktopNotificationsConfig` and read by nothing.
  Filed as `SNAG-CFG-001`; three comments named the wrong knob before the
  grep was run
- **Never `critical`.** Criticals break through DND by configuration
  (`notifications.dnd.allow_critical: true`), and waking someone at 02:00
  about a roadmap item is how a monitor gets muted wholesale
- **Escalation is a gap, not a multiplier.** A project that relaxes its own
  threshold to 21 days escalates at 28, not 42. The per-project knob moves
  when the clock starts, not how patient the escalation is
- **Raised once per open nudge, not once per scan.** `BaseAgent.raise_alert`
  inserts unconditionally — this is the mechanism behind the 1,664-row
  pile-up of `SNAG-PROJ-004` — and the organiser runs daily, so re-raising
  would write one row per day per stuck project. Escalation **resolves the
  quiet row and raises a loud one** rather than updating severity in place:
  the tray fingerprints on `"{severity}:{title}"`, so an in-place change
  keeps a fingerprint it has already suppressed and the escalation is never
  spoken
- **Resolution is set-based**, the inverse question `_resolve_recovered`
  already asks: the action moved, the project went dormant, the handoff was
  cleared, the repository was deleted — only the first is observable as an
  event, and a per-project loop leaves the rest open forever

**Verified 2026-08-11**, not assumed: a live organiser run over 25
repositories reported `nudges: {raised: 0, escalated: 0, resolved: 0}` —
correct, since all three eligible projects changed their next action that
morning. Because a clean run proves only that nothing crashed, the ladder
was then run over the **real** historical series for `sysadmin_assistant`
(the "Session 24: File organiser tiers" action, 9 scans across 2 days):
`streak_days` folded it to one run of 2 days, and the ladder produced
`info` / `warning` / no-nudge at the thresholds it should. The 9-scans-to-
2-days ratio is the argument for days over scans, live.

### Session 32: Start-versus-finish accounting ✅ (2026-08-11)

`GET /api/projects/momentum` ships. The reasoning lives in
[momentum.py](../../sysadmin/projects/momentum.py); what follows is what
was decided rather than what was built.

- [x] **The blocker named the wrong evidence and was already gone.** The
      recorded fix was "an append-only `docs/sessions/log.jsonl` written
      by the hook, **or** sysadmin recording handoff-date transitions per
      scan" — and the second had been true since 2026-08-06. Session 28
      writes `handoff_age_days` on every scan, so
      `scanned_at − handoff_age_days` reconstructs the date a handoff was
      written and a *change* in it between two scans is an observed
      session. The log existed sideways, in JSONB, and no new hook,
      writer or migration was needed
- [x] **A landing is matched by date window, not at the transition
      scan.** The obvious rule — "had a commit been made by the time the
      scanner saw the new handoff?" — was written first and refuted by
      the live series within the hour: the scan at `2026-08-10 09:06` saw
      this repository's new handoff while `last_commit_at` still read
      2026-08-08, because the handoff is written *before* the work is
      committed. That day's six commits arrived afterwards and a
      productive day was reported as dropped. Scan timing was deciding
      the answer, and no fixture with a tidy cadence would have shown it.
      A commit dated in `[session_date, next_session_date)` is now that
      session's output. Pinned by
      `test_a_commit_after_the_scan_still_counts_as_landed`
- [x] **Both landings are reported**, because they are different
      failures. `dropped_code` is a session that shipped no code;
      `dropped` is one that shipped *nothing at all*; `docs_only` is the
      gap. A session that wrote up what it decided is a materially better
      outcome than silence and must not be summed with it. No scanner
      change was needed for the second count: `findings['git']` is
      written only when a housekeeping commit was skipped (77 rows of
      3,635), and its absence means the newest commit *is* the newest
      code commit — so the fallback to `last_commit_at` is exact
- [x] **The observed period is the dated scans, not every scan.** Caught
      on the live run: this repo holds 198 snapshots back to 2026-05-13,
      of which 22 carry a roadmap block. Reporting the series as three
      months long invited dividing five sessions by ninety days
- [x] `handoff_date_source` is now recorded for the *chosen* handoff, not
      only the also-rans. An undated handoff falls back to mtime and a
      clone or checkout rewrites mtime, which would present a
      `git checkout` as a morning's work. Prospective only — every
      session observed before today reads `unverified`, and the count is
      hedged in the `reason` sentence rather than quietly asserted
- [x] The population is `ACTIVELY_SCORED` (`active` + `undeclared`),
      **borrowed** from the agent rather than restated — deliberately
      wider than `/api/projects/next`, which additionally requires a
      stated next action. A commitment needs someone to have written one
      down; a session that shipped nothing is a fact about a repository
      whether or not it has a plan
- [x] Couples to Session 31 as predicted — both answer "you said you
      would and didn't", from elapsed time and from attempts made

**Verified against the live estate, and it disagrees with the health
scores.** `alfred-glance` opened 2 sessions and landed nothing (last code
commit 2026-08-03); `venture-assistant` 3 sessions, 1 landed; this repo
5 sessions, 4 landed — the single drop is 2026-08-09, and `git log`
confirms zero commits that day. `Alfred` is 4 of 4. Suite 1776 → 1824.

### Follow-ups this session opened

- [ ] [SNAG-PROJ-013](snag_list.md) — ImbaBots' `HANDOFF.md` heading
      carries no ISO date, so the Stop hook will block its next
      code-changing session. **Deliberately left for that session to
      fix**: the hook demands *today's* date, so dating it on a day
      nobody worked there writes a handoff for a session that did not
      happen — a phantom transition, and therefore a phantom session in
      `/api/projects/momentum`. Close this when a dated ImbaBots handoff
      appears. **The snag was also filed with the wrong diagnosis
      first** ("commits without moving its handoff date") and corrected
      the same day by opening the repository: ImbaBots' last session
      updated its handoff in the same commit as the code, and its 0 is
      the baseline rule working, not a failure
- [ ] Re-read `/api/projects/momentum` after the next organiser run, when
      `handoff_date_source` starts arriving. Every session is currently
      `unverified` by absence of the field, which is honest but makes the
      hedge unconditional and therefore unreadable
- [ ] No consumer renders this yet. It is a `GET` with a `reason`
      sentence built for a one-line surface; alfred-glance is the
      obvious reader, and Session 30's fate says to ask before assuming

### Session 33: Seam drift detection

Requested 2026-08-06. Found by checking rather than assuming: Alfred's
consumer fixture was **two sections behind** the same day it was captured,
with its contract test green the whole time.

- [ ] **Producer publishes the sample.** A test here regenerates
      `docs/contracts/briefing_preview.sample.json` from
      `generate_briefing_data` and fails when it differs from the committed
      copy — so the sample cannot silently go stale, the same trick the
      schema-drift guard already uses for migrations
- [ ] **Detect a stale consumer.** sysadmin can read Alfred's fixture
      (`backend/tests/fixtures/briefing_producers/sysadmin_preview.json` —
      same disk) and raise a finding when its section set is a subset of
      what this service now serves. This catches drift *without waiting for
      anyone to commit*, which is the case that actually bites
- [ ] Consumer registry in config: which repo, which fixture path, which
      producer endpoint. Two entries today; the point is that adding a
      third consumer is a config line, not code
- [ ] **Do not** build a shared contract package or a monorepo. Three repos
      in three languages, two seams — a shared library would couple three
      release cycles to solve what two files and a test already cover.
      Considered and rejected 2026-08-06
- [ ] Write the additive-only rule into
      [guides/monitorable-project.md](../guides/monitorable-project.md):
      sections and fields are added, never renumbered or removed; consumers
      render what arrives and ignore what they do not recognise. That
      tolerance is why the briefing went 5 → 7 sections with no breakage,
      and it does more work than any schema tooling

---

## Project-side consolidation (34–36) — from the 2026-08-07 capability audit

Consolidated from one pass over the project side and the design decisions taken
alongside it. **The ordering was not negotiable**: every defect in Session 34
corrupts output Alfred already consumes, and building the briefing envelope
(36) on top of wrong data just makes the wrong data better formatted. 35 is the
structural work 36 needs; 34 blocked both.

**34 and 35 are both done** (35 on 2026-08-08, 34 on 2026-08-10 — taken out of
order because 35 was already in flight). **36 is now unblocked**, and is the
only remaining member of this group.

### Session 34: Defect clearance — the project side ✅ (2026-08-10)

All twelve defects fixed, tested and verified against the live estate.
Write-ups archived under "Fixed Issues" in [snag_list.md](snag_list.md).

- [x] [SNAG-PROJ-001](snag_list.md) + [SNAG-PROJ-002](snag_list.md) — the
      cutoff moved into a new `sysadmin/projects/snapshots.py`. The audit said
      eight surfaces; grep found **nine** open-coded copies of the join across
      three packages, which is the tell that counting them by hand was never
      going to be reliable. `tests/test_project_snapshots_query.py` now fails
      if any module re-implements it
- [x] [SNAG-PROJ-003](snag_list.md) + [SNAG-PROJ-004](snag_list.md) —
      `_resolve_recovered` closes every health alert a scan did not re-raise,
      and migration 010 resolved the backlog. **1,664 rows resolved live**,
      matching the audit's count exactly
- [x] [SNAG-PROJ-005](snag_list.md) — the project review's prompt is
      figure-free by construction: scores → bands, deltas → directions,
      recommendation titles → `kind` phrases. Guard test ported from the disk
      review
- [x] [SNAG-PROJ-007](snag_list.md), [008](snag_list.md), [009](snag_list.md) —
      `*.md` dropped from the scan, `grep -w` for word boundaries, a real
      project-total cap that records its own truncation, and the
      recommendation names the markers it charged for
- [x] [SNAG-PROJ-006](snag_list.md), [010](snag_list.md), [011](snag_list.md),
      [012](snag_list.md) — `/stale` implements `days` against last-commit age
      with a `StaleProjectsResponse` contract; `project_reviews`,
      `disk_reviews` **and `unit_audits`** added to retention (migration 011);
      the `archived` description corrected in three places and its absolute
      alert suppression pinned by a test

**Follow-up this session revealed** — not part of the twelve:

**[SNAG-DB-001](snag_list.md) — the un-applied migration that blacked out
monitoring for 39 hours.** Fixed by applying it; the three detection gaps that
let it run that long are not, and are the real work. In order of value:

- [x] **Fail startup on a schema-revision mismatch** — `sysadmin/core/schema_guard.py`,
      called from the lifespan straight after `verify_connection` and
      deliberately **not** wrapped in a `try`. The head comes from alembic's own
      `ScriptDirectory`, never a regex over `alembic/versions/*.py`: a second
      implementation of the revision graph would drift from the very command it
      exists to measure against. `alembic_version` is read schema-qualified,
      because the `projects` database holds another application's copy in
      `public` and resolving through `search_path` could compare this code
      against a stranger's revision and pass. Three ways of not-knowing all fail
      closed with their own message — unreadable scripts, a branched history
      (two heads, which `alembic upgrade head` refuses), and a database never
      migrated. Verified live 2026-08-13: passes at 011/011, and refuses a
      forced mismatch naming both revisions and the remedy
- [x] **Isolate the per-service health write** — one `session.begin_nested()`
      per service in `SysAdminAgent._execute`. The savepoint works *because
      leaving the block flushes*: `session.add` never talks to the database, so
      before this the rejection surfaced at the single commit ending the run, by
      which point the bad row could not be told from the eighteen good ones. A
      rejected service is recorded as `status="error"` with
      `details['source'] = 'write_isolation'` and its attempted status, because
      absence of a row is what made the 39-hour hole invisible; it is also added
      to `unhealthy`, so `_resolve_recovered` cannot announce a recovery nobody
      observed. `details['write_failures']` **names** the services. Documented
      limit: a savepoint rolls back SQL and not side effects — an auto-restart
      already issued stands, and the in-memory streak counters stay bumped
- [x] **Alert on consecutive agent-run failures** — `sysadmin/monitor/failures.py`,
      a **sibling of `stalls.py`, not an extension of it**. "Has not run" and
      "ran and failed" are different states with different remedies, and they
      are mutually exclusive by construction: a failing agent records runs, so
      its `last_run_at` is fresh and it is never marked stalled. The suffix
      `agent failing` is load-bearing — `failing` is not one of
      `SERVICE_ALERT_KINDS`, which is what keeps the family out of
      `_resolve_recovered`'s reach, and a test pins it. The threshold is a
      **count of runs, never a duration**, the opposite unit from
      `escalate_after_hours` in the same config section: `agent_runs` records a
      run rather than a schedule, so "failing for three hours" cannot tell a
      failing agent from one that is not running, which is the stall family's
      question. Both families read **one** snapshot of `agent_runs` and
      `alerts` via `_check_agent_health`, and the handover between them is
      automatic — an agent that fails and then stops being scheduled has its
      failure row resolved as the stall row opens, so one fault shows one alert
- [ ] **A live-database test path for the shared snapshot query.** The suite
      mocks every session, so the freshness filter's *effect* is unobservable
      — `tests/test_project_snapshots_query.py` asserts the predicate compiles
      into the statement, which is not the same as Postgres evaluating it.
      Worth one integration test against a real database

### Session 35: The inspection library and the `.project.yaml` manifest

**Groundwork landed unwired 2026-08-07** — `sysadmin/registry/` (discovery, id
derivation, manifest reader + validator, and the duplicate/unknown-id errors
that make an unrecognised id a load-time failure). 68 tests, ruff and mypy
clean, suite 1441 → 1509. **Nothing imports it yet**, so every checkbox below
stays open: the package is only worth its weight once `discover_projects` and
the three readers of `projects_root` are pointed at it, and until then it is a
second implementation of the thing it exists to deduplicate.

**Phase 6 complete 2026-08-08 — Session 35 is done.** The organiser has its
own oneshot unit and daily timer, ADR-0001 records the reasoning, and the spec
is marked superseded-in-part rather than rewritten. Two things deliberately
left for the operator: installing the timer (`systemctl --user enable --now
sysadmin-organiser.timer`), and the follow-on edit that stops the daemon
scanning as well — add the timer to services.yaml as `kind: timer` and set
`agents.project_organiser.enabled: false`. Neither is done here, because
declaring a unit in services.yaml before it is installed would have the monitor
correctly report it down.

**Phase 5 complete 2026-08-08.** `estate.json` is emitted on every organiser
run, versioned and written atomically, with `last_code_commit` separated from
`last_commit` and every downstream staleness figure derived from the former.
The ignore rule needed **two** patterns, not one — the roadmap-document fan-out
of 2026-08-06 is newer than the reorganisation snapshot and shadowed it.
Remaining for Phase 6: the organiser's own user timer, and the ADR.

**Phase 4 complete 2026-08-08.** projects.yaml is retired to
`docs/projects-registry-legacy.yaml` and nothing reads it. The registry removed
the last `units -> projects` import. Remaining: **delete the legacy file** once
its comments are all accounted for — the PA-worktrees note has no manifest to
move into, since the project was deleted, and that is the one piece of reasoning
the transfer cannot rehome.

**Phase 3 complete 2026-08-08.** services.yaml is wired: config.yaml holds no
per-service topology, startup validates project ids against the registry, and
`kind` decides every check. Behaviour deltas are recorded in STATUS.md. Still
open for Phase 4: `projects.yaml` becomes `docs/projects-registry-legacy.yaml`
and its comments move into `decisions:` blocks by hand, one project at a time.

**Phase 3, first half, landed 2026-08-08** — 16 `.project.yaml` manifests
(written by `scripts/migrate_registry.py`, pulled forward from Phase 4 because
Phase 3 cannot validate ids that do not exist yet), `services.yaml` with no
paths, `sysadmin/monitor/services.py`, and migration 009 adding `'skipped'`.
**Nothing reads services.yaml yet** — the wiring is the second half and it
changes monitoring behaviour: 8 http checks gain a unit assertion, 5 systemd
checks become `kind: timer`, `venture-chat-large` appears as a new declared-
but-skipped service, and the duplicate ingestion of `sysadmin.service` under
two log-source names has to be resolved one way or the other.

**Phase 2 landed 2026-08-08** — the module boundary. 62 modules moved into
`core/`, `monitor/`, `projects/`, `files/`, `units/` and `briefing/`, with
`tests/test_import_boundary.py` enforcing that monitor never imports projects.
Routes unchanged (55 → 55), suite 1509 → 1512. The registry is still unwired:
`units/agent.py` continues to import `discover_projects` from
`projects/agent.py`, which is one of the two edges Phase 1 exists to remove.

> **On the 2026-08-06 rejection**: the module split was refused that day on the
> grounds that it would duplicate `discover_projects`. It was re-briefed and
> landed as Phase 2, where the objection did not hold — `units/` imports the
> function from `projects/` rather than copying it. STATUS.md now records this
> as reversed rather than rejected; the remaining work is to remove that import
> in favour of the registry, which is Phase 3.

- [ ] **Extract the pure inspection layer** into a top-level package in this
      repository, installed as a path dependency: `utils/git.py`,
      `discover_projects`, `services/roadmap.py`, and the manifest reader
      below. No database, no config, no FastAPI, no scoring. Dependency is
      `gitpython` plus the grep binary
- [ ] Replace `from sysadmin.agents.project_organiser import discover_projects`
      in `agents/service_discovery.py` with the library import — resolving the
      drift the existing comment warns about, rather than relying on convention
- [ ] Promote `agents.project_organiser.projects_root` to a **top-level config
      key**. Three consumers read it (`service_discovery`, `routers/files` as a
      safety confinement rule, `branch_actions`) and only one is the organiser
- [ ] Define and implement the `.project.yaml` manifest — `schema`, `id`,
      `name`, `category`, `status`, `summary`, `supersedes`, `alert_threshold`,
      `decisions[]`. Reader **and** validator live in the library
- [ ] **Normalise project ids first**, or the current inconsistency is baked
      into twenty files: `sysadmin-service` points at `sysadmin_assistant`,
      `sports_analyser` at `SportsAnalyser`, `terrible` at what the docs call
      `TERRRIBLE`
- [ ] Write the migration generating `.project.yaml` from `projects.yaml` and
      emitting `services.yaml`. **Dry run by default**, and it must report both
      registry entries whose path does not exist and repos under the root the
      registry has never known about
- [ ] Transfer `projects.yaml`'s comments into `decisions:` blocks **by hand,
      one project at a time**. Do not automate it and do not delete the file —
      move it to `docs/projects-registry-legacy.yaml`
- [ ] Replace the runtime half of `projects.yaml` with `services.yaml`, keyed
      by project id and containing no paths: N services per project rather than
      one backend and one frontend, `kind` (`http`/`timer`/`oneshot`/`static`),
      and `monitor: false` with a **required reason**. Fold in the units
      currently exiled to `agents.sysadmin.services` in config.yaml
- [ ] Once ids are the join key, replace `ProjectsConfig._setting_for`'s
      three-way name matching with an id lookup, and make an unknown id a
      **load-time error**
- [ ] Add a CLI. There is no way to run a project scan without starting the web
      service, and the only console script is `sysadmin-tray`. With the library
      separated, `estate scan`, `estate check <path>` and `estate brief` are
      thin wrappers

**Two things considered and rejected 2026-08-07**, both worth re-reading before
anyone re-proposes them:

1. **Extracting the project side into its own repository or service.** Only one
   project endpoint needs anything from monitoring (`/managed`, joining
   `service_health`), while monitoring depends on the project side in three
   places — including a file-action safety rule. Migration 001 creates both
   sides' tables in one function, so this is a data migration wearing a
   directory move's clothes.
2. **The module split as originally briefed**, which asserted that monitoring
   must not import the project side. Backwards: the dependency runs that way
   deliberately, and enforcing the rule would mean duplicating
   `discover_projects` — the exact drift the existing comment warns against.
   The library replaces the rule.

Also rejected: **pre-commit hooks for document standards**. Most of the estate
is dormant, so blocking commits in repos nobody is working is pure friction,
and installing hooks across forty repos is its own maintenance problem.

### Session 36: The briefing publisher ✅ (2026-08-11)

Less work than expected, twice over. Half of it had already landed as Session
35 Phase 5 on 2026-08-08, and the two remaining builds were smaller than the
snag fixes they sat on top of.

- [x] Emit `estate.json` from the library's survey. This is the survey function
      serialised, not a separate feature — **done 2026-08-08 (Session 35 Phase
      5)**, `sysadmin/projects/estate.py`, `SCHEMA_VERSION = 1`
- [x] **Separate `last_commit` from `last_code_commit`**, with a configurable
      ignore rule (SHA list or commit-message pattern) seeded with the
      2026-08-04/05 "WIP snapshot before ~/projects reorganisation" commits.
      Every staleness figure downstream computes from `last_code_commit`.
      Supersedes the Session 28 follow-up describing the same weakness —
      **done 2026-08-08**; it needed **two** patterns, not one, because the
      roadmap-document fan-out of 2026-08-06 is newer than the reorganisation
      snapshot and shadowed it
- [x] Adopt the briefing envelope — `schema`, `source`, `generated`, `period`,
      `summary`, `alerts[]`, `facts{}`. Prose is what Alfred surfaces; `facts`
      is the deterministic input the prose was written from, **so briefings can
      be diffed and a drifting summary is detectable**
- [x] Generate the prose from the `facts` block rather than from raw code output
- [x] Write `estate.json` and any briefing artefact **atomically** — temporary
      path, then rename — **done 2026-08-08**, `tempfile` + `os.replace`
- [x] Confirm Alfred enforces staleness on `generated`. A publisher that has
      not run in three days still reads as current, which is worse than no
      briefing at all — **it does, and the check cannot fire.** See below

**The envelope is additive, and that was the whole delivery decision.**
Alfred's `adapt_sysadmin` reads `payload["sections"]` and returns one red
error section if it is absent, and reads `generated_at` into `produced_at`.
The spec named `generated` and no `sections`, so shipping it literally would
have turned Alfred's Infrastructure group red every morning. Additive is not
a compromise: the spec's own sentence — "prose is what Alfred surfaces,
`facts` is the deterministic input the prose was written from" — resolves it,
because **`sections` are the prose**. Alfred owns the section contract by its
ADR-0063; this service owns the envelope round it. Rejected: an
envelope-native second endpoint (two payloads where one gets updated is the
drift this repository keeps filing snags about) and a coordinated breaking
change (two repos in one sitting, digest red in between). No `generated` key
was added beside `generated_at` — two stamps holding one value is a fork
waiting to happen.

**Checkbox 6's answer is worse than the checkbox feared, and it is what
`facts` is for.** Alfred *does* enforce staleness: `_producer_timestamp`
carries `generated_at` into `produced_at` and `DigestSection.vue` flags a
12-hour gap. It is correctly implemented and **structurally incapable of
firing**, because this is a *pull* endpoint — `generated_at` is stamped when
the request is answered. It says when the phone was picked up, not how old
the data recited into it is. A service whose organiser died three days ago
serves a payload one second old. So every `facts` block carries its own
`measured_at`, `facts.stale_sources` names anything over 26 hours, and
`summary` says it in words. **First live run caught one**: `filesystem` last
measured 2026-08-06, corroborated by an open `file_organiser agent stalled`
alert in the same payload — two independent routes to the same fact, which
is the argument for the field.

**`period` is anchored to the schedule, not the last pull.** "Since the
previous briefing" has no anchor on a pulled endpoint: two consumers polling
would each shorten the other's window, and storing a row per pull turns the
route into a pull log and needs a migration. `schedules.briefing_hour`
already declares the cadence, so the window is the most recent 06:00
boundary — one meaning for every caller, no storage. `anchor: "schedule"` is
in the payload because the other reading is the one a consumer would
otherwise assume.

**`summary` is deterministic, and `facts` is a projection rather than a
copy.** No LLM in the 06:00 path: the two weekly reviews are narrated and
pay for it with a figure-free prompt, a deterministic facts prepend and a
markdown stripper, all of which a summary made only of numbers has nothing
to gain from — while a down llama-server would take the briefing with it.
`facts` carries counts and identifiers and never the rows the sections
render, because a facts block containing the whole payload cannot be diffed,
which is the only reason it exists. A test asserts every list in it holds
scalars.

Two defects fixed underneath, both in the functions the envelope wraps —
`SNAG-BRIEF-001` (26 project rows → 5, one query and one filter for both
sections) and `SNAG-BRIEF-002` (a bare `[:180]` slice → word boundary plus
`… (truncated)`, matching Alfred's own marker). The snag list's own note
made the ordering non-negotiable: *"building a briefing envelope on top of
wrong data only makes the wrong data better formatted."*

Also removed: the project snapshots were being **fetched twice** per
briefing, once per project section, differing only by an `ORDER BY` Python
does for free. Two reads of one table in one payload is two chances to
disagree.

### Deferred (34–36)

Not scheduled; recorded so they are not rediscovered as new.

- The **compliance checker** for required documents (CLAUDE.md, handoff, tasks,
  snags) and the relational checks carrying the real signal: handoff date
  against last code commit, unchecked task count against commit activity, snags
  opened versus closed. Held until the write discipline has produced data worth
  checking. Whatever ships must generalise `roadmap.is_placeholder` so an empty
  template counts as missing, tie requirements to declared `status`, and report
  as a **separate compliance result** rather than as score inputs
- `estate init`, scaffolding the template set into a repo without overwriting

### Open decisions (34–36)

- **Where project state ultimately lives** — an Alfred domain, or a standalone
  service Alfred reads from. The forcing function is the first requirement for
  *history* rather than a snapshot, since that needs a database. Until then the
  organiser stays stateless and file-based, and no project tables go into
  alembic
- **Whether the health score earns its place.** Roadmap state is the richest
  thing the scanner reads and is deliberately worth zero points, so the score is
  a directory-tidiness metric. Nothing has breached a threshold since
  2026-07-24, while the roadmap and next-action layer is what Alfred actually
  consumes. Worth settling before building anything further on top of the score
  — and it subsumes the Session 28 open decision on whether missing roadmap docs
  should cost points

---

## Session 37: The handoff pipeline — writer and reader ✅ (2026-08-10)

Raised by the estate owner: "the handoff hook isn't doing much in
venture-assistant." It was doing worse than nothing, on both ends.

**What was measured first** (15 repos, before any change): 5 carried
`docs/sessions/handoff.md` and **every one was hook output**. Exactly two
repos had ever held a handoff someone wrote — `venture-assistant`
(root `HANDOFF.md`, 8 of its 9 commits) and `SportsAnalyser` (abandoned
2026-03-07). Root `HANDOFF.md` existed in **1 of 15**, not "most".

- [x] **The writer.** `SessionEnd` **cannot block** — it is an
      observability event — so `generate-handoff.sh` could only emit what
      `git` already recorded. Retired (left on disk, unwired, with the
      reasoning). Replaced by `~/.claude/hooks/require-handoff.sh`, a
      **Stop** hook that blocks a session which changed code until
      `HANDOFF.md` carries today's date. Three independent loop guards
      (`stop_hook_active`, a per-session+repo marker file, exit 0 on every
      failure path); ten payload cases verified before wiring
- [x] **The reader.** `SNAG-ROADMAP-003` closed — four candidate paths,
      selection by `handoff_date` rather than tuple order, also-rans
      reported as `handoff_duplicates`. Live proof: `venture-assistant`
      now reads its 6 KB root handoff, `ImbaBots` its 141 KB
      `docs/handoff.md`; both had been serving the board an 850-byte stub
- [x] Stale references corrected in `recommendations.py` (its "No session
      handoff" advice described a hook that guaranteed the check could
      never fire), both `CLAUDE.md` files, `monitorable-project.md` (which
      said "don't hand-write handoffs" — now inverted), and
      `claude-preflight.sh`, whose extract was anchored on
      `## ⚠️ READ THIS FIRST` and `## In-Progress Tasks`: headings no
      handoff on this box has ever used, so it announced a handoff and
      then printed nothing

**The design lesson, worth keeping**: a file guaranteed to exist cannot
also be the file whose absence means something. The hook filled the slot
in every repo, so nothing ever signalled a real handoff was missing —
`venture-assistant` kept the habit only because its handoff lived at a
path the hook never touched.

### Follow-ups this session opened

- [x] Estate migration **done** (commit `0d56081`, 2026-08-10). Seven
      repos hold a handoff and every one holds exactly one: root
      `HANDOFF.md` in `Alfred`, `ImbaBots`, this repo,
      `apps/venture-assistant` and `apps/SportsAnalyser`, plus
      `docs/sessions/handoff.md` in the two archived `PersonalAssistant`
      repos. Re-checked at the top of Session 38 before building the
      reporter, which is what turned that work from a report on a live
      mess into a regression detector.
      **The first re-check was wrong** — it globbed `~/projects/*/`, which
      is 11 directories, while `discovery_depth: 2` makes the scanned
      population 25 across `~/projects/`, `apps/` and `archive/`. It
      reported `venture-assistant` and `SportsAnalyser` as having no
      handoff when both have a root one, contradicting a Session 37
      finding without that contradiction being spotted. Enumerate the
      estate the way the scanner does, or read `estate-map.md`; a
      top-level glob is not the estate
- [x] **The narrative history is now readable** (done 2026-08-10).
      `ProjectHistoryPoint` gained `next_action`, `next_action_source` and
      `next_action_changed`; `build_narrative_history` in
      [router.py](../../sysadmin/projects/router.py) builds them. The data
      was already being collected — Session 28 wrote the whole roadmap
      findings block into `project_snapshots` and the history list exposed
      the score only. **This unblocks Session 32**, whose recorded blocker
      was the SessionEnd hook overwriting its handoff instead of appending
      a log: the log exists, in JSONB, 90 days deep. Live proof — ImbaBots'
      `M5-T05` unchanged across 10 scans and 3 days
- [x] `handoff_duplicates` now has a reader (Session 38, 2026-08-10) — a
      zero-point `kind: "roadmap"` recommendation, so it reaches
      `/api/projects/{name}/recommendations`, `/api/projects/actions` and
      the weekly review without a new route. The field was widened from
      bare paths to `{path, date, date_source, days_older}` first: paths
      alone cannot separate migration debris (delete it) from a document
      that lost on tuple order (do not), and advice that conflated them
      would recreate SNAG-ROADMAP-003 from the deletion side. Nothing on
      the estate holds two handoffs any more, so it was verified against
      a constructed repository rather than live data
- [ ] `SNAG-ROADMAP-002` remains open and this session added evidence:
      `count_open_snags` reports 7 for 5 open snags in this very file

---

## Session 38: The unread handoff gets a reader ✅ (2026-08-10)

Session 37's `handoff_duplicates` reached a surface. Added to
`_roadmap_recommendations`, so it lands on
`/api/projects/{name}/recommendations`, `/api/projects/actions` and the
weekly review at once — no route, no contract change, no migration.

**The estate was re-measured before anything was built, and it changed
what was built.** Zero repos hold two handoffs; the migration cleared
them. This is therefore a regression detector, and it was verified against
a constructed two-handoff repository. The mtime branch is what fired — a
generated stub headed `# Session Handoff` carries no ISO date, so the
realistic case is the one where the age comes from the weaker clock.

### Follow-ups this session opened

- [ ] `handoff_path` is still read only inside the duplicate
      recommendation's detail line, so in a repo with one handoff — every
      repo on the estate today — it remains consumed by nothing. Putting
      it on `ProjectBoardEntry` would let any consumer rendering a
      handoff-sourced next action name the document it came from, which
      is the provenance argument Session 37 made. Deliberately deferred:
      it touches `contracts.py`, the board builder,
      `alfred-projects-page.md` and Alfred's expectations, and that is a
      sitting of its own rather than a rider on this one
- [ ] The recommendation is waived for non-active projects, inheriting
      `_roadmap_recommendations`' blanket rule. Defensible — nobody is
      misled by an unread handoff in a repo nobody opens — but it is an
      inherited default here rather than a decision taken for this item,
      and a dormant repo mid-migration is exactly where a stray handoff
      survives longest. Revisit if a dormant project is ever found
      holding two
- [ ] Nothing asserts the widened `handoff_duplicates` shape at the
      storage boundary. The recommendation tolerates both shapes and the
      scanner emits the new one, so a third shape would degrade quietly
      rather than fail — acceptable for advisory JSONB, worth a schema
      guard if a second consumer appears

---

## Session 39: Who watches the watchers

Raised by the estate owner on 2026-08-11, straight after `SNAG-AGENT-003`.
The framing question was "can we have someone who watches the watchers", and
the first thing worth recording is that **the watcher already existed and
worked**:

| Step | Component | Result |
|---|---|---|
| Detect | `self_monitor.build_self_report` | `stalled: true`, correct, at interval × 3 |
| Alert | `SysAdminAgent._check_agent_stalls` | **one** row, 2026-08-10 09:07 |
| Speak | tray, fingerprint `{severity}:{title}` | **one** toast |
| Escalate | — | nothing exists |

Detection is not the gap. `agent.py` skips raising when an unresolved alert
with that title is open — the same rule that stopped the 1,664-row pile-up,
and correct — but combined with the tray's fingerprint it means **the alarm
rings once, at the quietest severity, and is then silent while the fault
persists**. A warning that fires once and goes quiet is indistinguishable
from one that got fixed. Same shape as `SNAG-DB-001` and as the
`generated_at` hole Session 36 found: *absence of signal read as absence of
problem*.

**The owner's diagnosis, asked and answered rather than assumed: "I never
saw the toast."** Not ignored — away from the machine. That rules out
severity tuning and ranking, and it means escalating louder into D-Bus
repeats the miss on a longer timescale. Targets chosen: **an agent silently
stopping**, and **the daemon dying or wedging**. Explicitly not chosen: box
death (needs an off-box dead man's switch, which this estate has none of).

### What the box actually has — inventory, 2026-08-11

- **`notify-send` / D-Bus** — the tray plus `monitor/desktop.py`. The
  channel that was missed.
- **`zenity`** — installed, unused. Modal; blocks rather than notifies.
- **`claude-preflight.sh`, the briefing, journald** — passive surfaces the
  owner opens deliberately.
- **alfred-glance already renders pushed alerts** — `MqttEventReceiver.kt`
  subscribes to mosquitto (active) and `Notifier.kt` carries a dedicated
  `ALERTS_CHANNEL_ID` for "server-pushed alerts", separate from the daily
  nudge. **A working phone path that exists today.**
- **Off-box: nothing.** postfix/exim/opensmtpd/dma all inactive, no
  `.msmtprc`; `/usr/bin/mail` is s-nail with no MTA behind it. No ntfy, no
  healthchecks.io.
- **No `OnFailure=` anywhere** — user or system. Layer 2 is unbuilt, not
  partly built.

### Decisions taken 2026-08-11, before any code

1. **MQTT is promoted from Alfred's private bus to an estate bus.**
   [estate-map.md](../guides/estate-map.md) reserved this decision in
   writing — *"if a second consumer ever appears, decide then whether it is
   promoted"* — and a second **producer** has now appeared. The guide must
   be amended to record the promotion **and its terms** (who may publish,
   topic naming, LAN-only), not merely to delete the old sentence.
2. **`systemd WatchdogSec` for the wedge case**, over a polling timer. A
   true dead man's switch, native, no new unit — and the heartbeat proves
   the **event loop** is alive rather than merely the process.

### The two constraints found while checking the premises

Both were verified rather than assumed, and both change the shape of the
work:

- **alfred-glance's topic registry is closed by construction.**
  `RENDERERS` in `BusEvents.kt` is "the single source of truth" and
  `SUBSCRIBED_TOPICS` derives from `RENDERERS.keys`, so an unregistered
  topic cannot be subscribed to by design. Publishing therefore needs a
  **second repository, a Kotlin change and an Android release** — not a
  `mosquitto_pub` one-liner. Every existing topic is `alfred/events/<domain>/
  <event>`, so the namespace itself encodes the private-bus assumption:
  promotion has to decide between `alfred/events/sysadmin/…` (cheap,
  keeps a misleading prefix) and a neutral root (honest, touches seven
  existing constants and both ends).
- **`Restart=always` means the crash case is *already* invisible.**
  `sysadmin.service` is `Type=simple` with `Restart=always`, so the unit
  rarely enters `failed` and an `OnFailure=` hook would seldom fire. It
  needs `StartLimitBurst`/`StartLimitIntervalSec` to make a restart *loop*
  reach the failed state. This is the same silence-reads-as-health shape
  the session exists to fix, sitting in the unit file.

### The work

- [x] **Escalation ladder for stalled agents**, reusing
      `sysadmin/projects/nudges.py` rather than copying it — including the
      rule it already encodes: **resolve the quiet row and raise a louder
      one**, never update severity in place, because the tray fingerprints
      on `{severity}:{title}` and an in-place change stays suppressed —
      done 2026-08-11; the shared half had to move to `core` first, see
      below
- [ ] **Publish alerts to MQTT** at or above a configured severity. Decide
      the topic namespace first (above); amend estate-map.md with the terms
      of the promotion in the same change
      *(Unblocked 2026-08-11 by estate-manager Session 2: the broker-side
      identity `sysadmin-publisher` exists with write access to `estate/#`
      and survives Alfred restarts; the password arrives as
      `$CREDENTIALS_DIRECTORY/mqtt` per [ADR-0003](../adr/0003-mqtt-credential-by-loadcredential.md).
      Remaining here: an MQTT client dependency (Alfred uses `aiomqtt`),
      config keys for host/username/topic, the publisher itself wired to
      the severity gate, and the topic scheme under `estate/…`)*
- [ ] **Register the topic in alfred-glance** — `BusEvents.kt` renderer,
      `BusPayloads.kt` shape. Separate repo, separate session if it needs
      an Android release
- [ ] **`Type=notify` + `WatchdogSec=` on `sysadmin.service`**, with the
      ping issued from the async loop. **Risk to rehearse before enabling**:
      if `READY=1` is never sent, systemd treats startup as failed and kills
      the service — so the rollback must be written down before the unit is
      edited
- [x] **`StartLimitBurst` / `StartLimitIntervalSec`** so a restart loop
      reaches `failed`, then an `OnFailure=` unit that says so — done
      2026-08-11, `StartLimitBurst=5` / `StartLimitIntervalSec=600` plus
      `sysadmin-failed.service` → `scripts/notify-unit-failed.sh`.
      **Installed and verified on the live box the same day**, and the
      ladder proved itself in production on the stall that motivated it:
      the 2026-08-10 09:07 `warning` was resolved and a `critical` raised
      at 17:13 with `hours_since_first_alert: 32.1`
- [x] **A failure leaves state, not just a toast** — added the same day
      after the owner chose `agent='sysadmin'` over a sixth
      `chk_alert_agent` value. `sysadmin/core/unit_failure.py` writes a
      critical row through the **sync** engine (no event loop, no
      scheduler session, nothing subscribed — the application is dead by
      definition), with `details.source = systemd_onfailure` carrying the
      provenance `agent` cannot. **Paired with a resolve in the lifespan**,
      because the service starting *is* the recovery and nothing else can
      ever observe it; without that half it is an alert type that can only
      accumulate. Verified end to end against the live database
- [x] **Do not** build a second detector. Detection works; every item above
      is about a signal persisting until it is seen — held to; not one line
      of `self_monitor.py` changed

### Done 2026-08-11 (part 1 of the session)

**The ladder, and where it had to live.** `sysadmin/monitor` may not import
`sysadmin.projects` (`tests/test_import_boundary.py`), so "reuse nudges.py
rather than copy it" was not possible as stated. The shared half moved to
**`sysadmin/core/escalation.py`** — `SEVERITY_ORDER`, `Ladder`, `step_for`
— the same move `strip_markdown` made into `core/text.py` and for the same
reason. `nudges.py` now delegates to it; `severity_for` survives as a thin
wrapper because the *unit* (days) is what a reader of that module needs.

**The loud rung is `critical`, and the reason is not volume.**
`sysadmin_tray/notifications.py` sets `transient=effective == "info"` on a
first notification and `transient=False` only in `_maybe_escalate`, which
fires for `critical` alone. **`critical` is the only severity the tray
leaves on screen.** A `warning` toast expires whether or not anyone was in
the room — which is exactly the owner's reported failure, so the second
rung is about *persistence*, not loudness. This is the opposite of the rule
`nudges.py` encodes (a nudge never reaches `critical`) and the two
docstrings now point at each other so the difference reads as deliberate.

**The escalation clock runs from when the alarm rang, not from when the
stall began.** Both are computable; the alert row's `created_at` is right
for two reasons. It is the honest claim — "you were told yesterday and it
is still true", and the thing that failed was the telling. And anchoring to
the stall's own age would make **a daemon outage produce a wall of
criticals on restart**: while the service is down no agent runs, so the
first check back would escalate all five at once, charging the estate for
this application's downtime. `GET /api/services/reliability` already
encodes that rule as "a gap in the series never costs points".

**`escalate_after_hours: 24`, measured against the slowest agent, not the
fastest.** `file_organiser` and `service_discovery` run daily, so a stall of
theirs that is merely late recovers within one interval; a shorter gap
escalates faults that were about to clear themselves, and an alarm that
cries wolf stops being read. The knob cannot make *detection* faster —
that is `stall_grace_multiplier`, and the config docstring says so, because
that is the wrong knob someone will reach for.

**`StartLimit` risk, sized rather than assumed.** `Restart=always` with no
limit rides out a slow dependency, and this app does exit rather than
degrade when the database is absent (`verify_connection` raises inside the
lifespan). Measured before making the change: **`NRestarts=0` and zero
"Scheduled restart job" entries in 30 days of journal** — the retry has
never once fired on this box, so the resilience being traded away is
theoretical while the silence it causes is not. The window is 600s rather
than 300s to leave the headroom anyway, and the rollback (including the
`systemctl reset-failed` that is easy to forget) is written into the unit
file rather than into a session note.

`tests/test_systemd_units.py` pins the pair together: `Restart=always`
**with** a burst limit, a window that outlasts `burst × RestartSec`, an
`OnFailure=` naming a unit that exists, a handler with no `OnFailure=` of
its own, and `--expire-time=0` in the script. Installing either half alone
accomplishes nothing, which is the shape of half-change this repository has
shipped before (a retention row with no `TABLE_TIMESTAMP_MAP` entry).

### Still open, and what the two constraints did to the plan

- [x] **MQTT publishing is blocked on an Alfred-side change, not on a
      topic name.** The premise checked in the scoping session was
      alfred-glance's closed renderer registry. That is real but secondary:
      mosquitto here is `allow_anonymous false` with the **dynamic-security
      plugin**, whose schema Alfred owns
      (`Alfred/backend/alfred/events/dynsec.py`), and
      **`dynsec.reconcile()` deletes every client that is not Alfred's
      admin, not Alfred's publisher, and not a live device token**. A
      `sysadmin-publisher` added by hand with `mosquitto_ctrl` therefore
      works until Alfred next restarts and is then deleted — best-effort,
      logged at `info`, no alert. For an alerting path that is the worst
      available failure mode, and it is this session's own bug reinstalled
      in the fix. Decided 2026-08-11: **Alfred provisions a protected
      non-device publisher for sysadmin**, in its code.
      *(Unblocked 2026-08-11 by estate-manager Session 2, with the
      decision superseded in the details: Alfred's `reconcile()` was
      narrowed to subscriber-role clients with no live token (Alfred
      ADR-0068) rather than growing a protected list, and
      `sysadmin-publisher` is provisioned by the **estate**, declared in
      `estate-manager/mqtt/dynsec.yaml` (its ADR-0005 §3) — verified
      live: the client survived an alfred-backend restart. This service's
      password arrives via `LoadCredential=` — [ADR-0003](../adr/0003-mqtt-credential-by-loadcredential.md))*
- [x] **The neutral root costs a dynsec change too.** Both roles are
      scoped to `_TOPIC_FILTER = alfred/events/#`, so `estate/…` is
      **denied by the broker** until Alfred's roles gain a widened or
      second filter. The namespace decision (neutral root, taken
      2026-08-11) is therefore not "seven constants and both ends" as
      scoped — it is that plus the broker's access control. Terms recorded
      in [estate-map.md](../guides/estate-map.md).
      *(Done 2026-08-11, estate-side: `alfred-subscriber` now reads
      `estate/#`, the new `estate-publisher` role writes it, and the path
      was proven over the wire — a publish as `sysadmin-publisher` on
      `estate/alerts/test` reached a subscriber-role client. The
      publisher code here remains open, above)*
- [ ] **Persist an `OnFailure=` firing where the tray can see it.** The
      handler notifies and writes to journald; neither survives as an
      *alert row*, so a failure that happened while nobody was logged in is
      invisible to `GET /api/sysadmin/alerts` afterwards. Blocked on a
      decision rather than on work: `alerts.agent` has a `chk_alert_agent`
      CHECK constraint, so an external writer either lies about provenance
      (`agent='sysadmin'`, when the whole point is that the sysadmin
      service was dead) or needs a migration adding a value for it.
- [ ] **Off-box remains the known gap.** Listeners are `127.0.0.1` and
      `192.168.1.2` only, so nothing built this session survives the box
      being off. Recorded, not closed.

### Rejected, and why

- **A watchdog agent inside the daemon.** A watcher that shares fate with
  what it watches is not a watcher — and the failing component here was
  never the detector.
- **Escalating louder into D-Bus alone.** The owner was away from the
  machine; a louder alarm in an empty room is the same miss with more
  volume.
- **Email.** No MTA is configured and installing one to carry alerts is a
  new service to monitor, which is the problem recursing.
- **Off-box (ntfy / healthchecks.io)** — the only thing that survives the
  box being off, and deliberately deferred: it was not among the failures
  the owner chose, and it adds an external dependency and an account.
  Record it as the known gap rather than pretending the ladder closes it.

---

## Session 40: MOVED to ~/projects/estate-manager

The estate manager repository was created on 2026-08-11 and this session
became **its Session 1**. The work list, the two follow-on sessions and the
measurements behind them now live in
`~/projects/estate-manager/docs/roadmap/tasks.md`.

**A pointer, not a copy** — the rule that session's own scope insists on,
applied to itself. Two roadmaps describing one piece of work would disagree
inside a week, and this repository has filed three snags about exactly that.

What stays here, because it is about *this* service rather than about the
estate:

- **ADR-0002 moved on 2026-08-11** (estate-manager Session 1) and was
  renumbered to
  [estate-manager ADR-0001](../../../estate-manager/docs/adr/0001-estate-manager.md);
  a pointer stands at [../adr/0002-estate-manager.md](../adr/0002-estate-manager.md)
  and the number is never reused here.
- **sysadmin does not move.** It stays the monitor, keeps its own broker
  credential and publishes alerts directly, and will watch the estate
  manager's units like any other. The monitor must not own the things it
  monitors, and an alerting path with a live dependency on another service
  is not an alerting path.
- **The four cross-repo guides moved the same day**, leaving pointers in
  `docs/guides/` (`api_auth.md` stays — it is local). The port registry
  now lives in
  [estate-manager's monitorable-project.md](../../../estate-manager/docs/guides/monitorable-project.md),
  and `~/.claude/CLAUDE.md` points at the new paths — updated in the same
  sitting precisely because a stale global pointer would silently stop
  the contract being read.

---

## Backlog

**Carried-forward follow-ups** — small items noted by the sessions that
deferred them. Hoisted here 2026-08-05 when Sessions 10–23 were archived,
so nothing was buried with them.

Notifications (from SNAG-CFG-001, 2026-08-11):
- [ ] **The daemon announces an outage's start and never its end.**
      `sysadmin/monitor/desktop.py` notifies on `alert.raised` only,
      because `alert.resolved` carries a *match pattern* rather than a
      subject — `BaseAgent.resolve_alerts` publishes
      `{"agent", "match", "count"}`, and the project organiser's `match`
      is `"Project % health critical"`. A recovery toast needs the
      resolve events to name what recovered, which means changing the
      three resolve paths, not the notifier
- [ ] **The presence signal cannot tell the tray from any other client.**
      Any GET of `/api/sysadmin/alerts` counts as "somebody is watching",
      including a `curl`. It errs towards silence, which is the safe
      direction and the pre-existing behaviour, but a tray that
      identified itself (a header set in `sysadmin_tray/client.py`) would
      be exact. Deferred because an older tray build would then go
      unrecognised and both would toast — the duplicate this design
      exists to prevent
- [ ] **The tray re-announces the open alert set on every start**, because
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
- [ ] **Page-1 churn can re-notify a standing alert.** The tray fetches
      the newest 50 unresolved alerts; with 547,814 of them, a burst of
      new rows pushes an older title off the page, `_close_inactive`
      closes its episode, and the title notifies again as a *new* episode
      when it reappears. Harmless at the current rate (one alert in 90
      minutes) and unbounded when the log aggregator is noisy — which
      makes it a second consequence of SNAG-AGENT-002 rather than a tray
      defect. A fix belongs on the volume, not on `limit=50`
- [ ] **547,814 unresolved `Log error: kernel` rows** were found in the
      table while measuring notification volume. That is SNAG-AGENT-002's
      damage rather than a new defect, and the notifier's incident gate
      makes it harmless to *notifications*, but nothing has ever purged
      or resolved them — retention purges resolved rows only

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
  disabled because config.yaml is committed
- PA-auto's 224 branches will take 12 confirmed calls at the current
  `max_deletions: 20`; raising it for a one-off sweep is a config change,
  deliberately not a request parameter

---

## Maintenance

_Not numbered sessions — config/upkeep work that doesn't warrant one.
Completed maintenance is in the archive._

### ⚠️ Pending: restart the live daemon

`sysadmin.service` reads config at startup and is a **system** unit, so:

```bash
sudo systemctl restart sysadmin.service
```

Owed since the 2026-07-24 daemon fixes and the Alfred config migration, and
again since 2026-08-05's SportsAnalyser wiring — the running process
predates all of it.

**Measured cost, 2026-08-10 (Session 38):** the newest stored snapshot
(09:06 today) carries neither `handoff_path` nor `handoff_duplicates`, so
the whole Session 37 reader is absent from the database and every surface
built on it reads `None`. This debt is no longer only theoretical — two
sessions of project-side work are invisible until the restart happens.

### ⚠️ Pending: enable the SportsAnalyser backend unit

`sportsanalyser-backend.service` is `disabled` and only runs because the
frontend `Requires=` it — that survives exactly until the frontend is
stopped or its unit changes:

```bash
systemctl --user enable sportsanalyser-backend.service
```

---

## Session 41: The two P1 agent defects ✅ (2026-08-12)

`SNAG-AGENT-003` and `SNAG-AGENT-004`, taken together because both are the
same shape — **a component that stopped working and reported nothing** —
and because both had been diagnosed from the outside and not from the box.
Neither filed cause survived contact with the evidence.

### SNAG-AGENT-003 — the cause was a third possibility, found in 90 seconds of journal

The snag named two candidates (APScheduler never firing the job;
the agent dying before it records) and said they needed separating before
anything was changed. Separating them took one `journalctl` call and the
answer was neither:

```
17:08:12  scheduled_interval_job  file_organiser_scan  {"hours": 24}
17:11:10  agent_run_completed     file_organiser  duration_s 117.71  findings 25317
17:11:10  scheduler_job_error     InterfaceError: connection is closed
          [SQL: UPDATE sysadmin.agent_runs SET status='completed' ...]
```

**The scheduler fires and the agent succeeds. The transaction is killed
underneath it.** `SHOW idle_in_transaction_session_timeout` → `1min`.
`BaseAgent.run` inserted the `running` row and **flushed** it — starting a
transaction — before handing the same session to `_execute`, which then
spent 118 seconds in `asyncio.to_thread` touching no database at all.
PostgreSQL terminated the backend at t+60s.

Three things this explains that the snag recorded as separate mysteries:

1. **Why `agent_first_run_delay_seconds: 60` looked broken.** It was
   never broken. It has been doing its job since it was added.
2. **Why nothing has ever recorded a failure.** The failure record lived
   in the transaction the failure destroyed. `status='failed'` was written
   to a row that no longer existed.
3. **Why 2026-08-06 is the one surviving run.** It took **29.63 s** — the
   only file-organiser run in the agent's life to finish inside the
   timeout. The successful row is the evidence, not the exception.

It is a `BaseAgent` defect, not a file-organiser one; every other agent
survives only by being fast (sysadmin 13 s, project_organiser 2.3 s,
service_discovery 0.2 s, log_aggregator 0.3 s). And it is a rule this
repository had **already written down one layer up** — *"commit the read
transaction before calling the LLM"* in `files/review.py` — learned for
inference and not generalised to the framework underneath.

- [x] **`BaseAgent.run` runs in three transactions, not one.** The
      `running` row commits on its own; `_execute` gets a session that has
      never been flushed, so its transaction opens at its *first
      statement* rather than 118 seconds earlier; the outcome is an
      `UPDATE` by id from a third. Free, because `UUIDPrimaryKeyMixin`
      sets `default=uuid.uuid4` client-side — the id exists before the
      INSERT is sent
- [x] **A failed run now records that it failed.** The bookkeeping
      survives the work it books, which is the half that made five days of
      failure indistinguishable from five days of nothing having been
      scheduled
- [x] Rejected: **setting `idle_in_transaction_session_timeout` on
      scheduler connections.** One line, and it keeps a two-minute idle
      transaction holding locks and blocking vacuum — suppressing the
      host's deliberate guard on the one connection that idles longest,
      and still leaving a failed run unable to record itself
- [x] **Proven on the box, 2026-08-12.** After the restart the file
      organiser recorded **3 completed runs and one `running`** in
      `agent_runs`, against **one run in the agent's entire life** before
      today, and `filesystem_audits` gained three rows (08:59, 10:45,
      12:36) where it had held one since 2026-08-06. The `running` row is
      the new behaviour working as designed, not a fault: a run in flight
      is now visible instead of absent

**Two changes of meaning, both deliberate.** `_execute`'s writes are no
longer atomic with the run record — still atomic with each other, but a
failed run now leaves a `failed` row where it left nothing. And a process
killed mid-run leaves a permanent `running` row, where before it left no
row: an agent that died and an agent that was never scheduled used to look
identical, which is precisely how this stayed invisible.

### SNAG-AGENT-004 — right diagnosis, and about twenty times the stated scope

The filed cause was correct and the fix pattern was already named. What
the entry understated was the population. Counted live 2026-08-12,
unresolved rows under `agent='sysadmin'`:

| Family | Rows | Newest | Resolve path before |
|---|---:|---|---|
| Retired services (**five**, not four — `nuxt-frontend` was missed) | 27,827 | 2026-07-24 | per-service loop, unreachable once deconfigured |
| Resource thresholds (disk, RAM, VRAM) | 24,097 | 2026-08-11 | **none, ever** |

`Critical disk usage on /` alone is **13,971 open rows**, last raised
2026-07-26, against a disk that has been at 68 % since. `_check_thresholds`
raises unconditionally and nothing in this application's history has ever
resolved a resource alert. A condition that recovered and could not be
observed recovering is the same defect as a service that was retired, so
one statement closes both.

- [x] **`SysAdminAgent._resolve_recovered`**, mirroring the project side:
      *which of my open alerts would this run not raise?* Population is
      `RESOLVABLE_TITLE_PATTERNS` — **patterns, not the configured service
      list**, because a set built from configuration cannot contain a
      deconfigured service, which is the entire defect
- [x] **The per-service `resolve_alerts(session, service_name)` is gone.**
      It was also a substring `ilike`, so `venture-chat` recovering closed
      `venture-chat-large`'s alerts — a second, unfiled bug removed by the
      same change
- [x] **Three families deliberately excluded**, each having a lifecycle
      owner already: `% agent stalled` (`stalls.py` escalates *off* the
      quiet row staying open), `% failed` (`unit_failure.py` writes it
      dead, the lifespan resolves it alive), `Unusual % usage`
      (`_check_anomalies` resolves by id). Verified against the live
      table: the only `agent='sysadmin'` row the statement leaves open is
      the file organiser's stall, which is still true
- [x] **Services and resources take different exclusions, and the
      difference is not cosmetic** — see the rejected version below
- [x] **Backfill ran itself** on the first agent run after the restart —
      **51,976 rows resolved**, `agent='sysadmin'` unresolved **51,925 →
      43**. Chosen over a one-off script so the fix would be proven by
      doing exactly what it will do for ever after, and it was

**The version that was written first and refuted before it shipped.**
Excluding only "titles this run raised" is the obvious reading of the
project-side pattern and is wrong here. `_degraded_counts` is in memory
and resets on daemon restart, so the first run after one raises nothing
for a service that has been degraded for hours — the alert would be
**resolved as recovered and re-raised two checks later**, announcing a
recovery to the tray for a fault that never went away. Services are
therefore resolved only when this run measured them *healthy*
(`unhealthy` carries everything else, `error` included, where the check
itself failed and the state is genuinely unknown). Resource thresholds
keep the raised/not-raised test, because a mount either breached this run
or did not and no streak counter is involved.

`skipped` counts as healthy, deliberately: it means `services.yaml`
declares `monitor: false`, and an open critical nothing will ever look at
again is the pile-up wearing a declaration as an excuse.

### Residual, recorded rather than fixed

- **The table still grows by one row per check while a condition holds** —
  only one is *open* at a time now, which is what the tray and
  `GET /api/sysadmin/alerts` read. Retention can finally purge the rest,
  since it purges `resolved = TRUE` only
- **`log_aggregator`'s 547,891 rows are untouched and need their own
  rule.** `Log error: kernel` alone is 547,814. These are **events, not
  states** — a log line that happened cannot recover — so widening this
  resolve to cover them would be the wrong mechanism. Filed as
  `SNAG-AGENT-005`
- **`SNAG-AGENT-003`'s numbers in the snag entry were derived from a
  scheduler that was working.** Worth remembering next time an endpoint's
  output is used to reason about a cause: `GET /api/sysadmin/self` reports
  `agent_runs`, and `agent_runs` was the thing being lost

---

## Session 44: The collation check — a fault nobody was watching for ✅ (2026-08-13)

_`SNAG-DB-002`. A routine glibc upgrade moved this box from locale data
2.43 to 2.44. PostgreSQL records the version each database was created
with precisely so it can say it no longer matches, and every `psql`
session has printed that warning since — **read by nobody**. This
application is the thing on this box whose job is to notice, and the
fault was found because a human happened to open a shell while checking
a column type._

- [x] **`sysadmin/monitor/collation.py`** — one cluster-wide read of
      `pg_database` per sysadmin run, both sides of the comparison from
      one query. `pg_database_collation_actual_version(oid)` (PostgreSQL
      15+) gives the OS side, so no second engine, no second credential
      and no loop over connections
- [x] **`_check_collation` on the sysadmin agent**, with the raise, the
      dedup and the resolve in one method and the decisions in the pure
      module beside them
- [x] **`agents.sysadmin.collation.enabled`**, one knob and only one —
      severity is fixed in code because two of the four values turn the
      check into either an interruption (`critical` breaks DND) or
      silence (`info` is below `tray.notify_min_severity`)
- [x] **33 tests**, including the title asserted against every pattern in
      `RESOLVABLE_TITLE_PATTERNS` by emulating SQL `LIKE`

### The count in the snag was wrong, and the shape of the error is the lesson

The entry says three databases. It is **eight of eleven**: the five
`alfred*` copies, `postgres`, `projects` and `template1`. The original
number came from the databases someone had opened a `psql` session
against; `pg_database` is cluster-wide, so one query sees them all.
`estate`, `estate_test` and `venture` are clean at 2.44 — created after
the upgrade, which is the evidence that `CREATE DATABASE` stamps the
current OS version rather than inheriting the template's.

### Four rules, three of them the opposite of the obvious implementation

- [x] **Not-knowing is not a mismatch, and this check fails _open_** —
      deliberately the opposite of `schema_guard`. `template0` records no
      version, and a `C`-locale database has no actual version to compare
      against; `recorded != actual` in Python reads NULL as a fault and
      invents an alert whose remedy does not exist. Both sides are
      required non-NULL **in SQL**, and `IS DISTINCT FROM` is rejected
      for reporting `2.43` against `NULL` as a difference. The guard
      refuses to boot on not-knowing because serving against the wrong
      schema is worse than not serving; here the cost of a false positive
      is an operator reindexing a database that is fine
- [x] **One row per database, and the databases are not filtered.** Five
      of the eight are Alfred's dev and test copies. Filtering to "the
      ones that matter" needs a second registry of estate facts living in
      this repository, which `~/projects/estate-manager` exists to
      prevent — and a test database is where a wrong-ordering bug is
      cheapest to find. Per-database rather than one cluster row because
      the remedy names one database and a row that closes when its own
      database is reindexed shows progress
- [x] **Raised once per open row, never once per run.** The agent polls
      every 300 s and a stale collation persists for weeks, so the
      `_check_thresholds` pattern would write **2,304 rows a day** for
      this one fault — `SNAG-AGENT-004` and `SNAG-AGENT-005` a third time
- [x] **Therefore this family stays out of `RESOLVABLE_TITLE_PATTERNS`
      and owns its own lifecycle.** The two are mutually exclusive, which
      nothing in the codebase said before: that sweep closes any owned row
      the run did not raise, which is sound only for a family that
      re-raises every run. Dedup plus sweep makes a row flip-flop —
      resolved on the run that holds, re-raised on the next — and each
      flip clears the tray's `{severity}:{title}` fingerprint, so it
      notifies again. A pile-up is loud; that would be loud *and* read as
      recovery. The database name sits last in the title, which keeps it
      clear of the five `% <kind>` patterns by construction

### The remedy's trap is carried in the alert, not left to the reader

`ALTER DATABASE … REFRESH COLLATION VERSION` on its own clears the
warning by asserting the versions now match, **without rebuilding
anything** — a loud known risk turned into a silent one. The message
names `REINDEX` first and `details['remedy']` is a two-element list in
order, because a reader copying one line out of a paragraph is how that
gets sprung. A test asserts the ordering.

### Verified against the live database, 2026-08-13

Both halves, in transactions that were rolled back — residue 0 rows:

```
run 1: raised=8   (exactly the 8 stale databases, all `warning`)
run 2: raised=0   counts={'mismatched': 8, 'raised': 0}  open=8
narrowed as if 2 reindexed + 1 dropped:
       raised=0   counts={'mismatched': 5, 'resolved': 3}
       RESOLVED alfred_e2e / alfred_test_cc / template1, 5 left open
```

### Found on the way, filed rather than fixed

- [ ] **`SNAG-AGENT-006`** — a sustained fault still writes one alert row
      per run. `sysadmin-organiser-timer critical` held **60 unresolved
      rows in five hours**. This is `SNAG-AGENT-004`'s *raise* side: that
      session fixed the resolve, which bounds the leak at retention but
      does not stop it. Not fixed here because both halves must move
      together — dedup without removing the family from
      `RESOLVABLE_TITLE_PATTERNS` makes the rows flip-flop, and those are
      the families carrying `critical`
- [x] **The `REINDEX` half of `SNAG-DB-002` stays open**, and stays
      manual. Eight databases, two of them another application's, one of
      them 16 GB. It wants a quiet window and a human
      — *carried out by **estate-manager** on 2026-08-13, hours after this
      line was written, and verified here 2026-08-16 (Session 56). Every
      clause above is wrong in an instructive way: it was **eleven**
      databases not eight, the estate owns it precisely **because** two of
      them are another application's, the 16 GB was index bloat that the
      reindex itself reclaimed, and the quiet window was **30 seconds**.
      Only "a human" held. The three days this line spent asking for
      finished work are `SNAG-ESTATE-008`.*

---

## Session 48: The execution sitting — advice, carried out ✅ (2026-08-15)

Three sittings (46, 47, 26c) went into making the diagnosis speak. This
one **carried out what it says**, and that is the whole finding: two
defects surfaced inside an hour, neither visible by reading the code,
both the same root cause — `recommendations.py` under-reading a finding
the sweep had already filled in.

### What was executed

- **`garmin-sync.service` removed.** The armed orphan, enabled since
  February, alerting since 14 Aug, `WorkingDirectory` pointing at a
  `PersonalAssistant` directory that no longer exists. The emitted
  command ran **verbatim** and worked: enablement symlink removed, unit
  file gone, `is-enabled` → `not-found`. First end-to-end proof that an
  orphan action is correct as written.
- **`sysadmin-tray.service` start limit bounded.** The emitted snippet
  applied to this repository's own unit. `systemd-analyze verify` silent,
  `LoadError=` empty, and systemd's own reading agrees with the advice's
  arithmetic exactly: `StartLimitIntervalUSec=1min`, `StartLimitBurst=5`,
  `RestartUSec=10s` — so the 5th start lands 40 s after the first, inside
  the window, and the limiter is reachable. `restart_bounded` flips
  `False → True` on the same `load_unit` the sweep calls, so the family
  drops from 13 to 12 on the next sweep.
- **Three host units wired into `services.yaml`** — `ethernet-optimise`,
  `paccache-timer`, `deadlock-api-ingest-user`. The first entries in that
  file produced by pasting endpoint output rather than written by hand.
  All three parse, resolve, and check **`ok`** against the live box.

### The two defects, both found only by executing

1. **The advice never asked whether the unit is meant to be running.**
   `grep -n "enabled" recommendations.py` returned nothing, while every
   finding carries a measured `enabled` the orphan family has trusted
   since Session 46. Two of the five host snippets named units that are
   **disabled and inactive**; pasting them would have declared checks
   returning `critical` **every 300 s, for ever** — verified by running
   `_check_systemd`'s logic against them. That is the pile-up shape
   Sessions 41–45 spent themselves deleting, arriving through this
   module's own remediation text, and with `SNAG-AGENT-006` still open it
   would have been one row per run: the same 12/hour that entry already
   measures as "60 for one dead timer in five hours".
2. **`removal_command` left a folded oneshot's timer behind.**
   `ticktick-sync.service` is an orphan whose `ticktick-sync.timer`
   declares `Requires=` on it; the emitted command removed only the
   service. `monitor_unit` already named the timer — `classify_units`
   folds it — and the builder ignored the field. The timer is also the
   half carrying `[Install]`, so it is the half holding the enablement
   symlink. Now removed first, so the schedule is disarmed before its
   service goes away.

And the rule both imply: **a row offering no snippet must not say "paste
the snippet below"**. `sysadmin-failed.service` shipped exactly that —
`snippet: ""` under paste instructions — which is an item an execution
sitting *cannot close*, so it returns on every sweep for ever. The
roll-up defect wearing a single unit's name. Every no-snippet row now
names its real next step, and for a disabled unit that step is a fork:
enable it and the next sweep emits a snippet, or remove it.

### What the fixture churn revealed

Twenty tests failed on the gate, because `UnitFinding.enabled` defaults
to `False` — correct for its first consumer, `armed`, where absent
evidence must read as "not armed" (quiet), and the **opposite polarity**
from this one, where absent evidence suppresses advice (loud). One field,
two consumers, opposite safe defaults. Fixed in the fixtures rather than
the default: flipping `UnitFinding.enabled` to `True` would quietly make
every orphan armed.

### Blocked, and named rather than dropped

- **Five system-scope orphans need `sudo`**, which needs a password this
  session cannot supply. Files backed up; exact commands in HANDOFF.md.
- **`services.yaml` is read at start-up**, so the three new entries are
  not live until `sysadmin.service` restarts — also `sudo`.
- **Eleven restart-unbounded units belong to other repositories** (Alfred
  1, estate-manager 3, SportsAnalyser 2, venture-assistant 1, plus five
  unowned). Left as advice: the monitor must not own what it monitors,
  and the endpoint's own `detail` says the edit is that repository's to
  make.

Suite **1708 passed** (from 1701), ruff and mypy clean, no migration.

**The collation half of the brief was already closed.** All 12 databases
report `datcollversion = 2.44` against a live 2.44, and all 8 alert rows
are `resolved` — one row each, so the dedup rule held. "8 stale
collations" was a stale reading.

## Session 47: The restart-limit family — advice, not alarm ✅ (2026-08-15)

`SNAG-UNITS-002`, the general case Session 46 filed rather than fixed.
17 of the 20 hand-written units on this box that declare `Restart=` have
a start limit their own restart cadence can never reach, so a crash loop
never enters `failed`, no `OnFailure=` hook can fire, and `systemctl
is-failed` reports nothing wrong.

Suite **1653 passed** (from 1631), ruff and mypy clean, **no migration** —
the family lives in the audit row's JSONB blob.

### The measurement that decided the design

The snag costed the fix as "one line per unit" under
`GET /api/units/actions`. Driving the real sweep in-process first showed
why that is not the cheap option it reads as:

| sweep category | unbounded units |
|---|---|
| **`monitored`** | **11** — `venture-*` ×4, `sportsanalyser-*` ×2, `alfred-inference`, `estate-manager-api`, `estate-manager-searxng{,-shim}`, `sysadmin-tray` |
| `orphaned` | 4 — both PersonalAssistant units, `offline-agents-dashboard`, `ticktick-sync-db` (all disarmed) |
| `host` | 2 — `deadlock-api-ingest` in both scopes |

`classify_units` drops `monitored` units before they become findings, so
**two thirds of the population had nothing to hang advice on**. The
detection had existed since Session 46 — `restart_is_bounded`, and
`restart_bounded` on every finding — and the question "which units here
can loop for ever" was answerable for six units and invisible for every
live service on the box.

### The three decisions, taken by the owner

- [x] **Scope: all of them, whoever owns the unit.** The tier already
      advises on units this repository does not own — every
      `unmonitored`/`host` recommendation tells you to wire another
      project's unit. The estate rule that bites is about *writing* into
      another repository, and a paste-ready line served over a GET is a
      pointer. The `detail` names the owning project so the reader knows
      whose edit it is
- [x] **Surface: advice-only, with the count as evidence in the roll-up's
      `details`.** Deliberately **not** added to `scan.actionable` —
      that is the roll-up alert's title *and* the number
      `alert_threshold` is compared against, so 13 latent risks would
      trip it on their own and read as 13 new gaps to wire up. No alert
      family of its own, for the reason the armed split was worth making
- [x] **Rank: second, above `unmonitored`.** The two are competing
      safety nets and this is the stronger one — a wedged unit is seen as
      `unreachable` only if something polls it, whereas a reachable start
      limit makes systemd itself say so, to a hook, whether or not this
      service is running

### What shipped

- [x] **`restart_risk_findings` in `scan.py`** — a second pass over the
      same units, not a fifth category. `units_scanned` is the sum of the
      four buckets and a monitored unit appearing twice would break the
      one arithmetic property `UnitScanSummary` exists to make auditable.
      Same shape `armed` already takes: a subset reported beside the sum,
      never inside it
- [x] **Orphans excluded, which is the opposite of the obvious rule.** A
      broken unit that also loops reads like the worst case and belongs
      here twice over; it cannot, because the orphan recommendation is
      *remove it* and a start limit on a file you should delete is two
      contradictory instructions. Nothing is lost — an armed orphan that
      loops is what `armed_alert_severity` already promotes to `critical`.
      **The family ships with 13, not 17**
- [x] **`UnitFinding` carries the three numbers the verdict came from**
      (`restart_sec`, `start_limit_interval`, `start_limit_burst`).
      Without them the boolean asks a reader to trust arithmetic they
      cannot see, and the naive version of that arithmetic is wrong in
      **both** directions. They are also what
      `suggested_start_limit_interval` needs to name a value that fixes
      *this* unit
- [x] **`suggested_start_limit_interval`** — smallest round window
      clearing `RestartSec x (burst - 1)` by 1.5x. The margin cuts the
      opposite way from the intuition: a *longer* `StartLimitIntervalSec`
      is a *stricter* limiter, because more starts fit inside it. Where
      no window helps (`RestartSec` beyond an hour, `infinity`) it emits
      **no snippet at all** and says to lower `RestartSec` instead
- [x] **The snippet targets the unit file**, `[Unit]` section, with
      `snippet_target` the absolute path rather than a filename so the
      two destinations cannot be confused. First time this module has
      emitted text for a file another repository owns
- [x] **Scope-suffixed titles for a unit installed twice.**
      `deadlock-api-ingest.service` is in both scopes running two
      different binaries and both are unbounded today; two rows headed
      identically read as one item listed twice

### Two tests that are the point

- [x] **The advice is fed back through the detection.** Every live
      `RestartSec` shape gets its suggested window passed to
      `restart_is_bounded`, which must return `True`. Detection and
      remedy are separate arithmetic and nothing else makes them agree —
      a remedy that clears a symptom without fixing the fault is the trap
      `ALTER DATABASE … REFRESH COLLATION VERSION` set for the collation
      family, and it is cheap to build here by accident
- [x] **The snippet is appended to a real unit file and the unit
      re-scanned**, which must leave the family. Nothing else proves the
      two lines land in a section systemd reads them from

### Verified live, then rolled back

The real sweep written to `unit_audits` and read back through the
router's rehydration: blob carries `restart_unbounded_count: 13`, the
arithmetic inputs survive JSONB (`restart_sec=10.0`, both limits `None`),
and `/actions` builds **25 recommendations — 6 orphan, 13 restart, 1
unmonitored, 5 host**. Residue 0; `unit_audits` still holds 50 rows with
the same newest `scanned_at`.

### Left open

- [ ] **`sysadmin.service` must be restarted** for any of this to reach
      the live API — the sweep runs on a 6-hourly interval *inside* the
      daemon, so a restart is the whole deploy. Two restarts are now
      owed: this and the SearXNG entry from 2026-08-14
- [ ] **The `host` tier still prints `deadlock-api-ingest.service`
      twice with identical titles.** Pre-existing and untouched — its
      snippets disambiguate via `_service_name`, so only the heading is
      ambiguous. Filed nowhere; it is one line in `_host_recommendation`
      if it ever annoys anyone
- [ ] **Nothing re-checks a unit after the snippet is pasted.** The
      family clears on the next sweep, which is up to 6 hours later, and
      there is no "you fixed 3 of 13" signal anywhere

## Session 46: The unit sweep learns to speak ✅ (2026-08-14)

_`SNAG-ESTATE-001`'s durable half, the "make an orphan finding speak"
part of it. Not a detection failure: `GET /api/units/status` had both
PersonalAssistant units classified `orphaned`, with the dead path and the
cause in plain English, eight days before anyone looked — while they
restart-looped 52,178 times and stalled the kernel. There was even an
open alert. What no surface said is **which two of the seventeen findings
were live**._

- [x] **The sweep measures arming.** An orphan is `armed` when systemd
      will start it — `category == "orphaned" and enabled`. Enablement is
      an enablement symlink under a `*.wants/`/`*.requires/` directory the
      sweep already walks, matched on link *name* so a dangling link left
      by an `rm` without a `disable` still counts. Cross-checked against
      `systemctl is-enabled` on every unit on this box: they agreed
- [x] **`restart_is_bounded` — the loop test is arithmetic, not the
      presence of a setting.** `RestartSec × (StartLimitBurst − 1) <
      StartLimitIntervalSec`, against systemd's documented manager
      defaults. Recorded on every finding, not only the ones that alert
- [x] **One alert row per armed orphan**, titled with the unit *and*
      scope, beside the roll-up rather than instead of it. Deduplicated
      on title; escalates `warning` → `critical` when the loop appears;
      swept against the titles the run **judged**, not the titles it
      raised
- [x] **`enabled` / `restart` / `restart_bounded` / `armed` on
      `UnitFindingInfo`, `armed` on `UnitScanSummary`** (a subset of
      `orphaned`, deliberately outside the sum), armed orphans ranked
      first within the orphan tier of `GET /api/units/actions`
- [x] 51 new tests — suite 1546 → 1597. No migration: `armed_count` is a
      scalar in the existing `findings` blob

**The obvious rule was wrong, and the live units refuted it before it was
written.** "`Restart=` with no `StartLimitBurst=`" is wrong in *both*
directions. `personalassistant-backend.service` declares no start limit,
so systemd's defaults apply — a limit does exist. It also sets
`RestartSec=10`, so five starts can never fit in the ten-second window,
the limiter is unreachable, and it restarted 34,517 times without once
entering `failed`. And a bare `Restart=always` restarts every 100ms, five
starts fit easily, and the loop *is* terminal — so the naive rule would
have opened a critical on most of this box's healthy services on its
first run.

**Verified against the live database in a rolled-back transaction**,
which was necessary rather than ceremonial: the suite stands in for
PostgreSQL's `LIKE` with mocks, so it cannot prove the prefix plus `NOT
IN (judged)` selects the right rows in real SQL. Five runs of one fault
wrote **2** rows — raise, dedup, escalate, hold, resolve once on clearing
— roll-up untouched, residue 0.

### Live on this box

```
44 units scanned, 6 orphaned, 1 armed

  [warning] Orphaned unit still enabled: garmin-sync.service (user)

  4 disabled orphans carry Restart=always with an unreachable start
  limit — the PersonalAssistant shape exactly, harmless only because
  someone disabled them. They stay in the roll-up as debt.
```

### Left open

- [ ] **The retirement checklist**, which is the other half of
      `SNAG-ESTATE-001`'s durable part. A process rather than code, and
      not this repository's to enforce — an estate convention if it is
      anyone's
- [x] **`SNAG-UNITS-002` — the general case.** *(Fixed 2026-08-15,
      Session 47 below.)* 15 of the 18 units on this box with a
      `Restart=` policy cannot reach `failed`, including every live
      service except `sysadmin`, `alfred-backend` and `alfred-frontend`.
      Not alerted on: 15 rows on the first run is the pile-up shape
      wearing a new hat. The snag carried two candidate fixes and the
      decision each needed; the second was taken, and **the count was 17
      of 20 by the time it was** — the population grows with every
      service the estate adds, because the defect is what a
      correctly-written unit gets by default here
- [ ] **`sysadmin.service` must be restarted to pick this up**, and the
      **organiser** is a separate deploy path — this agent is on a
      6-hourly interval inside the daemon, so a restart is the whole
      deploy

## Archive

- Sessions 10–23, 2026-07-24 maintenance, and SNAGs fixed in that period →
  [archive/completed_2026-08-05.md](archive/completed_2026-08-05.md)
- Sessions 1–9 (full service + tray app) →
  [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md)

## Session 42: The log storm — a raise rule, not a resolve rule ✅ (2026-08-12)

`SNAG-AGENT-005`, the last of the alert-table defects and the only one
that could still grow without bound. **598,091 unresolved rows**, 91 % of
every unresolved alert in the table, 99.8 % of them two Bluetooth
firmware messages emitted by a kernel retry loop at ~8.5 lines a second.

The session opened on the question the handoff said to settle first —
burst alerting, or drop log alerting entirely — and the answer turned out
to be neither of the two options as written.

### The decision, and the third option the data produced

Dedup-plus-quiet-resolve was chosen over both. A burst threshold
suppresses a *single* genuine critical until it repeats, which is the
wrong signal to lose; dropping alerting outright means a first-ever
critical from a service reaches nobody, and `GET /api/logs/stats` is a
surface nothing polls.

But plain dedup — one open row per source, the obvious reading — was
**refuted by the live table before any of it was written**. The kernel's
30-day error population:

| Message | Rows |
|---|---|
| `Bluetooth: hci0: Failed to set up firmware (-2)` | 297,390 |
| `Bluetooth: hci0: Failed to load firmware file (-2)` | 297,389 |
| `usb 1-11: device descriptor read/64, error -110` | 66 |
| `usb 1-11: device not accepting address 9/10, error -71` | 44 |
| `usb usb1-port11: unable to enumerate USB device` | 22 |
| `rcu: … detected expedited stalls` / `INFO: task … blocked on a mutex` | 8 |

Every one of those shares the title `Log error: kernel`. Dedup on that
title and the Bluetooth storm holds the single open row while **an RCU
stall and a USB enumeration failure go silent** — not a hypothetical, all
three are in the same window. Half a million rows traded for a mask over
every other kernel fault is not a fix, so the key is the message with its
variable parts removed.

- [x] **`sysadmin/monitor/log_signature.py`** — digit runs → `N`, hex
      literals → `0xN`, whitespace collapsed. Collapses 594,779 Bluetooth
      lines to 2 signatures and 110 USB lines to 2, and leaves all six
      distinct faults distinguishable. The signature goes **in the
      title**, not in `details`: dedup, the set-based resolve and the
      tray's `{severity}:{title}` fingerprint all key on title already, so
      nothing new is needed and none of them can disagree about identity
      — and four open rows all reading `Log error: kernel` are
      indistinguishable to the person looking at the tray
- [x] **One row per fault, repeats bump `details['occurrences']`.** The
      count that used to be expressed as row volume, at 1/300,000th of the
      storage and legible on one line. `details` is *reassigned* rather
      than mutated — SQLAlchemy does not track mutation inside a plain
      JSONB dict, so an in-place update would look like it worked, write
      nothing, and leave `last_seen_at` frozen while the fault fired
- [x] **`_resolve_quiet` — silence is the only recovery signal an event
      has.** 15 minutes, i.e. 15 polls. Excluded by exact title as well as
      by age, because an exclusion set cannot race the clock that stamped
      the row; `COALESCE(details->>'last_seen_at', created_at)` so the
      pre-existing backlog is reachable at all
- [x] **`_open_alerts` bounded by the titles this run raised.** Written
      first as "every unresolved row this agent owns", which on the live
      table is **593,814 ORM objects on the first run** — the fix falling
      over on the backlog it exists to end. Caught before deployment, not
      after
- [x] **598,091 rows resolved as `superseded`**, in one statement, with
      the reason in `details`. Table-wide unresolved alerts: **2**

### The two smaller defects, fixed in the same sitting

- [x] **Double ingest.** `read_journal` resumes from `__CURSOR`, not from
      `since="2m ago"` on a 60-second poll. A cursor rather than a
      narrower window because narrowing trades the duplicate for a *gap*
      whenever a run runs long, and a gap is the worse failure for a
      monitor. Proven live: back-to-back runs ingested **96 then 0**. The
      cursor advances over every entry read, **not** only those surviving
      the severity filter — otherwise the resume point sits behind a run
      of info-level noise and the whole defect returns one layer down. It
      is in memory, so a restart falls back to the newest `logged_at`
      already stored for that source, passed as `--since @<epoch>`
      because journalctl reads a bare datetime as **local** time
- [x] **The silent `-n 500` cap** is now `details['truncated_sources']`.
      The ceiling stays — 8.5 messages a second makes it unavoidable —
      but `findings_count` sitting at exactly 200 on every run was the
      symptom nobody read. Sources are **named**, not counted: which one
      is at its ceiling decides whether it matters

### Verified live, 2026-08-12

```
2000 kernel error lines in 10 min -> 2 alert rows
  x1000  Log error: kernel — Bluetooth: hciN: Failed to load firmware file (-N)
  x1000  Log error: kernel — Bluetooth: hciN: Failed to set up firmware (-N)
  (old rule: 2000 rows, all titled 'Log error: kernel')
```

### Left open

- [ ] **The host fault is untouched and is now harder to stop.**
      `BT_RAM_CODE_MT6639_2_1_hdr.bin` is still absent from
      `/lib/firmware/mediatek/mt7927/`, and `rfkill list` now prints
      **nothing** — the adapter no longer registers a soft-block switch,
      so the one reversible workaround the handoff recorded is gone. This
      is deliberately not this repository's to fix; the point of Session
      42 is that the storm now costs 2 alert rows instead of 43,000 a day
- [ ] **`sysadmin.service` must be restarted to pick this up.** It is a
      **system** unit (`systemctl`, not `--user`) running from this
      working tree, so the running daemon serves start-time code and is
      still on the old raise rule
