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

# Check 2: Alembic head applied (BLOCKS on a mismatch)
#
# SNAG-DB-005. A migration written and never applied took the daemon down
# for 23 hours: `schema_guard` refused to serve, StartLimitBurst made the
# restart loop terminal, and nothing on this box applies migrations. The
# commit is the last scripted moment before the hand-typed restart — there
# is no deploy script between them — so the check lands here.
#
# It blocks whatever is staged, not only a migration file, because the
# question is about the state of the box rather than the content of the
# commit: a database behind the checkout means the daemon is already dead
# or dies at its next restart, and a docs commit does not make that less
# true.
#
# Exit 2 (the comparison could not be made) WARNS rather than blocks. A
# commit refused because PostgreSQL happens to be down teaches the operator
# to reach for --no-verify, which disarms this check for the mismatch it
# exists to catch — and a commit is not what breaks the box, the restart
# is. See rule 5 in sysadmin/core/schema_guard.py.
echo -e "\n${BLUE}🗄️  Schema check:${NC}"
# `|| SCHEMA_STATUS=$?` rather than a bare call: this script runs under
# `set -e`, which would abort here on any non-zero and skip the messages
# below — including the one that decides 2 must not block.
SCHEMA_STATUS=0
SCHEMA_OUT=$(./scripts/check-migrations.sh --quiet 2>&1) || SCHEMA_STATUS=$?
if [ "$SCHEMA_STATUS" -eq 0 ]; then
    echo -e "  ${GREEN}✓ Database is at this checkout's Alembic head${NC}"
elif [ "$SCHEMA_STATUS" -eq 1 ]; then
    echo -e "  ${RED}✗ BLOCKED: an Alembic migration is unapplied${NC}"
    echo -e "  ${RED}  $SCHEMA_OUT${NC}"
    echo -e ""
    echo -e "  ${BOLD}Required action:${NC}"
    echo -e "    uv run alembic upgrade head"
    echo -e "    systemctl reset-failed sysadmin && systemctl start sysadmin"
    echo -e ""
    echo -e "  ${YELLOW}⚠️  This is SNAG-DB-005: the same omission cost 23 hours of${NC}"
    echo -e "  ${YELLOW}   monitoring on 2026-08-23. Do not bypass with --no-verify.${NC}"
    exit 1
else
    echo -e "  ${YELLOW}⚠️  Could not check the schema (not the same as 'it is fine')${NC}"
    echo -e "  ${YELLOW}  $SCHEMA_OUT${NC}"
fi

# Check 3: Docs updated (ENFORCED for 5+ code files)
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

# Check 4: Active refactor progress check
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

