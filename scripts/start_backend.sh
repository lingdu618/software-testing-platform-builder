#!/bin/bash
# Start backend (bash version). Uses managed Python venv.
# Usage: ./scripts/start_backend.sh
set -e
PY="${PY:-C:/Users/admin/.workbuddy/binaries/python/envs/btplat/Scripts/python.exe}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR/backend"
echo "Starting uvicorn at $SCRIPT_DIR/backend..."
"$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000