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
# **The rest of the box is blinded by a mount namespace** (SNAG-TEST-020).
# The `box` mark covers four things besides the database: the Claude
# settings, the journal, `systemctl --user` and the installed unit files.
# An empty tmpfs is laid over each directory that holds them, so a test
# reading one without the mark meets an absence, as on the runner:
#
#   ~/.claude                  settings.json and the hook scripts
#   ~/.config/systemd/user     the user unit files
#   /etc/systemd/system        the system unit files
#   /run/user/<uid>            the user bus and systemd's private socket,
#                              which is all `systemctl --user` connects by
#   /var/log/journal,          the persistent and volatile journal, system
#   /run/log/journal           and user alike
#
# Only those six go, so the venv, estate-lib and uv's cache stay where
# they are and the half costs no clone. The rest of `~/projects` is not
# hidden: the `box` mark does not cover it. `unshare -m` makes the mounts
# private, so nothing outside the run sees them, and they go when it
# exits. A directory that does not exist is skipped.
#
# **uv runs offline.** The namespace has no route to PyPI either, and two
# files bring coverage in through `uv run --with 'coverage[toml]'`, which
# re-reads the package index once uv's cached copy goes stale. Inside a
# fresh cache that passed; outside it, 31 tests failed on a DNS error.
# `UV_OFFLINE` resolves from the cache alone, so the half depends on
# coverage having been fetched once, not on the hour.
#
# Arguments are passed to pytest after `-m "not box"`.
set -euo pipefail

cd "$(dirname "$0")/.."

export UV_OFFLINE=1

exec unshare -rnm sh -c '
    uid=$1 gid=$2 home=$3
    shift 3
    ip link set lo up || exit
    for dir in "$home/.claude" "$home/.config/systemd/user" \
               /etc/systemd/system "/run/user/$uid" \
               /var/log/journal /run/log/journal; do
        [ -d "$dir" ] || continue
        mount -t tmpfs -o mode=0700 none "$dir" || exit
    done
    exec unshare -U --map-user="$uid" --map-group="$gid" "$@"
' sh "$(id -u)" "$(id -g)" "$HOME" .venv/bin/python -m pytest -q -m "not box" "$@"
