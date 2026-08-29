#!/usr/bin/env bash
# Answer one question, quickly and without side effects: can this box put a
# notification on a screen *right now*?
#
# SNAG-SYSD-004, Session 125. Split out of notify-unit-failed.sh, which
# asked it by testing for the session bus socket and got the wrong answer
# for six days.
#
# **The socket is not the question.** `Linger=yes` for gaddi means
# `user@1000.service` starts at boot and creates /run/user/1000/bus with no
# human behind it, so the socket exists on a box nobody has logged into.
# What must exist is a *server owning* `org.freedesktop.Notifications`, and
# on this box nothing owns it until a Plasma session starts.
#
# **Asking the wrong question does not merely mis-answer, it hangs.**
# /usr/share/dbus-1/services/org.kde.plasma.Notifications.service declares
# `Exec=/usr/bin/plasma_waitforname org.freedesktop.Notifications` — so a
# method call to an unowned name is not refused, it *activates a program
# whose whole job is to block until the name appears*. Measured on this box
# against a private bus with no server: notify-send blocks for **60.08 s**
# and then fails with `StartServiceByName ... Timeout was reached`. The
# bus's own `service_start_timeout` is 120 s and the announcer's
# `TimeoutStartSec` is 30, so the call can never resolve there — it is
# always killed first.
#
# **NameHasOwner is answered by the bus daemon itself**, so unlike every
# call to the notification interface it cannot be caught in activation.
# Measured under `env -i` with no XDG_RUNTIME_DIR, which is what a system
# unit with `User=` actually gets: **3.1 ms** against the live bus, **3.8 ms**
# against a bus with nothing listening, and zero `plasma_waitforname`
# processes started by the asking.
#
# **Three verdicts and three exit statuses**, check-migrations.sh's shape
# and for its reason — `ports_checked`'s rule, that not-knowing must never
# be served as knowing. Nothing that could not tell reports that it could:
#
#   0  a server owns the name          — say it out loud
#   1  a bus, and nothing listening    — there is nobody to tell
#   2  no bus, or the question could not be answered
#
# The caller collapses 1 and 2 into "could not speak"; they are kept apart
# here because the operator reading the journal needs to know which, and
# because 1 is the state this box is in at every boot before login while 2
# means something is broken.
set -uo pipefail

# The bound is on the *question*, not on the answer. A wedged bus daemon
# would leave even this call unanswered, and a guard against hanging that
# can itself hang is not a guard. Five seconds is three orders of magnitude
# above the measured 3.8 ms, so it can only be reached by a fault.
readonly ASK_TIMEOUT=5
readonly NOTIFICATION_NAME=org.freedesktop.Notifications

bus_path="${1:-/run/user/1000/bus}"

if [[ ! -S "$bus_path" ]]; then
	echo "no session bus at ${bus_path} — no user manager is running"
	exit 2
fi

# `busctl` rather than `dbus-send` because systemd is already a hard
# dependency of everything calling this, and it honours
# DBUS_SESSION_BUS_ADDRESS — which is what lets a test point it at a bus it
# started itself rather than at the box's own.
owner=$(
	DBUS_SESSION_BUS_ADDRESS="unix:path=${bus_path}" \
		timeout "$ASK_TIMEOUT" \
		busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
		org.freedesktop.DBus NameHasOwner s "$NOTIFICATION_NAME" 2>&1
)
ask_rc=$?

if [[ $ask_rc -ne 0 ]]; then
	echo "could not ask ${bus_path} who owns ${NOTIFICATION_NAME}: ${owner}"
	exit 2
fi

case "$owner" in
"b true")
	echo "a notification server owns ${NOTIFICATION_NAME} on ${bus_path}"
	exit 0
	;;
"b false")
	echo "a session bus at ${bus_path} with nothing owning ${NOTIFICATION_NAME} — nobody is logged in to tell"
	exit 1
	;;
*)
	# An answer in a shape this does not recognise is not a "no". Reading
	# it as one would silence the notification on the day busctl changes
	# its output format, which is a decision taken by nothing.
	echo "unrecognised answer from ${bus_path} about ${NOTIFICATION_NAME}: ${owner}"
	exit 2
	;;
esac
