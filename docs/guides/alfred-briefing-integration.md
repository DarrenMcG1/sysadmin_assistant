# The morning briefing and Alfred

> **Corrected 2026-08-06.** The original version of this guide told you to
> build an inbox route in Alfred and flip three config values. **Don't.**
> Alfred already consumes this briefing, and has for some time — it
> *pulls* rather than receiving a push:
>
> ```
> Alfred  backend/alfred/services/briefings.py → adapt_sysadmin()
>         GET http://localhost:8500/api/sysadmin/briefing/preview
> ```
>
> `personal_assistant.enabled: false` was never relevant to that path.
> Sections added here appear in Alfred's briefing with no configuration
> change at all — "Pick This Up" landed on 2026-08-06 and flowed through
> immediately. **Before changing anything about delivery, check what the
> consumer already does**; this guide spent two days advising work that
> was already finished.

Written 2026-08-04, corrected 2026-08-06.

## The two paths

| | Pull (**in use**) | Push (dormant) |
|---|---|---|
| Route | `GET /api/sysadmin/briefing/preview` | POST to `personal_assistant.briefing_endpoint` |
| Trigger | whenever Alfred asks | 06:00 cron (`schedules.briefing_hour`) |
| Payload | the full dict — **includes `generated_at`** | `sections` only |
| Gate | none; open GET | `personal_assistant.enabled` (currently `false`) |
| Consumer | Alfred, today | nothing since PA was retired 2026-07-24 |

Both render the same sections from the same `generate_briefing_data`.
The push path is kept because it costs nothing and suits a consumer that
cannot poll — but nothing needs it today.

## What arrives, and when

Both paths serve the output of `generate_briefing_data`. The push path
POSTs only the `sections` array:

```json
{
  "source": "sysadmin-service",
  "sections": [
    {
      "title": "Infrastructure Status",
      "type": "status_grid",
      "data": {
        "all_services_healthy": false,
        "services": [
          {"name": "alfred", "status": "ok"},
          {"name": "postgres", "status": "critical", "note": "Connection refused"}
        ]
      }
    },
    {
      "title": "Overnight Log Summary",
      "type": "text",
      "data": "One narrative paragraph summarising the last 12h of logs."
    },
    {
      "title": "Filesystem",
      "type": "metrics",
      "data": {
        "disk_used_percent": 68.0,
        "reclaimable_mb": 1234,
        "empty_dirs": 5,
        "stale_project_dirs": 2,
        "duplicate_groups": 3
      }
    },
    {
      "title": "Project Health",
      "type": "table",
      "data": [
        {"project": "Alfred", "score": 95},
        {"project": "BudgetApp", "score": 65, "note": "3 stale branches, 25 TODOs"}
      ]
    },
    {
      "title": "Pick This Up",
      "type": "table",
      "data": [
        {"project": "ImbaBots", "next": "M5-T05 — free-aim feel with the chase camera",
         "source": "handoff"},
        {"project": "SportsAnalyser", "next": "Session 17: Venue & Contextual Features",
         "source": "handoff", "note": "stalled 152 days — resume or park"}
      ]
    },
    {
      "title": "Weekly Project Review",
      "type": "text",
      "data": "What moved: ...\n\n<LLM narrative: decay, archive candidates, focus>"
    },
    {
      "title": "Weekly Disk Review",
      "type": "text",
      "data": "<LLM narrative: occupancy direction, junk growth, horizon>"
    }
  ]
}
```

Rules a consumer must honour:

- **Sections are omitted, not empty** — no overnight logs means no
  "Overnight Log Summary" entry. Render what arrives; **never assume a
  fixed count.** There were five sections when this guide was written and
  seven now ("Pick This Up" and "Weekly Disk Review" arrived later); a
  consumer that hard-codes the set breaks silently every time one is
  added.
- **`type` drives rendering**, one of `status_grid | text | metrics |
  table`. Treat unknown types as `text` (stringify `data`) so new
  section types degrade gracefully.
- "Weekly Project Review" appears only while the latest stored review is
  **under 8 days old** (it is generated Mondays 05:30, deliberately
  before the 06:00 briefing). Its `data` opens with a deterministic
  "What moved:" line — the numbers are computed, not LLM output.
- `data` for `text` is a plain string; the LLM sometimes emits markdown
  despite instructions, so render it markdown-tolerantly. The same applies
  to `"Pick This Up"`'s `next` field — handoffs are hand-written and
  contain inline emphasis.
- **"Pick This Up" is capped at five rows** and sorted stalled-first. It is
  one action per project, deliberately not a backlog: a longer list is more
  to avoid, not less. `source` is `handoff` | `tasks` | `git` and says how
  much is actually known — a `git` value is a commit subject standing in
  for a next action, and rendering it identically to a `handoff` one
  overstates the confidence. `note` appears only when a project has
  stalled past 30 days, and then the row is a resume-or-park **decision**,
  not a task.
- **`generated_at` depends on the path.** The pull route returns it; the
  push path sends `sections` only, so a push consumer must timestamp on
  receipt. Do not assume its absence.

## Delivery mechanics (push path only — dormant)

None of this applies to Alfred, which pulls.

- Sender: `Notifier.send_briefing_data` → `_post_with_retry` — up to 3
  attempts with exponential backoff; success is any status < 400.
- **No auth header is sent.** Any future inbox would have to accept an
  unauthenticated localhost POST, or auth support needs adding to
  `Notifier` first.
- A failed delivery logs a warning here; nothing queues — the next
  morning simply sends the next briefing.

## Switching the push path on — only if a consumer needs it

**Alfred does not.** It pulls. Turning this on would deliver the same
sections a second time.

The outbound section is still *named* `personal_assistant`; it is just
"the briefing/notification consumer". The values in `config.yaml` today
are **PA-era and point at a service that no longer exists** — port 8000,
`/api/v2/intelligence/briefing/data`. They are inert while `enabled` is
`false`, and they are not a template to copy:

```yaml
personal_assistant:
  enabled: false                    # the master switch — leave it off
  url: http://localhost:8000        # dead: PA's port, retired 2026-07-24
  briefing_endpoint: /api/v2/intelligence/briefing/data   # dead route
  notify_endpoint: /api/v2/notifications/send             # dead route
```

If a future consumer genuinely cannot poll, point these at it and flip
`enabled`. Renaming the section to something neutral like
`briefing_consumer` would be a small tidy-up when next touched.

## The same switch also enables push notifications

`Notifier.send_notification` POSTs alerts to `notify_endpoint`:

```json
{
  "source": "sysadmin",
  "category": "system",
  "priority": "warning",
  "title": "Project BudgetApp health critical",
  "message": "Health score: 35/100 (alert threshold 40)",
  "details": {}
}
```

Gated by `notifications.pa_notify.min_severity` (below-threshold
severities are dropped) and DND windows. If Alfred only wants the
briefing, leave `notifications.pa_notify.enabled: false`.

## Everything else that is pullable

All unauthenticated GETs on :8500; response shapes pinned in
`sysadmin/contracts.py`.

| Data | Endpoint |
|------|----------|
| **The whole briefing** — what Alfred uses today | `GET /api/sysadmin/briefing/preview` |
| Estate board: per project, health + next action | `GET /api/projects/board` |
| One-call digest (services, alerts, resources, projects) | `GET /api/summary` |
| Weekly review narratives | `GET /api/projects/review`, `GET /api/files/review` |
| Ranked housekeeping actions | `GET /api/projects/actions`, `GET /api/files/actions` |
| Live event stream | `GET /api/sysadmin/events` (SSE) |

For a projects **page** rather than a briefing section, use the board and
read [alfred-projects-page.md](alfred-projects-page.md) — it specifies what
`next_action_source` obliges a consumer to render differently, and why the
board must not be written into Alfred's own `trackables.projects` table.

## Coming, and what it means for a consumer

Planned as Sessions 29–32 (see [tasks.md](../roadmap/tasks.md)); nothing
here is built yet, but the direction is fixed and worth designing around:

- **`GET /api/projects/next`** — *one* project and one action, with a
  `reason` field, rather than the board's list. This is the endpoint
  alfred-glance should eventually render, since glance-then-act wants one
  thing, not six. Expect it to supersede "Pick This Up" as the primary
  momentum surface; the briefing section will stay for the daily digest.
- **Alfred creating `work_item`s** from that endpoint — the write happens
  in Alfred, pulling, so this service stays read-only. No inbox, again.
- **Idle nudges** will ride the existing notification path
  (`Notifier.send_notification`), not a new one.

The stable contract across all of it: **sections and fields are added,
never renumbered or assumed complete.** Build consumers that render what
arrives and ignore what they do not recognise, and none of the above will
require a change on your side.
