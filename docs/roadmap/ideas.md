# Ideas & Feature Requests

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [snag_list.md](snag_list.md)
>
> **Last Updated**: 2026-03-23

---

## Ideas Inbox

_Capture ideas here as they come up. Promote to tasks.md when ready to implement._

### Nice to Have

- **More monitored services** — Add redis (tcp :6379), sshd (systemd), NetworkManager (systemd), and an internet connectivity check (HTTP to cloudflare) to `config.yaml` services list. Also add sysadmin-service itself and kernel to log aggregator sources.
- **Tray config improvements** — Reduce `alert_poll_seconds` from 180→60 for faster alert visibility. Change `notify_min_severity` from `critical`→`warning` to catch degradations. Add `show_resource_in_tooltip` and `click_action` options.
- **Ollama night model scheduling** — Add `night_hours: {start: "22:00", end: "06:00"}` to ollama config so the service knows when to switch models automatically.
- **Per-table retention policy** — Currently only logs have `retention_days: 30`. Add configurable retention for resource_snapshots (90d), service_health (30d), and alerts (180d) to prevent unbounded table growth.
- **Fix config key name** — `personal_assistant_backend1` in config.yaml should be `personal_assistant` to match the Pydantic model field name. The `1` suffix looks like a copy-paste artefact.

### Explored & Rejected

- ~~**SSL cert expiry checks**~~ — not needed for localhost-only services
