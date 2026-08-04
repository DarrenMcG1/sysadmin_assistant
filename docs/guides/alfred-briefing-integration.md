# Feeding the morning briefing into Alfred

The sysadmin service already generates a full briefing payload every
morning — delivery is merely switched off because PersonalAssistant (the
old consumer) died. To feed Alfred, build one inbox route in Alfred and
flip three config values here. Written 2026-08-04.

## What arrives, and when

`send_morning_briefing` runs daily at **06:00** (`schedules.briefing_hour`
/ `briefing_minute` in config.yaml) and POSTs JSON:

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
      "title": "Weekly Project Review",
      "type": "text",
      "data": "What moved: ...\n\n<LLM narrative: decay, archive candidates, focus>"
    }
  ]
}
```

Rules a consumer must honour:

- **Sections are omitted, not empty** — no overnight logs means no
  "Overnight Log Summary" entry. Render what arrives; never assume all
  five.
- **`type` drives rendering**, one of `status_grid | text | metrics |
  table`. Treat unknown types as `text` (stringify `data`) so new
  section types degrade gracefully.
- "Weekly Project Review" appears only while the latest stored review is
  **under 8 days old** (it is generated Mondays 05:30, deliberately
  before the 06:00 briefing). Its `data` opens with a deterministic
  "What moved:" line — the numbers are computed, not LLM output.
- `data` for `text` is a plain string; the LLM sometimes emits markdown
  despite instructions, so render it markdown-tolerantly.
- No `generated_at` in the wire payload (only sections are sent);
  timestamp on receipt.

## Delivery mechanics

- Sender: `Notifier.send_briefing_data` → `_post_with_retry` — up to 3
  attempts with exponential backoff; success is any status < 400.
- **No auth header is sent.** Alfred's inbox route must accept an
  unauthenticated localhost POST, or auth support needs adding to
  `Notifier` first.
- A failed delivery logs a warning here; nothing queues — the next
  morning simply sends the next briefing.

## Switching it on (this repo's config.yaml)

The outbound section is still *named* `personal_assistant` — it is just
"the briefing/notification consumer":

```yaml
personal_assistant:
  enabled: true                     # currently false — the master switch
  url: http://localhost:8100        # Alfred's backend
  briefing_endpoint: /api/v1/briefings/sysadmin   # whatever route Alfred exposes
  notify_endpoint: /api/v1/notifications/sysadmin # optional, see below
```

No restart-time schema to match — Alfred defines the route, these values
point at it. (Renaming the config section to something neutral like
`briefing_consumer` would be a small tidy-up when touched next.)

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

## Pull alternative (no Alfred inbox needed)

Everything in the briefing is also pullable from this service on :8500,
so Alfred could poll instead of hosting an inbox:

| Data | Endpoint |
|------|----------|
| One-call digest (services, alerts, resources, projects) | `GET /api/summary` |
| Weekly review narrative | `GET /api/projects/review` |
| Top housekeeping actions | `GET /api/projects/actions` |
| Live event stream | `GET /api/sysadmin/events` (SSE) |

All GETs are unauthenticated; response shapes are pinned in
`sysadmin/contracts.py`.
