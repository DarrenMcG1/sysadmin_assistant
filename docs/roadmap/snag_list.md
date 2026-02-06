# Snag List

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [ideas.md](ideas.md)
>
> **Last Updated**: _YYYY-MM-DD_

---

## Summary

| Status | Count | Description |
|--------|-------|-------------|
| Open | 0 | — |
| Fixed | 0 | — |

---

## Open Issues

_None — all clear._

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
