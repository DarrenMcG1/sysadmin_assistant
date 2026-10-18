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

Six rules, five of them the opposite of the obvious implementation:

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
6. **A runtime-suspended card reads 0, and the row says
   `runtime-pm`** (Session 310, 2026-10-01, from estate-manager's
   ADR-0227 and their message `81c4070e`). From that ADR on,
   `sample_gpu_busy` answers 0 for a suspended card without reading the
   counter, because a suspended card has nothing running on it and its
   driver refuses the read rather than wake it. Stored as it came, the 0
   would be labelled `sysfs`, a counter reading that never happened. The
   old answer was worse: `None`, then a fallback to `rocm-smi`, whose
   queries wake the card. On 2026-09-27/28, with both monitors off for
   9.5 h, that fallback wrote **92** dGPU rows, 75 at 0 and 17 at
   1–15 % with the card drawing power. So the collector asks
   `power/runtime_status` itself, first — reading it never wakes the
   device, so rule 1's order holds — and labels a suspended card
   `runtime-pm` on both paths. The library checks the state a second
   time after a refused read; a 0 from that check is still labelled
   `sysfs`. The window is one file read, and the figure is right either
   way.

   **The label changed; the wake did not** (Session 313, 2026-10-01).
   "A fallback to `rocm-smi`, whose queries wake the card" reads as if
   the wake belonged to the fallback. It belongs to the invocation:
   `_from_rocm_smi` spawns `rocm-smi` for temperature, VRAM and power
   after `runtime_status` reads `suspended`, so every poll of a
   suspended card still resumes it. Measured over the same night: all
   93 suspended-card polls were followed by a kernel `PSP is resuming`
   line 2.4–3.1 s after `recorded_at`, one resume in three of the
   night's 283. Rule 7 stops it.
7. **A suspended dGPU is never handed to `rocm-smi`, and nothing of it
   is read but its power state** (Session 323, 2026-10-02; the module's
   rule 6). `get_gpu_usage` asks `power/runtime_status` before choosing
   a path and takes `_from_sysfs` for a suspended card, which reads no
   `hwmon` or `mem_info` attribute of it: temperature, VRAM and power are
   `None`, and the threshold checks already read `None` as unmeasured.
   `_from_rocm_smi` no longer asks the state at all.

   **Chosen without the measurement it was waiting for.** The overnight
   drive of 2026-10-02 (`scripts/dgpu-wake-drive.py`, 01:30–05:30) logged
   240 trials and every one `skipped: not suspended`: the card's
   `runtime_suspended_time` is 0 for the whole boot, and of 1,133 dGPU
   rows since the 28 September reboot into kernel 7.2.7 not one came
   from `rocm-smi`, against 93 of 285 the night before on 6.18 LTS. So
   neither candidate read was measured. That decided it. *Query the
   iGPU alone* (`rocm-smi -d <iGPU>`) rested on the tool not opening
   every card at start-up, which nobody has seen. *Take the row from
   sysfs with the three fields `None`* rests only on the attribute rule
   6 already relies on. Its cost: on such a poll the rows are keyed and
   named in DRM's vocabulary (rule 2), `card1` rather than the product
   name, and `pci_slot` tells them apart.

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

## A resident evicted to GTT (2026-10-18, Session 384)

**A service declaring `holds_vram` reads `degraded` when its VRAM has
been pushed into GTT**, and the rules are in the docstring of
`sysadmin/monitor/gpu_residency.py`. Estate message
`af170afe-54d0-4997-8a10-42267c6a2214` reported `alfred-inference` with
1.0 GiB of its 2.2 GiB in GTT hours after a game had ended, and said the
estate's queue would not publish the per-resident split. So the monitor
records it, as a third term of the check that already writes the
`service_health` row, after ADR-0007's GPU-context term and for the same
reason: the reading is a predicate the kernel publishes per process, and
the unit's restart closes it.

The figure is `drm-total-vram` less `drm-resident-vram`, summed over the
main PID's distinct DRM clients on `llm.gpu_pci_slot`, clamped at zero,
against a 128 MiB floor. `amd-evicted-vram` read 0 KiB beside the 1.0 GiB
shortfall, so it is not the figure. A declared service with no client on
the card (`venture-embed`'s CPU-only boot start) is recorded and not
judged. The reading sits beside the 300 s poll, not on a feed of its
own, which is the continuous GPU feed the estate's ADR-0189 §4 left here.
