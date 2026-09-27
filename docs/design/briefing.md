# Briefing envelope — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**The briefing envelope is additive, and `sections` is the part Alfred
owns.** `GET /api/sysadmin/briefing/preview` carries `schema`, `period`,
`summary`, `alerts[]` and `facts{}` *alongside* `sections` and
`generated_at` — never replacing them, because Alfred's `adapt_sysadmin`
reads both and returns one red error section if `sections` is missing.
Alfred owns the section contract by its ADR-0063 and normalises every
producer into it; this service owns the envelope round it. There is no
`generated` key beside `generated_at`: two stamps holding one value is a
fork waiting to happen.

Four rules `sysadmin/briefing/data.py` encodes:

1. **`generated_at` cannot express staleness on a pulled endpoint.**
   Alfred's check is real (`_producer_timestamp` → `produced_at`, flagged
   at a 12-hour gap) and cannot fire, because the payload is stamped when
   the request is answered — an organiser dead three days still yields a
   payload one second old. Every `facts` block carries `measured_at`,
   `facts.stale_sources` names anything over 26 hours, and `summary` says
   it in words. It caught `filesystem` at five days on its first live run.
2. **`period` is anchored to `schedules.briefing_hour`, not to the last
   pull.** Two consumers polling would each shorten the other's window,
   and storing a row per pull makes this route a pull log. `anchor` is in
   the payload because the wrong reading is the one a consumer assumes.
3. **`facts` is a projection, not a copy** — counts and identifiers,
   never the rows the sections render. A facts block containing the whole
   payload cannot be diffed, which is the only reason it exists. A test
   asserts every list in it holds scalars.
4. **`summary` is deterministic.** The weekly disk review is LLM-narrated
   and pays for it with a figure-free prompt and a markdown stripper; a
   summary made only of numbers gains nothing from that and would take the
   06:00 path down with llama-server.

The briefing's **project half is gone** (2026-08-13, ADR-0005). "Project
Health", "Pick This Up" and "Weekly Project Review" come from the estate's
own producer (`GET :8400/api/estate/briefing`), which Alfred pulls
separately by its ADR-0070; `briefing/preview` keeps the machine sections
— Infrastructure, Overnight Logs, Filesystem, Weekly Disk Review — **and
the alert digest**, so the alerting path never routes through the estate.
`SNAG-BRIEF-001` (the two project sections disagreeing inside one payload,
26 rows against 5) and `SNAG-BRIEF-002` (a next action cut mid-word with
no marker) were both fixed here before the move and are the estate's to
keep fixed. `truncate_at_word`, which always marks the cut, went with them
to `estate.text`; `NEXT_ACTION_CHARS` still governs the alert messages
this service writes.
