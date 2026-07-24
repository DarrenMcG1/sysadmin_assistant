#!/bin/bash
# Live smoke test against the running sysadmin-service.
#
# Curls the real service (default http://127.0.0.1:8500) and checks:
#   - /health              → 200 with "healthy"
#   - /api/sysadmin/status → 200 with a services array
#   - /api/summary         → 200 JSON
#   - a deliberate 404     → JSON error body with "detail"
#
# Usage: ./scripts/smoke_test.sh [base_url]
# Exit code 0 = all checks passed, 1 = failure (or service not running).

set -u

BASE_URL="${1:-http://127.0.0.1:8500}"
CURL="curl -sS --max-time 5"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

echo -e "${BLUE}=== sysadmin-service smoke test — ${BASE_URL} ===${NC}"

# --- Fail fast if the service isn't running -------------------------------
if ! $CURL -o /dev/null "${BASE_URL}/health" 2>/dev/null; then
    echo -e "${RED}✗ Service is not reachable at ${BASE_URL}${NC}"
    echo "  Start it first, e.g.:"
    echo "    ./scripts/run-dev.sh"
    echo "  or: systemctl --user start sysadmin-service"
    exit 1
fi

check() {
    local name="$1" path="$2" expected_status="$3" expect_grep="$4"

    local body status
    body=$($CURL -w '\n%{http_code}' "${BASE_URL}${path}" 2>&1)
    status=$(echo "$body" | tail -n1)
    body=$(echo "$body" | sed '$d')

    if [ "$status" != "$expected_status" ]; then
        echo -e "${RED}✗ ${name}${NC} — expected HTTP ${expected_status}, got ${status}"
        FAIL=$((FAIL + 1))
        return
    fi

    if [ -n "$expect_grep" ] && ! echo "$body" | grep -q "$expect_grep"; then
        echo -e "${RED}✗ ${name}${NC} — HTTP ${status} but body missing '${expect_grep}'"
        echo "  body: $(echo "$body" | head -c 200)"
        FAIL=$((FAIL + 1))
        return
    fi

    echo -e "${GREEN}✓ ${name}${NC} (HTTP ${status})"
    PASS=$((PASS + 1))
}

check "GET /health"                 "/health"                 200 '"status":"healthy"'
check "GET /api/sysadmin/status"    "/api/sysadmin/status"    200 '"services"'
check "GET /api/summary"            "/api/summary"            200 '{'
check "GET nonexistent → JSON 404"  "/api/definitely-not-real" 404 '"detail"'

echo ""
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}=== PASS — ${PASS}/4 checks OK ===${NC}"
    exit 0
else
    echo -e "${RED}=== FAIL — ${FAIL} of $((PASS + FAIL)) checks failed ===${NC}"
    exit 1
fi
