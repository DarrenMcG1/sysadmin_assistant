# Ideas & Feature Requests

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [snag_list.md](snag_list.md)
>
> **Last Updated**: 2026-07-24

---

## Ideas Inbox

_Capture ideas here as they come up. Promote to tasks.md when ready to implement._

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

_Remaining inbox clear — all other pending ideas promoted to sessions on 2026-07-24:_

- File organisation & cleanup → **Session 18**
- Dashboard enhancements → **Session 19**
- Project management (branch cleanup, per-project thresholds, TODO cap) → **Session 20**
- Developer experience (shared models, drift guard, smoke test) → folded into **Sessions 13–14**
- Self-monitoring (self endpoint, SSE, anomaly detection) → **Session 17**
- Notifications — less obtrusive → **Session 16**

### Explored & Rejected

- ~~**SSL cert expiry checks**~~ — not needed for localhost-only services
