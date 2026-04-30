#!/bin/bash
# Phase Completion Helper for Dashboard Interface Project
# Generates a phase summary markdown doc under docs/phase-summaries/.
#
# Usage:
#   ./scripts/phase-completion.sh "Phase Name" "Summary Description" [--push]
#
# Behavior:
#   - Creates docs/phase-summaries/<timestamp>_<safe-name>_summary.md
#   - Stages and commits ONLY the new summary file (not -A)
#   - Does NOT push by default. Pass --push to opt in to pushing the
#     current branch (NEVER force-pushes to main).
#
# This script does not interact with any MCP server. If you want to
# checkpoint context to memory-keeper, do that manually in your tool of
# choice — instructions are echoed at the end of each run.

set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 \"Phase Name\" \"Summary Description\" [--push]" >&2
    exit 2
fi

PHASE_NAME="$1"
SUMMARY_DESC="$2"
PUSH_FLAG="${3:-}"

# Resolve project dir from git so this script works wherever it lives.
PROJECT_DIR="$(git rev-parse --show-toplevel)"
DOCS_DIR="$PROJECT_DIR/docs/phase-summaries"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_READABLE=$(date +"%Y-%m-%d %H:%M:%S")
SAFE_PHASE_NAME=$(echo "$PHASE_NAME" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g')

mkdir -p "$DOCS_DIR"

cd "$PROJECT_DIR"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "=== Phase Completion: $PHASE_NAME ==="
echo "[1/3] Generating phase summary document..."

SUMMARY_FILE="$DOCS_DIR/${TIMESTAMP}_${SAFE_PHASE_NAME}_summary.md"
RECENT_COMMITS=$(git log --oneline -10)
LATEST_COMMIT=$(git rev-parse --short HEAD)

cat > "$SUMMARY_FILE" << SUMMARY_EOF
# Phase Summary: $PHASE_NAME

**Date:** $DATE_READABLE
**Branch:** $CURRENT_BRANCH
**Latest Commit:** $LATEST_COMMIT

---

## Summary

$SUMMARY_DESC

---

## Recent Commits

\`\`\`
$RECENT_COMMITS
\`\`\`

---

## Next Steps

<!-- Add next steps here -->

---

## Manual Memory Save (optional)

If you want to checkpoint context for the next session, save the
following to your memory tool of choice (e.g. memory-keeper):

- Key: \`phase-complete-$SAFE_PHASE_NAME-$TIMESTAMP\`
- Channel: \`dashboard-project\`
- Category: \`progress\`
- Priority: \`high\`
- Value: $SUMMARY_DESC

---

## Restoration Instructions

### Git
\`\`\`bash
cd "$(git rev-parse --show-toplevel)"
git checkout $CURRENT_BRANCH
git log --oneline -5
\`\`\`

### Backend
\`\`\`bash
cd backend
source venv/Scripts/activate  # Git Bash on Windows
PYTHONPATH=. python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
\`\`\`

### Verify state
\`\`\`bash
curl -s http://localhost:8000/api/v1/extraction/status | python -m json.tool
\`\`\`

---

## Context for Next Session

Tell Claude:

> "Resuming work on the Dashboard Interface Project. Last session
> completed the '$PHASE_NAME' phase. See $SUMMARY_FILE for context."

SUMMARY_EOF

echo "[2/3] Committing summary file..."
git add "$SUMMARY_FILE"
if git diff --cached --quiet; then
    echo "Nothing staged — summary file may already be committed."
else
    git commit -m "docs(phase-summary): $SAFE_PHASE_NAME — $SUMMARY_DESC"
fi

echo "[3/3] Push step..."
if [ "$PUSH_FLAG" = "--push" ]; then
    if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
        echo "Refusing to auto-push to $CURRENT_BRANCH. Push manually if you really want to." >&2
    else
        echo "Pushing $CURRENT_BRANCH to origin..."
        git push -u origin "$CURRENT_BRANCH"
    fi
else
    echo "Skipping push (no --push flag). Run: git push -u origin $CURRENT_BRANCH"
fi

echo ""
echo "Summary document: $SUMMARY_FILE"
echo "Latest commit:    $LATEST_COMMIT"
echo "Branch:           $CURRENT_BRANCH"
