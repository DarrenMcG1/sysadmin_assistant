# ADR-0009: a remote is two questions with two deadlines, so it is answered twice

Decided 2026-09-09 by Session 205, answering the next action Session 204
filed, this repository's own estate board `top_action` (*Add a git
remote*), and estate message [`6e2e5a50`](#5-what-this-closes) from
alfred.

**The filed question was "where does the remote go". It is two
questions, and the reason to separate them is that only one of them is
urgent.** *Where does the second copy live* had a live cost — one disk
failure and `services.yaml`, the monitoring configuration for all
**32** declared services, was gone. *Should this be published* has no
deadline at all. Bundling them makes the backup wait on a curation
decision that nothing is pressing.

So the answer is **`git@github.com:DarrenMcG1/sysadmin_assistant.git`,
private, pushed today** — and *public* is deferred to its own sitting
with the audit that unblocks it already done and recorded below.

The remote is the house convention rather than a choice. Measured
before this push, **seven of the estate's eight** remote-bearing
repositories already sat at `git@github.com:DarrenMcG1/<name>.git` over
SSH — the eighth, `daiy`, is the same host over HTTPS — and **seven of
the eight are private**, the exception being `BSL-Translator`, last
pushed in January.

---

## 1. Why the split, and what it cost to not make it

The two questions differ in **deadline**, not in difficulty.

| | backup | publication |
|---|---|---|
| cost of delay | one disk failure loses 347 commits and the estate's monitoring configuration | none |
| what it needs | a remote | a disclosure judgement over 38,774 lines of documentation |
| reversible | yes — a remote is added and removed freely | **no** — a public repository is indexed, and unpublishing does not unindex |

The asymmetry decides the order on its own. A private push forecloses
nothing: `gh repo edit --visibility public` is one command, and the
audit in §2 is the same audit either way. The reverse is not true.

**This is the seam the estate rules already name** — a monitor that
holds the only copy of what it monitors. `services.yaml` *is* the
monitoring configuration, so its loss does not degrade monitoring, it
silently narrows what monitoring knows exists. Alfred's own case is the
specimen: `alfred-desktop.service` sat dead for **3 days 2 hours** from
2026-09-06 06:16 precisely because nothing declared it.

## 2. The audit, measured over all 347 commits

Publication exposes **every commit**, not the working tree, so every
check below runs over `git rev-list --all` rather than `git ls-files`. A
key deleted in commit 40 is still served at its blob SHA for ever.

| check | result |
|---|---|
| key material in any blob, all history — `sk-`, `ghp_`, `github_pat_`, `xox[baprs]-`, `AKIA`, `AIza`, PEM headers | **zero** |
| every value `api.auth_token` has held in `config.yaml`, all history | `""` — the only one |
| files ever named `.env`, `*.pem`, `*.key`, `*.p12`, `id_rsa`, `.pgpass`, `.netrc` | **never existed** |
| the broker password | never in git — `LoadCredential=` ([ADR-0003](0003-mqtt-credential-by-loadcredential.md)), verified rather than read |
| the owner's real name in file content | **zero occurrences** at 347 commits — **corrected to one** at 348, the occurrence being §3.1 of this document, which quotes the address in order to record that it appears in commit metadata. The commit recording the finding is what falsified it; exposure is unchanged either way, since commit metadata carries the address regardless and §4 refuses the rewrite that would scrub it. Argued in [ADR-0010 §5](0010-publication-was-one-option-wearing-three.md) |
| RFC1918 dotted-quads | **8**, of which 7 are `--help` text and tray-config test fixtures |

**The audit is boring because the repository was built for it, which is
the finding worth carrying.** `api.auth_token` ships empty *with a
startup warning* because `config.yaml` is committed — the design took
"unauthenticated, loudly" over "a secret in git, quietly". ADR-0003 then
refused `config.yaml`, an `EnvironmentFile` **and** a path-to-the-secret
in config for the same reason. Neither decision was taken with
publication in mind, and together they are the whole of why this took a
morning rather than a history rewrite.

## 3. What publication still owes, and it is disclosure rather than secrets

None of these is a leak. All are judgements, and they are recorded here
so the deferred sitting starts from evidence rather than from a re-scan.

1. **Commit metadata.** `darrenjmcgarvey@gmail.com` on all 347 commits.
2. **Identity of the box.** Username `gaddi`; hostname `dbelter`, in
   **8** places, all test fixtures.
3. **26 private project names** in `tests/fixtures/estate_projects_*.json`
   and throughout the roadmap — `BudgetApp`, `PupilProgressTracker`,
   `customer-churn-model`, `TeacherPlanner` among them. Seven of eight
   sibling repositories are private, so publishing here names
   repositories their owners have kept unnamed. **"Their owners" is
   wrong and this clause is what produced the option to ask them:**
   all 26 resolve to the owner's own accounts, so the set of third
   parties is empty
   ([ADR-0010 §1](0010-publication-was-one-option-wearing-three.md)).
4. **38,774 lines of roadmap narrative** describing a private machine:
   outages with timestamps, decisions taken and refused, and what each
   sitting got wrong.
5. **One LAN address in prose** — `192.168.1.2`, in `tasks.md`'s
   standing note that off-box is the known gap.
6. `~/Documents/DMDocs/Self/Briefings/Audits` in `home_audit.py`.

**The owner's standing decision on (4) is to publish it as-is**, on the
grounds that the narrative *is* the showcase: a service whose
documentation records falsified guards, refuted assumptions and
measurements that inverted their own rankings is not made more
impressive by deleting them. That decision is recorded now so the
deferred sitting does not relitigate it; what remains open is (3), which
names third parties' repositories rather than this one's work.
**Closed 2026-09-09 by ADR-0010, which found (3) largely decided by this
very ruling** — 19 of the 26 names are inside the roadmap narrative
being published as-is, so the two items overlap and the overlap had not
been measured.

## 4. Three refusals

**A history rewrite was refused, and the reason is citations rather than
effort.** Scrubbing the commit address means rewriting all 347 commits
and every SHA with them — and **116** backticked commit SHAs are cited
across `tasks.md`, `STATUS.md`, `snag_list.md`, `CLAUDE.md` and
`HANDOFF.md`, plus `aad8236` cited by alfred in the message this ADR
closes. The address is already public on this account's other commits,
so the rewrite spends every cross-repository reference in the estate to
buy nothing.

**A curated public mirror alongside a private backup was refused.** Two
repositories holding one history is the second-owner defect this
repository has found at seven scales, arriving as a release process:
two places to push, and a divergence nothing measures.

**Publishing today was refused** for §1's asymmetry alone. The audit
would support it; the indexing is what cannot be undone, and there is no
cost to waiting.

## 5. What this closes

Estate message `6e2e5a50` (alfred, 2026-09-09) reports that commit
`aad8236` — the `alfred-desktop` declaration alfred was contractually
obliged to write here — existed on one disk. Verified after the push:
`git branch -r --contains aad8236` names `origin/main`, and
`git show origin/main:services.yaml` carries the declaration. Local and
remote both hold **347** commits.

Alfred's second observation is **deliberately not answered here**: that
four repositories with no remote score 100/100 while a stale branch
costs five points, so `healthy` is displayed for repositories one disk
failure from total loss. That is estate-manager's scanner. A monitor
must not own the things it monitors, and this repository judging the
estate's own scoring of itself is that rule read backwards — it is
raised with the owner, not fixed here.

## 6. The residue

**`docs/roadmap/tasks.md`'s off-box note is unchanged and still true.**
A GitHub remote is a second copy of the *repository*; it is not a backup
of the `projects` database, of `log_entries`, or of anything else this
service writes. Nothing in this ADR touches that gap, and reading a
green remote as "the box is backed up" is the misreading it invites.
