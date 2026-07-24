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
HANDOFF_FILE="docs/sessions/handoff.md"
if [ -f "$HANDOFF_FILE" ]; then
    HANDOFF_AGE=$(( ($(date +%s) - $(stat -c %Y "$HANDOFF_FILE" 2>/dev/null || stat -f %m "$HANDOFF_FILE")) / 3600 ))
    if [ "$HANDOFF_AGE" -lt 48 ]; then
        echo -e "\n${BOLD}${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BOLD}${YELLOW}║  ⚠️  SESSION HANDOFF FOUND (${HANDOFF_AGE}h old)                        ║${NC}"
        echo -e "${BOLD}${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo -e "${YELLOW}Review previous session context:${NC}"
        sed -n '/## ⚠️ READ THIS FIRST/,/---/p' "$HANDOFF_FILE" 2>/dev/null | head -5 | sed 's/^/  /'
        echo ""
        sed -n '/## In-Progress Tasks/,/## Critical Snags/p' "$HANDOFF_FILE" 2>/dev/null | head -10 | sed 's/^/  /'
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

# 8. Snag list summary — only the "Open Issues" section counts
#    (the old grep counted the whole file, so Fixed Issues inflated the totals)
echo -e "\n${BLUE}🐛 Open snags:${NC}"
SNAG_FILE="docs/roadmap/snag_list.md"
if [ -f "$SNAG_FILE" ]; then
    # Slice out the Open Issues section (up to the next ## heading),
    # then keep only top-level snag bullets like "- [P1] SNAG-XXX: title"
    OPEN_SNAGS=$(awk '/^## Open Issues/{flag=1; next} /^## /{flag=0} flag' "$SNAG_FILE" \
        | grep -E '^- \[P[0-9]\]' || true)
    if [ -z "$OPEN_SNAGS" ]; then
        echo -e "  ${GREEN}None — all clear${NC}"
    else
        SNAG_COUNT=$(echo "$OPEN_SNAGS" | wc -l)
        echo -e "  ${YELLOW}${SNAG_COUNT} open:${NC}"
        echo "$OPEN_SNAGS" | sed 's/^- /  /'
    fi
else
    echo -e "  ${YELLOW}snag_list.md not found${NC}"
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

