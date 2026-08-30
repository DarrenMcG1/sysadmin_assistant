# Project management capability audit

**Date:** 2026-08-07
**Scope:** the project and repository management capability inside
`sysadmin_assistant`, its maturity, and what it depends on.
**Method:** read the code, then check the claims against the live database
and a test run. Where the code and the documentation disagree, both are
recorded and the verified one is named.

**Phase 0 separation audit:** none exists. `docs/` contains `ARCHITECTURE.md`,
`guides/`, `insights/`, `refactors/` (empty), `roadmap/`, `sessions/` and
`templates/`; no file in the repository covers separation, extraction or a
Phase 0 boundary analysis. Section 6 (coupling) is therefore written in full
rather than deferred.

**Evidence gathered live (read-only):**

- `sysadmin.project_snapshots`: 3,388 rows, 2026-05-09 → 2026-08-07, 26
  distinct project names, 25 rows per scan, scans every ~3–6 h.
- `sysadmin.agent_runs`: `project_organiser` 91 runs (30-day retention
  window), latest 2026-08-07 14:30:55, 68 alerts raised.
- `sysadmin.project_reviews`: 4 rows, all dated 2026-08-04.
- `sysadmin.alerts` where `agent='project_organiser'`: 1,664 rows, all
  `severity=warning`, all `resolved=false`, latest 2026-07-24.
- `uv run pytest` over the eight project-side test files: **290 passed**.

This is an evidence-gathering exercise. No course of action is recommended
and nothing found here was fixed.

---

**Code citations describe the tree as at this date.** The backend was split
into domain packages the following day (`512af01`, 2026-08-08) and the whole
project domain left for estate-manager on 2026-08-13
([ADR-0005](adr/0005-project-state-leaves.md)). Each citation below therefore
keeps its original path and line range as written — they are the evidence this
audit rests on — and carries a live pointer to where that code is now. **Line
ranges are not re-pinned to current files**: they were measured against the
2026-08-07 tree and no longer hold anywhere.

---

## 1. Capability inventory

The scheduled trigger for most of this is one APScheduler interval job,
`project_organiser_scan`, registered in `main.py:123-128` as at this date (the job left with the projects domain — [ADR-0005](adr/0005-project-state-leaves.md); scheduling is now [`sysadmin/core/jobs.py`](../sysadmin/core/jobs.py))
at `agents.project_organiser.scan_interval_hours` (6, from `config.yaml`),
with an explicit first run 60 s after startup. There is **no systemd timer
and no CLI entry point** for any of this — the only unit is
`/etc/systemd/system/sysadmin.service`, which runs the whole FastAPI app, and
the only console script in `pyproject.toml` is `sysadmin-tray`.

| Capability | Module and function | Trigger | Maturity | Output | Needs monitoring? |
|---|---|---|---|---|---|
| Project discovery (marker-based, depth-limited) | `agents/project_organiser.discover_projects` | internal — `ProjectOrganiserAgent._execute`, and `agents/service_discovery.py:136` | working | `list[Path]` | No |
| Explicit-path injection from `projects.yaml` | `ProjectOrganiserAgent._execute` (lines 92-99) | internal — project scan | working | appends to the discovered list | No |
| Status inference (`archive/` → archived) | `ProjectOrganiserAgent._infer_status` | internal — project scan | working | `"active"` / `"archived"` | No |
| Status resolution from `projects.yaml` | `config.ProjectsConfig.status_for` | internal — project scan | working | declared status or `None` | No |
| Health scoring | `ProjectOrganiserAgent._analyse_project` | internal — project scan; `POST /api/projects/scan`; `POST /api/sysadmin/scan-all` | working | `ProjectSnapshot` row | No |
| Git inspection (last commit, branches, stale branches, remote presence) | `utils/git.py` — `get_repo`, `get_last_commit_date`, `get_branches`, `get_stale_branches`, `has_remote` | internal — health scoring | working | dicts / datetimes / bool | No |
| TODO/FIXME counting | `ProjectOrganiserAgent._count_todos` (subprocess `grep`) | internal — health scoring | working | `{pattern: count}` | No |
| Repo size estimation | `utils/git.get_repo_size_mb` | internal — health scoring | working | int MB | No |
| TODO penalty capping | `ProjectOrganiserAgent._todo_penalty` | internal — health scoring | working | int, plus `todo_penalty_capped` finding | No |
| Roadmap document scan | `services/roadmap.scan_roadmap` | internal — health scoring | working | findings dict under `findings["roadmap"]` | No |
| Next-action extraction | `services/roadmap.next_action_from_handoff`, `first_unchecked_task` | internal — `scan_roadmap` | working | string or `None` | No |
| Template-placeholder rejection | `services/roadmap.is_placeholder` | internal — next-action extraction | working | bool | No |
| Handoff dating (authored date, mtime fallback) | `services/roadmap.handoff_date` | internal — `scan_roadmap` | working | `date` or `None` | No |
| Snag counting (open sections only) | `services/roadmap.count_open_snags` | internal — `scan_roadmap` | working | int | No |
| Task counting (measurable / not measurable) | `services/roadmap.count_unchecked`, `count_checked` | internal — `scan_roadmap` | working | int or `None` | No |
| Stalled-project flag | `services/recommendations.STALLED_HANDOFF_DAYS` applied in `_roadmap_recommendations`, `routers/projects.get_project_board:460`, `services/briefing._build_next_actions_section:287` | internal — three independent call sites | working | bool / a `risk` recommendation / a briefing note | No |
| Housekeeping recommendations | `services/recommendations.recommendations_for` | internal — `/actions`, `/board`, `/{name}/recommendations`, project review | working | `list[RecommendationInfo]` | No |
| Recoverable-score projection | `services/recommendations.potential_score` | internal — `/{name}/recommendations` | working | int | No |
| Alert on health floor breach | `ProjectOrganiserAgent._execute:122-133` + `agents/base.raise_alert` | internal — project scan | working | `alerts` row + `alert.raised` event | No |
| Per-project alert threshold resolution | `config.ProjectsConfig.alert_threshold_for` / `has_explicit_alert_threshold`, `ProjectOrganiserAgent._effective_threshold` | internal — project scan | working | int | No |
| Portfolio health list | `routers/projects.get_projects_overview` | `GET /api/projects/overview` | working | `ProjectOverviewResponse` | No |
| Per-project detail + score history | `routers/projects.get_project_detail` | `GET /api/projects/{name}` | working | untyped dict (parsed as `ProjectDetailResponse`) | No |
| Per-project TODO detail | `routers/projects.get_project_todos` | `GET /api/projects/{name}/todos` | working | untyped dict | No |
| Per-project branch detail | `routers/projects.get_project_branches` | `GET /api/projects/{name}/branches` | working | untyped dict | No |
| Per-project ranked advice | `routers/projects.get_project_recommendations` | `GET /api/projects/{name}/recommendations` | working | `ProjectRecommendationsResponse` | No |
| Portfolio ranked advice | `routers/projects.get_portfolio_actions` | `GET /api/projects/actions` | working | `PortfolioActionsResponse` | No |
| Estate board | `routers/projects.get_project_board` | `GET /api/projects/board` | working | `ProjectBoardResponse` | No |
| "Stale projects" list | `routers/projects.get_stale_projects` | `GET /api/projects/stale` | **partial** — the `days` query parameter is accepted and never referenced; the handler filters on `health_score < grade_bands.needs_attention_min` instead | untyped dict | No |
| Markdown portfolio report | `routers/projects.get_projects_report` | `GET /api/projects/report` | working | `{"report": str}` | No |
| Managed-projects view (project ⋈ live service health) | `routers/projects.get_managed_projects` | `GET /api/projects/managed` | working | `ManagedProjectsResponse` | **Yes** — reads `service_health` rows written by the SysAdmin agent |
| Manual rescan | `routers/projects.trigger_scan` | `POST /api/projects/scan` (auth) | working | `{"status": "scan_triggered"}` | No |
| Weekly LLM portfolio review | `services/project_review.generate_review` / `run_weekly_review` | APScheduler cron `weekly_project_review`, Mon 05:30; `POST /api/projects/review/generate` (auth) | working — 4 rows persisted | `ProjectReview` row + `info` alert | No (LLM optional) |
| Deterministic review digest (LLM-down fallback) | `services/project_review.build_fallback_narrative` | internal — `generate_review` when `LLMClient.generate` returns `None` | working (test-covered) | str | No |
| Deterministic "what moved" section | `services/project_review.build_movers_section` | internal — `generate_review` | working | str | No |
| Latest stored review | `routers/projects.get_project_review` | `GET /api/projects/review` | working | `ProjectReviewResponse` | No |
| Branch prune planning (dry run) | `services/branch_actions.plan_branch_cleanup` | `POST /api/projects/{name}/branches/prune` (auth, default) | working — 72 tests; **no evidence of a live invocation** | `BranchCleanupResponse` | No |
| Branch prune execution | `services/branch_actions.execute_branch_cleanup` | same endpoint with `confirm: true` | working — test-covered; **no evidence of a live invocation** | `BranchCleanupResponse` | No |
| Repo path resolution + root confinement | `services/branch_actions.resolve_project_repo` | internal — prune endpoint | working | `Path` | No |
| Default-branch detection | `utils/git.detect_default_branch` | internal — branch actions | working | str or `None` | No |
| Worktree-branch enumeration | `utils/git.worktree_branches` | internal — branch actions | working | `set[str]` | No |
| Merge-state and upstream checks | `utils/git.is_merged_into`, `upstream_state` | internal — branch actions | working | bool / tuple | No |
| Briefing "Project Health" table | `services/briefing._build_project_section` | internal — daily briefing 06:00; `GET /api/sysadmin/briefing/preview` | working | briefing section dict | No |
| Briefing "Pick This Up" section | `services/briefing._build_next_actions_section` | same | working | briefing section dict | No |
| Briefing weekly-review section | `services/briefing._build_review_section` | same | working | briefing section dict | No |
| Project block in the one-call digest | `routers/summary.py:108-153` | `GET /api/summary` | working | dict inside `SummaryResponse` | No |
| Project alert auto-resolution | — | — | **declared-only** | — | — |

On the last row: `agents/base.resolve_alerts` exists and is called by
`sysadmin_agent.py:268`, `service_discovery.py:175` and `:192`. The project
organiser never calls it. See §9.

`Needs monitoring?` is almost uniformly **No**. Only `GET /api/projects/managed`
requires anything from the monitoring side to produce a correct answer: it
joins each `projects.yaml` entry's derived service names against the latest
`service_health` row per service. Without those rows every service reports
`status: "unknown"` and `all_services_healthy` is `False` — the endpoint still
answers, but its whole added value over `/overview` is gone.

---

## 2. Scoring and advice logic

### 2.1 Every input to the health score

All in `ProjectOrganiserAgent._analyse_project`
(`project_organiser.py:170-312` as at this date; [moved to estate-manager 2026-08-13](adr/0005-project-state-leaves.md)).
Score starts at `100` and is clamped with `score = max(0, min(100, score))`.

| Input | Condition | Contribution | Quoted from code | Waived by status? |
|---|---|---|---|---|
| Stale branches | `get_stale_branches(repo, agent_config.stale_branch_days)` non-empty (default 30 days; the checked-out branch is exempt) | `score -= 5 * min(stale_branch_count, 5)` → max −25 | `if status != "archived": score -= 5 * min(stale_branch_count, 5)` | archived |
| Commit staleness (severe) | `days_since > 60` | −15 | `if days_since > 60: if status == "active": score -= 15` | dormant **and** archived |
| Commit staleness (mild) | `30 < days_since <= 60` | −10 | `elif days_since > 30: if status == "active": score -= 10` | dormant **and** archived |
| Missing README | `not (project_path / "README.md").exists()` | −10 | `if not has_readme: score -= 10` | never |
| Missing CLAUDE.md | `not (project_path / "CLAUDE.md").exists()` | −10 | `if not has_claude_md: score -= 10` | never |
| TODO/FIXME markers | `agent_config.track_todos` and total > 0 | `5 * (total // 10)`, capped at `max_todo_penalty` (30) | `raw = self.TODO_PENALTY_PER_BLOCK * (total_todos // self.TODO_BLOCK_SIZE)` | never |
| Missing `.env` | `.env.example` exists and `.env` does not | −10 | `if env_example and not env_file: score -= 10` | never |
| Stale git lock | `.git/index.lock` exists | −5 | `if (project_path / ".git" / "index.lock").exists(): score -= 5` | never |
| Stale `node_modules` | mtime older than 90 days | −5 | `if nm_days > 90: score -= 5` | never |
| No git remote | `not has_remote(repo)` | **0** — recorded only | `findings["no_remote"] = True` | n/a |
| Roadmap state | always | **0** — recorded only | `findings["roadmap"] = scan_roadmap(project_path)` | n/a |
| Last commit subject | best effort | **0** — recorded only | `findings["last_commit_subject"] = str(repo.head.commit.summary)[:200]` | n/a |

The maximum deduction an active project can accumulate is 110, so a genuinely
bad project floors at 0 and stops discriminating. The `max_todo_penalty` cap
was introduced for exactly that reason (`config.py:235-238`), and when it bites
the raw figure is preserved in `findings["todo_penalty_capped"]`.

Two things the score does **not** read, despite the module docstring
listing them: nothing about roadmap documents or missing documentation beyond
the two filename checks, and — see §7 — nothing about dependencies.

The 90-day `node_modules` threshold, the 60/30-day commit thresholds and the
30-day `STALLED_HANDOFF_DAYS` are **hardcoded constants**, not config. Only
`stale_branch_days`, `max_todo_penalty`, `todo_patterns`, `track_todos`,
`alert_threshold`, `grade_bands`, `discovery_depth` and `projects_root` are
configurable.

### 2.2 How status affects scoring

The brief's statement of the claim was: *dormant waives commit-staleness
penalties and roadmap advice while scoring everything else, and archived
additionally stops scoring git hygiene and suppresses alerts unless an explicit
threshold is set.*

**Confirmed, with two corrections.**

- **dormant** — confirmed exactly. Commit staleness costs nothing (both
  branches guard on `status == "active"`), and `_roadmap_recommendations`
  returns `[]` for anything that is not active. Everything else — README,
  CLAUDE.md, `.env`, git lock, `node_modules`, TODOs, **and stale branches** —
  is still scored. Note that a dormant project is still eligible to alert
  against the global threshold of 40: nothing suppresses it.

- **archived, "stops scoring git hygiene"** — *correct in substance, too broad
  in wording*. The only thing archived waives is the **stale-branch
  deduction** (`if status != "archived"`). The `.git/index.lock` deduction —
  also git hygiene — still applies to an archived project. `no_remote` is
  still recorded, but it never cost points for anyone.

- **archived, "suppresses alerts unless an explicit threshold is set"** —
  confirmed, and **stronger than stated**. `_effective_threshold` returns `0`
  for an archived project with no explicit `alert_threshold`, and
  `_analyse_project` clamps the score to `max(0, ...)`. The alert condition is
  `snapshot.health_score < threshold`, i.e. `score < 0`, which is
  arithmetically unreachable. An archived project cannot alert; it is not
  merely unlikely to.

- The `status` value is also copied into `findings["status"]` and is the
  **only** channel by which the recommendation layer, the board and the
  briefing learn it. They re-read it from the stored snapshot, never from
  config — so a status change in `projects.yaml` does not take effect
  anywhere until the next scan rewrites the snapshot.

### 2.3 The `alert_threshold` mechanism

**Global default** — `agents.project_organiser.alert_threshold`, declared in
`config.py:230` as `40` and set to `40` in `config.yaml:244`.

**Per-project override** — `alert_threshold: int | None` on `ManagedProject`
in `projects.yaml`. No entry in the live `projects.yaml` currently sets one;
the file documents the mechanism in a comment and gives `some-archive` /
`alert_threshold: 0` as a worked example only.

**Matching order** — `ProjectsConfig._setting_for`
(`config.py:454-495` as at this date; `config.py` is now [`sysadmin/core/config.py`](../sysadmin/core/config.py) but no longer holds `ProjectsConfig`, which [moved to estate-manager 2026-08-13](adr/0005-project-state-leaves.md)) tries three keys,
because the scanner names a project after its directory while `projects.yaml`
names it freely:

1. resolved filesystem path equality (`Path(...).expanduser().resolve()`) —
   returns immediately on a hit;
2. `project.name == name`;
3. `Path(project.path).name == name`.

Entries where the field is `None` are skipped entirely, so 2 and 3 collect
candidates across the whole list and `by_name` beats `by_basename`. The same
function serves `status_for` and `has_explicit_alert_threshold`.

**Resolution** — `_effective_threshold`
(`project_organiser.py:145-159` as at this date; [moved to estate-manager 2026-08-13](adr/0005-project-state-leaves.md)):

```
if projects_config.has_explicit_alert_threshold(name, path):
    return projects_config.alert_threshold_for(name, path, agent_config.alert_threshold)
return 0 if status == "archived" else agent_config.alert_threshold
```

An explicit value wins outright, including over the archived suppression.

**What firing an alert actually does** — `BaseAgent.raise_alert`
(`base.py:148-188` as at this date; now [`sysadmin/core/agent.py`](../sysadmin/core/agent.py), `raise_alert`):

1. inserts an `alerts` row (`agent='project_organiser'`, `severity='warning'`,
   title `Project {name} health critical`, message `Health score: {n}/100
   (alert threshold {t})`, `details` = the whole findings JSONB);
2. `session.flush()`;
3. logs `alert_raised` at WARNING;
4. queues an `alert.raised` event, published to the event bus on successful
   agent completion and fanned out over SSE (`GET /api/sysadmin/events`);
5. increments `alerts_raised` on the `agent_runs` row.

It does **not** call the notifier directly. Desktop/PA notification is a
separate path driven by the tray polling `GET /api/sysadmin/alerts` and by
`services/notifier.py`. And it does not deduplicate or resolve — see §9.

### 2.4 What "roadmap advice" produces

It is a **static rule set over parsed markdown**, not generated text, not a
template and not a model call. `services/recommendations._roadmap_recommendations`
(`recommendations.py:181-240` as at this date; [moved to estate-manager 2026-08-13](adr/0005-project-state-leaves.md))
returns at most three hand-written `RecommendationInfo` objects, all with
`points=0`:

| Trigger | kind | severity | title |
|---|---|---|---|
| `handoff_age_days > 30` | `roadmap` | `risk` | `Stalled {age} days — resume or park it` |
| `"handoff" in missing_docs` | `roadmap` | default | `No session handoff` |
| `open_snags > 0` | `roadmap` | default | `{n} open snag(s)` |

The whole block returns `[]` when `status != "active"`.

**Where the output goes:** nowhere persistent. Recommendations are computed on
every request from the stored snapshot by `GET /api/projects/actions`,
`GET /api/projects/board` (only `recs[0].title`, as `top_action`) and
`GET /api/projects/{name}/recommendations`. The only place recommendation
output is **stored** is indirectly: `project_review.gather_review_data` puts
each project's top three into `data["projects"][i]["top_recommendations"]`,
and that dict is persisted verbatim as `project_reviews.stats` (JSONB).

The separate, genuinely LLM-generated artefact is the **weekly portfolio
review** (§2.6), which is not roadmap advice and does not overlap with it.

### 2.5 The stalled-project flag

**What computes it:** three independent call sites, all applying the same
comparison to the same stored value. There is no single owning function.

- `services/recommendations._roadmap_recommendations:203` — emits the `risk`
  recommendation.
- `routers/projects.get_project_board:459-460` — sets the board's `stalled`
  boolean and `stalled_count`.
- `services/briefing._build_next_actions_section:287` — adds the note
  `stalled {age} days — resume or park`.

**Against which timestamp:** `findings["roadmap"]["handoff_age_days"]`,
computed once at scan time by `services/roadmap.scan_roadmap:274-283` as
`max(0, (today - written).days)`, where `written` is:

1. the first ISO date (`\d{4}-\d{2}-\d{2}`) appearing in the handoff's **first
   markdown heading** (`handoff_date`), else
2. the handoff file's **mtime**, else
3. `None`, in which case `handoff_age_days` stays `None` and nothing is
   stalled.

The authored date is preferred deliberately: a fresh clone rewrites every
mtime on disk and would reset the whole estate to "written this morning"
(`roadmap.py:220-226`). Note the consequence — the age is a property of the
**handoff document**, not of the repository. A project with no handoff at all
is never stalled, however long it has been abandoned. That project instead
gets the `No session handoff` recommendation, and the board falls back to
`last_commit_subject` for its next action.

**Threshold:** `STALLED_HANDOFF_DAYS = 30`, defined once in
`services/recommendations.py:178` and imported by the other two call sites.
`briefing.py:231` carries a comment reminding a maintainer to keep it in step.
Not configurable.

### 2.6 The weekly review (for completeness)

`services/project_review.py`. Gathers latest snapshot per project plus a
week-on-week delta against the **oldest snapshot inside the window** (not a
fixed offset), builds a prompt, calls `LLMClient`, prepends a deterministic
`build_movers_section`, and stores a `ProjectReview` row plus an `info` alert.
Falls back to `build_fallback_narrative` — a deterministic digest — when the
LLM returns `None`, with `llm_used=False`.

One divergence worth recording, because `CLAUDE.md` documents the opposite
rule for the sibling disk review. `CLAUDE.md` states, of `build_review_prompt`
in the **disk** review, that the model must be given *no numbers* — "do not
merely instruct it not to use them" — verified live on 2026-08-06 after
dria-agent-a-3b restated figures it had been told not to restate, and guarded
by a test asserting no digit reaches the model. The **project** review's
`build_review_prompt` (`project_review.py:147-168` as at this date; [moved to estate-manager 2026-08-13](adr/0005-project-state-leaves.md))
does the other thing: it passes the totals dict, every project's score, every
delta and every recommendation's point value into the prompt, and relies on
`REVIEW_INSTRUCTIONS` telling the model "do NOT list, restate or summarise
scores or deltas". `tests/test_project_review.py` contains no digit-free
assertion. Both mitigations are deliberate and documented in their own
comments; they are simply not the same mitigation, and the project one is the
approach the disk one was changed away from.

---

## 3. Repository inspection primitives

The reusable core: everything below reads disk or git and interprets nothing
about health, advice or status.

### 3.1 Git — `sysadmin/utils/git.py` (235 lines, GitPython)

| Function | Underlying git operation | Returns |
|---|---|---|
| `get_repo(path)` | `Repo(path)` | `Repo` or `None`; `InvalidGitRepositoryError` / `NoSuchPathError` are silent, anything else logs |
| `get_last_commit_date(repo)` | max `committed_datetime` over `repo.branches`, falling back to `repo.head.commit` | `datetime` or `None` |
| `get_branches(repo)` | iterate `repo.branches` | `[{name, last_commit, is_active}]` |
| `get_stale_branches(repo, days)` | same, filtered by tip age; skips the checked-out branch unless HEAD is detached | `[{name, last_commit, days_stale}]` |
| `detect_default_branch(repo)` | `git symbolic-ref refs/remotes/<remote>/HEAD` → `git config --get init.defaultBranch` → `("main","master","trunk","default")` → sole local branch | `str` or `None` (never assumes `main`) |
| `worktree_branches(repo)` | `git worktree list --porcelain`, parsing `branch refs/heads/…` | `set[str]` |
| `is_merged_into(repo, branch, target)` | `repo.is_ancestor` (`git merge-base --is-ancestor`) | `bool`; any error → `False` |
| `upstream_state(repo, branch)` | `branch.tracking_branch()` + `git rev-list --left-right --count <up>...<br>` | `(upstream_name \| None, commits_ahead \| None)` — `None` ahead means unreadable |
| `has_remote(repo)` | `len(repo.remotes) > 0` | `bool` |

`repo.head.commit.summary` is read directly in `_analyse_project:230` rather
than via a helper.

### 3.2 Filesystem walking and prune rules

Three separate exclusion lists exist, with three different memberships. None
imports another.

| Consumer | Constant | Members |
|---|---|---|
| `get_repo_size_mb` (`os.walk`, `dirs[:] = …` in-place prune, sums `stat().st_size`, `// 1024**2`) | `utils/git._SKIP_DIRS` | `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `dist`, `build`, `.next`, `.nuxt`, `coverage`, `.tox`, `.mypy_cache`, `.pytest_cache`, `site-packages`, `.eggs`, `vendor`, `bower_components` |
| `_count_todos` (`grep --exclude-dir`) | `ProjectOrganiserAgent._EXCLUDE_DIRS` | the same 17 **plus** `egg-info` |
| `discover_projects` | — | skips any entry whose name starts with `.`, and never descends into a directory that is itself a project |

`discover_projects` (`project_organiser.py:37-70` as at this date; [moved to estate-manager 2026-08-13](adr/0005-project-state-leaves.md)):
a directory containing any of `PROJECT_MARKERS = {".git", "pyproject.toml",
"package.json", "Cargo.toml", "go.mod"}` **is** a project and is never
descended into; a directory without markers is treated as a *category* and
scanned one level deeper, bounded by `max(max_depth, 1)` (config default 2).
`PermissionError` logs `permission_denied_scanning_projects` and returns.

### 3.3 File existence checks

Bare `Path.exists()` calls in `_analyse_project`: `README.md`, `CLAUDE.md`,
`.env.example`, `.env`, `.git/index.lock`, `node_modules` (plus `stat().st_mtime`
on the last).

### 3.4 Content analysis

**TODO counting** — `subprocess.run(["grep", "-rn", …])`, one invocation per
pattern in `todo_patterns` (`TODO`, `FIXME`, `HACK`, `XXX`), 30 s timeout,
`--include` restricted to `*.py *.js *.ts *.tsx *.vue *.md *.yaml *.yml`, and
`-m 1000`. Counted by splitting stdout on newlines.

Two properties of this worth recording, neither of which matches the
docstring's "Capped at 1000 matches":

- `-m` is grep's **per-file** match limit, not a global one. A project with
  400 files can return far more than 1000 lines.
- `--include=*.md` means the project's own roadmap and snag documents are
  scanned. A `snag_list.md` mentioning `FIXME`, or this audit file, counts
  towards the project's TODO penalty. The patterns are plain strings with no
  word boundary, so `TODOS` and `XXXX` also match.

**Roadmap parsing** — `services/roadmap.py`, pure text, no git and no disk
beyond `is_file()` / `read_text(encoding="utf-8", errors="replace")` /
`stat()`. Candidate paths, in preference order:

```
HANDOFF_PATHS = ("docs/sessions/handoff.md", "docs/roadmap/handoff.md")
TASKS_PATHS   = ("docs/roadmap/tasks.md", "TASKS.md", "docs/TASKS.md")
SNAGS_PATHS   = ("docs/roadmap/snag_list.md", "docs/roadmap/snags.md")
IDEAS_PATHS   = ("docs/roadmap/ideas.md",)
STATUS_PATHS  = ("docs/roadmap/STATUS.md", "STATUS.md")
```

Markdown is split into `(heading, body)` pairs by `_sections`; unchecked items
match `^\s*[-*]\s+\[ \]\s+(.*)$`; snags match `^\s*[-*]\s+.*\bSNAG-[A-Z]+-\d+`
and are counted **only under headings containing "open" or "outstanding"**.
`OSError` on any document is treated as absence.

### 3.5 What this layer does not read

No language detection, no file-type breakdown, no per-directory size ranking,
no dependency or lock-file parsing, no network access to any git remote. The
inspection layer's total external dependency is `gitpython` plus the `grep`
binary.

---

## 4. State and persistence

### 4.1 Tables holding project data

Two of the fourteen tables in the `sysadmin` schema.

**`sysadmin.project_snapshots`** — `alembic/versions/001_initial_schema.py:101-124`,
model `sysadmin/models/project_snapshot.py`.

| Column | Type | Note |
|---|---|---|
| `id` | uuid PK | `gen_random_uuid()` |
| `project_name` | varchar(200) NOT NULL | the **directory basename**, not the `projects.yaml` name |
| `project_path` | text NOT NULL | |
| `health_score` | integer NOT NULL | 0–100 |
| `last_commit_at` | timestamptz NULL | |
| `branch_count` | integer NULL | |
| `stale_branch_count` | integer NULL | |
| `todo_count` | integer NULL | `todos["TODO"]` only |
| `fixme_count` | integer NULL | `todos["FIXME"]` only |
| `has_readme` | boolean NULL | |
| `has_claude_md` | boolean NULL | |
| `total_size_mb` | integer NULL | |
| `findings` | jsonb, default `'{}'` | `status`, `stale_branches`, `stale`/`aging`, `no_remote`, `last_commit_subject`, `roadmap` (the whole `scan_roadmap` dict), `missing_readme`, `missing_claude_md`, `todos`, `todo_penalty_capped`, `missing_env`, `stale_git_lock`, `stale_node_modules` |
| `scanned_at` | timestamptz NOT NULL | `NOW()` |

Index: `idx_project_snapshots_name_time (project_name, scanned_at DESC)`.

Note that `todo_count` and `fixme_count` cover two of the four configured
patterns, while the **penalty** is computed from `sum(todos.values())` across
all four. `HACK` and `XXX` markers therefore cost score but appear in no
column — only inside `findings["todos"]`.

**`sysadmin.project_reviews`** — `alembic/versions/004_add_project_reviews.py`,
model `sysadmin/models/project_review.py`.

| Column | Type | Note |
|---|---|---|
| `id` | uuid PK | |
| `generated_at` | timestamptz NOT NULL | `NOW()` |
| `period_days` | integer NOT NULL | default 7 |
| `narrative` | text NOT NULL | LLM prose, or the deterministic digest |
| `llm_used` | boolean | default `FALSE` |
| `model_used` | varchar(100) NULL | `config.llm.model` when `llm_used` |
| `stats` | jsonb, default `'{}'` | the full `gather_review_data` output |

Index: `idx_project_reviews_generated (generated_at DESC)`.

**Shared with monitoring:** `sysadmin.alerts` carries project rows
(`agent='project_organiser'`) alongside every other agent's, governed by the
`chk_alert_agent` CHECK constraint. `sysadmin.agent_runs` likewise records
project scans alongside every other agent's runs. Neither is a project table,
but project data lives in both.

### 4.2 Project data persisted outside the database

**Nothing.** No cache file, no snapshot file, no scratch directory. The only
project-related file the code writes is the `alerts`-driven notification path,
which goes over HTTP, and the log stream. Confirmed by the absence of any
`open(..., "w")`, `write_text` or `mkdir` in the project modules.

`projects.yaml` is read-only to this codebase — hand-maintained, never
rewritten. (`agents/service_discovery.py` *generates* config.yaml fragments as
suggested text in an API response; it writes no file either.)

### 4.3 Retention

Driven by `sysadmin/services/retention.py`, a daily 03:00 job reading the
`retention_config` table.

| Table | Retention row | Rule |
|---|---|---|
| `project_snapshots` | 90 days, seeded in `001_initial_schema.py:238` | `DELETE … WHERE scanned_at < cutoff AND id NOT IN (SELECT DISTINCT ON (project_name) id … ORDER BY project_name, scanned_at DESC)` — **the newest row per project name is kept forever** |
| `project_reviews` | **none** | not in `retention_config`, and not in `TABLE_TIMESTAMP_MAP` — **never purged** |
| `alerts` (incl. project alerts) | 180 days | `DELETE … WHERE created_at < cutoff AND resolved = TRUE` — unresolved alerts are never purged |
| `agent_runs` | 30 days | plain age delete |

Live confirmation of the keep-latest rule and its consequence:
`PA-worktrees` — a directory deleted from disk during the `~/projects`
reorganisation — still has a `project_snapshots` row, `max(scanned_at) =
2026-08-04`, and it is the only project name whose latest row is more than two
days old. It is retained indefinitely by design.

Also live: 1,664 project alerts, none resolved, so none are eligible for the
180-day purge. `Project PersonalAssistant health critical` alone accounts for
326 rows.

### 4.4 Derived vs sole copy

**Derived and fully recomputable** (one scan reproduces them from disk and git):

- every column of the current `project_snapshots` row for any project that
  still exists on disk;
- everything the recommendation layer, the board, `/actions`, `/stale`,
  `/report`, the briefing sections and the `/api/summary` project block
  return — all are pure functions of the latest snapshot plus config;
- `project_reviews.stats`.

**Not recomputable:**

- **Snapshot history.** The score trend that `GET /api/projects/{name}` and
  the review's week-on-week delta depend on cannot be regenerated — git can
  tell you when a commit landed but not when a README was absent.
- **`project_reviews.narrative`.** An LLM output at a point in time against a
  model that may change. `llm_used=False` rows are the exception: those are
  deterministic given `stats`.
- **The snapshot of a project that no longer exists on disk** (e.g.
  `PA-worktrees`) — that row is the only record it was ever scanned.
- **`projects.yaml`'s `status` and `alert_threshold` declarations.** These are
  recorded human intent, stated nowhere else in the system. They are copied
  *into* each snapshot's `findings["status"]`, but the source of truth is the
  hand-written file, and its comments — which carry the reasoning behind each
  declaration — exist nowhere else at all.

### 4.5 How board rows are produced

**Computed on request, from stored snapshots.** There is no board table and
nothing writes a board row.

`routers/projects.get_project_board` (`routers/projects.py:369-509` as at this date; [moved to estate-manager 2026-08-13](adr/0005-project-state-leaves.md)):

1. `_latest_snapshot_query()` — newest row per `project_name`, self-join on
   `MAX(scanned_at)`. **No freshness predicate.**
2. **Freshness filter** (lines 411-417) — compute `newest = max(scanned_at)`
   across the result, then keep only rows with `scanned_at >= newest - 1 hour`.
3. Drop non-`active` statuses unless `include_inactive=true`.
4. Per row: read `findings["roadmap"]` for `next_action` / `next_action_source`;
   if absent, fall back to `findings["last_commit_subject"]` with
   `source="git"`; compute `days_since_commit`; compute `stalled`; call
   `recommendations_for` and take `recs[0].title` as `top_action`.
5. Sort by `activity` (default, least-idle first) or `neglect`.

**On the known stale row.** The comment at lines 400-410 records it directly:
`PA-worktrees` "was removed during the `~/projects` reorganisation and still
occupied a board row two days later, with a health score and a next action."
The cause is §4.3 — retention keeps the newest row per project name forever,
and the query has no freshness test. The fix is the step-2 filter, applied at
**read time in this endpoint only**.

Consequences, verified in code:

- The stale row is still in the table. Confirmed live.
- The filter is **not shared**. `GET /api/projects/overview`, `/stale`,
  `/report`, `/actions`, `GET /api/summary`, `_build_project_section` and
  `_build_next_actions_section` all use the same
  no-freshness-test latest-per-name pattern (four of them open-coding it
  rather than calling `_latest_snapshot_query`). A deleted project still
  appears in every one of those. The board is the only surface that filters.
- `project_review.gather_review_data` also does not filter, so a deleted
  project is still scored in the weekly review and still contributes to
  `average_active_score`.
- The one-hour slack is a heuristic: it assumes a scan stamps every project
  within a few seconds and that the scan interval (6 h) is much larger than
  the window.

---

## 5. HTTP surface

58 routes are registered. Tagging below is by what the endpoint's data *is*,
not by which router file holds it.

### 5.1 Project management

| Method | Route | Response shape | Consumed by |
|---|---|---|---|
| GET | `/api/projects/overview` | `ProjectOverviewResponse` (`projects[]`, `count`) | **Tray** — `client.fetch_project_overview`, projects tab "All" view |
| GET | `/api/projects/{name}` | untyped dict; tray parses as `ProjectDetailResponse` (`current` + `history[]`) | **Tray** — `client.fetch_project_detail`, drives the score trend chart |
| GET | `/api/projects/managed` | `ManagedProjectsResponse` | **Tray** — `client.fetch_managed_projects`, default projects-tab view |
| GET | `/api/projects/board` | `ProjectBoardResponse` (`projects[]`, `count`, `stalled_count`, `generated_at`) | **External** — specified for Alfred's projects page (`docs/guides/alfred-projects-page.md`, `alfred-briefing-integration.md`). Not in the tray client |
| GET | `/api/projects/actions` | `PortfolioActionsResponse` (`actions[]`, `total_available`, `dropped_by_kind`) | **External** — listed as pullable for Alfred. Not in the tray client |
| GET | `/api/projects/{name}/recommendations` | `ProjectRecommendationsResponse` | **Nothing.** `ProjectRecommendationsResponse` is re-exported by `sysadmin_tray/models.py:58` but the tray client never fetches it |
| GET | `/api/projects/review` | `ProjectReviewResponse` | **External** — listed for Alfred; also surfaced inside the briefing. `ProjectReviewResponse` is re-exported by the tray, unfetched |
| POST | `/api/projects/review/generate` | `ProjectReviewResponse` | **Nothing** automated — manual/auth. The scheduler calls `run_weekly_review()` in-process, not this route |
| GET | `/api/projects/{name}/todos` | untyped dict | **Nothing.** Referenced only as advice text in `recommendations.py:167` |
| GET | `/api/projects/{name}/branches` | untyped dict | **Nothing** |
| GET | `/api/projects/stale` | untyped dict | **Nothing** |
| GET | `/api/projects/report` | `{"report": "<markdown>"}` | **Nothing** |
| POST | `/api/projects/scan` (auth) | `{"status": "scan_triggered"}` | **Nothing** automated |
| POST | `/api/projects/{name}/branches/prune` (auth) | `BranchCleanupResponse` | **Nothing** — no evidence of a live call |

Five of the fourteen are consumed by something; six have no known consumer at
all. Four (`/stale`, `/report`, `/{name}/todos`, `/{name}/branches`) have no
`response_model` and appear in no contract registry.

### 5.2 Shared — project data inside a monitoring-shaped response

| Method | Route | Project content | Consumed by |
|---|---|---|---|
| GET | `/api/summary` | `projects: {count, items[]}` — name, score, scanned_at | External (documented one-call digest) |
| GET | `/api/sysadmin/briefing/preview` | sections `Project Health`, `Pick This Up`, `Weekly Project Review` | **External** — Alfred pulls this today |
| GET | `/api/sysadmin/alerts` | project alerts among all others | **Tray** |
| GET | `/api/sysadmin/events` (SSE) | `alert.raised` events from project scans | **Tray** |
| GET | `/api/sysadmin/self` | `project_organiser` agent liveness | **Tray** |
| POST | `/api/sysadmin/scan-all` (auth) | triggers the project scan among four others | Manual |

### 5.3 Monitoring — no project content

`/health`; `/api/sysadmin/status`, `/status/{service}`, `/resources`,
`/resources/history`, `/dnd`, `/ports`, `/services/{name}/details`,
`/services/{name}/{action}`, `/alerts/{id}/ack`; `/api/logs/*` (6);
`/api/files/*` (15); `/api/units/*` (2); `/api/services/reliability`.

`/api/units/*` deserves a note: the service-discovery sweep it exposes is
*about* projects — it walks the same `discover_projects` tree to decide
whether a systemd unit belongs to a known project — but what it reports is
unit monitoring coverage, so it is tagged monitoring here.

---

## 6. Coupling

No Phase 0 report exists, so this is written in full.

### 6.1 Project code → monitoring code

| Call site | What it needs | Hard or soft |
|---|---|---|
| `routers/projects.get_managed_projects:190-210` | `models.service_health.ServiceHealth` — latest row per service name, to attach live status to each managed project | **Hard.** Without it the endpoint's distinguishing content is `"unknown"` for every service |
| `agents/project_organiser` (class) | `agents/base.BaseAgent` — the `run()` → `_execute()` template, `agent_runs` recording, `raise_alert`, event queueing | **Hard**, but generic: `BaseAgent` is agent scaffolding, not monitoring logic |
| `ProjectOrganiserAgent._execute` → `raise_alert` | `models.alert.Alert` and the `chk_alert_agent` CHECK constraint, which enumerates agent names in the database | **Hard.** The database rejects an unknown agent string |
| `services/project_review.run_weekly_review` | `models.alert.Alert` — the "review ready" `info` alert | Soft; the review persists regardless |
| `services/project_review.generate_review` | `services/llm_client.LLMClient` and `config.llm` — shared with the disk review and nothing else | Soft by construction — the digest fallback exists precisely for this |
| `routers/projects` | `auth.require_auth`, `database.get_db_session`, `config.get_config` | Hard, generic |

### 6.2 Monitoring code → project code

| Call site | What it takes | Hard or soft |
|---|---|---|
| `config._merge_projects_config:692-701` | Every `projects.yaml` entry's `to_monitored_services()` is appended to `agents.sysadmin.services`, and `to_log_sources()` to `agents.log_aggregator.sources`, deduplicated by name | **Hard, and the deepest coupling in the codebase.** The health checker and log aggregator get part of their target list from the project registry |
| `agents/service_discovery.py:28,136` | `from sysadmin.agents.project_organiser import discover_projects` — a direct import of a project-side function, plus `organiser_config.projects_root` and `organiser_config.discovery_depth` | **Hard.** The comment at `project_organiser.py:44-48` states why: two independent ideas of "what is a project" would drift and produce false orphan reports |
| `routers/files._excluded_roots:564-566` | `config.agents.project_organiser.projects_root` — the file organiser refuses to act on anything inside it | **Hard as a safety rule.** A file action is confined by a project-side config key |
| `routers/summary.py:108-153` | `models.project_snapshot.ProjectSnapshot` | Soft; presentational |
| `services/briefing.py:25,185-299` | `ProjectSnapshot`, `ProjectReview`, `recommendations.STALLED_HANDOFF_DAYS` | Soft; presentational, but three of the briefing's sections vanish without it |
| `services/self_monitor.AGENT_NAMES` | must list `project_organiser` or the agent runs unwatched | Hard, registration-style |
| `services/retention.TABLE_TIMESTAMP_MAP` + the `project_snapshots` branch | knows `project_snapshots` and its `project_name` entity column by name | Hard, registration-style |

### 6.3 Shared configuration keys and their owner

| Key | Owner | Also read by |
|---|---|---|
| `agents.project_organiser.projects_root` | project | `service_discovery` (sweep root), `routers/files` (exclusion root), `branch_actions` (confinement root) |
| `agents.project_organiser.discovery_depth` | project | `service_discovery` |
| `agents.project_organiser.*` (the rest) | project | project only |
| `projects.yaml` → `projects[].name/path` | project | `service_discovery` (matching units to projects), `branch_actions` (`managed_paths`) |
| `projects.yaml` → `projects[].backend/frontend/log` | **monitoring**, living in a project-side file | `agents.sysadmin.services`, `agents.log_aggregator.sources` |
| `projects.yaml` → `projects[].status/alert_threshold` | project | project only |
| `schedules.review_day_of_week/review_hour/review_minute` | project | also constrains `disk_review_hour` — the disk review is staggered after it so only one LLM generation is in flight |
| `llm.*` | shared | project review, disk review |
| `notifications.*`, `dnd.*` | monitoring | project alerts ride this path |

`projects.yaml` is the one file that serves both sides. Its per-project
`status` and `alert_threshold` are pure project-management concerns; its
`backend`/`frontend`/`log` blocks exist solely to feed the health checker and
log aggregator. Both halves are validated by the same `ManagedProject` model
in `sysadmin/config.py`.

### 6.4 Database sessions, connections, migration ordering

- **Sessions.** Two factories in `sysadmin/database.py` (177 lines), used by
  both sides identically: `get_db_session` (FastAPI dependency) and
  `get_scheduler_session` (`NullPool`, for the scheduler's separate event
  loop). No project-specific session handling.
- **Connections.** One engine, one pool, one `search_path` (`sysadmin`), one
  database (`projects`). Async `asyncpg` for the app, sync `psycopg2` for
  Alembic.
- **Migration ordering.** Linear and interleaved: `001` (project_snapshots
  alongside every monitoring table) → `002` (nullability/indexes, touching
  both) → `003` (monitoring) → **`004` (project_reviews)** → `005` (disk
  reviews) → `006` (unit audits) → `007` (monitoring) → `008` (reliability
  scores). Project migrations are not separable by revision range; `001` in
  particular creates project and monitoring tables in one function, and the
  `retention_config` seed at `001:230-244` inserts the `project_snapshots`
  policy in the same statement as everything else.
- **The `chk_alert_agent` CHECK constraint** on `sysadmin.alerts` enumerates
  agent names, so the two sides share a database-level enum of who may write
  an alert.

---

## 7. Implied but unbuilt

| Claim | Where stated | What is actually there |
|---|---|---|
| "Dependency audit — checks for outdated lock files, missing .venv, stale node_modules" | `SYSADMIN-SERVICE-SPEC.md:241` | Only the `node_modules` mtime check. No lock file is read; `.venv` presence is never checked. **declared-only** |
| "Orphan detection — projects with no git remote, **or remotes that 404**" | `SYSADMIN-SERVICE-SPEC.md:245` | `has_remote()` returns a bool from `len(repo.remotes)`. Nothing contacts a remote. **declared-only** (the second half) |
| "Size tracking — total size per project, **largest directories, growth over time**" | `SYSADMIN-SERVICE-SPEC.md:244` | `total_size_mb` only. Growth is *derivable* from snapshot history but nothing computes it; no per-directory breakdown exists. **declared-only** (the second half) |
| "Dev environment check — missing .env files, **broken symlinks, incorrect Python versions**" | `SYSADMIN-SERVICE-SPEC.md:246` | `.env.example`-without-`.env` only. **declared-only** (the second half) |
| "Staleness detection — last commit date, **last file modification**, days since activity" | `SYSADMIN-SERVICE-SPEC.md:239` | Commit dates only. No mtime is consulted for staleness (the only mtime read is `node_modules`, and the handoff's as a date fallback). **declared-only** (the middle) |
| "Branch hygiene — flags **merged**/stale branches" | `SYSADMIN-SERVICE-SPEC.md:240` | The **scanner** flags stale only and never computes merged-ness. Merge state is computed only inside `branch_actions`, on demand, per endpoint call. Not wrong, but the scanner does not do it |
| `GET /api/projects/next` — one project, one action, with a `reason` field | `docs/guides/alfred-briefing-integration.md:213` | Not implemented. The doc says so explicitly ("nothing here is built yet"), so this is **honestly declared** |
| Alfred creating `work_item`s from that endpoint; idle nudges | same, lines 218-222 | Not implemented; likewise honestly declared |
| `/infrastructure/projects` UI page — sortable health table, clickable to a detail view | `SYSADMIN-SERVICE-SPEC.md:764-766` | The PyQt tray projects tab covers roughly this. No web UI exists |
| Health-score alerts clearing when a project recovers | implied by `agents/base.resolve_alerts` existing, by the `resolved` column, and by `retention.py:49-54` special-casing "only purge resolved" alerts | The project organiser **never calls `resolve_alerts`**. See §9 |
| "**dormant** — deliberately resting… everything else is still scored" | `projects.yaml:93-95` | Correct, and worth spelling out because the file does not: a dormant project is still fully eligible to alert against the global threshold of 40 |
| "`status: archived` means git hygiene is no longer scored" | `projects.yaml:173`, `config.py:404`, `project_organiser.py:174-180` | Only the stale-branch deduction is waived. `.git/index.lock` still costs an archived project 5 points |

**Where `projects.yaml` reads as more than is implemented.** The file's
comments are unusually informative and are, on inspection, accurate about what
the code does — but they document a system with more machinery than exists.
Three specific readings a newcomer would get wrong:

1. The header comment describes `alert_threshold` matching in detail as
   though per-project thresholds were in use. **No entry in the live file sets
   one.** Every project currently resolves to the global 40 or to the archived
   suppression.
2. The `venture-assistant` and `sports_analyser` comments explain at length
   which units are monitored where and why. That reasoning is enforced by
   nothing — it is a hand-maintained cross-reference between `projects.yaml`
   and `config.yaml`, and the file itself notes the model only holds "one
   backend + one frontend per project".
3. The `PA-worktrees` parenthetical (lines 202-207) reads as though the stale
   row were resolved. It records that the *entry* was removed and that the
   board *filters* it — both true — but the snapshot row is still in the
   database and still visible from six other endpoints (§4.5).

---

## 8. Cost of standing alone

What the project-management side currently gets from this repository, and
whether it is genuinely shared infrastructure or a thin wrapper.

| Facility | Where | Size | Assessment |
|---|---|---|---|
| **Configuration loading** | `sysadmin/config.py` | 736 lines total; `ProjectOrganiserConfig` + `BranchActionsConfig` + `HealthGradeBands` + the whole `projects.yaml` model tree ≈ 200 lines are project-owned | **Thin wrapper around Pydantic** — `load_config` is 20 lines of `yaml.safe_load` + `model_validate` + a singleton. The models themselves would move wholesale. The genuinely shared part is `_merge_projects_config`, which exists *only* to feed the monitoring side |
| **Logging setup** | `sysadmin/logging_setup.py` | 45 lines | **Thin.** `python-json-logger` formatter plus handlers |
| **Database session handling** | `sysadmin/database.py` | 177 lines | **Genuinely shared**, but generic. Two session factories, `search_path` wiring for asyncpg's `server_settings`, and a `NullPool` scheduler session (a real, hard-won detail — separate event loop in a thread pool). Nothing in it is project-specific or monitoring-specific |
| **Alembic scaffolding** | `alembic/env.py` (138 lines) + 8 migrations | **Shared, and entangled.** The `env.py` `version_table_schema="sysadmin"` and the sync-engine `search_path` listener are reusable in principle. The migration history is not separable: `001` creates project and monitoring tables in one function and seeds `retention_config` for both in one INSERT |
| **Systemd unit pattern** | `/etc/systemd/system/sysadmin.service` | one unit | **Thin**, and documented as a reusable contract in `docs/guides/monitorable-project.md`. There is no project-specific unit and no timer — the project scan is an in-process APScheduler job |
| **Scheduler** | `sysadmin/services/scheduler.py` (156 lines) + `main.py` job registration | **Genuinely shared.** APScheduler `BackgroundScheduler` with an `asyncio.run()` bridge, plus the `agent_first_run_delay_seconds` workaround for `IntervalTrigger` scheduling its first fire at `now + interval` — a bug that had already cost `file_organiser` all its runs |
| **Agent framework** | `sysadmin/agents/base.py` (209 lines) | **Genuinely shared.** Template method `run()` → `_execute()`, automatic `agent_runs` recording, timing, error capture, `raise_alert`, `resolve_alerts`, event queueing |
| **Tray integration** | `sysadmin_tray/` (~20 modules), of which `dashboard/projects_tab.py` is project-specific | **Genuinely shared** — the tray is a whole PyQt6 application: icon state machine, notification calming, DND, SSE-adjacent polling, widgets. It consumes exactly **three** project endpoints (`/managed`, `/overview`, `/{name}`) |
| **Authentication** | `sysadmin/auth.py` | 44 lines | **Thin.** Bearer token compared against config, as a FastAPI dependency |
| **HTTP framework setup** | `sysadmin/main.py` (294 lines), `middleware.py` (49) | **Mixed.** Router inclusion and the app factory are boilerplate; the lifespan wiring (agent construction, scheduler start/stop, `app.state` registration, event-bus fan-out) is real shared machinery |
| **Dependency management** | `pyproject.toml` | 13 runtime deps | **Thin.** The project side needs `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic`, `pyyaml`, `httpx`, `apscheduler`, **`gitpython`**, `psycopg2-binary`, `python-json-logger`. It does **not** need `psutil`, which is imported only by `agents/sysadmin_agent.py` and `services/briefing.py`. `gitpython` is imported only by `utils/git.py` and `services/branch_actions.py` — both project-side |
| **Test fixtures** | `tests/conftest.py` | 174 lines | **Genuinely shared.** The async DB session fixture, the app/test-client fixture and the config-override fixture serve every test file |
| **Contract registry** | `sysadmin/contracts.py` | 1,261 lines, of which the project models (`ProjectOverviewEntry`, `ProjectOverviewResponse`, `ManagedProject*`, `ProjectHistoryPoint`, `ProjectDetailResponse`, `BranchInfo`, `BranchCleanupResponse`, `RecommendationInfo`, `ProjectRecommendationsResponse`, `PortfolioAction*`, `ProjectBoardEntry`, `ProjectBoardResponse`, `ProjectReviewResponse`) are ~15 classes | **Shared file, cleanly divided.** `ManagedProjectInfo` is the only project contract that embeds a monitoring shape (`ManagedServiceInfo`) |
| **Event bus / SSE** | `services/event_bus.py` (122 lines), `services/sse.py` | **Genuinely shared**, and the project side is a trivial consumer — it emits `alert.raised` and nothing else |
| **Notifier** | `services/notifier.py` | **Shared.** Project alerts reach the desktop and Alfred through it, gated by DND and severity, with no project-specific branch |
| **LLM client** | `services/llm_client.py` | **Genuinely shared** with the disk review — including the per-run construction rule (SNAG-AGENT-003: never share a client across scheduler event loops) and the commit-before-inference rule (this host's `idle_in_transaction_session_timeout=1min`) |

---

## 9. Facts for the decision

Findings that bear on whether this is one project or two, stated flat.

**On maturity**

1. The project side is not a prototype. 3,388 snapshot rows over three months,
   91 recorded agent runs, 25 projects scanned per pass every 3–6 h, and 290
   passing tests across eight files (`test_branch_actions.py` alone has 72).
2. Of ~45 distinct capabilities, one is `partial` (`GET /api/projects/stale`),
   one is `declared-only` (project alert resolution), and the rest are
   `working`. Nothing is a stub.
3. `branch_actions.py` — 502 lines with a ten-rule safety model, the most
   dangerous code on the project side — is heavily test-covered and has **no
   evidence of ever having been invoked live**.

**On what depends on what**

4. Only **one** project endpoint needs anything from monitoring:
   `GET /api/projects/managed`, which joins `service_health`. Every other
   project capability is a pure function of disk, git and `project_snapshots`.
5. The reverse dependency is stronger. Monitoring imports *from* the project
   side in three places, one of which is a safety rule: `routers/files`
   refuses to touch anything under
   `config.agents.project_organiser.projects_root`.
6. `agents/service_discovery.py` imports `discover_projects` directly from
   `agents/project_organiser.py`. The comment says why — two independent
   definitions of "what is a project" would drift, and the visible symptom
   would be units falsely reported as orphans.
7. `projects.yaml` is a project-management file whose `backend`/`frontend`/
   `log` blocks exist *only* to populate `agents.sysadmin.services` and
   `agents.log_aggregator.sources`. `_merge_projects_config` is the seam.
8. Dependency split is clean at the edges: `psutil` is imported only by
   `agents/sysadmin_agent.py` and `services/briefing.py`; `gitpython` only by
   `utils/git.py` and `services/branch_actions.py`. The other eleven runtime
   dependencies are needed by both sides.
9. Migration `001` creates project and monitoring tables in a single function
   and seeds their retention policies in a single INSERT. Migrations are not
   separable by revision range.

**Defects found, not fixed**

10. **`GET /api/projects/stale` ignores its own `days` parameter.** It is
    declared as `days: int = Query(default=30, le=365)` and never referenced;
    the handler filters on `health_score < grade_bands.needs_attention_min`.
    A caller asking for "no activity in 365 days" gets projects scoring under
    60. No `response_model`, no contract entry, no known consumer.
11. **Project alerts are never resolved and never deduplicated.** The project
    organiser does not call `BaseAgent.resolve_alerts`, though
    `sysadmin_agent` and `service_discovery` both do. Every 6-hour scan
    re-raises a warning for every project under threshold. Live: 1,664 rows,
    100 % unresolved, 326 for `PersonalAssistant` alone. Retention only purges
    **resolved** alerts, so these never expire.
12. **The board's stale-row fix is applied in one endpoint out of seven.**
    `GET /api/projects/board` filters rows older than `newest_scan − 1h`.
    `/overview`, `/stale`, `/report`, `/actions`, `/api/summary` and both
    briefing sections use the same latest-per-name query with no freshness
    test, and `project_review.gather_review_data` does not filter either — so a
    deleted project still contributes to `average_active_score`.
13. **`todo_count` and `fixme_count` under-report what was scored.** The
    columns record `todos["TODO"]` and `todos["FIXME"]`; the penalty is
    computed from `sum(todos.values())` across all four configured patterns.
    `HACK` and `XXX` markers cost score but appear in no column.
14. **The TODO scan reads `*.md`.** A project's own `snag_list.md`,
    `tasks.md` and this audit file count towards its TODO penalty. The
    patterns have no word boundary, so `TODOS` matches `TODO`.
15. **`-m 1000` is grep's per-file limit, not global**, contradicting
    `_count_todos`'s docstring "Capped at 1000 matches".
16. **`project_reviews` is never purged.** It is absent from both
    `retention_config` and `retention.TABLE_TIMESTAMP_MAP`. Currently 4 rows,
    so harmless, but unbounded.

**Documentation that does not match the code**

17. **Archived "stops scoring git hygiene" is too broad.** Only the
    stale-branch deduction is waived; `.git/index.lock` still costs an
    archived project 5 points. Stated in the `_analyse_project` docstring,
    `projects.yaml:173` and `config.py:404`.
18. **Archived alert suppression is stronger than documented.** The docs say
    "no alert is raised unless an explicit `alert_threshold` says otherwise";
    the implementation sets the threshold to 0 while the score is clamped to
    `max(0, …)`, making the alert condition `score < 0` — unreachable.
19. **The project review feeds the model numbers; the disk review does not.**
    `CLAUDE.md` records that giving figures plus a "do not restate them"
    instruction was *verified to fail* on 2026-08-06, and that
    `build_review_prompt` for the disk review is now figure-free by
    construction with a test asserting no digit reaches the model. The project
    review's `build_review_prompt` passes scores, deltas, totals and point
    values, and relies on the instruction. No digit-free test exists for it.
20. **Five spec capabilities are declared-only** (§7): dependency audit,
    remote-404 detection, per-directory size and growth tracking, broken
    symlink / Python version checks, and last-file-modification staleness.
21. **`projects.yaml` documents a threshold mechanism nobody uses.** Its
    header explains per-project `alert_threshold` matching in detail; no entry
    in the live file sets one.

**Things that surprised me**

22. **There is no CLI and no dedicated systemd unit for any of this.** The
    project scan is an in-process APScheduler interval job inside the FastAPI
    app. Nothing can run a project scan without starting the web service.
23. **Six of fourteen project endpoints have no consumer at all**, and the
    tray — the only first-party UI — consumes three. The two endpoints built
    most recently and most deliberately (`/board`, `/actions`) are consumed by
    an external application, not by anything in this repository.
24. **The tray re-exports `ProjectRecommendationsResponse` and
    `ProjectReviewResponse` but never fetches them.** The contracts are wired;
    the client methods do not exist.
25. **The score is a directory-tidiness metric, and it says so.** Roadmap
    state, the single richest thing the scanner reads, is deliberately worth
    **zero points** — the comment at `project_organiser.py:234-239` explains
    that scoring it "would move every active project's health score at once
    and could trip alert thresholds as a side effect of adding a feature".
    The most sophisticated capability on the project side is excluded from the
    number that capability's own project is judged by.
26. **The status system was invented to fix a signal-to-noise problem, and it
    worked.** `projects.yaml:100-102` records the cause: undeclared projects
    default to active, so "the board showed 18 rows for a five-project
    estate". Nine projects were declared dormant or archived on 2026-08-06.
    The last project health alert in the database is dated **2026-07-24** —
    nothing has breached a threshold since.
27. **`Athenaeum` is deliberately left `active` against its own interest.**
    The comment records the reasoning: 2.9 MB of real source, zero commits, no
    remote — marking it dormant "would waive the advice while the only copy of
    the work still exists nowhere but this disk". That is a piece of
    judgement encoded in a YAML comment and in nothing else.
28. **The one-hour board freshness window is the only place in the system that
    knows a project can stop existing.** Nothing deletes a snapshot for a
    vanished directory; nothing alerts on one; the row is retained forever by
    design.
