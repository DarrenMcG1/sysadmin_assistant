# Adding an agent touches four places, and three of them fail silently

_2026-08-07, from Session 26 (service discovery)._

Adding the fifth agent to this service looked like a one-file change. It
was four, and only one of them was obvious. Written down because the next
agent will hit exactly the same list.

## The four places

| # | Place | What happens if you miss it |
|---|-------|-----------------------------|
| 1 | `sysadmin/main.py` — instantiate, schedule, `app.state`, scan-all | The agent never runs. Obvious immediately. |
| 2 | `sysadmin/config.py` — a config class on `AgentsConfig` | `AttributeError` at startup. Obvious immediately. |
| 3 | **`chk_alert_agent` CHECK constraint on `sysadmin.alerts`** | The scan succeeds, then the transaction is rejected at flush. Needs a migration. |
| 4 | **`self_monitor.AGENT_NAMES` + `agent_schedules`** | Nothing at all. The agent runs, and the service whose job is watching agents never watches it. |

Numbers 3 and 4 are the interesting ones.

## Number 3: the database has an opinion about agent names

`sysadmin.alerts` has carried this since migration 001:

    CHECK (agent IN ('sysadmin', 'project_organiser', 'file_organiser', 'log_aggregator'))

So the first live run of `service_discovery` swept 38 units, classified
them correctly, built the audit row — and was then rejected by Postgres at
`flush()` with a `CheckViolationError`. The work was right; the write was
refused.

**The constraint is worth keeping.** It is the reason an agent-name typo
fails loudly instead of quietly creating alerts that no dashboard query
will ever return. What was missing was not the constraint but any statement
that it existed. Migration 007 widens it, and this now guards the pairing:

```python
def test_the_agent_name_is_accepted_by_the_alerts_constraint():
    assert set(module.AGENTS) == set(AGENT_NAMES)
```

## Number 4: the self-monitor keeps its own register

`self_monitor.py` deliberately duplicates `main.py`'s scheduling — it
rebuilds each agent's interval and `job_id` from config so it can compute a
stall window. Its docstring says so and asks you to keep them in step.

A new agent absent from `AGENT_NAMES` produces **no error anywhere**. It
runs on schedule, writes `agent_runs` rows, and is invisible to
`/api/sysadmin/self`. If it stalls, nothing notices — in the one service on
this box whose entire purpose is noticing that.

`test_self_monitor.py` already asserted `set(schedules) == set(AGENT_NAMES)`,
which catches adding to one and not the other. It cannot catch adding to
neither.

## The generalisable bit

Three of the four registrations are **secondary registries**: a database
constraint, a self-monitoring list, a retention table map. Each exists for
a good reason, each duplicates a fact that lives primarily somewhere else,
and each fails differently — loudly at write time, silently forever, or
only when a purge runs.

The cheap fix is not to remove the duplication. It is to make the
duplication *assertable*: a test that pins the two lists together turns a
silent omission into a red CI run. That is what shipped, plus a table in
`CLAUDE.md` so the next session reads the list before hunting for it.

## Related

- `CLAUDE.md` → Contract Registry → the `/api/units/*` section ends with
  the four-place list.
- `docs/roadmap/tasks.md` → Session 26 → "Four things the plan got wrong".
