# Handoff — 2026-08-27

## Next action

Take `SNAG-AGENT-007` — `SysAdminAgent._active_alerts` issues four unbounded reads of `alerts` per 300-second run and materialises whole ORM rows, and the entry's own body names the tension the fix turns on, since the dedup caller needs titles alone while a `select(Alert.title)` projection beside it is a second definition of *this agent's open rows* — so the sitting's real question is where the one definition lives rather than how to write the query, and it is the first entry to be taken since the register ran out of checks to write, which is the direction the whole family was built to run in and has never once been run in.

## Session 104 is complete — the first entry closed because the delegate did the work

`SNAG-ESTATE-004` is **closed**. Open **24 → 23**, entries unmoved at
**94** either side (driven through `estate.snags.read_snags` before and
after), checks-in-registry **23 → 22**, `convention:unchecked` unmoved at
**1**. Suite **2751 → 2722** — 347 − 29 in `tests/test_snag_claims.py`,
stated as a subtraction because a green suite cannot witness tests that
no longer exist. The other 22 checks all hold. Daemon restarted
**19:16:31**, `/health` 200.

### What the sitting settled

- **The judgement the handoff asked for, and it went the short way.** A
  delegated entry is not a different kind of entry — delegation changes
  who does the work, never whose box the claim is about. This entry's
  claim is *the rule is enforced by nobody*, and that claim is now false
  on the estate's published surface, so it closes. Holding it open to
  track the delegate's rollout would make this repository a second owner
  of their deploy state, which is the defect the estate rules exist to
  prevent and which `SNAG-ROADMAP-001`'s closure had already refused
  once.
- **The trigger was `estate_module_state()` and nothing else.** It reads
  **committed**, which is what separates a landed fix from an edit in
  flight — the distinction that function was written for within an hour
  of needing it, and the only reason either of the two cross-repo
  closures has fired.
- **Committed *and* deployed, which is stronger than the precedent
  needed and is deliberately not the test.** The estate's live audit
  carries `ports:port 8080:claimed_tool_default` at `info`, first seen
  **15:00:13Z**, 4 runs observed, naming venture-assistant and quoting
  §2.1 in its summary. Recorded as evidence. The precedent closed
  *without* it and named the reason discharged rather than met; nothing
  here was judged on it.
- **The entry died the right way round.** §2.1 still states *"Never take
  a tool's default port"*, so the complaint went and the premise did not
  — the distinction the check reports apart, and the reason a single
  boolean over its two halves would have filed a deleted rule as a job
  well done.
- **The delegated constant changed shape, and that is the one occasion
  the check's design could be tested.** Their branch is a **dict** keyed
  port → tool names, not the `WELL_KNOWN_DEFAULTS` *set* the entry
  proposed, and they measured before typing: nine of seventeen registry
  rows sit on some tool's default depending on which tools are counted,
  so the five named here were right today by luck and 1883, 8384 and
  22000 are absent by decision. The obvious probe — an `ast` walk for the
  name the entry proposed — is refused in the check's own docstring
  because a fix that *inlines the set, renames it, or files from another
  module* would each read as **still holds**. The fix renamed **and**
  reshaped it. An argument written in advance is only worth what it is
  worth on the day it is tested, and this one was.
- **What the closure found on this side is older than the fix that
  prompted it.** `judgements.JUDGED_AUDIT_SEVERITY` enumerated the
  estate's ports vocabulary as **two** codes; it is **four**, and the
  omitted one — `dormant_but_listening` at `info` — has been theirs since
  2026-08-13. So the sentence was incomplete the day it was typed rather
  than made stale by the new branch, which is the more uncomfortable of
  the two readings and the one the correction now states. Neither `info`
  code reaches `judge_audit_findings`, which filters on `breach`, and
  that is right twice over: this entry's own fix bullet **asked** for
  `SEVERITY_INFO`, and `info` sits below `tray.notify_min_severity` here,
  so a judged row would be silent. What was missing was the record of the
  decision — `SNAG-CFG-001`'s shape — and it is written down rather than
  answered by alerting on a finding this repository asked to be advisory.
- **The id resolves wrongly rather than not at all, so the citation is
  repo-qualified now.** estate-manager's message `153c1c96` measures it:
  71 `SNAG-ESTATE-*` entries there to 14 here, **all 14 collide**, every
  pair a different defect, and their `SNAG-ESTATE-004` is an abandoned
  `projects.project_meta` prototype closed **2026-08-13, the day before
  this delegation was filed** — so a lookup answers plausibly and stops
  the session, and the more diligent the session the more reliably it
  stops. This entry *knew* the ids would not correspond and said so in
  this repository's document, which reached a reader of the snag list and
  not a reader of their inbox.

### Decisions taken, and what was rejected

- **The check left the registry with its entry**, which
  `test_every_checked_entry_is_open` already makes a rule: a check
  outliving its entry re-measures a claim nobody reads, and a refuted
  check on a closed entry says *go and judge this* for ever. Removed:
  `check_default_port_uncontended`, `ESTATE_PORT_RULE_PATHS`,
  `DEFAULT_PORT_RULE`, `ENTRY_DEFAULT_PORTS`, `DEFAULT_PORT_PROBE`,
  `_probe_ports`, `_finding_rows`, `_names_port`, and 29 tests.
  `estate_probe`, `estate_module_state`, `ESTATE_REGISTRY` and `_named`
  stayed — reachable from other checks, checked by line rather than
  assumed.
- **Two `:func:` references to the removed check were repaired rather
  than left dangling**, one in `check_queue_stamps_local`'s docstring and
  one in a test's, because a pointer to a function that no longer exists
  is the stale artefact this repository files entries about.
- **Rejected: filing a new snag for the unjudged `info` findings.** The
  silence is a decision this repository asked for, so what was owed was
  the record and not an entry; an entry would imply an unfixed defect
  where there is a stated policy.
- **Rejected: closing estate-manager's message `153c1c96`.** The half
  this repository owns is discharged — the counterpart is cited
  repo-qualified in the closed entry — but the rule it recommends, that
  snag ids be repo-qualified everywhere, binds Alfred and estate-manager
  too, and their own message routes it to the owner rather than to a
  session. **This is the one thing waiting on the owner.**
- **The restart is the twentieth in a row that moved nothing a caller can
  observe, and the first where the edited file is one the daemon
  imports.** `sysadmin.estate.judgements` is the estate judge's; what
  moved inside it is a comment. The previous sitting's measurement is
  what makes that sayable — the nineteen before it rested on the file
  being unimportable, which is a different claim and only one of the two
  was ever checked.

---

*Previously:*

## Session 103 is complete — the twenty-fifth check, and the register runs out of entries

`SNAG-ESTATE-006` is **checked and stays open**; `SNAG-ESTATE-014` is
**closed** and `SNAG-DOCS-006` **opened** as its stated cost. Checked
entries **22 → 23**, unchecked **2 → 1**, open unmoved at **24** — one
closed, one opened — measured either side of the edit by driving
`load_entries`, and by estate-manager's `read_snags`, which reads
**93 → 94 rows / 24 open**. Suite **2731 → 2751**,
`tests/test_snag_claims.py` **327 → 347**.

### What the sitting settled

- **Two instruments, and the second exists because the first goes blind
  at the finish line.** The live wire is read through
  `estate.client.pull_all` — the call the judge itself makes, so the
  path, base URL and failure handling are the consumer's rather than a
  second set that can disagree — and the specimen drives the producer's
  own `findings()` route in their interpreter. Across **135 audit runs
  the audit has never once been clean**, so rule 1's weather problem does
  not bite the way it did for the nudge surface. What bites is the *end*
  state: a clean audit publishes `"findings": []` and says nothing about
  its own key set, so a wire-only check reports `unknown` on precisely
  the morning the estate becomes conformant.
- **The wire can refute and cannot confirm.** A `code` key on a served
  finding kills the claim whatever the checkout says; its absence is one
  deploy behind by construction, which is `estate_module_state`'s
  "committed is not deployed" read the other way and is named rather than
  measured, for that function's own reason.
- **The two readings produced the identical eleven-key set**, which makes
  the wire a **control on the specimen** rather than only extra evidence:
  a stand-in drifted from their query shape could not have done that.
- **No database is opened in either repository.** The key set is decided
  by a literal dict in their serialiser, so the session is a stand-in
  dispatching on SQLAlchemy's public `column_descriptions` — a reordered
  query raises rather than being answered wrongly — and `get_db_session`
  is poisoned **before** their router is imported, which is
  `QUEUE_TIMEZONE_PROBE`'s `UserSystemd(runner=refuse)` one surface over.
- **The entry's *not worked around here* bullet is a constraint on the
  instrument, not a note beside it.** Nothing splits `fingerprint`; the
  reading is the set of published keys; and a test walks this module's
  source *and* its probe string for such a split, because the cheapest
  way for a later sitting to make the check "better" is the one thing the
  entry forbids.
- **What the entry does not say**: `Finding.as_payload` — the form
  published on `estate/audit/findings/{check}` — **does** carry `code`.
  It is not computed-and-dropped everywhere, only on the one surface this
  repository reads. Carried as evidence and kept out of the verdict,
  because the claim that matters is about the surface the judge pulls.
- **Three falsifications passed against deliberately broken code**, the
  fifth, sixth and seventh here, and each was a repair to the *check*
  rather than a wider patch. The substring one passed because the test
  varied the **wire's** detail blob while the rule lived in the
  **probe's** — and it could only do that because `WireReading.detail_keys`
  was collected and read by nothing, `SNAG-CFG-001`'s shape inside a
  check written in the repository that named it; the wire now refutes
  through a detail blob too. The two fingerprint ones showed a detector
  aimed at the shape the *producer* uses: `str(f.fingerprint).rsplit(…)`
  hides behind a `Call` receiver, and `payload.get("fingerprint")
  .rsplit(…)` hides behind a **dict key**, which is how *this* module
  would really reach it since it reads JSON and never producer objects.

### The judgement

- **`SNAG-ESTATE-014` is closed, and the trigger it was handed does not
  exist.** The sitting was asked whether `convention:unchecked` *reaching
  zero* should retire it. It reaches **one**, and the one is the entry —
  and it cannot reach zero while the entry is open, because that entry's
  own judgement rules it permanently unmeasurable. A sitting waiting for
  zero would have waited for ever.
- **What closes it is that it is about a harm and not a count.** Its
  sentence is *"their claims are only as fresh as the last hand sweep"*,
  and the number of entries in that condition is now **nought**: every
  open entry but that one carries a check, and its own claim is published
  every run by the finding it is about. The count is one and the harm is
  nought, and the entry is about the harm.
- **Its objection to exempting itself does reach the closure and is
  answered rather than dodged.** *"The first user of the category to
  subtract itself from its own subject"* is true of a closure as much as
  of an exemption; the effect on the sentence is identical. What
  separates them is whether the work is finished, and *one check per
  sitting* has run out of entries — so the refusal recorded there stands
  unamended and does not extend to this.
- **That the machinery survives was demonstrated by accident.** Filing
  `SNAG-DOCS-006` in the same edit put the report straight back to
  `1 of 24` naming it, with `SNAG-ESTATE-014` closed. That is the
  argument for closing it arriving as evidence instead of as reasoning.
- **`SNAG-DOCS-006` is the stated cost**: `check_convention` emits the
  finding only when the set is non-empty, so a register in which every
  open entry is checked says *nothing* rather than saying nought —
  `ports_checked`'s rule arriving at the register, and a fifth way for
  that count to move where the closed entry catalogued three. Filed and
  not fixed, because `_convention` returns `unknown` unconditionally and
  a zero line today would pin `sysadmin-check-snags` at exit 2 for ever.
- **Not `SNAG-ESTATE-015`**, and the reason arrived this morning:
  estate-manager's message `153c1c96` records that namespace as having
  **two minters and no owner** — all 14 ids here collide with one of
  their 71 and every pair names a different defect, so an id-shaped
  lookup answers plausibly and wrongly. `SNAG-DOCS-*` is this
  repository's alone, measured against their list the same afternoon.

### Open, and for the owner

- **The estate message `153c1c96` is left open deliberately.** Its own
  text says nothing is asked; its recommendation — that snag ids be cited
  repo-qualified across repositories — changes how this repository and
  Alfred write, which their note says fails the routing test in the
  owner's global `CLAUDE.md` and is the owner's call rather than a
  session's. This sitting acted on it only to the extent of not minting a
  fifteenth colliding id, which is not enough to close it on.
- **`SNAG-ESTATE-004` reads red** and is the next action above.
- The daemon was restarted at **18:57:23**. The eighteen sittings before
  this one asserted that "nothing the daemon imports" moved; this one
  **measured** it — `create_app()` was built in-process and `sys.modules`
  asked afterwards, and `sysadmin.snag_claims` is not among the modules
  the application loads. Route count unmoved at 51.
