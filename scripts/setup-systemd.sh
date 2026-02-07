#!/usr/bin/env bash
# Install and enable the sysadmin.service systemd unit
# and the KDE tray autostart entry.
# Must be run as root (or with sudo) for the systemd part.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
UNIT_FILE="$PROJECT_DIR/systemd/sysadmin.service"
DEST="/etc/systemd/system/sysadmin.service"
DESKTOP_FILE="$PROJECT_DIR/systemd/sysadmin-tray.desktop"
REAL_USER="${SUDO_USER:-$USER}"
AUTOSTART_DIR="/home/$REAL_USER/.config/autostart"

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
echo "=== Installing tray autostart ==="
mkdir -p "$AUTOSTART_DIR"
cp "$DESKTOP_FILE" "$AUTOSTART_DIR/sysadmin-tray.desktop"
chown "$REAL_USER:$REAL_USER" "$AUTOSTART_DIR/sysadmin-tray.desktop"
echo "Copied $DESKTOP_FILE → $AUTOSTART_DIR/"

echo ""
echo "=== Done ==="
echo "Start backend:  sudo systemctl start sysadmin.service"
echo "Start tray now: sysadmin-tray &"
echo "Check with:     systemctl status sysadmin.service"
echo ""
echo "The tray app will autostart on next KDE login."
