# ADR-0004: The llama client's mechanics move to estate-lib; the None-convention stays

- **Status**: accepted
- **Date**: 2026-08-12
- **Executed under**: estate-manager Session 3 (the founding inference
  extraction — the bounded exception in estate ADR-0002 under which an
  estate session edits this repository), recording the decision in this
  repository's own sequence per that same ADR
- **Estate side**: [estate-manager ADR-0006](../../../estate-manager/docs/adr/0006-shared-library-shape.md)

## Context

`sysadmin/core/llm_client.py` was one of three llama-server clients on
this box (121 lines here, 163 in Alfred, 155 in venture-assistant), all
speaking the same OpenAI-compatible API to the same class of server. The
estate's survey (2026-08-12) found the trio drifted in mechanics that
were never meant to differ — and this service's copy was the barest: no
retry, no breaker, no GPU guard, sharing Alfred's `:8081` as a second
uncoordinated consumer.

`sysadmin/core/text.py` separately carried `TRUNCATION_MARKER` with a
comment asserting it "matches the marker Alfred's own `sanitise_text`
appends" — it never did. Alfred's constant is `"\n\n… (truncated)"`;
ours joined the bare token with a space. Each side believed it matched.

## Decision

- **The wire mechanics move**: payload construction, POST with typed
  errors, content extraction and the health probe come from
  `estate.llama`. `pyproject.toml` gains `estate-lib` as an editable
  relative-path uv source (estate ADR-0006 decision 4 — no rollout
  gate, accepted).
- **The conventions stay**: `LLMClient`'s public interface is unchanged;
  failures still degrade to `None` with the same log events
  (`llm_unavailable`, `llm_error`, `llm_malformed_response`,
  `llm_unexpected_error`); `LoopBoundClient` still owns the client
  lifecycle (SNAG-AGENT-003), which is possible precisely because the
  estate library takes the `httpx.AsyncClient` as an argument.
- **The free-text path keeps the server's sampling defaults**
  (`temperature=None`): this client generates prose narratives, not
  structured extraction, so the estate's structured-path `temperature: 0`
  default does not apply here.
- **`TRUNCATION_MARKER` is imported from `estate.text`** and re-exported
  from `sysadmin.core.text`; the false parity comment is corrected. The
  visible token is now shared by import; the single-space separator in
  `truncate_at_word` is explicitly ours.

## What this deliberately does not do

- **No GPU guard is added.** This service remains the estate's unguarded
  inference consumer. Adding `estate.gpu` gating to the dispatch path is
  a behaviour change for this repository to weigh in its own session —
  it is now one import away instead of a copied file. Until then the
  queue service (estate Session 3's second half) is the plan of record
  for arbitrating `:8081`.
- **No retry, no breaker.** Same reasoning: those are behaviour changes,
  not extractions.

## Amendment, same day: the guard arrives after all

"What this deliberately does not do" said no GPU guard would be added —
a behaviour change does not belong inside an extraction. That reasoning
stands; what changed is that **the owner instructed the change
directly** (2026-08-12, estate Session 3 follow-up), which is the
delegation rule's own exception: estate ADR-0002 constrains what an
estate session may decide for this repository, not what its owner may.

- `generate()` now runs `estate.gpu.ensure_gpu_idle` before dispatch. A
  busy dGPU logs `llm_gpu_busy` (with the numbers) and returns `None` —
  the same first-class "no narrative" outcome callers already handle,
  because this service's inference is deferrable housekeeping sharing
  Alfred's server on a GPU someone may be gaming on.
- `is_available()` is **not** gated: it answers "is the server up", and
  a busy GPU must not make the server look down.
- `LLMConfig` gains `gpu_pci_slot` / `gpu_busy_threshold`, **defaulting
  to the estate's constants** (`estate.gpu.DGPU_PCI_SLOT`,
  `DEFAULT_BUSY_THRESHOLD`) so this repository never transcribes the
  slot or threshold — the third transcription was the drift being
  prevented. Empty slot disables the gate; unreadable counter fails
  open, per the estate contract.
- Estate-side record: estate ADR-0006's same-day amendment; closes
  estate `SNAG-ESTATE-006`.

Takes effect on this service's next restart (the running process holds
the old module).

## Consequences

- One minor logging change: a 200 response with a non-JSON body now logs
  `llm_malformed_response` (warning) instead of `llm_unexpected_error`
  (error) — the library classifies it as an invalid response, which it
  is. All 17 client tests and all text tests pass unchanged.
- This service now depends on a repository outside its own tree. The
  dependency is import-time only and carries no network hop; estate
  death does not affect this client (estate ADR-0001's alerting-path
  rule is untouched).
