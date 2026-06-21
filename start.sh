#!/bin/bash
# Start CrimsonHelper backend (collab server included)
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

PORT=$(python3 -c "import json; print(json.load(open('../config.json'))['server_port'])" 2>/dev/null || echo 8000)
HOST=$(python3 -c "import json; print(json.load(open('../config.json'))['server_host'])" 2>/dev/null || echo "127.0.0.1")

echo "[CrimsonHelper] Starting on http://${HOST}:${PORT}"
echo "[CrimsonHelper] Collab server on :7777"
echo "[CrimsonHelper] Press F6 in-game to capture"
echo ""

python -m uvicorn main:app --host "$HOST" --port "$PORT" --reload
