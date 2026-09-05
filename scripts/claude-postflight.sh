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

# 3.5. Alembic head applied
#
# SNAG-DB-005. Advisory here and blocking in claude-precommit.sh, and the
# split is deliberate: the pre-commit hook is what makes an unapplied
# migration hard to leave, while this catches the case a commit cannot —
# a migration applied earlier and since rolled back, or a database
# restored from a backup mid-sitting. Session 69's outage began *during*
# the sitting, at a restart, so a session-end check alone would have been
# too late; it is the second line, not the first.
echo -e "\n${BLUE}🗄️  Schema revision:${NC}"
SCHEMA_STATUS=0
SCHEMA_OUT=$(./scripts/check-migrations.sh --quiet 2>&1) || SCHEMA_STATUS=$?
if [ "$SCHEMA_STATUS" -eq 0 ]; then
    echo -e "  ${GREEN}✓ Database is at this checkout's Alembic head${NC}"
elif [ "$SCHEMA_STATUS" -eq 1 ]; then
    echo -e "  ${RED}${BOLD}✗ An Alembic migration is unapplied${NC}"
    echo -e "  ${RED}  $SCHEMA_OUT${NC}"
    echo -e "  ${BOLD}  Run: uv run alembic upgrade head${NC}"
    echo -e "  ${RED}  Leaving it costs the daemon its next restart (SNAG-DB-005)${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "  ${YELLOW}⚠️  Could not check (not the same as 'it is fine')${NC}"
    echo -e "  ${YELLOW}  $SCHEMA_OUT${NC}"
fi

# 3.6. Do the claims the session is about to write still hold?
#
# SNAG-ESTATE-008. Preflight runs the same check at the start of a sitting,
# which is where a stale claim is caught; this is where one is *made*. The
# numbers in STATUS.md's opening block are written at the close, so a wrong
# one caught here is caught before it is committed rather than one sitting
# later — the same split as the schema check above, in the other direction.
#
# A red "serves the code on disk" line at the close is the check working:
# the session changed code and the daemon is still running the old copy, so
# the sitting owes either a `kill -TERM` or a sub-session line saying it is
# owed. Both are honest; saying nothing is not.
echo -e "\n${BLUE}🔎 Ops claims (STATUS.md against the box):${NC}"
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
    echo -e "  ${BOLD}Correct the artefact named, not the check:${NC}"
    echo -e "  ${BOLD}a 'block says' line means STATUS.md is stale;${NC}"
    echo -e "  ${BOLD}a state line means the box is${NC}"
    ISSUES=$((ISSUES + 1))
elif [ "$CLAIMS_STATUS" -ne 0 ]; then
    echo -e "  ${YELLOW}⚠️  Something could not be measured (not the same as 'it holds')${NC}"
fi

# Preflight asks this at the start of a sitting, which is
# where a dead entry is *found*; this is where one is made — a sitting that
# fixed something has just refuted an entry it may not have thought to
# close, and the close is the last moment before the docs are committed.
#
# It never raises ISSUES. A refuted claim is an entry to judge and the
# judgement may legitimately be "leave it open" — Session 83's residue rule
# — so blocking the close on it would make the check an author of the
# document, which is the one thing this family does not do.
echo -e "\n${BLUE}🔎 Snag claims (open entries against the box):${NC}"
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
    echo -e "  ${BOLD}Did this sitting kill one of those? Measure it and say so${NC}"
    echo -e "  ${BOLD}in the entry — a refuted claim is a candidate for closure${NC}"
fi

# 3.8. Did every assert this sitting wrote actually evaluate?
#
# SNAG-TEST-006. A test looping over a live artefact's members is green
# while that population is empty, because an empty `for` completes. Review
# does not catch it and the suite cannot report it, because passing is
# exactly what it does — the founding instance stood eleven days.
#
# Here rather than at the commit, and that is the whole placement
# argument: the measure is coverage over a *green full suite*, which is
# 90 seconds, and `claude-precommit.sh` runs on every commit while this
# runs once at the close. It is also the moment a guard written this
# sitting is newest and least examined.
#
# It raises ISSUES on a finding — unlike the snag claims above, because
# this is not a judgement about an entry but a defect in the sitting's own
# work, and the two remedies (fix it, or declare why it cannot evaluate)
# are both cheap and both belong to whoever wrote the assert.
echo -e "\n${BLUE}🧪 Vacuous guards (asserts that never evaluated):${NC}"
GUARDS_STATUS=0
GUARDS_OUT=$(./scripts/check-vacuous-guards.sh 2>&1) || GUARDS_STATUS=$?
while IFS= read -r line; do
    case "$line" in
        "ok "*) echo -e "  ${GREEN}✓${NC} ${line#ok }" ;;
        "no "*) echo -e "  ${RED}${BOLD}✗ ${line#no }${NC}" ;;
        "?? "*) echo -e "  ${YELLOW}? ${line#?? }${NC}" ;;
        *)      echo -e "  ${BLUE}${line}${NC}" ;;
    esac
done <<< "$GUARDS_OUT"
if [ "$GUARDS_STATUS" -eq 1 ]; then
    echo -e "  ${BOLD}Fix it, or declare it — an assert that asserted nothing${NC}"
    echo -e "  ${BOLD}is a guard the suite cannot tell you it is not holding${NC}"
    ISSUES=$((ISSUES + 1))
elif [ "$GUARDS_STATUS" -ne 0 ]; then
    echo -e "  ${YELLOW}⚠️  The measure did not run (not the same as 'nothing found')${NC}"
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

if [ "$GUARDS_STATUS" -le 1 ]; then
    # The gate above runs the whole suite under coverage and refuses to
    # judge a red one, so a status it could return at all is a green run.
    # Advising a suite run here as well would be this script printing the
    # name of a guard it has just run — the mention rule the retired
    # `vacuous_guard_ungated` check was built around, in reverse.
    echo -e "  ${GREEN}✓ Suite ran green under the vacuous-guard gate above${NC}"
elif [ "$TOTAL_CODE" -gt 0 ]; then
    echo -e "  $TOTAL_CODE code file(s) with uncommitted changes"
    echo -e "  ${YELLOW}The gate above could not run the suite — run it yourself${NC}"
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

