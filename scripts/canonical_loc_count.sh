#!/bin/bash
# Canonical LOC measurement for Real Estate OS
# Scope: Python (backend, scripts, tests) + TypeScript/TSX (frontend)
# Exclusions: node_modules, __pycache__, .venv, migrations, generated files, infra configs

set -euo pipefail

echo "=== CANONICAL LOC MEASUREMENT ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Commit: $(git rev-parse HEAD)"
echo ""

# Define scope explicitly
INCLUDE_PATHS=(
    "api"
    "src"
    "scripts"
    "db/seeds"
    "frontend/src"
    "frontend/app"
    "frontend/components"
    "frontend/lib"
)

EXCLUDE_PATTERNS=(
    "*/node_modules/*"
    "*/__pycache__/*"
    "*/.venv/*"
    "*/migrations/*"
    "*/.next/*"
    "*/dist/*"
    "*/build/*"
    "*_pb2.py"
    "*.min.js"
)

# Build find command
FIND_CMD="find"
for path in "${INCLUDE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        FIND_CMD="$FIND_CMD $path"
    fi
done
FIND_CMD="$FIND_CMD -type f"

# Add exclusions
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    FIND_CMD="$FIND_CMD ! -path '$pattern'"
done

# Add file type filters
FIND_CMD="$FIND_CMD \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \)"

echo "--- Python Backend LOC ---"
eval "$FIND_CMD -name '*.py'" | xargs wc -l 2>/dev/null | tail -1 || echo "0 total"

echo ""
echo "--- TypeScript/JavaScript Frontend LOC ---"
eval "$FIND_CMD \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \)" | xargs wc -l 2>/dev/null | tail -1 || echo "0 total"

echo ""
echo "--- Combined Total ---"
eval "$FIND_CMD" | xargs wc -l 2>/dev/null | tail -1 || echo "0 total"

echo ""
echo "--- File Count Breakdown ---"
echo "Python files: $(eval "$FIND_CMD -name '*.py'" | wc -l)"
echo "TypeScript files: $(eval "$FIND_CMD -name '*.ts'" | wc -l)"
echo "TSX files: $(eval "$FIND_CMD -name '*.tsx'" | wc -l)"
echo "JavaScript files: $(eval "$FIND_CMD -name '*.js'" | wc -l)"
echo "JSX files: $(eval "$FIND_CMD -name '*.jsx'" | wc -l)"
