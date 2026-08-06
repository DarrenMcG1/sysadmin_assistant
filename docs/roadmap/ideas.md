# Ideas & Feature Requests

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [snag_list.md](snag_list.md)
>
> **Last Updated**: 2026-08-05

---

## Ideas Inbox

_Capture ideas here as they come up. Promote to tasks.md when ready to implement._

### ✅ Promoted 2026-08-05 — the project-manager tier pattern in other domains

Sessions 21–23's three-tier ladder (measure → advice as data → periodic LLM
narrative) generalises, and all four candidates captured here are now
**Sessions 24–27 in [tasks.md](tasks.md)**, where the full detail lives:

| Session | Domain | Note |
|---|---|---|
| 24 | File organiser tiers | Currency is reclaimable bytes; also promotes the forecast maths out of the tray |
| 25 | Service reliability scoring | Scores services from `health_checks`/`alerts` history, which nothing reads today |
| 26 | Service discovery — unmonitored-unit detector | Directly requested; the mechanical backstop for [guides/monitorable-project.md](../guides/monitorable-project.md) |
| 27 | Log aggregator tiers | Coupled to SNAG-AGENT-002 — signature fingerprinting fixes both |

The detector ideas parked below feed **Session 24** as new Tier 1 findings:
once a finding exists, the advice for it follows automatically, which is the
payoff of the advice-mirrors-findings design.

### Housekeeping follow-ups from the 2026-08-04 ~/projects reorganisation

The Tier 2 recommendations engine landed 2026-08-04 (Session 22:
`GET /api/projects/{name}/recommendations` + `GET /api/projects/actions`)
and now surfaces **missing remotes natively** — the six unbacked repos
appear as `risk` items in `/api/projects/actions` after every scan, so
that follow-up no longer needs a doc entry. The rest stay parked because
the scanner has no finding for them yet; each is really a *detector idea*:

- **apps/oanIt vs apps/habitTracker** — habitTracker contains
  `oanIt_Frontend`/`oanIt_backend` dirs; both trees have real content.
  Needs a manual look. (Detector idea: name-similarity duplicate flag.)
- **apps/BudgetApp venv clutter** — carries both `.venv` and `.venv1`
  (~290M, recreatable). (Detector idea: multiple/oversized venvs as a
  `hygiene` finding — the file organiser already hunts stale caches.)
- **Config loader could warn on nonexistent managed paths** — would have
  caught SNAG-CONF-001 immediately (also noted in snag_list.md).

### Rebuild the sysadmin web UI inside Alfred's frontend

The web dashboard was built in PersonalAssistant and died with it (2026-07-24);
the PyQt6 tray is currently the only UI. Alfred — PA's replacement — ships a
**Nuxt frontend on :3100**, which is the obvious host for a rebuild.

Nothing on the backend needs to change to make this possible:

- **The API is unchanged.** The same 25+ endpoints the PA dashboard consumed are
  still served on :8500, and their response shapes are now pinned by
  `sysadmin/contracts.py` (the tray's contracts) rather than hand-copied — so a
  web client and the tray can't drift apart the way they used to.
- **`GET /api/sysadmin/events`** (SSE, Session 17) means a browser client can
  subscribe with `EventSource` instead of polling, which the tray still doesn't
  do — the web UI could be the first real consumer.
- **Mutating routes are bearer-auth protected** (Session 12: service actions,
  alert ack, DND, scans, file/branch actions). A browser UI therefore needs the
  `api.auth_token` — and since it can't hold a shared secret safely, the sane
  shape is for Alfred's *backend* to proxy the mutating calls and hold the token
  server-side, leaving the browser to hit read-only GETs directly. Worth
  deciding before any UI work starts, not after.
- **CORS** already lists `http://localhost:3100` / `http://127.0.0.1:3100` in
  `service.cors_origins`, added during the PA→Alfred migration.

Scope worth having on day one: the Overview/resource charts, the alerts list with
ack, and the Projects tab — the parts that benefit most from a big screen. The
Files tab's action endpoints (Session 18) are the higher-risk surface and should
follow, not lead.

---

_Promoted 2026-08-05:_

- Tier pattern in other domains (file organiser, service reliability,
  service discovery, log aggregator) → **Sessions 24–27**

_Promoted 2026-07-24:_

- File organisation & cleanup → **Session 18**
- Dashboard enhancements → **Session 19**
- Project management (branch cleanup, per-project thresholds, TODO cap) → **Session 20**
- Developer experience (shared models, drift guard, smoke test) → folded into **Sessions 13–14**
- Self-monitoring (self endpoint, SSE, anomaly detection) → **Session 17**
- Notifications — less obtrusive → **Session 16**

### Explored & Rejected

- ~~**SSL cert expiry checks**~~ — not needed for localhost-only services
