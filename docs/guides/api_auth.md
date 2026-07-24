# API Authentication

State-changing endpoints require a shared bearer token (Session 12). Read-only
GET endpoints stay open so dashboards keep working without a token.

## Setup

`config.yaml` is committed to git, so the committed value is an empty
placeholder (auth disabled, warning logged at startup). To enable auth, set a
real token **locally** and do not commit it:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

```yaml
api:
  auth_token: "<generated hex token>"
```

Restart the service. The tray app reads the same `config.yaml` and picks the
token up automatically.

## Protected endpoints (POST)

- `/api/sysadmin/services/{name}/{action}` — start/stop/restart
- `/api/sysadmin/alerts/{id}/ack`
- `/api/sysadmin/dnd`
- `/api/sysadmin/scan-all`
- `/api/projects/scan`
- `/api/files/scan`
- `/api/files/clean/stale-caches`

All GET endpoints (status, resources, alerts, logs, summary, briefing preview,
DND status, etc.) remain unauthenticated.

## Client usage

Send the header on mutating requests (sending it on every request is fine):

```
Authorization: Bearer <token>
```

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8500/api/sysadmin/scan-all
```

Missing/wrong token → `401` with `WWW-Authenticate: Bearer`.

## PA integration (follow-up in the PA repo)

The PA frontend calls into this API. Its read-only dashboard views use GET
endpoints only, so they keep working with no changes. Any PA feature that
POSTs (triggering scans, acking alerts, service actions, DND) must add the
`Authorization: Bearer <token>` header, with the token stored in PA's own
config. That wiring lives in `/home/gaddi/projects/PersonalAssistant` and is
outside this repo.
