#!/bin/bash
# Run sysadmin-service in development mode with auto-reload.
#
# Usage:
#   ./scripts/run-dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "SysAdmin Service — Development Mode"
echo "=========================================="

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run: ./scripts/install.sh"
    exit 1
fi

echo ""
echo "Starting on http://127.0.0.1:8500"
echo "API Docs:   http://127.0.0.1:8500/docs"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="

exec .venv/bin/uvicorn sysadmin.main:app \
    --host 127.0.0.1 \
    --port 8500 \
    --reload \
    --reload-dir sysadmin
