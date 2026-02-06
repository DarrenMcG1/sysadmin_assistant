#!/usr/bin/env bash
# Install and enable the sysadmin.service systemd unit.
# Must be run as root (or with sudo).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
UNIT_FILE="$PROJECT_DIR/systemd/sysadmin.service"
DEST="/etc/systemd/system/sysadmin.service"

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
echo "=== Done ==="
echo "Start with: sudo systemctl start sysadmin.service"
echo "Check with: systemctl status sysadmin.service"
