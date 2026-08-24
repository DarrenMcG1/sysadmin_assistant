#!/usr/bin/env bash
# Is the live database at this checkout's Alembic head?
#
# SNAG-DB-005. On 2026-08-23 migration 013 was written, committed and never
# applied; the daemon was restarted to serve a new route, `schema_guard`
# refused (correctly), StartLimitBurst made it terminal, and
# `sysadmin.service` stayed dead for 23 hours. Nothing on this box applied
# migrations and nothing checked either.
#
# Three things about this script are deliberate.
#
# **It is one line of shell around a console script**, not a `psql` query.
# The comparison is alembic's own ScriptDirectory against a
# schema-qualified `alembic_version` — two rules `sysadmin/core/schema_guard.py`
# exists to state once, and a shell reimplementation of either is the
# second implementation of the revision graph that module's rule 1 forbids.
#
# **It never applies anything.** Applying a migration unattended is how a
# bad migration reaches production with nobody watching; the snag entry
# rules it out by name. This reports and exits.
#
# **It is the one place the venv path is named.** All three callers reach
# it through their own directory — `claude-precommit.sh`,
# `claude-postflight.sh` and `notify-unit-failed.sh`, the last of which
# runs as a system unit with no working directory of ours and so passes
# `$(dirname "$0")` explicitly.
#
# Exit status, passed straight through from `sysadmin-check-schema`:
#   0  the database is at the packaged head
#   1  a migration is unapplied (or the database is ahead of the code)
#   2  the comparison could not be made — see rule 5 in schema_guard's
#      docstring for why that is not the same answer as 1

set -uo pipefail
cd "$(dirname "$0")/.."

CHECK=".venv/bin/sysadmin-check-schema"

if [[ ! -x "$CHECK" ]]; then
	# Not a mismatch and not clean: nothing looked. Exit 2 so callers that
	# distinguish the two are not told the schema is fine.
	echo "no $CHECK — run 'uv sync'; schema not checked" >&2
	exit 2
fi

exec "$CHECK" "$@"
