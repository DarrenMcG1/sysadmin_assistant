# STATUS.md claims — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**A document that states what is owed has to be re-measured, and the
place to do it is the script that already prints it** (Session 73,
`SNAG-ESTATE-008`). `docs/roadmap/STATUS.md` opens with the block a
sitting reads before deciding anything. Measured 2026-08-16, **all three
ops actions it carried had already been done**, two of them by a party
that never touched the document, and it went on asking for five sittings.
`sysadmin/ops_claims.py` is the reader; `sysadmin-check-claims` and
`scripts/check-ops-claims.sh` are how `claude-preflight.sh` (start of a
sitting) and `claude-postflight.sh` (the close, where the numbers are
*written*) run it. It sits beside `main.py` for `reload.py`'s reason —
the route count comes from `create_app()`, so it imports every domain.

Six rules, three of them the opposite of the obvious implementation:

1. **The parsed region is exactly the region preflight prints**, and the
   parse runs over `flatten()`ed prose rather than markdown. Not the
   whole file, which restates old figures on purpose (*"44 before Session
   27"*), and not a machine-readable marker beside the sentence, which is
   a second statement of one fact that can disagree with the first —
   `SNAG-DB-003`'s shape arriving in a document.
2. **Every way of not-knowing is `unknown`, never `match`** —
   `ports_checked`'s rule, and the verdicts and exit statuses are
   `schema_guard`'s three, imported rather than restated. Four
   distinguishable faults: a pattern that finds nothing, a block stating
   one figure two ways (drift with both halves inside one file), a
   database that will not answer, and a unit systemd has never heard of.
3. **Two kinds of check, because the remedies are opposites.** A `claim`
   compares the document against the box, so a mismatch means the
   *document* is stale; a `state` check compares the box against this
   checkout, so a mismatch means the *box* is, and no wording would fix
   it. The state checks run even when STATUS.md cannot be read at all.
4. **The deploy check compares file mtimes, never commit times**, and the
   obvious version was wrong on the day it was written: the daemon
   entered active at 09:58:28 and the newest commit touching `sysadmin/`
   landed at 10:05:22 with identical content, because this repository
   restarts to verify and commits afterwards. The newest `.py` on disk —
   09:57:46, 42 s *before* the start — answers the question actually
   being asked. **The population is the daemon's import graph, and was
   every `.py` here until 2026-09-06** (Session 190) — this rule's own
   stated cost, *"a file the daemon never imports reports a restart
   owed"*, turning out to be a quarter of its fires rather than the rare
   miss it was priced as: **50 of 191** commits touching `sysadmin/`
   touch only the six modules the daemon cannot reach, and `tasks.md`
   records the restart paid on **eleven consecutive sittings** "whose
   restart moves nothing a caller can observe". The same sentence priced
   that restart at "a second"; `SNAG-SYSD-007` is what it cost, one of
   the five restarts that tripped `StartLimitBurst` and left the box down
   **77 minutes**. `daemon_modules` is a **walk of the source, not a
   trace of an import** — the opposite of what the entry proposed, and
   the reason the fix is cheap. `core/llm_client.py` is imported lazily
   inside three review functions and named at module scope nowhere, so a
   trace of a constructed `create_app()` drops it, and the sitting that
   opened this concluded from exactly that that the measurement had to
   come from a running daemon over a new surface. It does not: a
   function-level `import` is in the AST as plainly as a top-level one,
   so the walk reaches **94 of 100** with no endpoint, no contract entry
   and no restart to bootstrap. It follows every **ancestor package**
   too, because importing `a.b.c` runs `a/b/__init__.py` — one level
   reaches all eleven inits here by coincidence of which modules happen
   to be imported directly, and only the mutation drive said so. The cost
   is unchanged in direction: a rebase, or a lazily-imported module the
   daemon has not reached yet, still reports a restart owed and never the
   reverse. A newer file **outside** the graph is named on the `match`
   rather than swept — `ports_checked`'s rule, because "considered, and
   no restart is owed for it" must not read like "nobody looked".
5. **A *fall* in the unresolved-alert count is the founding case.**
   Equality, or a rise, is the rule anyone would write. This snag exists
   because `SNAG-DB-002`'s eight collation rows resolved themselves at
   18:01:48 when estate-manager ran the `REINDEX` and four documents went
   on asking for it — so a fall is the signal that already existed and
   had no reader. Open titles are named, never counted.
6. **Nothing here writes to a document**, and there is no `--quiet`: a
   check that corrects the file it reads becomes a second author of the
   claim, and a flag nothing passes is `SNAG-CFG-001` at the size of a
   flag.

Three things only running it could have said. `systemctl show` **answers
for a unit that does not exist** — exit `0`, `ActiveState=inactive` —
which is this snag's own shape inside its own fix, so `LoadState` is the
gate and its test drives the real binary. `len(app.routes)` is **50**
against the documented **46**, because FastAPI adds `/openapi.json`,
`/docs`, `/docs/oauth2-redirect` and `/redoc` itself. And the check
**refuted its author within a minute**: the first rewrite of the block
wrapped `holds **2**` and `unresolved` across two lines with a `>`
between them and the claim came back `unknown`, which is why the region
is flattened before matching. `SNAG-ESTATE-011` is what remains — the
block's other claims are prose no pattern can reach.

**The other claims name the check that closes them, and the marker that
works is the one that states no fact** (Session 76, `SNAG-ESTATE-011`).
Five figures were machine-checkable and the rest of the block was prose;
the entry proposed `<!-- check: … -->` and refused a marker in the next
clause, which is `ops_claims.py` rule 1 — `<!-- routes=46 -->` beside a
sentence can agree with the box while the prose disagrees, and nothing
notices. **`<!--check:routes-->` is not that.** It names a *check*, never
a value, so the figure in the prose stays the only statement of itself
and the two cannot disagree about a fact, because one of them states
none. Live, the first run against the real block reported **five
unclaimed figures** — every one a sentence checked for a sitting and
never claimed.

Four rules, three of them the opposite of the obvious implementation:

1. **The marker is additive and cannot subtract.** Every pattern-bearing
   claim runs whether or not a line names it, so deleting a marker is a
   way to be *told*, never a way to retire a check. A marker that gated
   one would make "edit the document" a switch, which is rule 2's silent
   retirement arriving inside the fix for it. What the marker buys is
   `check_markers`: a figure this module can test that no line claims,
   and a marker naming a check nobody implements. A typo fires from
   **both** sides — `<!--check:helth-->` produced the unknown name *and*
   the now-unclaimed `health` beside it, which was not designed.
2. **A prediction is timed, not measured.** The entry was opened by *"the
   row clears at 03:32 with nothing done"*, written at 00:30 — not wrong
   when written and not measurable when written, so no pattern reaches
   it. `expires` is the one family whose **members the document
   declares**. After its moment the claim is `unknown`, never `mismatch`:
   the prediction may well have come true, and "nobody went back" is what
   rule 2 reserves `unknown` for.
3. **The instant is the one fact stated twice, so it is pinned rather
   than trusted.** The marker must carry a date the prose has no room for
   — "at 03:32" names a wall clock and no day — so the wall clock it
   renders must appear in the block or the claim is `unknown` naming both
   moments. `syslog_priority` against `PRIORITY_MAP`'s treatment. **The
   pin was broken and only a live run said so**: it searched the
   flattened region, *which contains the marker*, so it matched the
   marker's own copy and passed whatever the sentence said — a check
   agreeing with itself by construction. Three fixture tests of that pin
   were green either side of the fix, because their fixtures happen not
   to carry a marker.
4. **`check_open_titles` is the finer half of the alert count**, which
   holds still through a **swap** — one row resolving as another opens —
   while the sentence about *which* rows are open goes wrong. One
   direction only: a row the block names that has resolved is already
   `check_alerts`'s *fall* note, and what that note cannot say is that a
   row nobody wrote about is open.

`/health` is checked and **8400 deliberately is not**, though the block
asserts both. The first is a different fact from the deploy check's —
`systemctl` reporting `active` says the process is up, `/health` says the
application is serving, and `SNAG-DB-005` is the 23 hours where those
parted company. The second is estate-manager's availability, which
`estate/judgements.py` rule 3 declines to judge here; a claims-checker
that alerted on it would re-import the second owner that rule exists to
prevent. The block says so in its own prose rather than leaving the
silence to be read as an oversight — which is the cheapest form of the
convention for a claim no pattern reaches, and is `SNAG-ESTATE-012`: a
sentence with **no pattern and no marker** is still invisible, because
deciding that an English sentence is a claim is a human's job.

The cost is stated rather than implied: the markers are HTML comments and
do not render, but `claude-preflight.sh` prints the block as raw text, so
the session-opening banner is slightly noisier and every figure in it now
carries the name of the thing that would refute it.
