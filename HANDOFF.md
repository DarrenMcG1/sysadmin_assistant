# Handoff — 2026-08-27

## Next action

Judge `SNAG-ESTATE-004`, whose check has read **refuted** since Session 102's postflight and which nothing has acted on: drive `default_port_uncontended` once more to confirm the estate is still filing `claimed_tool_default` for 3000, 5000, 8080, 8888 and 9000, read `estate_module_state` to separate a committed fix from an edit in flight the way `SNAG-ROADMAP-001`'s closure did, and then either close the entry — in which case its check leaves the registry with it, taking checks-in-registry 23 → 22 while `convention:unchecked` stays at 1 — or record why a delegated entry whose enforcement has landed elsewhere stays open, which is a judgement no sitting here has yet had to make about a claim refuted by the *other* repository doing the work.

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
