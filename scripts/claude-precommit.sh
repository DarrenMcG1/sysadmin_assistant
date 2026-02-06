#!/bin/bash
# scripts/claude-precommit.sh
# Pre-commit validation for Claude Code development workflow
# Called by .git/hooks/pre-commit
#
# Enforces:
# - Lint check must pass for code file changes
# - Warns (but doesn't block) if docs not updated for <5 files
# - BLOCKS if 5+ code files changed without doc updates
#
# IMPORTANT: These checks exist to maintain code quality. If a check fails,
# FIX THE ISSUE rather than bypassing with --no-verify.

set -e
cd "$(dirname "$0")/.."

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Pre-commit Validation                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e ""
echo -e "${YELLOW}⚠️  If checks fail, fix the issues - don't bypass with --no-verify${NC}"

# Auto-stage generated files if they have changes
AUTO_STAGED=0
if [ -f "audit-report.md" ] && git diff --name-only | grep -q "^audit-report.md$"; then
    git add audit-report.md
    AUTO_STAGED=$((AUTO_STAGED + 1))
fi
if [ -f "docs/roadmap/auto_snag_list.md" ] && git diff --name-only | grep -q "^docs/roadmap/auto_snag_list.md$"; then
    git add docs/roadmap/auto_snag_list.md
    AUTO_STAGED=$((AUTO_STAGED + 1))
fi

# Count staged code files
STAGED_CODE=$(git diff --cached --name-only | grep -E "\.(py|vue|ts|js|tsx|jsx|dart|go|rs)$" | wc -l)
STAGED_DOCS=$(git diff --cached --name-only | grep -E "(STATUS|tasks|snag_list)\.md$" | wc -l)

echo -e "\n${BLUE}📊 Staged files:${NC}"
echo -e "  Code files: $STAGED_CODE"
echo -e "  Doc files:  $STAGED_DOCS"
if [ "$AUTO_STAGED" -gt 0 ]; then
    echo -e "  ${GREEN}Auto-staged: $AUTO_STAGED generated file(s)${NC}"
fi

# Check 1: Lint check (always run if code files staged)
echo -e "\n${BLUE}🧹 Lint check:${NC}"
if [ "$STAGED_CODE" -gt 0 ]; then
    if [ -f "./scripts/lint_check.sh" ]; then
        if ./scripts/lint_check.sh > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Lint check passed${NC}"
        else
            echo -e "  ${RED}✗ Lint check failed${NC}"
            echo -e "  ${BOLD}Required action:${NC} Run './scripts/lint_check.sh' and fix all issues"
            exit 1
        fi
    else
        echo -e "  ${YELLOW}Lint script not found - skipping${NC}"
    fi
else
    echo -e "  ${GREEN}✓ No code files - lint skipped${NC}"
fi

# Check 2: Docs updated (ENFORCED for 5+ code files)
echo -e "\n${BLUE}📝 Documentation check:${NC}"

STAGED_TASKS=$(git diff --cached --name-only | grep -E "tasks\.md$" | wc -l)
STAGED_SNAGS=$(git diff --cached --name-only | grep -E "snag_list\.md$" | wc -l)
STAGED_STATUS=$(git diff --cached --name-only | grep -E "STATUS\.md$" | wc -l)
STAGED_REFACTORS=$(git diff --cached --name-only | grep -E "docs/refactors/" | wc -l)

if [ "$STAGED_CODE" -ge 5 ] && [ "$STAGED_DOCS" -eq 0 ]; then
    echo -e "  ${RED}✗ BLOCKED: 5+ code files changed without documentation${NC}"
    echo -e "  ${RED}  Large changes MUST update tracking docs${NC}"
    echo -e ""
    echo -e "  ${BOLD}Required - update at least one of:${NC}"
    echo -e "    - docs/roadmap/tasks.md    (session progress)"
    echo -e "    - docs/roadmap/snag_list.md (if bugs fixed/found)"
    echo -e "    - docs/roadmap/STATUS.md   (if feature completed)"
    echo -e "    - docs/refactors/*.md      (if refactoring)"
    echo -e ""
    echo -e "  ${YELLOW}⚠️  Documentation is mandatory for large changes${NC}"
    exit 1
elif [ "$STAGED_CODE" -gt 0 ] && [ "$STAGED_DOCS" -eq 0 ]; then
    echo -e "  ${YELLOW}⚠️  WARNING: Code changed but no docs updated${NC}"
    echo -e "  Consider updating:"
    echo -e "    - docs/roadmap/tasks.md (session progress)"
    echo -e "    - docs/roadmap/snag_list.md (if bugs fixed/found)"
else
    if [ "$STAGED_DOCS" -gt 0 ]; then
        echo -e "  ${GREEN}✓ Documentation updated${NC}"
        [ "$STAGED_TASKS" -gt 0 ] && echo -e "    • tasks.md ✓"
        [ "$STAGED_SNAGS" -gt 0 ] && echo -e "    • snag_list.md ✓"
        [ "$STAGED_STATUS" -gt 0 ] && echo -e "    • STATUS.md ✓"
        [ "$STAGED_REFACTORS" -gt 0 ] && echo -e "    • refactor doc ✓"
    else
        echo -e "  ${GREEN}✓ No code changes requiring docs${NC}"
    fi
fi

# Check 3: Active refactor progress check
if [ -d "docs/refactors" ] && [ "$STAGED_CODE" -gt 0 ]; then
    ACTIVE_REFACTORS=$(find docs/refactors -name "*.md" -exec grep -l "🔴 Planning\|🟡 In Progress" {} \; 2>/dev/null | wc -l)
    if [ "$ACTIVE_REFACTORS" -gt 0 ] && [ "$STAGED_REFACTORS" -eq 0 ]; then
        echo -e "\n${BLUE}🔄 Active refactor check:${NC}"
        echo -e "  ${YELLOW}⚠️  $ACTIVE_REFACTORS active refactor(s) - update progress?${NC}"
        for file in $(find docs/refactors -name "*.md" -exec grep -l "🔴 Planning\|🟡 In Progress" {} \; 2>/dev/null); do
            NAME=$(basename "$file" .md | sed 's/refactor-//')
            echo -e "    • $NAME"
        done
        echo -e "  ${BLUE}If these changes are part of a refactor, update the tracking doc${NC}"
    fi
fi

# Summary
echo -e "\n${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Pre-commit checks passed - ready to commit${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"

