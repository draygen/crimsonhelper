# CrimsonHelper

A local game assistant for **Crimson Desert** that captures, reads, and indexes in-game screens as you play — quests, loot, NPC dialogue — and surfaces everything through a real-time web dashboard.

Runs entirely on your machine: WSL2 backend + React frontend, no cloud required.

---

## Features

| Feature | Detail |
|---------|--------|
| **Hotkey capture** | Press F6 (configurable) to grab the current screen |
| **OCR pipeline** | Tesseract extracts text from every capture automatically |
| **Auto-classification** | Heuristic classifier tags each screenshot: quest / loot / NPC / general |
| **Quest tracker** | Titles, descriptions, zone, status (active / completed / failed) |
| **Loot log** | Item names, quantities, zone, aggregated summary view |
| **NPC memory** | Dialogue history keyed by NPC name, last-seen timestamps |
| **Process guard** | Captures only fire when CrimsonDesert.exe is running |
| **Voice commands** | "find quest …", "capture", "open dashboard" via microphone |
| **Collab server** | Built-in SSE hub lets multiple agents share captures in real time |
| **YouTube guides** | One-click lookup for quests or loot items (optional API key) |

---

## Requirements

| Requirement | Notes |
|-------------|-------|
| Windows 11 + WSL2 | Ubuntu 22.04 LTS recommended |
| Python 3.11+ | Inside WSL |
| Node.js 20+ | Inside WSL, for the frontend build |
| Tesseract OCR | Installed automatically by `setup.sh` |

---

## Quick start

```bash
# Clone
git clone https://github.com/draygen/crimsonhelper.git
cd crimsonhelper

# One-time setup (installs Python deps, Tesseract, espeak-ng, builds frontend)
./setup.sh

# Start
./start.sh
# — or double-click start.bat from Windows Explorer
```

Open **http://localhost:8765** in your browser.

**To use F6 in-game**, run `hotkey.ahk` on Windows (requires [AutoHotkey v2](https://www.autohotkey.com)).  
It intercepts F6 at the Windows level and calls the API — works even while CrimsonDesert has focus.  
The dashboard "Capture Now" button always works as a manual fallback.

---

## Configuration

All settings live in `config.json` at the project root. Edit and restart to apply.

```jsonc
{
  "hotkey": "f6",                        // capture hotkey
  "game_process": "CrimsonDesert.exe",   // process guard — captures blocked if not running
  "process_guard_enabled": true,
  "capture_debounce_secs": 2.0,          // minimum seconds between captures

  "voice_enabled": true,                 // microphone voice commands
  "ocr_lang": "eng",                     // Tesseract language code
  "tesseract_path": "",                  // leave empty to use system Tesseract

  "server_host": "127.0.0.1",
  "server_port": 8000,

  "screenshots_dir": "./screenshots",    // where PNGs are saved
  "db_path": "./data/crimsonhelper.db",  // SQLite database

  "youtube_api_key": "",                 // optional — for inline guide results
  "collab_enabled": true,                // multi-agent collab server (port 7777)
  "collab_agent_id": "local"
}
```

---

## Voice commands

Voice requires a working microphone and `espeak-ng` (installed by `setup.sh`).

| Say | Action |
|-----|--------|
| `find quest <name>` | Search quest log |
| `find npc <name>` | Search NPC memory |
| `find item <name>` | Search loot log |
| `read last quest` | Reads the most recent quest aloud |
| `capture` / `screenshot` | Triggers a screen capture |
| `open dashboard` | Opens the browser dashboard |
| `stop listening` | Pauses voice commands |

Toggle voice on/off from the dashboard sidebar.

---

## Architecture

```
crimsonhelper/
├── backend/
│   ├── main.py          # FastAPI app, WebSocket hub, lifespan wiring
│   ├── capture.py       # Hotkey listener + mss screen grab
│   ├── pipeline.py      # Capture → OCR → classify → DB → broadcast
│   ├── ocr.py           # Tesseract wrapper with preprocessing
│   ├── classifier.py    # Keyword/regex heuristics for quest/loot/npc
│   ├── voice.py         # SpeechRecognition listener + pyttsx3 TTS
│   ├── process_guard.py # Checks CrimsonDesert.exe is running (cached 5 s)
│   ├── collab.py        # SSE client — connects to collab server
│   ├── collab_server.py # Built-in SSE hub on :7777
│   ├── youtube.py       # YouTube Data API v3 guide lookup
│   ├── db/
│   │   ├── database.py  # SQLAlchemy engine + session factory
│   │   └── models.py    # Screenshot, Quest, LootEntry, NPC, VoiceLog
│   └── api/
│       ├── quests.py    # GET/DELETE/PATCH /api/quests
│       ├── loot.py      # GET/DELETE /api/loot, /api/loot/summary
│       ├── npcs.py      # GET/DELETE /api/npcs
│       └── screenshots.py # GET/DELETE /api/screenshots
├── frontend/            # React + Vite + Tailwind + TanStack Query
│   └── src/
│       ├── pages/       # Dashboard, Quests, Loot, NPCs, Screenshots
│       ├── components/  # Layout (sidebar + live feed)
│       ├── hooks/       # useWebSocket (auto-reconnect)
│       └── lib/api.ts   # Typed fetch wrapper
├── config.json
├── setup.sh             # One-time WSL setup
├── start.sh             # Launch backend
└── start.bat            # Launch from Windows Explorer
```

**Data flow:**  
`F6 keypress → capture.py grabs screen → pipeline.py runs OCR → classifier tags it → saved to SQLite → broadcast over WebSocket → dashboard updates live`

---

## REST API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/status` | OCR, voice, game process status |
| `POST` | `/api/capture` | Trigger a manual capture |
| `GET` | `/api/quests` | List quests (search, zone, status filters) |
| `PATCH` | `/api/quests/{id}/status` | Update quest status |
| `DELETE` | `/api/quests/{id}` | Delete quest |
| `GET` | `/api/quests/{id}/guide` | YouTube guide lookup |
| `GET` | `/api/loot` | List loot entries |
| `GET` | `/api/loot/summary` | Aggregated totals per item |
| `GET` | `/api/npcs` | List NPCs |
| `GET` | `/api/screenshots` | List screenshots |
| `WS` | `/ws` | Real-time event stream |

---

## WSL notes

- **Hotkey (F6)**: requires the `input` group — `setup.sh` adds you automatically. Start a new WSL session after first setup.
- **Voice**: needs PulseAudio or PipeWire wired to Windows audio. Works out-of-the-box on WSL2 with recent Windows 11 builds.
- **Screen capture**: `mss` grabs the primary Windows display via the WSL2 display bridge.
- **Tesseract path**: set `tesseract_path` to a Windows path (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`) if you prefer the Windows binary over the apt-installed one.

---

## License

MIT
