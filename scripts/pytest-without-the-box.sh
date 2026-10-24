#!/usr/bin/env bash
# Run the suite's non-`box` half the way GitHub's runner meets it: with no
# database to reach.
#
# The pre-push gate runs on the box, so a test that reads the live
# database without `@pytest.mark.box` passes here and fails only in CI,
# which runs `-m "not box"` on a runner with no PostgreSQL. That shipped
# twice (SNAG-TEST-015, SNAG-TEST-019). This half is the same selection
# CI makes, run where the database cannot answer.
#
# **The blind is a network namespace, not a patch.** `unshare -rn` gives
# the run a network stack of its own with only `lo`, so every localhost
# service (PostgreSQL on 5432, the estate on 8400, the broker) answers
# "connection refused", as on the runner. Patching the connection in
# Python would guard the patch's idea of every route to the database
# (asyncpg, psycopg2, `psql`, estate-manager's own interpreter) rather
# than the absence itself.
#
# **Two namespaces, nested.** The outer one maps us to root, which is
# what lets it raise `lo`; with `lo` down, `Errno 99` fails tests the
# runner passes. The inner one maps back to our own uid, so file
# permissions read as they do outside.
#
# **What it does not blind:** `~/.claude/settings.json`, the journal,
# `systemctl --user` and the installed unit files are still the box's.
# A test reading those without the mark still passes here and fails in
# CI. Recorded as SNAG-TEST-020.
#
# Arguments are passed to pytest after `-m "not box"`.
set -euo pipefail

cd "$(dirname "$0")/.."

exec unshare -rn sh -c '
    uid=$1 gid=$2
    shift 2
    ip link set lo up &&
    exec unshare -U --map-user="$uid" --map-group="$gid" "$@"
' sh "$(id -u)" "$(id -g)" .venv/bin/python -m pytest -q -m "not box" "$@"
