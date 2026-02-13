# Snag List

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-02-13

---

## Summary

| Status | Count | Description |
|--------|-------|-------------|
| Open | 0 | — |
| Fixed | 3 | SNAG-TRAY-001, SNAG-TRAY-002, SNAG-TRAY-003 |

---

## Open Issues

_None — all clear._

---

## Fixed Issues

### SNAG-TRAY-001 — Tray app crashes on startup (P0) — Fixed 2026-02-13
`DbusNotifier._on_action_invoked` and `_on_notification_closed` missing `@pyqtSlot` decorators. PyQt6 requires decorated methods for `QDBusConnection.connect()`.

### SNAG-TRAY-002 — D-Bus Notify call fails with signature mismatch (P1) — Fixed 2026-02-13
`QDBusInterface.call()` inferred INT32 for `replaces_id` (needs UINT32) and array-of-variant for `actions` (needs array-of-string). Fixed with `QDBusMessage.createMethodCall()` + explicit `QDBusArgument` types.

### SNAG-TRAY-003 — Notification spam on startup (P1) — Fixed 2026-02-13
Backend creates new DB rows per scan cycle for the same alert. Dedup by `alert.id` caused N notifications per logical alert. Fixed with content fingerprint dedup (`severity:title`).

---

## Creating New SNAGs

**Naming**: `SNAG-###` or use domain prefixes like `SNAG-WEB-###`, `SNAG-API-###`, `SNAG-DB-###`

**Priority levels:**
- `[P0]` - Critical: Blocks users or causes data loss
- `[P1]` - High: Important functionality broken
- `[P2]` - Medium: Workaround exists

**Format:**
```markdown
- [P1] SNAG-WEB-001: Brief description (YYYY-MM-DD)
  - **Symptom**: What the user sees
  - **Cause**: Root cause (if known)
  - **Fix**: What was done to fix it (when resolved)
```

**Create for**: User-facing bugs, 500 errors, security issues, performance regressions

**Don't create for**: Feature requests (use ideas.md) | Transient errors
