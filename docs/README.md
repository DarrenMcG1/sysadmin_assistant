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
| see the shape of the system | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| know why a module is built the way it is | [`design/`](design/) |
| set up bearer-token auth | [`guides/api_auth.md`](guides/api_auth.md) |
| work in this repository with Claude Code | [`../CLAUDE.md`](../CLAUDE.md) |

## Architecture decision records — `adr/`

Fifteen records. They are the highest-value documents here for a reader who is not
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
| [ADR-0011](adr/0011-a-cited-register-id-is-a-claim-about-this-repository.md) | what a commit says when it cites a cross-repo register message id |
| [ADR-0012](adr/0012-a-transient-holder-has-no-project.md) | why a transient port holder is refused a document comparison |
| [ADR-0013](adr/0013-a-published-key-is-necessary-and-was-never-sufficient.md) | why the session's audit reader stays on `docs` though `ports` publishes the key |
| [ADR-0014](adr/0014-a-sample-cannot-be-both-pinnable-and-real.md) | why the briefing sample is not published, though two documents ask for it |
| [ADR-0015](adr/0015-pointers-has-an-owner-and-the-cause-is-here.md) | why the estate's `pointers` check is not judged here, and the test that speaks for it instead |

ADR-0009 and ADR-0010 together are the record of the publication decision: the
secrets audit over all 348 commits, what was found, and why two of the three
options a previous session had written down turned out not to exist.

## Design reasoning — `design/`

Fourteen documents, one per domain, moved verbatim out of
[`../CLAUDE.md`](../CLAUDE.md) on 2026-09-27. An ADR states a decision; these
state why the code under it is shaped as it is — which rules each module
encodes, which of them are the opposite of the obvious implementation, and what
was measured to settle them.

| | |
|---|---|
| [`notifications.md`](design/notifications.md) | who speaks on the box, the escalation ladder, and reminders for a standing fault |
| [`logs.md`](design/logs.md) | the log aggregator: signatures, trends, advice, incident correlation, and how the journal is read |
| [`alerts.md`](design/alerts.md) | how alert rows open, deduplicate, refresh, quieten and close |
| [`agent-runs.md`](design/agent-runs.md) | how an agent run is recorded, and what happens to one that dies |
| [`schema-and-storage.md`](design/schema-and-storage.md) | the schema guard, autogenerate's configuration, and retention |
| [`status-claims.md`](design/status-claims.md) | how `roadmap/STATUS.md`'s opening block is checked against the live box |
| [`estate.md`](design/estate.md) | judging what `estate-manager` publishes, including its port audit |
| [`gpu.md`](design/gpu.md) | where the GPU busy figure comes from, and why not `rocm-smi` |
| [`files.md`](design/files.md) | the file organiser, its actions and its weekly disk review |
| [`units-and-ports.md`](design/units-and-ports.md) | the systemd unit sweep and the three registries that claim a port |
| [`services.md`](design/services.md) | the service reliability score and its advice |
| [`health-review.md`](design/health-review.md) | the weekly narrated health review |
| [`config.md`](design/config.md) | unread config keys, the reload, and the job plan |
| [`briefing.md`](design/briefing.md) | the morning briefing's envelope |

## The roadmap — `roadmap/`

About 32,000 lines, measured 2026-09-26, and the reason the repository is
worth reading.

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

## Other directories and files

- **[`insights/`](insights/)** — three retrospectives written at points where a
  batch of sessions had a common lesson.
- **[`sessions/movement-log.md`](sessions/movement-log.md)** — snag-count
  movement for Sessions 82–170, split out of `snag_list.md` when it outgrew it.
- **[`project-capability-audit.md`](project-capability-audit.md)** — a 2026-08-07
  audit of the project-management capability. Largely of historical interest:
  it predates ADR-0005, and the capability it audits has since moved out.
- **[`projects-registry-legacy.yaml`](projects-registry-legacy.yaml)** — the
  retired `projects.yaml`. Project state moved into each repository's
  `.project.yaml` under [ADR-0001](adr/0001-project-registry.md); this copy is
  kept only until the reasoning in its comments has moved into `decisions:`
  blocks, and nothing reads it.
- `refactors/`, `templates/` — empty placeholders.

## What `ARCHITECTURE.md` claims, and what it does not

[`ARCHITECTURE.md`](ARCHITECTURE.md) carried a stale diagram for four weeks —
it showed `ProjectOrganiserAgent` and the `projects/` and `registry/` packages,
all of which left on 2026-08-13 under
[ADR-0005](adr/0005-project-state-leaves.md) — and this section warned you about
it. That was `SNAG-DOCS-011`, **closed 2026-09-10**: its packages, agents,
routes, tables and tray tabs were re-measured against the running box and
corrected, and the file states the date it was measured.

The caveat that stands in its place is narrower, and it is about *kind* rather
than *currency*. The file describes the system's **shape** — the request path,
the schedule, the seams — and is deliberately thin on the reasoning: which rules
each module encodes, and which of them were the opposite of the obvious
implementation, is in [`design/`](design/), one document per domain, which is
long and is the long account on purpose. For the short one, see the
[README](../README.md#what-it-does).
