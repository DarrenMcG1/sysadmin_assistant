# Ideas & Feature Requests

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [snag_list.md](snag_list.md)
>
> **Last Updated**: _YYYY-MM-DD_

---

## Ideas Inbox

_Capture ideas here as they come up. Promote to tasks.md when ready to implement._

### High Priority

- **KDE System Tray App** — Desktop tray icon with popup stats window. Shows service health at a glance (green/amber/red), CPU/RAM/disk gauges, active alert count. Includes a dev instance manager to start/stop/restart monitored services without opening a terminal. Uses KDE desktop notifications (D-Bus) for critical alerts. Could be PyQt6/PySide6 polling the sysadmin API, packaged as `sysadmin-tray` or an optional `[tray]` extra. The API is already there — this is purely a frontend/UX layer.

### Nice to Have

_Ideas for later consideration._

### Explored & Rejected

_Ideas that were considered but won't be implemented, with rationale._
