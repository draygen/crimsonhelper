#!/bin/bash
# CrimsonHelper setup — run once from WSL
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== CrimsonHelper Setup ==="

# ── Python venv ────────────────────────────────────────────────────────────────
echo "[1/4] Setting up Python environment..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "      Python deps installed."
cd ..

# ── System dependencies ────────────────────────────────────────────────────────
echo "[2/4] Checking system dependencies..."
_PKGS=()
command -v tesseract &>/dev/null || _PKGS+=(tesseract-ocr tesseract-ocr-eng)
command -v espeak-ng  &>/dev/null || _PKGS+=(espeak-ng)
dpkg -s portaudio19-dev &>/dev/null 2>&1 || _PKGS+=(portaudio19-dev)
if [ ${#_PKGS[@]} -gt 0 ]; then
    echo "      Installing: ${_PKGS[*]}"
    sudo apt-get update -qq && sudo apt-get install -y -qq "${_PKGS[@]}"
fi
echo "      Tesseract : $(tesseract --version 2>&1 | head -1)"
echo "      espeak-ng : $(espeak-ng --version 2>&1 | head -1)"
echo "      portaudio : $(dpkg -s portaudio19-dev 2>/dev/null | grep Version | awk '{print $2}')"

# ── Hotkey input permissions ───────────────────────────────────────────────────
if ! groups | grep -qw input; then
    echo "      Adding $USER to 'input' group for hotkey support..."
    sudo usermod -aG input "$USER"
    echo "      NOTE: Start a new WSL session (or run 'newgrp input') before launching."
    echo "      Until then the F6 hotkey won't fire; use /api/capture or the dashboard button."
fi

# ── Frontend ────────────────────────────────────────────────────────────────────
echo "[3/4] Setting up React frontend..."
if ! command -v node &>/dev/null; then
    echo "      Node.js not found. Install from https://nodejs.org first, then re-run."
    exit 1
fi
cd frontend
npm install -q
echo "      Node deps installed."

echo "[4/4] Building frontend..."
npm run build
echo "      Frontend built → backend/static/"
cd ..

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start:  ./start.sh"
echo "           or double-click start.bat from Windows"
echo ""
echo "Dashboard: http://localhost:8000"
echo "Hotkey:    F6 (change in config.json)"
