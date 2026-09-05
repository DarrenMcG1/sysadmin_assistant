#!/usr/bin/env bash
# Did every assert under tests/ actually evaluate?
#
# SNAG-TEST-006. A test looping over a live artefact's members is green
# while that population is empty, because an empty `for` completes. Review
# does not catch it — the code reads correctly — and the suite cannot
# report it, because passing is exactly what it does. The founding
# instance shipped 2026-08-24 and ran its body for the first time on
# 2026-09-04, eleven days later.
#
# Five things about this script are deliberate.
#
# **The suite is run here and the judging is not.** The measure is
# coverage over a *green* full suite; the join of that report to an AST
# walk of `tests/` is `sysadmin/vacuous_guards.py`, which never imports
# coverage — `check-migrations.sh`'s rule, one file over. That split is
# what lets the analysis be tested on a box where coverage is not
# installed, which is every box here.
#
# **coverage is not a dependency and does not become one.** It arrives
# through an ephemeral `uv run --with` overlay, which leaves `.venv`
# untouched — verified at 122 packages and an unchanged lock either side
# of a run, the distinction the `uv-run-active-reshapes-this-venv` memory
# is about. `--all-extras` rather than `--extra dev`, because this
# repository's documented sync is `uv sync --all-extras` and a narrower
# spelling is one uv release away from pruning the tray extra out of the
# environment the operator is standing in.
#
# **A red suite is exit 2, never exit 1.** An assert not reached because
# an earlier one blew up is not a guard that asserted nothing, so a
# failing suite means the measure did not run — and reporting it as a
# finding would make this gate loudest exactly when pytest is already
# saying something truer.
#
# **The report is thrown away.** It is written under a mktemp directory
# and removed on exit: a coverage.json left in the tree is a file the
# *next* run could be pointed at, and the analysis joins line numbers to
# line numbers, so a stale report read against an edited tree is
# confidently wrong rather than absent. `--report` exists for a caller
# that has just produced one and knows it is fresh; the module refuses
# the join anyway if any test file is newer than the report.
#
# **It is the one place the venv path is named**, for its caller —
# `claude-postflight.sh`, the close of a sitting, which is where a guard
# written this sitting is newest and least examined.
#
# Exit status, passed straight through from `sysadmin-check-guards`:
#   0  every evaluable assert under tests/ ran on this suite run
#   1  at least one asserted nothing and declares no reason why
#   2  the measure did not run — a red suite, no uv, no console script, or
#      a tree the report does not describe. Not the same answer as 0:
#      `ports_checked`'s rule
#
# **The run is made with `--branch`, and that is the whole of the second
# half.** `assert all(f(x) for x in live)` is True over an empty `live`
# with its line executing, so line coverage cannot see a guard that ran
# over nothing — but CPython compiles the comprehension to a real loop and
# coverage records its back-edge as an arc. Measured on this suite: 68.3 s
# plain, 90.2 s under `coverage run`, 88.3 s under `coverage run --branch`.
# There is no second pass, which is what `SNAG-TEST-009` was filed to
# weigh and what measuring it dissolved.
#
# **The arcs come from the SQLite data file, not from the JSON.**
# `coverage json` reports `num_branches: 0` for a file whose only loops
# are comprehensions — coverage's static analysis does not model one as a
# branch point — and lists only statement lines, so the element
# expression never appears there either. Both files therefore go to the
# judge: `--report` for the line half, `--arcs` for the loop half.
#
# Whatever the status, the report ends with how many comprehension sites
# turned, and names the handful whose written shape leaves a turning loop
# and an empty one indistinguishable. That is a standing declaration
# rather than a fourth exit status — a gate that is always yellow is
# `SNAG-LOG-002`'s binary LOW confidence, read by nobody for fourteen days.

set -uo pipefail
cd "$(dirname "$0")/.."

CHECK=".venv/bin/sysadmin-check-guards"

if [[ ! -x "$CHECK" ]]; then
	echo "?? no $CHECK — run 'uv sync --all-extras'; guards not checked" >&2
	exit 2
fi

# A caller that already holds a fresh report skips the 90-second run.
if [[ "${1:-}" == "--report" ]]; then
	exec "$CHECK" "$@"
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "?? no uv on PATH; the suite was not run under coverage" >&2
	exit 2
fi

WORK=$(mktemp -d) || exit 2
trap 'rm -rf "$WORK"' EXIT

if ! uv run --with 'coverage[toml]' --all-extras \
	coverage run --branch --data-file="$WORK/.coverage" --source=tests \
	-m pytest -q >"$WORK/suite.log" 2>&1; then
	echo "?? the suite is not green, so a never-evaluated assert cannot be told" >&2
	echo "?? from one an earlier failure stopped short of:" >&2
	tail -n 5 "$WORK/suite.log" >&2
	exit 2
fi

if ! uv run --with 'coverage[toml]' \
	coverage json --data-file="$WORK/.coverage" -o "$WORK/coverage.json" >/dev/null 2>&1; then
	echo "?? the suite ran but coverage would not report on it" >&2
	exit 2
fi

"$CHECK" --report "$WORK/coverage.json" --arcs "$WORK/.coverage"
exit $?
