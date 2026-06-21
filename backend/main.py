"""
CrimsonHelper backend — FastAPI entry point.
Starts: DB, pipeline worker, hotkey listener, voice listener, collab server + client.
WebSocket at /ws broadcasts real-time events to the React dashboard.
"""
import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ── Config ─────────────────────────────────────────────────────────────────────
_root = Path(__file__).resolve().parents[1]
with open(_root / "config.json") as _f:
    _cfg = json.load(_f)

SCREENSHOTS_DIR = (_root / _cfg["screenshots_dir"]).resolve()

# ── DB ─────────────────────────────────────────────────────────────────────────
from db.database import init_db, SessionLocal
from db.models import VoiceLog
from datetime import datetime

# ── Internal modules ───────────────────────────────────────────────────────────
import capture
import pipeline
import voice
import collab
import collab_server
import ocr as ocr_mod
import process_guard

# ── API routers ────────────────────────────────────────────────────────────────
from api.quests import router as quests_router
from api.screenshots import router as screenshots_router
from api.loot import router as loot_router
from api.npcs import router as npcs_router

# ── WebSocket connection manager ───────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def _set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket):
        try:
            self._connections.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, data: dict):
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def broadcast_sync(self, data: dict):
        """Thread-safe broadcast from pipeline/voice/collab worker threads."""
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self.broadcast(data), self._loop)


manager = ConnectionManager()


# ── Voice command dispatcher (runs inside the listener thread) ─────────────────

def _voice_dispatch(cmd: str) -> str:
    db = SessionLocal()
    try:
        import re
        from db.models import Quest, NPC, LootEntry

        m = re.search(r"(?:search|find)\s+quest\s+(.+)", cmd)
        if m:
            term = m.group(1)
            quests = db.query(Quest).filter(Quest.title.ilike(f"%{term}%")).limit(3).all()
            if quests:
                names = ", ".join(q.title for q in quests)
                return f"Found quests: {names}"
            return f"No quests matching {term}."

        m = re.search(r"(?:search|find)\s+npc\s+(.+)", cmd)
        if m:
            term = m.group(1)
            npcs = db.query(NPC).filter(NPC.name.ilike(f"%{term}%")).limit(3).all()
            if npcs:
                names = ", ".join(n.name for n in npcs)
                return f"Found NPCs: {names}"
            return f"No NPC matching {term}."

        m = re.search(r"(?:search|find)\s+item\s+(.+)", cmd)
        if m:
            term = m.group(1)
            items = db.query(LootEntry).filter(LootEntry.item_name.ilike(f"%{term}%")).limit(3).all()
            if items:
                names = ", ".join(f"{i.item_name} x{i.quantity}" for i in items)
                return f"Found loot: {names}"
            return f"No loot matching {term}."

        m = re.search(r"read\s+(?:last|latest)\s+quest", cmd)
        if m:
            q = db.query(Quest).order_by(Quest.captured_at.desc()).first()
            if q:
                return f"Last quest: {q.title}. {q.description or ''}"
            return "No quests recorded yet."

        return ""
    finally:
        db.close()


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    manager._set_loop(asyncio.get_running_loop())
    init_db()

    # Wire up broadcast callbacks
    pipeline.register_broadcast(manager.broadcast_sync)
    pipeline.register_db_factory(SessionLocal)
    voice.register_broadcast(manager.broadcast_sync)
    voice.register_dispatch(_voice_dispatch)
    collab.register_broadcast(manager.broadcast_sync)

    # Start background services
    collab_server.start_in_thread()
    capture.start_listener()
    pipeline.start()
    collab.start()

    if _cfg.get("voice_enabled") and voice.is_available():
        voice.start_listener()

    print(f"[main] CrimsonHelper ready → http://{_cfg['server_host']}:{_cfg['server_port']}")
    yield

    # Shutdown
    capture.stop_listener()
    pipeline.stop()
    voice.stop_listener()
    collab.stop()


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="CrimsonHelper", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quests_router)
app.include_router(screenshots_router)
app.include_router(loot_router)
app.include_router(npcs_router)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            # Handle client commands (e.g., trigger capture)
            if data.get("action") == "capture":
                capture.trigger_capture(source="api")
            elif data.get("action") == "voice_toggle":
                if voice.is_active():
                    voice.stop_listener()
                    await ws.send_json({"type": "voice_status", "active": False})
                else:
                    voice.start_listener()
                    await ws.send_json({"type": "voice_status", "active": True})
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── REST utility endpoints ─────────────────────────────────────────────────────

@app.post("/api/capture")
async def manual_capture():
    reason = capture.trigger_capture(source="api")
    if reason:
        return {"ok": False, "reason": reason}
    return {"ok": True}


@app.get("/api/status")
def status():
    guard_enabled = _cfg.get("process_guard_enabled", True)
    game_proc = _cfg.get("game_process", "CrimsonDesert.exe")
    return {
        "ocr_available": ocr_mod.is_available(),
        "voice_active": voice.is_active(),
        "voice_available": voice.is_available(),
        "collab_enabled": _cfg.get("collab_enabled", False),
        "hotkey": _cfg.get("hotkey", "f6").upper(),
        "game_running": process_guard.is_running(game_proc) if guard_enabled else True,
        "game_process": game_proc,
    }


@app.get("/api/collab/status")
def collab_status():
    return collab.get_status() or {"error": "collab server unreachable"}


@app.get("/api/collab/inbox")
def collab_inbox():
    return {"messages": collab.poll_inbox()}


@app.post("/api/collab/task")
def collab_task(description: str, priority: str = "normal"):
    result = collab.create_task(description, priority)
    return result or {"error": "collab server unreachable"}


# ── Screenshot file serving ────────────────────────────────────────────────────

@app.get("/screenshots/{filename}")
async def serve_screenshot(filename: str):
    from fastapi import HTTPException
    # Reject paths that try to escape the screenshots directory
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(400, "Invalid filename")
    path = (SCREENSHOTS_DIR / filename).resolve()
    if not path.is_relative_to(SCREENSHOTS_DIR):
        raise HTTPException(400, "Invalid filename")
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(path))


# ── Serve built React app (production) ────────────────────────────────────────

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists() and any(_static_dir.iterdir()):
    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = _static_dir / "index.html"
        return FileResponse(str(index))
