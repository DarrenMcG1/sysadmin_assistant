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

summary="FAILED: ${unit}"
body="systemd gave up restarting it (result=${result:-unknown}, exit=${status:-?}, restarts=${restarts:-?}).
Monitoring and all agents are DOWN until it is started.
  sudo systemctl status ${unit}
  journalctl -u ${unit} -n 50 --no-pager"

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
