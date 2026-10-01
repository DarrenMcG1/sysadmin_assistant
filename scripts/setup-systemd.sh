#!/usr/bin/env bash
# Install and enable the sysadmin.service systemd unit
# and the tray's user unit, sysadmin-tray.service.
#
# The tray is launched by the user unit ONLY. Until 2026-10-01 this script
# installed an XDG autostart entry instead, while the box ran a hand-written
# unit that was in no repository (estate message 633d1a86). The tray has no
# single-instance guard and Plasma turns an autostart entry into a unit of its
# own, so installing both starts two trays; any old entry is removed below.
# Must be run as root (or with sudo) for the systemd part.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
UNIT_FILE="$PROJECT_DIR/systemd/sysadmin.service"
DEST="/etc/systemd/system/sysadmin.service"
TRAY_UNIT_FILE="$PROJECT_DIR/systemd/sysadmin-tray.service"
REAL_USER="${SUDO_USER:-$USER}"
USER_UNIT_DIR="/home/$REAL_USER/.config/systemd/user"
OLD_AUTOSTART="/home/$REAL_USER/.config/autostart/sysadmin-tray.desktop"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root. Use: sudo $0"
    exit 1
fi

echo "=== Installing systemd unit ==="
cp "$UNIT_FILE" "$DEST"
echo "Copied $UNIT_FILE → $DEST"

echo "=== Reloading systemd ==="
systemctl daemon-reload

echo "=== Enabling service ==="
systemctl enable sysadmin.service

echo ""
echo "=== Installing tray user unit ==="
install -d -o "$REAL_USER" -g "$REAL_USER" "$USER_UNIT_DIR"
install -m 644 -o "$REAL_USER" -g "$REAL_USER" "$TRAY_UNIT_FILE" "$USER_UNIT_DIR/sysadmin-tray.service"
echo "Copied $TRAY_UNIT_FILE → $USER_UNIT_DIR/"
if [[ -e "$OLD_AUTOSTART" ]]; then
    rm -f "$OLD_AUTOSTART"
    echo "Removed $OLD_AUTOSTART (it would start a second tray)"
fi
systemctl --user --machine="$REAL_USER@" daemon-reload
systemctl --user --machine="$REAL_USER@" enable sysadmin-tray.service

echo ""
echo "=== Done ==="
echo "Start backend:  sudo systemctl start sysadmin.service"
echo "Start tray now: systemctl --user start sysadmin-tray.service   (as $REAL_USER)"
echo "Check with:     systemctl status sysadmin.service"
echo ""
echo "The tray starts with the graphical session (graphical-session.target)."
