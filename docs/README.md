# docs/

Everything here is written for someone deciding whether a change is safe to
make. It is unusually long for a project this size, deliberately: this
repository keeps the reasoning rather than only the result, so most documents
record what was measured, which options were rejected, and what the previous
attempt got wrong.

If you are visiting rather than working here, the fastest way to see what that
means is [`roadmap/snag_list.md`](roadmap/snag_list.md) — open it at any entry
and read the bullets beneath it.

---

## Where to start

| If you want to | Read |
|---|---|
| understand a decision, or why an obvious approach was *not* taken | [`adr/`](adr/) |
| know what is broken and what is known-but-unfixed | [`roadmap/snag_list.md`](roadmap/snag_list.md) |
| know what is being worked on now | [`roadmap/STATUS.md`](roadmap/STATUS.md) (first 50 lines) |
| follow the session-by-session record | [`roadmap/tasks.md`](roadmap/tasks.md) |
| see the shape of the system | [`ARCHITECTURE.md`](ARCHITECTURE.md) — **but see the caveat below** |
| set up bearer-token auth | [`guides/api_auth.md`](guides/api_auth.md) |
| work in this repository with Claude Code | [`../CLAUDE.md`](../CLAUDE.md) |

## Architecture decision records — `adr/`

Ten records. They are the highest-value documents here for a reader who is not
going to read the code, because each one states the alternatives that were
measured and refused, not only the option taken.

| | |
|---|---|
| [ADR-0001](adr/0001-project-registry.md) | project identity lives in the repositories |
| [ADR-0002](adr/0002-estate-manager.md) | *(moved — pointer only)* shared infrastructure gets a non-application owner |
| [ADR-0003](adr/0003-mqtt-credential-by-loadcredential.md) | the broker credential arrives by `LoadCredential` |
| [ADR-0004](adr/0004-estate-lib-client-core.md) | the LLM client's mechanics move to a shared library |
| [ADR-0005](adr/0005-project-state-leaves.md) | **project state leaves this repository** — read before writing anything about projects here |
| [ADR-0006](adr/0006-wiring-joins-ports.md) | admitting a second audit check, and why the filter had to change shape |
| [ADR-0007](adr/0007-a-poisoned-gpu-context-is-a-predicate.md) | a poisoned GPU context is a predicate, not a state |
| [ADR-0008](adr/0008-the-file-half-of-the-wiring-check.md) | moving a check relocates the comparator, not the operands |
| [ADR-0009](adr/0009-the-remote-is-two-questions.md) | a remote is two questions with two deadlines |
| [ADR-0010](adr/0010-publication-was-one-option-wearing-three.md) | **why this repository is public, and what that discloses** |

ADR-0009 and ADR-0010 together are the record of the publication decision: the
secrets audit over all 348 commits, what was found, and why two of the three
options a previous session had written down turned out not to exist.

## The roadmap — `roadmap/`

About 24,500 lines, and the reason the repository is worth reading.

- **[`snag_list.md`](roadmap/snag_list.md)** — open and fixed defects. Entries
  are corrected in place when the box refutes them, so an entry often records
  its own mis-ranking. Ids are `SNAG-AREA-000`.
- **[`STATUS.md`](roadmap/STATUS.md)** — the dashboard. Its opening block is
  machine-checked: figures in it carry `<!--check:name-->` markers naming the
  check that would refute them, and `scripts/check-ops-claims.sh` runs those
  against the live box.
- **[`tasks.md`](roadmap/tasks.md)** — the working record, session by session.
- **[`ideas.md`](roadmap/ideas.md)** — unbuilt, no commitment implied.

## Guides — `guides/`

Only [`api_auth.md`](guides/api_auth.md) is a document. **The other four are
pointers into `estate-manager`, a sibling repository that is not public**, so
those links will not resolve for an outside reader: the estate map, the
monitorable-project contract (which holds the shared port registry), and two
briefing integration specs moved there on 2026-08-11. A moved document leaves a
pointer rather than a copy, which is why the stubs remain.

## Other directories

- **[`insights/`](insights/)** — three retrospectives written at points where a
  batch of sessions had a common lesson.
- **[`sessions/movement-log.md`](sessions/movement-log.md)** — snag-count
  movement for Sessions 82–170, split out of `snag_list.md` when it outgrew it.
- **[`project-capability-audit.md`](project-capability-audit.md)** — a 2026-08-07
  audit of the project-management capability. Largely of historical interest:
  it predates ADR-0005, and the capability it audits has since moved out.
- `refactors/`, `templates/` — empty placeholders.

## A caveat on `ARCHITECTURE.md`

[`ARCHITECTURE.md`](ARCHITECTURE.md) was last rewritten on 2026-07-24 and is
**stale in ways that will mislead you**: its diagram and agent list still show
`ProjectOrganiserAgent` and the `projects/` and `registry/` packages, all of
which left this repository on 2026-08-13 under
[ADR-0005](adr/0005-project-state-leaves.md). It is accurate about the request
path, the database and the tray. Tracked as `SNAG-DOCS-011`; until that is
fixed, the accurate short account of what runs is in the
[README](../README.md#what-it-does), and the accurate long one is
[`../CLAUDE.md`](../CLAUDE.md).
