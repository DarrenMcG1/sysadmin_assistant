# ADR-0010: the deferred publication question had one live option, and measurement removed the other two

Decided 2026-09-09 by Session 206, taking the question
[ADR-0009](0009-the-remote-is-two-questions.md) §3.3 deliberately
deferred to its own sitting.

**`github.com/DarrenMcG1/sysadmin_assistant` is public**, verified
unauthenticated — `curl` with no token against `api.github.com` returns
`200`, which is the honest test, since `gh repo view` runs authenticated
and would succeed either way. Local and remote both hold **348**
commits.

ADR-0009 left one item open and Session 205's handoff stated the choice
as *accept them, redact them, or ask their owners*. **Two of those three
are unavailable, and nothing new had to be measured to see it** — the
evidence was in ADR-0009 already, needing only to be cross-read.

---

## 1. "Ask their owners" has no one to address

ADR-0009 §3.3 reads *"publishing here names repositories their owners
have kept unnamed"*, and the handoff turned that into an option. It is
a claim about the **population**, and the population refutes it.

Every one of the 27 repositories on this box — the 26 named here plus
this one — resolves to the owner's own accounts: **23** at
`git@github.com:DarrenMcG1/<name>.git`, `daiy` at the same host over
HTTPS, `terrible` at `gitlab.com/Gaddi_/terrible`, and the rest with no
remote at all. The last commit on every repository that has one is
authored `darrenjmcgarvey@gmail.com`.

There is no third party in the set. The option is not declined, it is
**empty** — which is `verify-ops-claims-live`'s rule applied to a
*scope*, the thing that memory names explicitly as a claim.

## 2. "Redact" is unavailable for a reason ADR-0009 had already written down

The names entered history on **2026-08-04** (`BudgetApp`, 10 commits)
and **2026-08-06** (`customer-churn-model`, `TeacherPlanner`, 4 each).
Publication exposes every commit, which is §2's own argument, written
there for the secrets sweep and never applied to this item:

> A key deleted in commit 40 is still served at its blob SHA for ever.

So a working-tree redaction changes nothing a visitor can reach, and a
real one is the **history rewrite §4 already refused** — over **116**
backticked commit SHAs cited across `tasks.md`, `STATUS.md`,
`snag_list.md`, `CLAUDE.md` and `HANDOFF.md`, plus `aad8236` cited by
alfred in message `6e2e5a50`. That reason has nothing to do with these
names and does not move.

**Only 2 of the 26 could have been reached by a working-tree edit at
all** — `bsl-app` and `detection-system`, two occurrences each, nowhere
outside `tests/fixtures/` — and both are in history regardless.

## 3. The ruling already made on §3.4 had largely decided §3.3

ADR-0009 records the owner's standing decision to publish the roadmap
narrative as-is, *"on the grounds that the narrative is the showcase"*,
and states in the next sentence that §3.3 *"remains open"*. The two
items overlap and nobody had measured the overlap.

**19 of the 26 names are inside `docs/roadmap/` itself:**

| name | in `docs/roadmap/` | tracked total |
|---|---:|---:|
| `Alfred` | 144 | 330 |
| `venture-assistant` | 51 | 116 |
| `PersonalAssistant` | 32 | 94 |
| `ImbaBots` | 31 | 44 |
| `SportsAnalyser` | 22 | 54 |
| `alfred-glance` | 19 | 35 |
| *(13 others)* | 1–4 each | 5–14 each |

`estate-manager` adds a further 327 and 801, and `sysadmin_assistant`
19 and 84, both excluded above as this estate's own infrastructure
rather than the private-project population.

The narrative is **made of** these names — it is a record of one
estate's services failing and being fixed, and a sentence like *"186
alert rows for one `venture-assistant` outage"* has no figure-free form
that keeps its evidentiary value. Publishing it as-is and redacting its
subjects are not compatible instructions, so the ruling on §3.4 had
already decided most of §3.3 by implication.

## 4. What was swept that ADR-0009 had not swept

The §2 audit looked for **secrets**, and §3 for **project names**. The
population neither covered is **third-party personal data**, which
matters because two of the names — `PupilProgressTracker` and
`TeacherPlanner` — suggest a school context that would raise a question
no amount of self-ownership settles.

Measured over all 348 commits' blobs:

| check | result |
|---|---|
| `\bdob\b`, `date_of_birth`, `postcode` | **zero** (the 1,580 substring hits for `dob` are all inside `tests/test_file_actions.py` and none is word-boundary) |
| `pupil_name`, `student_name`, `client_name` | **zero** |
| `@*.sch.uk`, `@*.ac.uk` addresses | **zero** |
| human email addresses in file content | **one** — `darrenjmcgarvey@gmail.com`; the rest are systemd unit templates (`user@1000.service`), `git@github.com` and `test@example.com` |

Nothing rides along with the two school-sounding names.

## 5. A correction to ADR-0009's audit table

Its final row reads *"the owner's real name in file content: **zero
occurrences**"*. Re-run over 348 commits it is **one**, and the
occurrence is **ADR-0009 itself**, line 79:

> 1. **Commit metadata.** `darrenjmcgarvey@gmail.com` on all 347 commits.

§3.1 quotes the address in prose in order to record that it appears in
*commit metadata*, and in doing so puts it into *file content*. **The
commit that recorded the finding is what falsified it** — a measurement
that changed the property it measured by being written down.

It blocks nothing and changes no exposure: §4 refuses the rewrite that
would scrub the address, and publication serves it through commit
metadata on all 348 commits regardless, so the disclosure is identical
either way. It is corrected here rather than left standing because a
future sitting reading that cell would trust it, and this repository's
whole practice is that a claim which has stopped being true is worse
than no claim.

## 6. Why the audit was re-run at all

ADR-0009 measured at **347** commits and the ADR's own commit is the
**348th**, so the audit did not cover the last thing that landed before
an irreversible action. Re-run in full: zero key-shaped strings in any
blob, zero files ever named `.env`/`*.pem`/`*.key`/`*.p12`/`id_rsa`/
`.pgpass`/`.netrc`, and `api.auth_token` still holds `""` as the only
value it has ever held. The one movement is §5 — introduced by the
audit's own commit, which is precisely the case a re-measure at *N+1*
exists to catch.

## 7. Three things this does not do

**It does not make the box backed up.** ADR-0009 §6 stands unchanged
and is now more inviting to misread, not less: a public remote is a
copy of the *repository*, not of the `projects` database, of
`log_entries`, or of anything else this service writes.

**It does not change the monitorable-project contract.** That contract
obliges other repositories to declare units in this repository's
`services.yaml` the same day their units are created, and that
obligation was written when this repository was private. It now routes
other repositories' text into a public one. The obligation is to
declare a unit — a port, a path, a unit name — rather than to explain
it, so the contract needs no change; what is worth a sentence there is
that **comments** in `services.yaml` are published. That is
estate-manager's to decide and is filed as a recommendation, not taken
here.

**It does not fan out further than two.** Measured rather than assumed:
`aad8236` (alfred, today, the `alfred-desktop` declaration per their
ADR-0093) and `d514b39` (the five-minute evaluator timer) are the only
cross-repo writes into this repository, so the measured audience is
alfred and the contract's owner. Announced as message
`58b208d5` (alfred) and `871fa2f1` (estate-manager) before the commit
carrying this ADR — the estate's announce-by-filing rule, whose own
clause says a measured-empty audience files nothing, and this one is
not empty.

## 8. What this closes, and one thing it cannot

It closes the item ADR-0009 §3.3 left open and the next action Session
205 filed.

**It cannot amend alfred's message `6e2e5a50`.** That message was
closed by Session 205 with a note reading *"private, pushed"*, the
register has no reopen, and a close note is one-shot. So the correction
lives in this ADR and in message `58b208d5`, which is filed
`in_reply_to` the closed row — the field estate-manager built in
response to this repository's own recommendation, used here for the
first time by this side for exactly the case it was built for: a
closed row whose note has stopped being true.
