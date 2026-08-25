# Handoff — 2026-08-25

## Next action

Take the four permanent `running` rows in `agent_runs` — two `file_organiser` from 2026-08-17, one `log_aggregator` and one `sysadmin` from 2026-08-14 — which reach `GET /api/sysadmin/self` and the tray as `last_status: "running"` so a dead agent reads as busy, and which are Session 41's deliberate decision working rather than a defect in it, so the fix is a reader rule and not a writer one.

## Sub-session items

**Two are owed, both cross-repo asks and neither a session.** (1) **Ask
estate-manager the Session 33 question** — seam drift detection's second
task reads another repository's fixture off the same disk, and cross-repo
concerns have had an owner since 2026-08-13, so the question comes before
the ranking. Named as blocked in **six** consecutive rankings without
being asked. (2) **Report `SNAG-ROADMAP-002`'s ninth consecutive
misreport** — 59 → 61 entries / 57 → 59 open for a sitting that closed
one and opened two, measured either side of the edit by driving
`read_snags` over the file. The parser is estate-manager's since
2026-08-13, so what is owed from here is a report and not a fix.
**Partially discharged and deliberately not ticked**: the figures were
put to the live `estate-manager-48` session in the announcement of
`SNAG-ESTATE-049`, and that session had `roadmap.py` and
`test_snags_format.py` open at the time — but **a message to a session is
ephemeral and no document over there records it**, so if that session
ends without acting the report leaves no trace. What is still owed is the
durable form. Ask (1) is untouched. Both are cross-repo writes: committed
on their own and announced, which `SNAG-ESTATE-049` now demonstrates.

## What this sitting decided, and what it rejected

**The entry left one decision open and it was put to the owner rather
than guessed**: delete the fifteen unreachable models, or keep them and
give them the consumer that would make them honest — the seam test
already covering `/overview` and `/{name}`, extended to the eight routes
on 8400. **Delete won, and the reason is worth keeping**: those routes
are estate-manager's and it owns their contracts, so a live seam test
here would make this repository's CI answerable to another repository's
route shapes for routes nothing here parses — a second statement of
somebody else's fact, which is the shape the estate rules exist to
prevent. Deletion is one `git show` from reversal.

**The owner then split the answer, and the split is the interesting
half.** The fifteen leave the *registry*; the five that
`sysadmin_tray/models.py` re-exports stay *importable*, because
`sysadmin_tray` ships in the wheel and an import list is a published
surface rather than an internal tidy. That is not a compromise between
the two options — it separates "what the contract registry describes"
from "what the package still resolves", which were one question only
because nobody had had to answer them differently.

**Rejected: marking them deprecated in place.** A deprecation comment
beside a live model is a second statement of which models are
load-bearing and can disagree with the file it annotates. Moving them out
makes membership of the registry the only statement, which is what let it
become a property a test computes.

**Rejected: warning at import.** It fires on every tray start whether or
not anything touched a deprecated name, which teaches the reader to
filter the category rather than act on it.

## Blocked

`SNAG-DOCS-003` — this sitting's own cost — is blocked on an
**operational** fact rather than on code: confirmation that nothing
outside this repository imports the five deprecated names. Every importer
measured today is inside it and the wheel is only ever installed on this
box, but that is a claim about where an artefact went, which is the class
`verify-ops-claims-live` says to measure rather than assume. The removal
itself is two deletions and a test edit, and the entry names the one test
that must **not** go with them.

Session 33 remains blocked on the estate-manager question above.

## Not owed here, and named because the next sitting will see it

Nothing is open on this box beyond `Weekly disk review ready` (`info`,
below `tray.notify_min_severity`, open since 2026-08-17). The two rows
the last handoff named both **closed themselves overnight with nothing
done**: `venture-chat unreachable` at 05:31:10, because
venture-assistant's owner restarted their own service — the estate rule
working rather than a coincidence — and `Estate scan could not reach
sources` at 05:32:07 on the first judge poll after the estate's daily
scan.

That second one produced `SNAG-ESTATE-013` and is worth reading, because
it is the `expires` marker's **first live test**: the prediction came
true and was named two hours early, since the block rendered the estate's
`+00:00` timestamp as a local wall clock. `SNAG-LOG-009`'s defect one
document over. The check reported `unknown` rather than `mismatch`,
correctly — what it cannot see is a marker written in the wrong zone.

**`uv.lock` was committed on its own (`405146c`) after the session
commit, and the three lines are not this repository's tooling.** They sit
under `[package.metadata.requires-dev]` for **`estate-lib`**, which is an
editable path source here (`[tool.uv.sources]` →
`../estate-manager/lib`), so that library's `[dependency-groups] dev`
reaches this lock: `mypy==2.3.1`, `ruff==0.16.2`, `types-pyyaml`.
estate-manager pinned them under its own `SNAG-ESTATE-020` — *"both
projects move together or the gate means two things at once"*. Measured
rather than assumed before committing: `uv lock` regenerates the file
byte-identically and `uv lock --check` exits 0, so it is a real
resolution and not a hand-edit or a stale artefact.

**That question was routed to the owner and is now `SNAG-ESTATE-049`**
in `estate-manager/docs/roadmap/snag_list.md`, commit `e60b589` — written
from here, **committed on its own** and announced, with a recommendation
and **no ruling** (their ADR-0011 §1). Nothing else in that file was
touched and its preamble carries no count to restate.

**Measuring it before filing changed what the question is, which is why
it was worth doing.** The lock line was the symptom, not the mechanism.
`estate-lib` is an editable path dependency carrying `estate/py.typed`,
so `mypy sysadmin` **resolves `estate.*` to that repository's real source
files** — `estate.gpu`, `estate.llama`, `estate.text`, `estate.registry`
and `estate.registry.discovery` all came back as
`/home/gaddi/projects/estate-manager/lib/estate/…` under
`mypy --verbose`. So this library's code is analysed by two checkers: its
own pinned `mypy==2.3.1` with `types-pyyaml`, and this tree's **2.3.0
without it**, under `ignore_missing_imports = true`. The version gap was
the visible half; the **stub set** is the half that could bite, since
`estate.registry` parses YAML.

**The `ruff` half is probably not a question at all**, and the entry says
so as a recommendation rather than a ruling: a consumer's `ruff check .`
never opens a file in `lib/`, so this tree running 0.15.0 cannot make the
estate's gate mean two things — which is that pin's whole stated purpose.
The `mypy` half is different because the analysis genuinely crosses the
boundary, and `py.typed` is what invites it.

**It lands beside `SNAG-ESTATE-047` and does not duplicate it.** That
entry asks which `ruff` a venv *runs* against what its file *declares*,
within estate-manager's two trees, and explicitly rejected reading a
`uv.lock` as "a resolution rather than an installation" — this reading is
an installation. It also counted five `ruff`s on this box including
**0.15.0**, which is the one this venv runs, so one of the five now has
an address.

**Nothing was changed on this side, deliberately.** Pinning `mypy` here
to match would be this repository answering another's question by acting
on it, and would bind Alfred and venture-assistant by precedent without
either being asked. Neither of those two consumers was measured.

## State of the box

`sysadmin` restarted at **07:58:56** after the deletion and verified:
`/health` 200, 11 jobs scheduled, schema guard passed at 014,
`create_app()` serving 52 routes with `/api/projects/managed` still the
only one under `/api/projects`. Suite **2238** green, `ruff` clean,
`mypy sysadmin` clean. `./scripts/check-ops-claims.sh` reports every
claim in `STATUS.md`'s opening block `ok`, with no unclaimed figure.
