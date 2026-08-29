#!/bin/bash
# scripts/claude-preflight.sh
# Run this before starting any Claude Code development session

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Claude Code Preflight Check                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

# 0. CHECK FOR SESSION HANDOFF (context from previous session)
#
# Candidates match sysadmin/projects/roadmap.py HANDOFF_PATHS, newest first
# by mtime. Root HANDOFF.md is the convention; the rest are read so repos
# can migrate one at a time.
#
# The extract below prints the "## Next action" section. It used to print
# ranges anchored on "## ⚠️ READ THIS FIRST" and "## In-Progress Tasks" —
# headings from a template no handoff on this box has ever used, so this
# banner announced a handoff and then displayed nothing at all. Anchor on
# what is actually written, which is the same heading the scanner parses.
HANDOFF_FILE=$(ls -t HANDOFF.md docs/sessions/handoff.md docs/handoff.md \
    docs/roadmap/handoff.md 2>/dev/null | head -1)
if [ -n "$HANDOFF_FILE" ] && [ -f "$HANDOFF_FILE" ]; then
    HANDOFF_AGE=$(( ($(date +%s) - $(stat -c %Y "$HANDOFF_FILE" 2>/dev/null || stat -f %m "$HANDOFF_FILE")) / 3600 ))
    if [ "$HANDOFF_AGE" -lt 48 ]; then
        echo -e "\n${BOLD}${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BOLD}${YELLOW}║  ⚠️  SESSION HANDOFF FOUND (${HANDOFF_AGE}h old)                        ║${NC}"
        echo -e "${BOLD}${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
        head -1 "$HANDOFF_FILE" 2>/dev/null | sed 's/^/  /'
        echo ""
        awk '/^## / { if (seen) exit; if (tolower($0) ~ /next/) { seen=1; print; next } }
             seen { print }' "$HANDOFF_FILE" 2>/dev/null | head -8 | sed 's/^/  /'
        echo -e "\n  ${BLUE}Full handoff: $HANDOFF_FILE${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    fi
fi

# 1. Check for conflicting branches
echo -e "\n${BLUE}📌 Existing feature branches:${NC}"
BRANCHES=$(git branch -a 2>/dev/null | grep -E "(fix|feature|claude|local-dev)/" || true)
if [ -z "$BRANCHES" ]; then
    echo -e "  ${GREEN}None${NC}"
else
    echo "$BRANCHES" | sed 's/^/  /'
    echo -e "  ${YELLOW}⚠️  Check if any overlap with your planned work${NC}"
fi

# 2. Check worktrees
echo -e "\n${BLUE}📂 Active worktrees:${NC}"
WORKTREES=$(git worktree list 2>/dev/null)
WORKTREE_COUNT=$(echo "$WORKTREES" | wc -l)
echo "$WORKTREES" | sed 's/^/  /'
if [ "$WORKTREE_COUNT" -gt 1 ]; then
    echo -e "  ${YELLOW}⚠️  Multiple worktrees active - avoid overlapping work${NC}"
fi

# 3. Check uncommitted changes
echo -e "\n${BLUE}📝 Uncommitted changes:${NC}"
CHANGES=$(git status --short 2>/dev/null)
if [ -z "$CHANGES" ]; then
    echo -e "  ${GREEN}Working tree clean${NC}"
else
    echo "$CHANGES" | sed 's/^/  /'
    echo -e "  ${YELLOW}⚠️  Commit or stash before starting new work${NC}"
fi

# 4. Current branch
echo -e "\n${BLUE}🌿 Current branch:${NC}"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached HEAD")
echo -e "  $CURRENT_BRANCH"

# 5. Recent commits
echo -e "\n${BLUE}📜 Recent commits:${NC}"
git log --oneline -5 2>/dev/null | sed 's/^/  /'

# 6. Show current priorities from STATUS.md
echo -e "\n${BLUE}🎯 Current priorities (from STATUS.md):${NC}"
if [ -f "docs/roadmap/STATUS.md" ]; then
    sed -n '/## Quick Status/,/^## /p' docs/roadmap/STATUS.md | head -30 | sed 's/^/  /'
else
    echo -e "  ${YELLOW}STATUS.md not found${NC}"
fi

# 6.5. The sub-session block, which the global rules say to read first
#
# STATUS.md's opening blockquote is where "what is owed" is written — a
# restart, a migration, an alert row waiting on somebody. This script has
# printed the Quick Status table since it was written and never printed
# that, which is how five sittings re-read a stale one. Bounded at 30
# lines and stopped at the ranked recommendation, which is prose for the
# reader rather than a claim about the box.
echo -e "\n${BLUE}📌 Sub-session block (STATUS.md):${NC}"
SUBSESSION=$(awk '/^> \*\*Next up\*\*/ {exit} /^>/ {print}' docs/roadmap/STATUS.md 2>/dev/null | head -30)
if [ -z "$SUBSESSION" ]; then
    echo -e "  ${YELLOW}No opening blockquote found — not the same as 'nothing owed'${NC}"
else
    echo "$SUBSESSION" | sed 's/^/  /'
fi

# 6.6. ...and the claims in it, re-measured
#
# SNAG-ESTATE-008. Everything above this line is prose being repeated;
# this is the only part of the banner that has looked at the box. Six
# consecutive sittings were spent on claims that had stopped being true —
# an ops action done three days earlier, a restart that needed no sudo, a
# retention boundary asserted three hours before it happened.
#
# Advisory, never blocking, and it must not take the banner down with it:
# `set -e` is on, so the exit status is captured rather than allowed to
# propagate. A check that can end the session it opens would be worse
# than the drift it reports.
echo -e "\n${BLUE}🔎 Ops claims, re-measured:${NC}"
CLAIMS_STATUS=0
CLAIMS_OUT=$(./scripts/check-ops-claims.sh 2>&1) || CLAIMS_STATUS=$?
while IFS= read -r line; do
    case "$line" in
        "ok "*) echo -e "  ${GREEN}✓${NC} ${line#ok }" ;;
        "no "*) echo -e "  ${RED}${BOLD}✗ ${line#no }${NC}" ;;
        "?? "*) echo -e "  ${YELLOW}? ${line#?? }${NC}" ;;
        *)      echo -e "  ${BLUE}${line}${NC}" ;;
    esac
done <<< "$CLAIMS_OUT"
if [ "$CLAIMS_STATUS" -eq 1 ]; then
    echo -e "  ${BOLD}A claim above is false. Fix the artefact it names —${NC}"
    echo -e "  ${BOLD}a 'block says' line means the document is stale;${NC}"
    echo -e "  ${BOLD}a state line means the box is.${NC}"
elif [ "$CLAIMS_STATUS" -ne 0 ]; then
    echo -e "  ${YELLOW}Something could not be measured — not the same as 'it holds'${NC}"
fi

# The same question one document over, and the one the
# ops-claims check cannot ask: `snag_list.md` sets the agenda for what gets
# fixed, and Session 82 measured five of its thirty open entries dead on the
# box — three P1, three of them fixed for between nine and thirteen days.
#
# A red line here is *news*, not a fault: the entry may be closeable, which
# is a judgement rather than a correction. Advisory for that reason as well
# as for its sibling's — `set -e` is on, so the status is captured.
echo -e "\n${BLUE}🔎 Snag claims, re-measured:${NC}"
SNAGS_STATUS=0
SNAGS_OUT=$(./scripts/check-snag-claims.sh 2>&1) || SNAGS_STATUS=$?
while IFS= read -r line; do
    case "$line" in
        "ok "*) echo -e "  ${GREEN}✓${NC} ${line#ok }" ;;
        "no "*) echo -e "  ${RED}${BOLD}✗ ${line#no }${NC}" ;;
        "?? "*) echo -e "  ${YELLOW}? ${line#?? }${NC}" ;;
        *)      echo -e "  ${BLUE}${line}${NC}" ;;
    esac
done <<< "$SNAGS_OUT"
if [ "$SNAGS_STATUS" -eq 1 ]; then
    echo -e "  ${BOLD}An entry above no longer describes this box. Measure it and${NC}"
    echo -e "  ${BOLD}judge it — a refuted claim is a candidate for closure,${NC}"
    echo -e "  ${BOLD}never a closure. Nothing here edits the document.${NC}"
fi

# 7. Check running servers
echo -e "\n${BLUE}🖥️  Running servers:${NC}"
BACKEND=$(pgrep -fa "uvicorn\|run_api" 2>/dev/null || true)

FRONTEND=""


if [ -n "$BACKEND" ]; then
    echo -e "  ${GREEN}Backend: Running${NC}"
else
    echo -e "  ${YELLOW}Backend: Not running${NC}"
fi

if [ -n "$FRONTEND" ]; then
    echo -e "  ${GREEN}Frontend: Running${NC}"
else
    echo -e "  ${YELLOW}Frontend: Not running${NC}"
fi

# 8. Snag list summary — the closure-aware reader, not a grep.
#
# This counted `^- \[P[0-9]\]` under `## Open Issues` until 2026-08-29,
# which is every bullet in the section whatever its title says. That
# printed **76 open** eight lines below the snag-claims section's
# **18 open entries** — one figure stated two ways inside one banner, with
# the wrong half carrying the list, whose first ten rows were titled
# **FIXED**. `ops_claims` rule 2 in the surface that sets the agenda.
#
# `--list-open` is `sysadmin.snag_claims.list_open`, which applies
# `closure_declared` — the rule the count above it already uses. A shell
# approximation of that rule would be a second implementation of it, free
# to drift from the number printed eight lines up, which is the defect
# rather than a cheaper way to have it.
#
# **Exit non-zero prints "could not be counted", never "all clear"**:
# `ports_checked`'s rule. `set -e` is on, so the status is captured.
echo -e "\n${BLUE}🐛 Open snags:${NC}"
OPEN_STATUS=0
OPEN_SNAGS=$(./scripts/check-snag-claims.sh --list-open 2>/dev/null) || OPEN_STATUS=$?
if [ "$OPEN_STATUS" -ne 0 ]; then
    echo -e "  ${YELLOW}could not be counted — the closure-aware reader did not run${NC}"
elif [ -z "$OPEN_SNAGS" ]; then
    echo -e "  ${GREEN}None — all clear${NC}"
else
    SNAG_COUNT=$(echo "$OPEN_SNAGS" | wc -l)
    echo -e "  ${YELLOW}${SNAG_COUNT} open:${NC}"
    echo "$OPEN_SNAGS" | sed 's/^/  /'
fi

# 9. Testing reminder
echo -e "\n${BLUE}🧪 Testing reminder:${NC}"
echo -e "  When adding features, include tests."

# Final: Scope declaration prompt
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}📋 BEFORE YOU START - Be explicit about:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e ""
echo -e "  ${BOLD}1. What${NC} - Describe the specific outcome you want"
echo -e "     ❌ \"Help me with the backend\""
echo -e "     ✅ \"Add a /users endpoint that returns paginated results\""
echo -e ""
echo -e "  ${BOLD}2. Where${NC} - List the files/areas that will change"
echo -e "     ❌ \"Update the backend\""
echo -e "     ✅ \"Modify src/routes/users.py, add types in src/schemas/user.py\""
echo -e ""
echo -e "  ${BOLD}3. Type${NC} - Is this a:"
echo -e "     • ${GREEN}Quick fix${NC} - Single bug, <5 files"
echo -e "     • ${YELLOW}New feature${NC} - Adding something new"
echo -e "     • ${RED}Refactor${NC} - Changing existing patterns"
echo -e ""
echo -e "  ${BOLD}4. Patterns${NC} - Ask Claude to check existing patterns first"
echo -e "     \"Before implementing, show me how other modules implement X\""
echo -e ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Preflight complete.${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

