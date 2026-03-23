# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-03-23

---

## Active Sessions

_No active sessions._

---

## Backlog

### KDE Tray App — Phase 3 Polish

Core service actions already work end-to-end (right-click menu in popup, buttons in dashboard, controllable flag gating, desktop notifications). Two UX polish items remain:

- [ ] Refresh service status after popup actions (dashboard already does this, popup doesn't)
- [ ] Show "working..." label on popup service row during in-flight actions
- [ ] Add router tests for `POST /services/{name}/{action}` (404, 403, 400, 200 paths)

### Future

- [ ] Nuxt frontend pages in PA (/infrastructure, /infrastructure/projects, /infrastructure/storage, /infrastructure/logs)

---

## Archive

All completed sessions and features archived in [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md).
