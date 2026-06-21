"""
Collab client — connects crimsonhelper to the shared collab server (port 7777).
Runs an SSE listener in a background thread so the remote agent can push
commands/results back in real-time.

The collab server lives at /mnt/c/projects/.collab/collab-server.py.
This process registers as the "local" agent; the remote WSL machine is "remote".
"""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable

_root = Path(__file__).resolve().parents[1]
with open(_root / "config.json") as _f:
    _cfg = json.load(_f)

COLLAB_URL: str = _cfg.get("collab_server_url", "http://localhost:7777")
AGENT_ID: str = _cfg.get("collab_agent_id", "local")
ENABLED: bool = _cfg.get("collab_enabled", True)

_ws_broadcast: Callable[[dict], None] | None = None
_sse_thread: threading.Thread | None = None
_stop_evt = threading.Event()


def register_broadcast(fn: Callable[[dict], None]):
    global _ws_broadcast
    _ws_broadcast = fn


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _post(path: str, payload: dict) -> dict | None:
    url = f"{COLLAB_URL}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"[collab] POST {path} failed: {exc}")
        return None


def _get(path: str) -> dict | None:
    url = f"{COLLAB_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"[collab] GET {path} failed: {exc}")
        return None


# ── Public send API ────────────────────────────────────────────────────────────

def send_event(event_type: str, content: str, meta: dict | None = None):
    """Fire-and-forget: push an event to the 'remote' agent."""
    if not ENABLED:
        return
    _post("/send", {
        "from": AGENT_ID,
        "to": "remote",
        "type": event_type,
        "content": content,
        "meta": meta or {},
    })


def send_quest(title: str, description: str, zone: str = ""):
    send_event("quest_captured", f"Quest: {title}", {"description": description, "zone": zone})


def send_loot(items: list[str], zone: str = ""):
    send_event("loot_captured", f"Loot: {', '.join(items)}", {"items": items, "zone": zone})


def send_screenshot(filename: str, category: str, ocr_text: str):
    send_event("screenshot_captured", f"Screenshot [{category}]: {filename}",
               {"filename": filename, "category": category, "ocr_preview": ocr_text[:200]})


def create_task(description: str, priority: str = "normal", assigned_to: str = "remote") -> dict | None:
    if not ENABLED:
        return None
    return _post("/task/create", {
        "from": AGENT_ID,
        "description": description,
        "priority": priority,
        "assigned_to": assigned_to,
    })


def poll_inbox() -> list[dict]:
    """Pull any pending messages from the collab server inbox."""
    if not ENABLED:
        return []
    data = _get(f"/poll/{AGENT_ID}")
    return data.get("messages", []) if data else []


def get_status() -> dict | None:
    return _get("/status")


# ── SSE listener ───────────────────────────────────────────────────────────────

def _sse_listen():
    """Long-lived SSE connection. Forwards server events to the WS broadcast."""
    url = f"{COLLAB_URL}/stream/{AGENT_ID}"
    while not _stop_evt.is_set():
        try:
            req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                print(f"[collab] SSE connected as '{AGENT_ID}'")
                for raw_line in resp:
                    if _stop_evt.is_set():
                        break
                    line = raw_line.decode("utf-8").strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        payload_str = line[5:].strip()
                        try:
                            msg = json.loads(payload_str)
                        except json.JSONDecodeError:
                            continue
                        _handle_incoming(msg)
        except Exception as exc:
            if not _stop_evt.is_set():
                print(f"[collab] SSE lost ({exc}), reconnecting in 5s…")
                time.sleep(5)


def _handle_incoming(msg: dict):
    """Process a message arriving from the collab server."""
    print(f"[collab] ← {msg.get('type','msg')} from {msg.get('from','?')}: {str(msg.get('content',''))[:80]}")
    if _ws_broadcast:
        _ws_broadcast({
            "type": "collab_message",
            "payload": msg,
            "ts": datetime.utcnow().isoformat(),
        })


# ── Lifecycle ──────────────────────────────────────────────────────────────────

def start():
    global _sse_thread
    if not ENABLED:
        print("[collab] Disabled in config.")
        return
    _stop_evt.clear()
    _sse_thread = threading.Thread(target=_sse_listen, daemon=True, name="collab-sse")
    _sse_thread.start()
    print(f"[collab] Client started → {COLLAB_URL} as '{AGENT_ID}'")


def stop():
    _stop_evt.set()
