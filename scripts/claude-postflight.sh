#!/bin/bash
# scripts/claude-postflight.sh
# Run this before ending a Claude Code session
# Enhanced with documentation enforcement

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Claude Code Session End Checklist                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ISSUES=0
DOC_ISSUES=0

# 1. Check for uncommitted changes
echo -e "\n${BLUE}📝 Checking for uncommitted changes...${NC}"
CHANGES=$(git status --short 2>/dev/null)
if [ -n "$CHANGES" ]; then
    echo -e "  ${YELLOW}⚠️  Uncommitted changes detected:${NC}"
    echo "$CHANGES" | sed 's/^/    /'
    ISSUES=$((ISSUES + 1))
else
    echo -e "  ${GREEN}✓ Working tree clean${NC}"
fi

# 2. Check current branch
echo -e "\n${BLUE}🌿 Current branch:${NC}"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached HEAD")
echo -e "  $CURRENT_BRANCH"
if [[ "$CURRENT_BRANCH" == feature/* ]] || [[ "$CURRENT_BRANCH" == fix/* ]] || [[ "$CURRENT_BRANCH" == local-dev/* ]] || [[ "$CURRENT_BRANCH" == claude/* ]]; then
    echo -e "  ${YELLOW}⚠️  Still on a feature branch - consider merging or documenting progress${NC}"
    ISSUES=$((ISSUES + 1))
fi

# 3. Check for worktrees with changes
echo -e "\n${BLUE}📂 Checking worktrees...${NC}"
WORKTREES=$(git worktree list 2>/dev/null | tail -n +2)
if [ -n "$WORKTREES" ]; then
    echo -e "  Active worktrees found. Check each for uncommitted work."
    echo "$WORKTREES" | sed 's/^/    /'
else
    echo -e "  ${GREEN}✓ No additional worktrees${NC}"
fi

# 4. DOCUMENTATION ENFORCEMENT - Critical check
echo -e "\n${BLUE}${BOLD}📋 DOCUMENTATION ENFORCEMENT CHECK${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Get recent commits to check what was modified
RECENT_CODE_CHANGES=$(git log --oneline --name-only -20 2>/dev/null | grep -E "\.(py|vue|ts|js|tsx|jsx|dart|go|rs)$" | sort -u | wc -l)

# Check if tracking docs were modified in recent commits
STATUS_MODIFIED=$(git log --oneline --name-only -10 2>/dev/null | grep -c "STATUS.md" || true)
TASKS_MODIFIED=$(git log --oneline --name-only -10 2>/dev/null | grep -c "tasks.md" || true)
SNAG_MODIFIED=$(git log --oneline --name-only -10 2>/dev/null | grep -c "snag_list.md" || true)
IDEAS_MODIFIED=$(git log --oneline --name-only -10 2>/dev/null | grep -c "ideas.md" || true)

# Also check uncommitted changes
UNCOMMITTED_STATUS=$(git diff --name-only 2>/dev/null | grep -c "STATUS.md" || true)
UNCOMMITTED_TASKS=$(git diff --name-only 2>/dev/null | grep -c "tasks.md" || true)
UNCOMMITTED_SNAG=$(git diff --name-only 2>/dev/null | grep -c "snag_list.md" || true)
UNCOMMITTED_IDEAS=$(git diff --name-only 2>/dev/null | grep -c "ideas.md" || true)

# Combine committed and uncommitted changes
TOTAL_STATUS=$((STATUS_MODIFIED + UNCOMMITTED_STATUS))
TOTAL_TASKS=$((TASKS_MODIFIED + UNCOMMITTED_TASKS))
TOTAL_SNAG=$((SNAG_MODIFIED + UNCOMMITTED_SNAG))
TOTAL_IDEAS=$((IDEAS_MODIFIED + UNCOMMITTED_IDEAS))

echo -e "\n  ${BOLD}Documentation Status:${NC}"
if [ "$TOTAL_STATUS" -gt 0 ]; then
    echo -e "  ${GREEN}✓ STATUS.md${NC} - updated"
else
    echo -e "  ${YELLOW}? STATUS.md${NC} - not modified (update if features completed)"
    DOC_ISSUES=$((DOC_ISSUES + 1))
fi

if [ "$TOTAL_TASKS" -gt 0 ]; then
    echo -e "  ${GREEN}✓ tasks.md${NC} - updated"
else
    echo -e "  ${YELLOW}? tasks.md${NC} - not modified (update session status)"
    DOC_ISSUES=$((DOC_ISSUES + 1))
fi

if [ "$TOTAL_SNAG" -gt 0 ]; then
    echo -e "  ${GREEN}✓ snag_list.md${NC} - updated"
else
    echo -e "  ${YELLOW}? snag_list.md${NC} - not modified (update if bugs fixed/found)"
fi

if [ "$TOTAL_IDEAS" -gt 0 ]; then
    echo -e "  ${GREEN}✓ ideas.md${NC} - updated"
else
    echo -e "  ${YELLOW}? ideas.md${NC} - not modified (update if ideas implemented)"
fi

# Warn if code changed but docs didn't
if [ "$RECENT_CODE_CHANGES" -gt 5 ] && [ "$DOC_ISSUES" -gt 1 ]; then
    echo -e "\n  ${RED}${BOLD}⚠️  WARNING: Significant code changes detected without doc updates!${NC}"
    echo -e "  ${RED}   $RECENT_CODE_CHANGES code files changed in recent commits${NC}"
    echo -e "  ${RED}   Please update STATUS.md and/or tasks.md before ending session${NC}"
    ISSUES=$((ISSUES + 1))
fi

# 5. Remind about insights
echo -e "\n${BLUE}💡 Insight preservation:${NC}"
TODAY=$(date +%Y-%m-%d)
INSIGHT_FILE="docs/insights/insights-$TODAY.md"
if [ -f "$INSIGHT_FILE" ]; then
    echo -e "  ${GREEN}✓ Today's insight file exists${NC}"
else
    TODAY_INSIGHTS=$(find docs/insights/ -name "insights-$TODAY*.md" 2>/dev/null | wc -l)
    if [ "$TODAY_INSIGHTS" -gt 0 ]; then
        echo -e "  ${GREEN}✓ $TODAY_INSIGHTS insight file(s) created today${NC}"
    else
        echo -e "  ${YELLOW}? No insight files for today${NC}"
        echo -e "  If you learned something valuable, save it to:"
        echo -e "    docs/insights/insights-$TODAY-<topic>.md"
    fi
fi

# 6. Run tests if there are code changes
echo -e "\n${BLUE}🧪 Test status:${NC}"
CODE_CHANGES=$(git diff --name-only HEAD 2>/dev/null | grep -E "\.(py|vue|ts|js|dart|go|rs)$" | wc -l)
STAGED_CODE=$(git diff --cached --name-only 2>/dev/null | grep -E "\.(py|vue|ts|js|dart|go|rs)$" | wc -l)
TOTAL_CODE=$((CODE_CHANGES + STAGED_CODE))

if [ "$TOTAL_CODE" -gt 0 ]; then
    echo -e "  $TOTAL_CODE code file(s) with uncommitted changes"
    echo -e "  ${YELLOW}Consider running your test suite${NC}"
else
    echo -e "  ${GREEN}✓ No uncommitted code changes to test${NC}"
fi

# 7. Run consistency audits (mandatory for 5+ file changes)
echo -e "\n${BLUE}🔍 Consistency audits:${NC}"
if [ "$TOTAL_CODE" -ge 5 ]; then
    echo -e "  ${YELLOW}⚠️  5+ code files changed - consider running audits${NC}"
    echo -e "  ${YELLOW}Run: ./scripts/lint_check.sh${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "  ${GREEN}✓ <5 changes - audits optional${NC}"
fi

# 8. Quick doc sync check
echo -e "\n${BLUE}📊 Quick Documentation Sync:${NC}"
echo -e "  Recent commits vs docs:"
git log --oneline -5 2>/dev/null | sed 's/^/    /'
echo ""

# 8.5. Check for active refactors
echo -e "\n${BLUE}🔄 Checking active refactors...${NC}"
if [ -d "docs/refactors" ]; then
    ACTIVE_REFACTORS=$(find docs/refactors -name "*.md" -exec grep -l "🔴 Planning\|🟡 In Progress" {} \; 2>/dev/null | wc -l)
    if [ "$ACTIVE_REFACTORS" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠️  $ACTIVE_REFACTORS active refactor(s) in progress${NC}"
        for file in $(find docs/refactors -name "*.md" -exec grep -l "🔴 Planning\|🟡 In Progress" {} \; 2>/dev/null); do
            NAME=$(basename "$file" .md | sed 's/refactor-//')
            TODO=$(grep -c "⬜ TODO" "$file" 2>/dev/null || true)
            echo -e "    • $NAME ($TODO files remaining)"
        done
    else
        echo -e "  ${GREEN}✓ No active refactors${NC}"
    fi
else
    echo -e "  ${GREEN}✓ No refactors directory${NC}"
fi

# 9. Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
if [ "$ISSUES" -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}⚠️  $ISSUES issue(s) need attention before ending session${NC}"
    echo -e "\n${BOLD}Recommended actions:${NC}"
    echo -e "  1. ${BOLD}Update docs${NC}: STATUS.md, tasks.md, snag_list.md"
    echo -e "  2. Commit or stash any uncommitted changes"
    echo -e "  3. Save any insights to docs/insights/"
    echo -e "  4. Run tests if code was modified"
    echo -e "\n${YELLOW}Documentation files to check:${NC}"
    echo -e "  - docs/roadmap/STATUS.md   (feature completions)"
    echo -e "  - docs/roadmap/tasks.md    (session progress)"
    echo -e "  - docs/roadmap/snag_list.md (bugs fixed/found)"
    echo -e "  - docs/roadmap/ideas.md    (ideas implemented)"
else
    echo -e "${GREEN}${BOLD}✅ Session end checklist complete - all clear!${NC}"
fi
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Return exit code based on issues (useful for hooks)
if [ "$ISSUES" -gt 2 ]; then
    exit 1
fi
exit 0

