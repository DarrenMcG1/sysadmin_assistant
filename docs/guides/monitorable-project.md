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

**Declaring status is the highest-leverage line in this file.** An
undeclared project defaults to `active`, because a directory cannot tell
the scanner your intent — which is why the board showed 18 "active"
projects for a four-project estate. One line per repo suppresses
staleness penalties, roadmap nagging and board rows at once. Write the
declaration before writing any document the declaration would make
unnecessary.

### The roadmap document set (active projects only)

Added 2026-08-06. Recorded by the scanner, surfaced on
`GET /api/projects/board`, and **waived entirely for `dormant` and
`archived`** — generating session docs for a repo you have deliberately
parked is busywork dressed as progress.

| Document | Purpose | Who writes it |
|---|---|---|
| `docs/sessions/handoff.md` | Where work actually stopped. **The** source of the next action | the SessionEnd hook, automatically |
| `docs/roadmap/tasks.md` | What was *planned*. Fallback when no handoff exists | you |
| `docs/roadmap/snag_list.md` | Known bugs, under an "Open Issues" heading | you |
| `docs/roadmap/STATUS.md` | Current phase and recently completed | you |
| `docs/roadmap/ideas.md` | Not yet promoted to work | you |

Notes that stop this rotting:

- **Don't hand-write handoffs.** `~/.claude/hooks/generate-handoff.sh`
  runs on SessionEnd in whatever repo the session ran in, and skips
  sessions that changed nothing so a read-only visit cannot overwrite a
  real one. A hand-written handoff is a snapshot that starts rotting
  immediately; a generated one is a byproduct of work you were doing.
- **`docs/roadmap/handoff.md` is accepted too** (Alfred's convention).
  Both paths are read; pick one and stay with it.
- **Checkboxes are optional.** A `tasks.md` tracked as a status table
  (Alfred) reports `open_tasks: null`, meaning "not measurable here" —
  which is honest. Only checkbox lists get counted.
- **Age qualifies the content.** A next action from a handoff older than
  30 days is not today's task; the board flags it `stalled` and the
  advice becomes "resume or park", not "do this".

### Basic hygiene (every project, whatever its status)

| Requirement | Why |
|---|---|
| `README.md` | Costs 10 points; the only doc the scanner has always checked |
| `CLAUDE.md` | Costs 10 points — agent sessions otherwise start blind |
| **A git remote** | Costs no points but ranks above everything as a `risk`: no remote means the only copy is on this disk |

The remote is the one that matters. As of 2026-08-06, **11 repos have
none** — including `sysadmin_assistant` itself, which also has no
`README.md`. `GET /api/projects/actions` lists them; they saturate its
default view, which is what `dropped_by_kind` in the response exists to
tell you.

---

## Contract 2 — Service integration (manual: follow this at creation time)

For any project that runs as a service (backend, frontend, scheduled job).

### 2.1 Ports — the registry

One backend port and one frontend port per project, allocated here. **Add
your row when you claim one.**

| Port | Project | Role |
|---|---|---|
| 8080 | venture-assistant | llama-server chat, granite-3.1-8b (`venture-chat.service`) — ⚠ see below |
| 8081 | Alfred | llama-server inference (`alfred-inference.service`) |
| 8082 | venture-assistant | llama-server embeddings, nomic-embed (`venture-embed.service`) |
| 8083 | venture-assistant | llama-server nightly chat, mistral-small-24b (`venture-chat-large.service`) |
| 8100 | Alfred | backend (FastAPI) |
| 8200 | SportsAnalyser | backend (FastAPI) |
| 8300 | venture-assistant | backend (FastAPI, `venture-assistant-backend.service`) — claimed 2026-08-07 |
| 8400 | _free — next backend allocation_ | |
| 8500 | sysadmin-service | backend (FastAPI) |
| 3100 | Alfred | frontend (Nuxt) |
| 3200 | SportsAnalyser | frontend (Next.js) |
| 3300 | _free — next frontend allocation_ | |

**Never take a tool's default port.** 8080 is llama.cpp's default, and it
is also the default of Tomcat, Jenkins, webpack-dev-server, `http.server`
in half the tutorials, and most Docker examples. A project sitting on a
popular default will one day lose a race at boot to something started by
hand, and the symptom is an obscure connection error in the *other*
project. venture-assistant holds 8080 today only because it was allocated
before this rule existed; it should move to 8301 when next touched
(`app/config.py:10` is the sole consumer).

Sidecar processes count. An inference server, a worker's admin port and a
metrics exporter each need a row — a registry that records only "the
backend" is how a project ends up with three unlisted listeners.

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

### 2.5 GPU-resident services

Only if the project loads a model onto the dGPU. Added 2026-08-06 after
three llama-servers were found running their models in system RAM.

- **Gate the start on the GPU actually being visible**:
  `ExecStartPre=%h/.local/bin/wait-for-dgpu`. At boot the user manager
  starts services before amdgpu is ready; llama.cpp logs `no devices with
  dedicated memory found` and loads every layer into CPU buffers. The unit
  stays `active (running)` and `/health` returns 200 throughout, so
  nothing monitors its way to the truth.
- **`After=dev-dri-renderD128.device` does not work** — udev does not TAG
  the render node with `systemd`, so that unit is permanently
  `inactive (dead)` and ordering against it is a silent no-op. Verify
  before trusting any device ordering:
  `systemctl --user show dev-dri-renderD128.device -p ActiveState`.
- **`-ngl 99` is a request, not a constraint.** So is any equivalent flag.
  Assert the outcome after a config change:

  ```bash
  journalctl --user -u <unit> -b | grep "model buffer size"
  # Vulkan0 → on the GPU.  CPU_Mapped / CPU_REPACK → it fell back.
  ```

- **Declare the VRAM.** The card is 24 GB and shared by every project.
  Record roughly what your service holds resident, and if a scheduled job
  needs a large model, make it `Conflicts=` the resident server it must
  displace — with `After=` on the same unit so the eviction completes
  before the load starts. `Conflicts=` does **not** restart what it
  stopped: the job's `ExecStopPost` must put it back.
- **CPU-only on purpose? Say so in the flags**, not just a comment
  (`-ngl 0`). An intent that only exists in prose is one boot race away
  from being violated.

| Service | Model | Resident VRAM |
|---|---|---|
| `alfred-inference` | dria-agent-a-3b Q4, 4k ctx | ~2.0 GB |
| `venture-chat` | granite-3.1-8b Q4, 8k ctx | ~6.1 GB |
| `venture-embed` | nomic-embed-text-v1.5 | none (`-ngl 0`) |
| `venture-chat-large` | mistral-small-24b Q4, 8k ctx | ~14.8 GB, 02:00 only, evicts `venture-chat` |

### 2.6 Checklist (copy into the new project's setup task)

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
- [ ] GPU-resident? `ExecStartPre=%h/.local/bin/wait-for-dgpu`, VRAM row
      added to §2.5, and the startup log asserted to show a `Vulkan0`
      model buffer rather than `CPU_Mapped`

---

## Why a doc is not enough

Docs drift, so the backstop is mechanical. **Since 2026-08-07 this contract
is enforced by the service-discovery agent** (Session 26), which sweeps
every installed unit every six hours and reports the gaps:

    curl -s localhost:8500/api/units/status  | jq .summary
    curl -s localhost:8500/api/units/actions | jq '.recommendations[] | {kind, title, action}'

`/api/units/actions` hands back **ready-to-paste YAML**, correctly targeted:
a `config.yaml` `services:` entry for timers and for units with no project,
a `projects.yaml` fragment for a long-running unit whose project already has
an entry. It never edits either file — both are hand-curated and their
comments carry the reasoning, which a rewriter would destroy.

Three categories, worst first:

| Category | Meaning | Fix |
|----------|---------|-----|
| `orphaned` | Dead `WorkingDirectory`, or the project is declared `archived` | Remove it — the exact `systemctl disable && rm` is in `action` |
| `unmonitored` | Maps to a live project, nothing in projects.yaml or config.yaml watches it | Paste the snippet |
| `host` | Hand-written, maps to no project (`pgbackrest-backup`, `ethernet-optimise`) | Paste the config.yaml snippet |

An orphan is ranked `risk`, above everything else, because it is not merely
unwatched: a `WorkingDirectory` that no longer exists makes systemd fail the
start job outright, so the unit has been failing on every start — silently,
precisely because nothing monitored it.

**Two contract rules the detector will catch you breaking**, both because
they cost a live debugging session first:

- A `projects.yaml` endpoint with a `systemd_unit` but **no `url` is
  inert** — `ManagedProject.to_monitored_services` skips it, so the entry
  looks wired and checks nothing. This is why generated snippets leave
  `url:` commented rather than omitting it.
- A `Type=oneshot` service must be monitored **via its `.timer`**. A oneshot
  is `inactive (dead)` between runs by design, so checking the service
  alerts continuously; a timer stays `active (waiting)` whenever it is
  armed, which makes an inactive one a genuine fault.

The pointer in `~/.claude/CLAUDE.md` (which makes every future Claude
session building a service read this contract) remains the *creation-time*
enforcement; the agent is the ongoing one.
