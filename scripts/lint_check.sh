#!/bin/bash
set -e
echo "=== Sysadmin Assistant Syntax Check ==="

echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0
CHECK_NUM=1



echo -e "${BLUE}${CHECK_NUM}. Checking Python syntax...${NC}"
while read -r file; do
  if ! python3 -m py_compile "$file" 2>/dev/null; then
    echo -e "${RED}✗ Syntax error:${NC} $file"
    python3 -m py_compile "$file" 2>&1 | sed 's/^/  /'
    ((ERRORS++))
  fi
done < <(find . -name "*.py" -type f -not -path "*/venv/*" -not -path "*/.venv/*" -not -path "*/node_modules/*" -not -path "./.git/*")
CHECK_NUM=$((CHECK_NUM + 1))

echo ""
echo -e "${BLUE}${CHECK_NUM}. Checking for tab/space mixing in Python...${NC}"
while read -r file; do
  if grep -q $'\t' "$file" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Mixed indentation:${NC} $file"
    grep -n $'\t' "$file" 2>/dev/null | head -5 | sed 's/^/  Line /'
    ((WARNINGS++))
  fi
done < <(find . -name "*.py" -type f -not -path "*/venv/*" -not -path "*/.venv/*" -not -path "*/node_modules/*" -not -path "./.git/*")
CHECK_NUM=$((CHECK_NUM + 1))






echo ""
echo -e "${BLUE}${CHECK_NUM}. Checking JavaScript syntax...${NC}"
while read -r file; do
  if ! node --check "$file" 2>/dev/null; then
    echo -e "${RED}✗ Syntax error:${NC} $file"
    node --check "$file" 2>&1 | sed 's/^/  /'
    ((ERRORS++))
  fi
done < <(find . -name "*.js" -type f -not -path "*/node_modules/*" -not -path "*/venv/*" -not -path "*/.venv/*" -not -path "./.git/*" -not -path "*/.nuxt/*")
CHECK_NUM=$((CHECK_NUM + 1))

echo ""
echo -e "${BLUE}${CHECK_NUM}. Checking JSON files...${NC}"
while read -r file; do
  if ! python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
    echo -e "${RED}✗ Invalid JSON:${NC} $file"
    python3 -c "import json; json.load(open('$file'))" 2>&1 | head -3 | sed 's/^/  /'
    ((ERRORS++))
  fi
done < <(find . -name "*.json" -type f -not -path "*/node_modules/*" -not -path "*/venv/*" -not -path "*/.venv/*" -not -path "./.git/*" -not -path "./.vscode/*" -not -path "*/test_results/*" -not -path "*/.nuxt/*")
CHECK_NUM=$((CHECK_NUM + 1))

echo ""
echo -e "${BLUE}${CHECK_NUM}. Checking YAML files...${NC}"
while read -r file; do
  if ! python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
    echo -e "${RED}✗ Invalid YAML:${NC} $file"
    python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>&1 | head -3 | sed 's/^/  /'
    ((ERRORS++))
  fi
done < <(find . \( -name "*.yaml" -o -name "*.yml" \) -type f -not -path "*/node_modules/*" -not -path "*/venv/*" -not -path "*/.venv/*" -not -path "./.git/*")
CHECK_NUM=$((CHECK_NUM + 1))





echo ""
echo "=== Summary ==="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo -e "${GREEN}✓ No syntax errors or warnings found${NC}"
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo -e "${YELLOW}⚠ Found $WARNINGS warnings (no errors)${NC}"
  exit 0
else
  echo -e "${RED}✗ Found $ERRORS errors and $WARNINGS warnings${NC}"
  exit 1
fi

