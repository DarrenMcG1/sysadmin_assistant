#!/usr/bin/env bash
# Does the block that opens every sitting still hold?
#
# SNAG-ESTATE-008. `docs/roadmap/STATUS.md` opens with the claims a sitting
# reads before it decides anything — what is owed, what was restarted, how
# many routes and tables there are. Nothing had ever checked them, and on
# 2026-08-16 all three ops actions the block carried had already been done,
# two of them by a party that never touched the document.
#
# Three things about this script are deliberate.
#
# **It is one line of shell around a console script.** The comparison needs
# `create_app()`, the Alembic head and a database connection; a shell
# reimplementation of any of those is a second statement of a fact
# `sysadmin/ops_claims.py` exists to state once — `check-migrations.sh`'s
# rule, one file over.
#
# **It never edits a document.** A check that corrects the file it reads
# becomes a second author of the claim, and the next sitting cannot tell a
# measured number from a written one. It reports; the sitting edits.
#
# **It is the one place the venv path is named**, for its two callers —
# `claude-preflight.sh`, which reads the block at the start of a sitting,
# and `claude-postflight.sh`, which is where the numbers get written and so
# is the earliest moment a wrong one can be caught.
#
# Exit status, passed straight through from `sysadmin-check-claims`:
#   0  every claim holds
#   1  at least one claim is false — the document or the box is stale, and
#      the report says which
#   2  at least one claim could not be tested and none is false. Not the
#      same answer as 0: `ports_checked`'s rule

set -uo pipefail
cd "$(dirname "$0")/.."

CHECK=".venv/bin/sysadmin-check-claims"

if [[ ! -x "$CHECK" ]]; then
	# Nothing looked. Exit 2 so a caller that distinguishes the two is not
	# told the block is fine.
	echo "?? no $CHECK — run 'uv sync --all-extras'; claims not checked" >&2
	exit 2
fi

exec "$CHECK" "$@"
