#!/bin/bash
# Start CrimsonHelper backend (collab server included)
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

PORT=$(python3 -c "import json; print(json.load(open('../config.json'))['server_port'])" 2>/dev/null || echo 8765)
HOST=$(python3 -c "import json; print(json.load(open('../config.json'))['server_host'])" 2>/dev/null || echo "127.0.0.1")

# ── Kill any stale CrimsonHelper processes on our port ──────────────────────
_STALE=$(lsof -ti :"$PORT" 2>/dev/null || true)
if [ -n "$_STALE" ]; then
    for _PID in $_STALE; do
        _CMD=$(ps -p "$_PID" -o args= 2>/dev/null || true)
        if echo "$_CMD" | grep -q "main:app\|uvicorn"; then
            echo "[CrimsonHelper] Stopping stale process (PID $_PID)..."
            kill "$_PID" 2>/dev/null || true
            sleep 1
        else
            echo ""
            echo "  ERROR: Port $PORT is in use by another app (PID $_PID):"
            echo "  $_CMD"
            echo ""
            echo "  Change 'server_port' in config.json (e.g. to 8766) and retry."
            exit 1
        fi
    done
fi

echo "[CrimsonHelper] Starting on http://${HOST}:${PORT}"
echo "[CrimsonHelper] Collab server on :7777"
echo "[CrimsonHelper] Press F6 in-game to capture"
echo ""

python -m uvicorn main:app --host "$HOST" --port "$PORT" --reload
