#!/usr/bin/env bash
# Install sysadmin-service: create venv, install deps, run migrations.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Creating virtual environment ==="
uv venv

echo "=== Installing dependencies ==="
uv pip install -e ".[dev]"

echo "=== Running database migrations ==="
.venv/bin/alembic upgrade head

echo "=== Verifying tables ==="
psql projects -c "SELECT table_name FROM information_schema.tables WHERE table_schema='sysadmin' ORDER BY table_name;"

echo ""
echo "=== Installation complete ==="
echo "Start the service with:"
echo "  uvicorn sysadmin.main:app --host 127.0.0.1 --port 8500"
