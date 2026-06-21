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

# ── AutoHotkey integration ────────────────────────────────────────────────────
_AHK_PID_FILE="$ROOT/hotkey.pid"
_AHK_SCRIPT_WIN="$(wslpath -w "$ROOT/hotkey.ahk" 2>/dev/null || true)"

_find_ahk() {
    local _p
    _p="$(cmd.exe /c 'where AutoHotkey64.exe 2>nul' 2>/dev/null | head -1 | tr -d '\r\n')"
    [ -n "$_p" ] && { wslpath "$_p" 2>/dev/null; return; }
    _p="$(cmd.exe /c 'where AutoHotkey.exe 2>nul' 2>/dev/null | head -1 | tr -d '\r\n')"
    [ -n "$_p" ] && { wslpath "$_p" 2>/dev/null; return; }
    local _u
    _u="$(cmd.exe /c 'echo %USERNAME%' 2>/dev/null | tr -d '\r\n')"
    local _candidates=(
        "/mnt/c/Program Files/AutoHotkey/v2/AutoHotkey64.exe"
        "/mnt/c/Program Files/AutoHotkey/v2/AutoHotkey32.exe"
        "/mnt/c/Program Files/AutoHotkey/AutoHotkey64.exe"
        "/mnt/c/Program Files/AutoHotkey/AutoHotkey.exe"
        "/mnt/c/Users/$_u/AppData/Local/Programs/AutoHotkey/v2/AutoHotkey64.exe"
    )
    for _c in "${_candidates[@]}"; do
        [ -f "$_c" ] && { echo "$_c"; return; }
    done
}

_stop_ahk() {
    if [ -f "$_AHK_PID_FILE" ]; then
        local _wpid
        _wpid="$(tr -d '[:space:]' < "$_AHK_PID_FILE")"
        [ -n "$_wpid" ] && taskkill.exe /F /PID "$_wpid" >/dev/null 2>&1 && \
            echo "[CrimsonHelper] AutoHotkey stopped."
        rm -f "$_AHK_PID_FILE"
    fi
}

_start_ahk() {
    [ -z "$_AHK_SCRIPT_WIN" ] && return
    local _exe
    _exe="$(_find_ahk)"
    if [ -z "$_exe" ]; then
        echo "[CrimsonHelper] AutoHotkey not found — run hotkey.ahk manually for in-game hotkey"
        return
    fi
    _stop_ahk   # replace any lingering instance
    "$_exe" "$_AHK_SCRIPT_WIN" &
    sleep 1     # let AHK write its PID file
    local _wpid
    _wpid="$(tr -d '[:space:]' < "$_AHK_PID_FILE" 2>/dev/null || true)"
    echo "[CrimsonHelper] AutoHotkey started${_wpid:+ (PID $_wpid)} — hotkey active"
}

trap '_stop_ahk' EXIT
_start_ahk

echo ""
echo "[CrimsonHelper] Starting on http://${HOST}:${PORT}"
echo "[CrimsonHelper] Collab server on :7777"
echo "[CrimsonHelper] Ctrl+C to stop everything"
echo ""

python -m uvicorn main:app --host "$HOST" --port "$PORT" --reload
