# Handoff — 2026-08-29

## Next action

Take the next open entry on its own terms and measure the cost it states as well as the mechanism it names, since the last four sittings each found the entry's own scoping to be the smaller or the wrong half and this one found the same of its cost bullet and of the instrument written to check it.

## Session 123 is complete — the cost an entry states is a claim like any other

`SNAG-LOG-014` **stays open at P4 and nothing was deleted.** Its remedy
judgement was re-read and stands: two rows are two rows. What moved is
its stated **cost**, which was the smaller half twice, and the key its
own check was grouping on.

**Every surface enumerated before the cost was accepted.**
`build_trend_report`'s docstring says the advice *must* be computed off
the same report the trend serves, so the two surfaces cannot disagree
about whether a signature is new — which makes an error in the grouped
counts reach both **by construction**. The entry names one.

Driven through the real pipeline against the live table in a rolled-back
transaction, stored against true:

```
/api/logs/trends    previous 23->21   total 91->89
                    ratio 2.96->3.24  sources[].previous_warnings 28->26
/api/logs/actions   title: 'sysadmin.service fault up 3.0x — "alert_raised"'
                    true:  '...up 3.2x'      detail: 23 -> 21 last window
not reached         the alert family, the weekly review, the 06:00 briefing,
                    /api/logs/stats, /api/logs/recent, the trend ordering
```

The advice row carries the error in a **title**, which `SNAG-LOG-010`
made that surface's row identity — the same cap-and-count family
reaching the field it was written to protect.

**The duration is wrong in the field the entry offers as the
mitigation.** `previous` is windowed and converges 2026-08-31 as filed.
`total` is `func.count()` with **no window filter**, so it stays 2 high
until retention — on `ingested_at`, not `logged_at` — puts both copies
at **2026-09-16**. Eighteen days, not three.

**The check was keyed on the column the fix rewrote, and this entry is
the best evidence against that.** It grouped on `(source, logged_at,
message)`; these rows were invisible for eleven days precisely because
`SNAG-LOG-008`'s backfill had not yet made the copies agree. The
**verdict** stays narrow — a wide key admits a microsecond coincidence
and would hold `match` open after the pair aged out, which is the
calendar keeping an entry alive rather than closing one. The
**"elsewhere"** limb reaches no verdict and moves to the record's own
identity, because that is the limb whose blindness costs something: a
second occurrence needs a restart, and a restart is when a declaration
changes.

**The entry's own untested question is answered, and it moved the
deciding population to another source.** 0 of **235,230 rows across 9
sources** have two distinct records sharing a `(source, logged_at)`, so
the `message` component does no work today; the tightest genuine gap is
**3 µs at `kernel`**, not the millisecond of `alert_raised` writes the
fix bullet named — 333× wide and the wrong source.

2,872 tests pass (2,869 + 3, none retired), ruff and mypy clean. Four
mutations driven, each red on exactly one intended test — and **one
passed against deliberately broken code** on the first attempt: `>=` for
`>` emits a nonsense "0 of them agree…" clause and no test carried the
equal-count case, which is the live one.

Daemon restarted at **2026-08-29 16:09:37**, **not owed** and measured
rather than argued — `create_app()` does not import `snag_claims`.
Taken because the deploy check compares `.py` mtimes, `ops_claims` rule
4's documented false positive for the third sitting running. `/health`
200, clean journal, all nine ops claims green, **0** unresolved alerts.

**What is still open on this entry**: nothing about the mechanism, which
closed on 2026-08-17 at 20:09:44. The residue ages out on 2026-09-16 and
the check now reports both identities until it does.
