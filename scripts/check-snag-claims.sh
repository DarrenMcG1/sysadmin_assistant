#!/usr/bin/env bash
# Do the open snag entries still describe this box?
#
# `docs/roadmap/snag_list.md` is the second document a
# sitting reads and was the only one nothing checked. Session 82 measured
# all thirty open entries by hand and found five dead on the box — three of
# them P1, and three fixed for between nine and thirteen days. That sweep
# cost a whole sitting and was stale the moment the next fix landed.
#
# Three things about this script are deliberate, and two of them are
# `check-ops-claims.sh`'s for its reasons.
#
# **It is one line of shell around a console script.** The checks need an
# `ast` walk over this package, a database connection and a live sweep of a
# synthetic unit tree; a shell reimplementation of any of those is a second
# statement of a fact `sysadmin/snag_claims.py` exists to state once.
#
# **It never edits a document.** A refuted claim is an entry to *judge* —
# Session 83 spent a sitting on one such judgement — and a check that
# closed entries on its own would be the second author the whole convention
# exists to keep out.
#
# **Exit 1 is not a failure here**, which is where this parts company with
# its sibling. A stale STATUS.md figure is wrong; a refuted snag claim is
# *news*, and the right response is to measure the entry and decide, not to
# correct a sentence. Both callers treat it as advisory.
#
# Exit status, passed straight through from `sysadmin-check-snags`:
#   0  every checked claim still holds
#   1  at least one is refuted — the entry may be dead; go and judge it
#   2  at least one could not be tested, or an open entry carries no check
#      at all. Not the same answer as 0: `ports_checked`'s rule

set -uo pipefail
cd "$(dirname "$0")/.."

CHECK=".venv/bin/sysadmin-check-snags"

if [[ ! -x "$CHECK" ]]; then
	# Nothing looked. Exit 2 so a caller that distinguishes the two is not
	# told the entries are fresh.
	echo "?? no $CHECK — run 'uv sync --all-extras'; snag claims not checked" >&2
	exit 2
fi

exec "$CHECK" "$@"
