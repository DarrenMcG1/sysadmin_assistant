# Spec — the projects page in Alfred

What Alfred needs to build to show the software estate: which projects
exist, what state they're in, and **what to pick up next**. Written
2026-08-06, against the endpoints that shipped the same day.

Everything here is a read. sysadmin does the filesystem work — scanning
directories, reading git, parsing roadmap documents — and hands Alfred
JSON. **Alfred never touches a directory**; that separation is the point
of the design, not an implementation detail.

---

## 1. The one call

```
GET http://localhost:8500/api/projects/board
```

No auth (all sysadmin GETs are open on localhost).

Two parameters:

- `?sort=activity` (**default**) — most recently touched first. This is
  the working view and what the page should use.
- `?sort=neglect` — stalled first, then longest-idle. A separate "needs a
  decision" panel, or a weekly triage view. Do not make it the default:
  the first draft did, and an actively-developed project landed at row 12
  of 18 while abandoned ones led the page.
- `?include_inactive=true` adds dormant and archived projects, which the
  page should not use — see §5.

Response (`ProjectBoardResponse` in `sysadmin/core/contracts.py` — that file is
the contract, this is the summary):

```json
{
  "projects": [
    {
      "name": "SportsAnalyser",
      "path": "/home/gaddi/projects/apps/SportsAnalyser",
      "status": "active",
      "health_score": 80,
      "grade": "healthy",
      "last_commit_at": "2026-03-22T18:04:11+00:00",
      "days_since_commit": 136,
      "next_action": "**Session 17**: Venue & Contextual Features",
      "next_action_source": "handoff",
      "handoff_age_days": 152,
      "stalled": true,
      "open_tasks": 3,
      "open_snags": 0,
      "top_action": "Stalled 152 days — resume or park it",
      "scanned_at": "2026-08-06T12:40:02+00:00"
    }
  ],
  "count": 18,
  "stalled_count": 1,
  "generated_at": "2026-08-06T12:40:59+00:00"
}
```

Rows arrive **pre-sorted** per the `sort` parameter. Render them in the
order given. Re-sorting by health score is the obvious temptation and
it's wrong — a 95-scoring project nobody has touched in four months is
the one that needs a decision, and score ranking buries it.

## 2. Rendering rules that carry meaning

### `next_action_source` is the honesty field

| Value | What it means | Suggested treatment |
|---|---|---|
| `handoff` | A session recorded where it stopped | Show plainly — this is the real thing |
| `tasks` | No handoff; this is the *plan*, not the record | Show, marked "planned" |
| `git` | No roadmap docs at all; last commit subject standing in | Show dimmed, marked "from git" |
| `null` | Nothing known | Show "No next action recorded" |

**Rendering all four identically is lying about how much is known.** A
commit subject like "WIP snapshot before ~/projects reorganisation" is not
a next action — it is the absence of one, and it should not look like a
handoff-authored step. Several projects on this box are in exactly that
state today.

### `stalled` outranks `next_action`

When `stalled` is true the next action is a *record of where work stopped*,
not today's task. Render it as a decision, not a to-do:

> **SportsAnalyser** — stalled 152 days.
> Was: "Session 17: Venue & Contextual Features"
> `[ Resume ]` `[ Mark dormant ]`

Threshold is 30 days, defined once in
`sysadmin/projects/recommendations.STALLED_HANDOFF_DAYS`. Don't
re-implement it — read the `stalled` boolean.

### `open_tasks: null` is not zero

`null` means the project's task list can't be counted in checkboxes —
Alfred's own repo tracks sessions in a status table, so a box count of 0
would be a confident lie. Render `null` as "—", never "0".

### `next_action` may contain markdown

Handoffs are authored by humans and by the SessionEnd hook, and both emit
inline markdown (`**Session 17**`). Render markdown-tolerantly or strip
it; don't print raw asterisks.

## 3. Do not write these into `trackables.projects`

Alfred's own `Project` table is a curated list of things you've chosen to
work on — warhammer, birdfeeder, flight-tracker-clock. sysadmin's registry
is every directory on disk with a project marker. They overlap by two rows
today (`terrible`, `athenaeum`) and mean different things:

|  | `trackables.Project` | sysadmin board |
|---|---|---|
| Created by | you, via POST | discovered by scanner |
| Deleted by | you, softly | never — reappears next scan |
| Includes | hobbies, non-code | code repos only |

Inserting the board into that table turns a short intentional list into a
mixed feed, and the soft-deleted rows would fight re-discovery every six
hours.

**Render the board as its own view**, the way Alfred already renders
briefings. For the two that genuinely overlap, add a nullable
`sysadmin_name` on `trackables.Project` and decorate that row with health
data — a join, not a merge.

## 4. Where else the same data appears

- **The 06:00 briefing** gains a `"Pick This Up"` section (`type: table`,
  rows of `{project, next, source, note?}`, capped at 5, stalled first).
  Same data, pushed rather than pulled — the nudge, where the page is the
  detail. Section is **omitted entirely** when there is nothing to show,
  per the standing briefing rule.
- `GET /api/projects/actions` — ranked housekeeping advice across the
  portfolio, including `kind: "roadmap"` items. Use for a "needs
  attention" panel; the board's `top_action` is a one-line preview of it.

  **This list saturates.** Its currency is recoverable score points, so
  0-point advice sorts last, and 11 projects currently share one
  `no_remote` risk that fills the default limit entirely. Always read
  `dropped_by_kind` from the response and surface it — "+12 more,
  including 6 roadmap items" — or the panel will look complete while
  hiding a whole category. Raise `limit` (max 50) if you want the tail.
- `GET /api/projects/{name}` — per-project detail and score history, for
  a drill-down.

## 5. Deliberate omissions

- **Dormant and archived projects are excluded by default.** They have no
  next action by definition — declaring a project dormant *was* the
  decision. `include_inactive=true` exists for an inventory view; the
  main page should not use it.
- **No writes.** The board reports; it does not restart services, create
  tasks or edit repos. If "turn this recommendation into a work item"
  becomes a feature, the write belongs in Alfred against its own tables —
  sysadmin stays read-only by design.

## 6. Failure states

| Condition | Response | Page should show |
|---|---|---|
| sysadmin down | connection refused | "Estate data unavailable" — not an empty list |
| No scan yet | `200`, `projects: []` | "No projects scanned yet" |
| Stale data | `200` | `scanned_at` — surface it if older than ~12h (the scanner runs 6-hourly) |

Empty and unreachable must look different. An empty list rendered as "no
projects" when the service is actually down is the same silent-degradation
failure this repo keeps finding.

## 7. What is coming, and what to leave room for

Planned as Sessions 29–32 (see [tasks.md](../roadmap/tasks.md)). None of it
is built; the point of listing it here is that **one of these changes what
the primary surface should be**, and building the wrong thing first is
avoidable:

- **`GET /api/projects/next`** — *one* project, one action, plus a `reason`
  string, instead of a list. For **alfred-glance** this is the right
  endpoint, not the board: glance-then-act wants one thing, and a six-row
  list on a phone reintroduces the choosing problem the feature exists to
  remove. The board stays correct for a desktop page.

  Its ranking policy is an open decision and is the whole feature — longest
  idle optimises for guilt, smallest-next-step optimises for momentum. Do
  not assume an order; render the `reason` the endpoint gives you.
- **Alfred creating `work_item`s** from that endpoint, one per active
  project, refreshed daily, linked by the nullable `sysadmin_name` on
  `trackables.Project`. The write happens **in Alfred, pulling** — which is
  what keeps §3's boundary intact and sysadmin read-only.
- **Idle nudges** — a project with a stated next action and no commits for
  N days. Delivered over the existing notification path, not a new one.

Design so additions are free: **render what arrives, ignore what you do not
recognise, never hard-code the set of fields or sections.** The briefing
grew from five sections to seven without any consumer change, which is the
standard to hold to.

## 8. CORS

`http://localhost:3100` and `http://127.0.0.1:3100` are already in
`service.cors_origins`, added during the PA→Alfred migration. A browser
fetch from Alfred's Nuxt frontend works without changes here.
