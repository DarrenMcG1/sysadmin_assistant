#!/bin/bash
# scripts/install_hooks.sh
# Install git hooks for the development workflow

set -e

HOOK_DIR=".git/hooks"

echo "Installing git hooks..."

# Install pre-commit hook
cat > "$HOOK_DIR/pre-commit" << 'EOF'
#!/bin/bash
./scripts/claude-precommit.sh
EOF

chmod +x "$HOOK_DIR/pre-commit"
echo "  ✓ Pre-commit hook installed"

# Make Claude hooks executable
chmod +x .claude/hooks/*.sh 2>/dev/null || true
echo "  ✓ Claude hooks made executable"

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will:"
echo "  - Run lint checks on staged code files"
echo "  - Block commits with 5+ code files if no docs updated"
echo "  - Auto-stage audit-report.md and auto_snag_list.md"

