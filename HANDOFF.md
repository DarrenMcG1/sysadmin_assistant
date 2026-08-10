# Handoff — 2026-08-10

## Next action

Decide whether the estate migration runs now — four repos still carry a generated `docs/sessions/handoff.md` beside or instead of a real one, and `SportsAnalyser`'s is 156 days old.

## This session (Session 37): the handoff pipeline, both ends

Raised as "the handoff hook isn't doing much in venture-assistant". It was
doing worse than nothing, and the measurement changed the diagnosis twice.

**What the estate actually showed** (15 repos, before any change): five
carried `docs/sessions/handoff.md` and **every one was hook output**.
Exactly two repos had ever held a handoff someone wrote —
`venture-assistant` (root `HANDOFF.md`, 8 of its 9 commits) and
`SportsAnalyser` (abandoned 2026-03-07). Both lived at paths the scanner
could not read. Root `HANDOFF.md` existed in **1 of 15**, not "most" — the
owner's belief was checked before it was acted on, and it was wrong on
location while right on mechanism.

**Writer.** `SessionEnd` **cannot block** — it is an observability event —
so `generate-handoff.sh` could only emit what `git` already recorded.
Retired: unwired from `settings.json`, left on disk with its reasoning and
an explicit "do not re-wire this". Replaced by
`~/.claude/hooks/require-handoff.sh`, a **Stop** hook that blocks a session
which changed code until `HANDOFF.md` carries today's date. Three
independent loop guards, because a blocking Stop hook that misfires hangs
every session: `stop_hook_active`, a per-session+repo marker file, and
exit 0 on every failure path. Ten payload cases verified before wiring —
including that `touch HANDOFF.md` does not satisfy it.

**Reader.** `SNAG-ROADMAP-003` closed. Four candidate paths; selection by
`handoff_date` rather than tuple order; also-rans returned as
`handoff_duplicates`. Live proof: `venture-assistant` now reads its 6 KB
root handoff and `ImbaBots` its 141 KB `docs/handoff.md`, both of which had
been invisible while an 850-byte stub supplied the estate board.

**Also corrected**, all found by grepping for the old path rather than by
being reported: `recommendations.py`'s "No session handoff" advice
described the hook that made the check unfireable; `monitorable-project.md`
said "don't hand-write handoffs"; `claude-preflight.sh` anchored its
extract on `## ⚠️ READ THIS FIRST` and `## In-Progress Tasks`, headings no
handoff on this box has ever used — so it announced a handoff and printed
nothing.

## Decisions and what was rejected

- **Root `HANDOFF.md` over `docs/sessions/handoff.md`** — owner's call,
  taken knowing it is currently 1 of 15 and contradicts the documented
  convention. All four paths stay readable so migration can go a repo at a
  time.
- **Stop hook over "split the two jobs"** — the rejected alternative was
  keeping the SessionEnd hook writing a clearly-secondary file the scanner
  ignores. Recorded in the retired script as the fallback if blocking
  proves too intrusive.
- **Authored date over mtime** for choosing between handoffs, following the
  rule `handoff_date` already set: a clone rewrites every mtime, which
  would make a five-month-old handoff outrank a current one.
- **First attempt at that rule was wrong.** Ranking every *undated*
  candidate below every dated one re-creates the bug from the other side —
  ImbaBots' real handoff carries no ISO date and lost to a stub written an
  hour earlier. The fallback has to apply uniformly.

## Blocked / waiting on

- **Estate migration needs a decision, not a blocker.** `Alfred`,
  `ImbaBots`, `alfred-glance` and this repo still hold a generated
  `docs/sessions/handoff.md`. The reader handles duplicates, so nothing is
  broken — but it is four repos of housekeeping across repo boundaries and
  was deliberately not done unilaterally.
- `handoff_duplicates` and `handoff_path` are recorded by `scan_roadmap`
  and **read by nothing**. A `kind: "roadmap"` recommendation is the
  natural consumer.
- `SNAG-ROADMAP-002` remains open, with new evidence: `count_open_snags`
  reports 7 for the 5 open snags in this repo's own list.

## State

Branch `main`, suite 1635 passing, ruff and mypy clean. Nothing committed
yet — the working tree holds this session's changes.
