# GPU figure — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**The GPU figure this service publishes is the counter the GPU gate
reads, and until 2026-09-22 it was a different instrument answering in
the same vocabulary** (Session 248, `SNAG-GPU-004`). `sysadmin/monitor/gpu.py`
launched two `rocm-smi` subprocesses concurrently, one of them querying
temperature, meminfo and power — and those sensor queries are themselves
GPU work landing inside the window `GPU use (%)` is averaged over, so the
act of taking the reading disturbed it. Three interleaved arms, same
card, same minute, n=30 each: sysfs `gpu_busy_percent` sd **0.7**, one
bare `rocm-smi --showuse` sd **0.8**, this collector sd **9.3** with two
readings of exactly **0** against a card holding 10.5 GB at ~100 W.
`rocm-smi` is not the culprit; the invocation is. `gpu_percent` for the
dGPU now comes from `estate.gpu.sample_gpu_busy` resolved by PCI slot,
and `rocm-smi` keeps only what it alone supplies — product name,
temperature, VRAM, power.

Five rules, four of them the opposite of the obvious implementation:

1. **The counter is sampled *before* the subprocesses, and that is half
   the fix rather than a detail.** The entry recorded the ordering as
   corroboration — a sysfs read bracketing one `rocm-smi` call gave sd
   **0.2** before and **3.1** ~55 ms after, off the same file — which
   makes a post-spawn read a fix that inherits the perturbation it
   exists to remove, passes every test written for it, and merely
   measures less badly. A test pins the call *order*, because no
   assertion about the returned value can see it.
2. **The dGPU is resolved by PCI slot, and the slot is asked of the
   payload rather than of an index** (`SNAG-GPU-005`). `rocm-smi` and
   DRM enumerate this box's two cards in **opposite** order — the
   RX 7900 XTX is `rocm-smi`'s `card0` and DRM's `card1` — so `card0` is
   a vocabulary and never an identity, and one stored row already
   carried the swap with nothing saying so. `--showbus` rides in the
   existing invocation at no extra subprocess, every row on **both**
   paths carries `pci_slot`, and the match is `data["PCI Bus"] ==
   dgpu_pci_slot`: keying on `card_id == "card0"` works here by luck and
   names the iGPU on a box that enumerates the other way. This is
   `estate.gpu`'s opening rule, stated one repository over and not
   obeyed here.
3. **The slot is the caller's, so the collector and the gate cannot
   part company.** `SysAdminAgent._take_resource_snapshot` passes
   `config.llm.gpu_pci_slot` — the leaf `ensure_gpu_idle` already reads
   — rather than the collector reading config itself or defaulting
   silently. A test asserts the agent passes a slot that is *not* the
   module default, because an assertion against the default passes
   whether the agent passes anything at all.
4. **Every row says which instrument answered it.** A perturbed reading
   and a clean one are the same integer in the same field, so
   `gpu_percent_source` is `sysfs` or `rocm-smi` — `SNAG-API-004`'s
   lesson, and the property whose absence let this figure be recruited
   into a cross-repo finding against a sampler that was right. The iGPU
   keeps `rocm-smi`'s value and says so, since `sample_gpu_busy` answers
   for one slot; the mixed payload is legible rather than silent. It is
   written on every row rather than only the interesting one (Session
   128's rule), which is also what makes the pre-2026-09-22 rows legible
   **by absence**.
5. **An unresolvable slot falls back to the tool and never blanks the
   figure.** No threshold reads `gpu_percent` — `_check_thresholds` reads
   `temp_c` and `vram_percent` — so there is no alert to fail open or
   closed, and a labelled imperfect figure beats none for the human,
   `GET /api/sysadmin/resources` and the briefing that do read it. **The
   cost of an unjudged figure is not zero, it is deferred until somebody
   reasons from it**, which is what this entry is a record of.

Two things only the live half can say, so they are
`tests/test_gpu_live.py` rather than fixtures. That `rocm-smi` still
publishes the key the slot match is made on — a tool that dropped
`--showbus` would leave every row reverting to the perturbed figure with
nothing red, quiet and correct by its own lights — and that the counter
is readable at the configured slot at all, `sample_gpu_busy` failing
**open** by design. The premise test spreads `METRICS_ARGS` rather than
restating the flags, because two statements of one argument list can
disagree and the one that would go quiet is the `--showbus` the whole
match rests on.

**The historic rows are deliberately not backfilled.** The single
fallback specimen carries `card0` at 2048 MB beside `card1` at 24560, so
it identifies its own devices from inside itself and nothing is
recoverable that a reader does not already have; writing today's
enumeration onto a seven-week-old row asserts a mapping no evidence from
that day supports. `message_backfill` could repair its ten rows because
`raw_line` held the record's own `MESSAGE` byte-for-byte and made the
repair *exact* — there is no such witness here, and a repair that cannot
be witnessed is refused rather than approximated.
