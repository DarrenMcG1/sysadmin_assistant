#!/usr/bin/env bash
# Say out loud that a unit has entered `failed`.
#
# Session 39. Invoked by sysadmin-failed.service via OnFailure= on
# sysadmin.service, with the failed unit's name passed as $1 (systemd's %n).
#
# Three things about this script are deliberate.
#
# **It notifies rather than restarts.** systemd is already trying to
# restart; reaching `failed` means it gave up after StartLimitBurst. A
# handler that restarted again would loop round the limit that exists to
# stop the loop.
#
# **-t 0 (never expires) and -u critical.** The failure this whole session
# exists to fix was a transient toast nobody was in the room to see. An
# expiring notification about a dead monitor is the same miss with extra
# steps.
#
# **It exits non-zero when it cannot speak.** If nobody is logged in there
# is no session bus and notify-send fails. Returning 0 there would record
# "the failure was reported" in the journal when it was not. This handler
# failing is the honest outcome, and it is visible as
# `systemctl status sysadmin-failed`.
#
# **It names the cause when the cause is knowable.** SNAG-DB-005: on
# 2026-08-23 this handler fired correctly and said only
# `result=exit-code, restarts=5`. The fault was an unapplied migration and
# the remedy was one command, both of which `sysadmin/core/schema_guard.py`
# knew and wrote only to the journal. The daemon stayed dead 23 hours. The
# schema check below is asked first and its answer goes into the toast.
#
# Off-box notification is the known gap, recorded in tasks.md rather than
# pretended closed: nothing here survives the machine being off.

set -uo pipefail

unit="${1:-sysadmin.service}"

# `systemctl show` is used rather than `is-failed` because the interesting
# part is *why*: Result distinguishes exit-code from timeout from OOM, and
# NRestarts says whether it thrashed or died once and stopped.
props=$(systemctl show "$unit" \
	--property=Result \
	--property=NRestarts \
	--property=ExecMainStatus \
	--property=ActiveEnterTimestamp 2>/dev/null)

result=$(printf '%s\n' "$props" | sed -n 's/^Result=//p')
restarts=$(printf '%s\n' "$props" | sed -n 's/^NRestarts=//p')
status=$(printf '%s\n' "$props" | sed -n 's/^ExecMainStatus=//p')

# The most common cause this handler has ever had, asked before anything
# is written, so every destination below carries the same answer.
#
# Three outcomes, and only two of them say anything: a mismatch names the
# remedy, an unreachable database says it could not look (which is itself
# a candidate cause of the failure), and a healthy schema adds nothing —
# a critical toast is not the place to rule things out one at a time.
#
# `|| schema_rc=$?` because `set -u -o pipefail` is in effect without
# `-e`; the explicit capture is so a future `-e` cannot silently turn a
# mismatch into a handler that never speaks.
schema_rc=0
schema_out=$("$(dirname "$0")/check-migrations.sh" --quiet 2>&1) || schema_rc=$?
schema_note=""
case "$schema_rc" in
0) ;;
1) schema_note="

CAUSE: ${schema_out#mismatch: }
  uv run alembic upgrade head
  systemctl reset-failed ${unit} && systemctl start ${unit}" ;;
*) schema_note="

The schema revision could not be checked, which may itself be why it died:
  ${schema_out}" ;;
esac

# `systemctl status` and `journalctl -u` are unprivileged here — verified
# as gaddi, exit 0 for both. The `sudo` this line used to carry was wrong
# and is the same defect as the missing remedy: a next step the reader
# cannot take, or can take more easily than they were told.
summary="FAILED: ${unit}"
body="systemd gave up restarting it (result=${result:-unknown}, exit=${status:-?}, restarts=${restarts:-?}).
Monitoring and all agents are DOWN until it is started.
  systemctl status ${unit}
  journalctl -u ${unit} -n 50 --no-pager${schema_note}"

# Journald first, and unconditionally. It is the one destination that does
# not depend on a graphical session existing, so the record survives even
# when the notification below cannot be delivered.
printf '%s | %s\n' "$summary" "${body//$'\n'/ | }" | systemd-cat -t sysadmin-failed -p err

# Then an alert row, so the failure is still visible on
# GET /api/sysadmin/alerts once the service is back — a toast expires and a
# journal entry is not a surface anyone opens unprompted, so without this a
# failure that happened overnight leaves no state behind.
#
# `|| true` is deliberate and load-bearing: the database may itself be why
# the service died, and this script's exit status is reserved for whether it
# could tell a *human*. A failed insert must not become a failed unit that
# then needs its own explanation. The row is filed under agent='sysadmin'
# with the real provenance in details.source — see
# sysadmin/core/unit_failure.py for why, and ADR-0002 for the migration that
# was considered instead.
venv="/home/gaddi/projects/sysadmin_assistant/.venv/bin/sysadmin-record-failure"
if [[ -x "$venv" ]]; then
	"$venv" "$unit" \
		--result "${result:-}" \
		--exit-status "${status:-}" \
		--restarts "${restarts:-}" 2>&1 |
		systemd-cat -t sysadmin-failed -p warning || true
else
	echo "no sysadmin-record-failure at $venv — alert row not written" >&2
fi

# The session bus is not inherited by a system unit, so it is named
# explicitly. Hardcoded uid 1000 (gaddi) — this box has one human, and
# guessing the "current" session from a system unit is how a handler picks
# the wrong bus on the one day it matters.
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus"

if [[ ! -S /run/user/1000/bus ]]; then
	echo "no session bus at /run/user/1000/bus — nobody is logged in to tell" >&2
	exit 1
fi

exec notify-send \
	--app-name=sysadmin \
	--urgency=critical \
	--expire-time=0 \
	--icon=dialog-error \
	"$summary" "$body"
