#!/bin/bash
# scripts/claude-worktrees.sh
# Manage parallel Claude Code sessions using git worktrees

set -e

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
PROJECT_NAME=$(basename "$PROJECT_ROOT")
WORKTREE_BASE=$(dirname "$PROJECT_ROOT")
SESSION_PREFIX="sysadmin-assistant-session"

show_help() {
    echo -e "${BOLD}Claude Worktree Manager${NC}"
    echo ""
    echo "Manage parallel Claude Code sessions using git worktrees."
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  $0 setup [count]     Create worktrees for parallel sessions (default: 3)"
    echo "  $0 list              List all active worktrees and their status"
    echo "  $0 status            Show detailed status of all sessions"
    echo "  $0 teardown          Remove all session worktrees and merge branches"
    echo "  $0 claim <session> <scope>  Mark a session as working on specific scope"
    echo "  $0 help              Show this help message"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 setup 3           # Create 3 parallel session worktrees"
    echo "  $0 claim A backend   # Session A claims backend/ scope"
    echo "  $0 teardown          # Clean up all worktrees"
    echo ""
    echo -e "${BOLD}Recommended Scopes:${NC}"
    echo "  backend    - Backend source code"
    echo "  frontend   - Frontend components and pages"
    echo "  tests      - Test files and scripts"
    echo "  docs       - Documentation and markdown files"
}

create_session_scope() {
    local worktree_path=$1
    local session_id=$2
    local scope=${3:-"unassigned"}

    cat > "$worktree_path/SESSION_SCOPE.md" << EOF
# Session $session_id Scope

**Created:** $(date -Iseconds)
**Branch:** session-$session_id-$(date +%Y%m%d)
**Status:** 🟡 Ready

## Assigned Scope

\`$scope\`

## Scope Guidelines

When working in this session, you should:
- ✅ Only modify files within your assigned scope
- ✅ Run preflight at session start: \`./scripts/claude-preflight.sh\`
- ✅ Commit frequently with clear messages
- ❌ Do NOT modify files outside your scope
- ❌ Do NOT modify shared config files without coordination

## Session Log

- $(date -Iseconds): Session created
EOF
}

setup_worktrees() {
    local count=${1:-3}
    local base_branch=$(git branch --show-current)

    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║         Setting Up Parallel Claude Sessions                  ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        echo -e "${YELLOW}⚠️  You have uncommitted changes. Commit or stash first.${NC}"
        git status --short
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    echo -e "${BLUE}Creating $count session worktrees...${NC}"
    echo ""

    # Session labels (A, B, C, D, etc.)
    local labels=(A B C D E F G H)
    local scopes=("backend" "frontend" "tests" "docs" "misc" "misc" "misc" "misc")

    for i in $(seq 0 $((count - 1))); do
        local label=${labels[$i]}
        local scope=${scopes[$i]}
        local branch_name="session-$label-$(date +%Y%m%d)"
        local worktree_path="$WORKTREE_BASE/$SESSION_PREFIX-$label"

        echo -e "${CYAN}━━━ Session $label ━━━${NC}"

        if [ -d "$worktree_path" ]; then
            echo -e "  ${YELLOW}⚠️  Worktree already exists at $worktree_path${NC}"
            continue
        fi

        # Create branch from current HEAD
        git branch "$branch_name" 2>/dev/null || true

        # Create worktree
        git worktree add "$worktree_path" "$branch_name"

        # Create session scope file
        create_session_scope "$worktree_path" "$label" "$scope"

        echo -e "  ${GREEN}✓${NC} Created: $worktree_path"
        echo -e "  ${GREEN}✓${NC} Branch: $branch_name"
        echo -e "  ${GREEN}✓${NC} Default scope: $scope"
        echo ""
    done

    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo ""
    echo -e "${BOLD}Next steps:${NC}"
    echo ""
    for i in $(seq 0 $((count - 1))); do
        local label=${labels[$i]}
        local scope=${scopes[$i]}
        echo -e "  ${CYAN}Terminal $((i + 1)):${NC} cd $WORKTREE_BASE/$SESSION_PREFIX-$label && claude"
        echo -e "           Scope: $scope"
        echo ""
    done

    echo -e "${BOLD}Quick commands:${NC}"
    echo "  List sessions:    $0 list"
    echo "  Session status:   $0 status"
    echo "  Clean up:         $0 teardown"
}

list_worktrees() {
    echo -e "${BOLD}Active Claude Session Worktrees${NC}"
    echo ""

    local found=false

    while IFS= read -r line; do
        local path=$(echo "$line" | awk '{print $1}')
        local branch=$(echo "$line" | awk '{print $2}' | tr -d '[]')

        if [[ "$path" == *"$SESSION_PREFIX"* ]]; then
            found=true
            local session_id=$(basename "$path" | sed "s/$SESSION_PREFIX-//")
            local scope_file="$path/SESSION_SCOPE.md"
            local scope="unassigned"

            if [ -f "$scope_file" ]; then
                scope=$(grep '^\`' "$scope_file" | head -1 | tr -d '`' || echo "unassigned")
            fi

            echo -e "${CYAN}Session $session_id${NC}"
            echo "  Path:   $path"
            echo "  Branch: $branch"
            echo "  Scope:  $scope"
            echo ""
        fi
    done < <(git worktree list)

    if [ "$found" = false ]; then
        echo -e "${YELLOW}No session worktrees found.${NC}"
        echo "Run '$0 setup' to create them."
    fi
}

show_status() {
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║         Claude Session Status                                ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local found=false

    while IFS= read -r line; do
        local path=$(echo "$line" | awk '{print $1}')
        local branch=$(echo "$line" | awk '{print $2}' | tr -d '[]')

        if [[ "$path" == *"$SESSION_PREFIX"* ]]; then
            found=true
            local session_id=$(basename "$path" | sed "s/$SESSION_PREFIX-//")

            echo -e "${CYAN}━━━ Session $session_id ━━━${NC}"
            echo "  Path: $path"
            echo "  Branch: $branch"

            # Check for uncommitted changes
            local changes=$(cd "$path" && git status --short 2>/dev/null | wc -l)
            if [ "$changes" -gt 0 ]; then
                echo -e "  Changes: ${YELLOW}$changes uncommitted files${NC}"
            else
                echo -e "  Changes: ${GREEN}Clean${NC}"
            fi

            # Count commits ahead of main
            local ahead=$(cd "$path" && git rev-list --count main..HEAD 2>/dev/null || echo "0")
            echo "  Commits ahead: $ahead"

            # Show scope
            local scope_file="$path/SESSION_SCOPE.md"
            if [ -f "$scope_file" ]; then
                local scope=$(grep '^\`' "$scope_file" | head -1 | tr -d '`' || echo "unassigned")
                echo "  Scope: $scope"
            fi

            echo ""
        fi
    done < <(git worktree list)

    if [ "$found" = false ]; then
        echo -e "${YELLOW}No session worktrees found.${NC}"
    fi
}

claim_scope() {
    local session=$1
    local scope=$2

    if [ -z "$session" ] || [ -z "$scope" ]; then
        echo -e "${RED}Usage: $0 claim <session> <scope>${NC}"
        echo "Example: $0 claim A backend"
        exit 1
    fi

    local worktree_path="$WORKTREE_BASE/$SESSION_PREFIX-$session"

    if [ ! -d "$worktree_path" ]; then
        echo -e "${RED}Session $session not found at $worktree_path${NC}"
        exit 1
    fi

    # Update scope in SESSION_SCOPE.md
    local scope_file="$worktree_path/SESSION_SCOPE.md"
    if [ -f "$scope_file" ]; then
        sed -i "s/^\`.*\`$/\`$scope\`/" "$scope_file"
        echo "- $(date -Iseconds): Scope claimed: $scope" >> "$scope_file"
        echo -e "${GREEN}✓ Session $session now claims scope: $scope${NC}"
    else
        create_session_scope "$worktree_path" "$session" "$scope"
        echo -e "${GREEN}✓ Created scope file for session $session with scope: $scope${NC}"
    fi
}

teardown_worktrees() {
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║         Tearing Down Session Worktrees                       ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local sessions_found=()
    local branches_to_check=()

    # Find all session worktrees
    while IFS= read -r line; do
        local path=$(echo "$line" | awk '{print $1}')
        local branch=$(echo "$line" | awk '{print $2}' | tr -d '[]')

        if [[ "$path" == *"$SESSION_PREFIX"* ]]; then
            sessions_found+=("$path")
            branches_to_check+=("$branch")
        fi
    done < <(git worktree list)

    if [ ${#sessions_found[@]} -eq 0 ]; then
        echo -e "${YELLOW}No session worktrees found to tear down.${NC}"
        exit 0
    fi

    echo -e "${BLUE}Found ${#sessions_found[@]} session worktree(s):${NC}"
    for path in "${sessions_found[@]}"; do
        echo "  - $path"
    done
    echo ""

    # Check for uncommitted changes
    echo -e "${BLUE}Checking for uncommitted changes...${NC}"
    local has_changes=false
    for path in "${sessions_found[@]}"; do
        local changes=$(cd "$path" && git status --short 2>/dev/null | wc -l)
        if [ "$changes" -gt 0 ]; then
            echo -e "  ${YELLOW}⚠️  $path has $changes uncommitted files${NC}"
            has_changes=true
        fi
    done

    if [ "$has_changes" = true ]; then
        echo ""
        read -p "Some sessions have uncommitted changes. Continue? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Ask about merging
    echo ""
    read -p "Merge session branches into main before removing? (Y/n) " -n 1 -r
    echo
    local do_merge=true
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        do_merge=false
    fi

    # Return to main project
    cd "$PROJECT_ROOT"

    # Merge branches if requested
    if [ "$do_merge" = true ]; then
        echo -e "\n${BLUE}Merging session branches...${NC}"
        git checkout main 2>/dev/null || git checkout master 2>/dev/null

        for branch in "${branches_to_check[@]}"; do
            if git rev-parse --verify "$branch" >/dev/null 2>&1; then
                local ahead=$(git rev-list --count HEAD.."$branch" 2>/dev/null || echo "0")
                if [ "$ahead" -gt 0 ]; then
                    echo -e "  ${CYAN}Merging $branch ($ahead commits)...${NC}"
                    if git merge "$branch" --no-edit; then
                        echo -e "  ${GREEN}✓ Merged $branch${NC}"
                    else
                        echo -e "  ${RED}✗ Merge conflict in $branch - resolve manually${NC}"
                        exit 1
                    fi
                else
                    echo -e "  ${YELLOW}Skipping $branch (no changes)${NC}"
                fi
            fi
        done
    fi

    # Remove worktrees
    echo -e "\n${BLUE}Removing worktrees...${NC}"
    for path in "${sessions_found[@]}"; do
        if git worktree remove "$path" --force 2>/dev/null; then
            echo -e "  ${GREEN}✓ Removed $path${NC}"
        else
            echo -e "  ${YELLOW}⚠️  Could not remove $path - try manually${NC}"
        fi
    done

    # Clean up branches
    echo -e "\n${BLUE}Cleaning up branches...${NC}"
    for branch in "${branches_to_check[@]}"; do
        if git branch -d "$branch" 2>/dev/null; then
            echo -e "  ${GREEN}✓ Deleted branch $branch${NC}"
        elif git branch -D "$branch" 2>/dev/null; then
            echo -e "  ${YELLOW}✓ Force deleted branch $branch${NC}"
        fi
    done

    # Prune worktree references
    git worktree prune

    echo -e "\n${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Teardown complete!${NC}"
}

# Main command router
case "${1:-help}" in
    setup)
        setup_worktrees "${2:-3}"
        ;;
    list)
        list_worktrees
        ;;
    status)
        show_status
        ;;
    claim)
        claim_scope "$2" "$3"
        ;;
    teardown)
        teardown_worktrees
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

