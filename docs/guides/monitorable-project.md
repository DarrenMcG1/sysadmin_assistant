# The Monitorable-Project Contract

How to build a project under `~/projects` so the sysadmin assistant can
discover, score, health-check and log-follow it **without anyone having to
remember anything later**. Written 2026-08-05 after the SportsAnalyser case:
three live systemd units sat unmonitored for weeks because wiring them into
monitoring was a manual step nobody was reminded to do.

Two contracts live here. The first is enforced automatically by the scanner —
break it and your score drops and a recommendation appears. The second is
**manual and rots silently** — follow it at creation time, because every
monitoring incident in this repo's history (the PA path that never existed,
the missing `user: true` scope, SportsAnalyser's unwired units, Alfred's
guessed-wrong health path) was a violation of this second contract.

---

## Contract 1 — What the scanner scores (automatic)

Any directory under `~/projects` within discovery depth gets this for free.
No registration needed.

| Requirement | Why / what happens otherwise |
|---|---|
| A project marker at the top level: `.git`, `pyproject.toml`, `package.json`, `Cargo.toml`, or `go.mod` | No marker → not discovered as a project (treated as a category folder and searched one level deeper) |
| Placed in the right category folder (`apps/`, `web/`, `ml/`, `games/`, `learning/`) | Location is metadata: anything under `archive/` is inferred `status: archived` (staleness + branch hygiene waived) |
| `README.md` at the project root | Missing → score deduction + recommendation |
| A git remote configured | No remote → `risk` finding ranked above everything ("the only copy of this repo is on this disk") |
| Branches pruned (merged + stale ones deleted) | Deduction per stale branch, capped at 5; `POST /api/projects/{name}/branches/prune` does it safely (dry-run by default) |
| TODO/FIXME kept down | Deduction capped at 30 points |
| No stale `.git/index.lock` | Deduction (usually means a crashed git process) |
| Vendored sub-repos are fine | A marker-bearing directory is never descended into, so inner repos stay invisible |

Non-default lifecycle? Declare it in `projects.yaml`: `status: dormant`
(resting on purpose — staleness unpenalised) or `status: archived`.

---

## Contract 2 — Service integration (manual: follow this at creation time)

For any project that runs as a service (backend, frontend, scheduled job).

### 2.1 Ports — the registry

One backend port and one frontend port per project, allocated here. **Add
your row when you claim one.**

| Port | Project | Role |
|---|---|---|
| 8081 | Alfred | llama-server inference (`alfred-inference.service`) |
| 8100 | Alfred | backend (FastAPI) |
| 8200 | SportsAnalyser | backend (FastAPI) |
| 8300 | _free — next backend allocation (e.g. venture-assistant)_ | |
| 8500 | sysadmin-service | backend (FastAPI) |
| 3100 | Alfred | frontend (Nuxt) |
| 3200 | SportsAnalyser | frontend (Next.js) |
| 3300 | _free — next frontend allocation_ | |

### 2.2 Health endpoint

- Serve **`GET /api/health`** returning HTTP 200 with a small JSON body,
  e.g. `{"status": "healthy", "version": "...", "database": "connected"}`.
- This is the canonical path for **new** projects. The existing variants
  (`/health` on sysadmin, `/api/v1/health` on SportsAnalyser) are
  grandfathered — the checker takes any URL, but every new variant is a
  path someone has to discover by probing. Alfred's first entry 404'd
  twice before the right path was found; don't repeat that.
- The endpoint must not require auth: the monitor sends a bare GET.

### 2.3 systemd units

- **User units** in `~/.config/systemd/user/`, named
  **`<project>-<role>.service`** (lowercase project name, e.g.
  `venture-assistant-backend.service`). The name prefix and the
  `WorkingDirectory` are how tooling maps a unit back to its project —
  keep both honest.
- Skeleton for a long-running service:

  ```ini
  [Unit]
  Description=<Project> - <Role>
  After=network-online.target
  Wants=network-online.target

  [Service]
  Type=simple
  WorkingDirectory=%h/projects/<category>/<ProjectDir>
  ExecStart=<absolute command>
  Restart=always
  RestartSec=10
  StandardOutput=journal
  StandardError=journal
  SyslogIdentifier=<project>-<role>

  [Install]
  WantedBy=default.target
  ```

- **Scheduled jobs are `Type=oneshot` + a `.timer`** (with
  `Persistent=true`), never a long-running loop. A oneshot service is
  inactive between runs *by design*, so the sysadmin monitors the
  **timer**, not the service — an inactive timer genuinely means the
  schedule has stopped. (This is the alfred-evaluate rule.)
- **`systemctl --user enable` every unit explicitly** — including ones
  another unit `Requires=`. SportsAnalyser's backend was `disabled` and
  only ran because the frontend dragged it in; that survives exactly
  until the frontend is stopped or changed.
- Lingering is already enabled for `gaddi` (`loginctl show-user gaddi -p
  Linger` → `yes`), so user units run without an open session. If this is
  ever a fresh machine: `loginctl enable-linger gaddi` first.

### 2.4 Wire it into the sysadmin (same day, not "later")

1. **projects.yaml** — add/extend the project entry. `user: true` is
   mandatory for user units: without it the daemon queries the *system*
   scope, which has never heard of the unit, and the check fails silently
   forever (how the old PA entries rotted).

   ```yaml
   - name: venture-assistant
     path: /home/gaddi/projects/apps/venture-assistant
     backend:
       url: http://localhost:8300/api/health
       port: 8300
       systemd_unit: venture-assistant-backend.service
       user: true
       log:
         type: journalctl
         unit: venture-assistant-backend.service
         severity_filter: warning
     frontend:
       url: http://localhost:3300
       port: 3300
       systemd_unit: venture-assistant-frontend.service
       user: true
       log:
         type: journalctl
         unit: venture-assistant-frontend.service
         severity_filter: warning
   ```

2. **config.yaml** — projects.yaml only models `backend`/`frontend`, so
   **timers go in `agents.sysadmin.services`**:

   ```yaml
   - name: venture-assistant-pipeline-timer
     type: systemd
     systemd_unit: venture-assistant-pipeline.timer
     user: true
     controllable: false
   ```

3. **CORS** — only if the project's *browser* frontend will call the
   sysadmin API directly: add its origin to `service.cors_origins`.
   Serving its own app does not need this.

4. **Restart the daemon** — config is read at startup:
   `sudo systemctl restart sysadmin.service` (system unit, needs sudo).

5. **Verify, don't assume** — the wiring is only done when you've seen it
   work:

   ```bash
   curl -sf http://localhost:8300/api/health          # endpoint answers
   systemctl --user is-active venture-assistant-backend.service
   curl -s http://localhost:8500/api/sysadmin/status | python -m json.tool \
     | grep -A3 venture                               # sysadmin sees it as ok
   ```

### 2.5 Checklist (copy into the new project's setup task)

- [ ] Ports claimed in the registry table above (backend + frontend)
- [ ] `GET /api/health` returns 200 JSON, no auth
- [ ] User units named `<project>-<role>.service`, `WorkingDirectory` set,
      `SyslogIdentifier` set, journald output
- [ ] Scheduled jobs are oneshot + timer (`Persistent=true`)
- [ ] Every unit `systemctl --user enable`d explicitly
- [ ] projects.yaml entry with `user: true` and log blocks
- [ ] Timers added to config.yaml `agents.sysadmin.services`
- [ ] `sudo systemctl restart sysadmin.service`
- [ ] Verified via `/api/sysadmin/status`

---

## Why a doc is not enough

Docs drift; the backstop is mechanical: `docs/roadmap/ideas.md` holds the
**unmonitored-unit detector** idea — the project organiser cross-referencing
installed units against projects.yaml and raising findings (with ready-to-
paste snippets) for anything unwired or orphaned. Until that lands, this
guide plus the pointer in `~/.claude/CLAUDE.md` (which makes every future
Claude session building a service read this contract) are the enforcement.
