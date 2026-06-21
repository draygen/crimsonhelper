"""
Screen capture module. Runs a hotkey listener in a background daemon thread.
When the hotkey fires it grabs the full screen (or configured region),
saves a full-res PNG + a thumbnail, and hands the image to the OCR pipeline.
Captures are gated by a process guard (game must be running) and a debounce
timer to prevent duplicate jobs from rapid keypresses.
"""
import json
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

import mss
import mss.tools
from PIL import Image

import process_guard

_root = Path(__file__).resolve().parents[1]
with open(_root / "config.json") as _f:
    _cfg = json.load(_f)

SCREENSHOTS_DIR = (_root / _cfg["screenshots_dir"]).resolve()
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
HOTKEY: str = _cfg.get("hotkey", "f6")
REGION: dict | None = _cfg.get("capture_region")
THUMB_SIZE: tuple = tuple(_cfg.get("thumbnail_size", [320, 180]))
GAME_PROCESS: str = _cfg.get("game_process", "CrimsonDesert.exe")
GUARD_ENABLED: bool = _cfg.get("process_guard_enabled", True)
DEBOUNCE_SECS: float = float(_cfg.get("capture_debounce_secs", 2.0))

# Queue that the OCR worker drains
capture_queue: queue.Queue = queue.Queue()

_listener_thread: threading.Thread | None = None
_stop_event = threading.Event()

_debounce_lock = threading.Lock()
_last_capture_ts: float = 0.0


def _game_is_running() -> bool:
    if not GUARD_ENABLED:
        return True
    return process_guard.is_running(GAME_PROCESS)


def _take_screenshot() -> tuple[Path, Path]:
    """Capture the screen and return (full_path, thumb_path)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"cap_{ts}.png"
    thumb_name = f"thumb_{ts}.jpg"

    full_path = SCREENSHOTS_DIR / filename
    thumb_path = SCREENSHOTS_DIR / thumb_name

    with mss.mss() as sct:
        monitor = REGION or sct.monitors[1]  # monitors[0] = all combined; [1] = primary
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    img.save(str(full_path), "PNG")
    thumb = img.copy()
    thumb.thumbnail(THUMB_SIZE, Image.LANCZOS)
    thumb.save(str(thumb_path), "JPEG", quality=75)

    return full_path, thumb_path


def trigger_capture(source: str = "hotkey") -> str | None:
    """
    Called by the hotkey listener or via API. Returns None on success or a
    reason string if the capture was skipped.
    """
    global _last_capture_ts

    if not _game_is_running():
        msg = f"[capture] Skipped ({source}) — {GAME_PROCESS} is not running"
        print(msg)
        return "game_not_running"

    now = time.monotonic()
    with _debounce_lock:
        if now - _last_capture_ts < DEBOUNCE_SECS:
            print(f"[capture] Debounced ({source}) — {DEBOUNCE_SECS}s not elapsed")
            return "debounced"
        _last_capture_ts = now

    try:
        full_path, thumb_path = _take_screenshot()
        capture_queue.put({
            "full": str(full_path),
            "thumb": str(thumb_path),
            "filename": full_path.name,
            "thumb_filename": thumb_path.name,
            "source": source,
        })
    except Exception as exc:
        capture_queue.put({"error": str(exc), "source": source})
    return None


def _hotkey_loop():
    try:
        import keyboard as kb
        kb.add_hotkey(HOTKEY, trigger_capture, args=("hotkey",))
        _stop_event.wait()
        kb.remove_all_hotkeys()
    except Exception:
        # The keyboard library can't intercept keys while a Windows game has
        # focus — use hotkey.ahk on the Windows side instead.
        print(f"[capture] In-WSL hotkey unavailable. "
              f"Run hotkey.ahk on Windows to use {HOTKEY.upper()} in-game.")


def start_listener():
    global _listener_thread
    if _listener_thread and _listener_thread.is_alive():
        return
    _stop_event.clear()
    _listener_thread = threading.Thread(target=_hotkey_loop, daemon=True, name="hotkey-listener")
    _listener_thread.start()
    print(f"[capture] Hotkey listener started — press {HOTKEY.upper()} to capture")


def stop_listener():
    _stop_event.set()
