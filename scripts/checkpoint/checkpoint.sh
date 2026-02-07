#!/bin/bash
# Checkpoint System Shell Wrapper
# Usage: ./checkpoint.sh save|restore|list|show|delete [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

python3 "$SCRIPT_DIR/checkpoint.py" "$@"
