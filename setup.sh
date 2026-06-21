#!/bin/bash
# CrimsonHelper setup — run once from WSL
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== CrimsonHelper Setup ==="
echo ""

# ── Python venv ────────────────────────────────────────────────────────────────
echo "[1/4] Setting up Python environment..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "      Python deps installed."
cd ..
echo ""

# ── System dependencies ────────────────────────────────────────────────────────
echo "[2/4] Checking system dependencies..."
_PKGS=()
command -v tesseract &>/dev/null || _PKGS+=(tesseract-ocr tesseract-ocr-eng)
command -v espeak-ng  &>/dev/null || _PKGS+=(espeak-ng)
command -v pactl      &>/dev/null || _PKGS+=(pulseaudio alsa-utils)
dpkg -s portaudio19-dev &>/dev/null 2>&1    || _PKGS+=(portaudio19-dev)
if [ ${#_PKGS[@]} -gt 0 ]; then
    echo "      Installing: ${_PKGS[*]}"
    sudo apt-get update -qq && sudo apt-get install -y -qq "${_PKGS[@]}"
fi
echo "      Tesseract : $(tesseract --version 2>&1 | head -1)"
echo "      espeak-ng : $(espeak-ng --version 2>&1 | head -1)"
echo "      portaudio : $(dpkg -s portaudio19-dev 2>/dev/null | grep Version | awk '{print $2}')"
echo ""

# ── Hotkey input permissions ───────────────────────────────────────────────────
if ! groups | grep -qw input; then
    echo "      Adding $USER to 'input' group for hotkey support..."
    sudo usermod -aG input "$USER"
    echo "      NOTE: Start a new WSL session (or run 'newgrp input') for the hotkey to work."
fi

# ── Frontend ───────────────────────────────────────────────────────────────────
echo "[3/4] Setting up React frontend..."
if ! command -v node &>/dev/null; then
    echo ""
    echo "  ERROR: Node.js not found."
    echo "  Install Node.js 20+ inside WSL:"
    echo "    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "    sudo apt-get install -y nodejs"
    echo "  Then re-run this script."
    exit 1
fi
echo "      Node $(node --version) / npm $(npm --version)"
cd frontend
echo "      Installing npm packages (this may take a minute on WSL2)..."
npm install --no-fund --no-audit
echo "      npm packages installed."
echo ""

echo "[4/4] Building frontend..."
npm run build
echo "      Frontend built → backend/static/"
cd ..
echo ""

echo "=== Setup complete ==="
echo ""
echo "  Start:     ./start.sh"
echo "             or double-click start.bat from Windows Explorer"
echo ""
echo "  Dashboard: http://localhost:8000"
echo "  Hotkey:    F6 in-game (change in config.json)"
echo ""
