"""
Capture → OCR → Classify → Persist → Broadcast pipeline.
Drains capture_queue in a background thread.
"""
import threading
from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from capture import capture_queue
from ocr import extract_text
from classifier import classify
from db.models import Screenshot, Quest, LootEntry, NPC
import collab

_broadcast: Callable[[dict], None] | None = None
_db_factory: Callable[[], Session] | None = None
_stop_evt = threading.Event()
_thread: threading.Thread | None = None


def register_broadcast(fn: Callable[[dict], None]):
    global _broadcast
    _broadcast = fn


def register_db_factory(fn: Callable[[], Session]):
    global _db_factory
    _db_factory = fn


def _emit(payload: dict):
    if _broadcast:
        _broadcast(payload)


def _process(job: dict):
    if "error" in job:
        _emit({"type": "capture_error", "error": job["error"], "ts": datetime.utcnow().isoformat()})
        return

    _emit({"type": "capture_started", "filename": job["filename"], "ts": datetime.utcnow().isoformat()})

    text = extract_text(job["full"])
    result = classify(text)

    db = _db_factory()
    try:
        # Always save the screenshot
        shot = Screenshot(
            filename=job["filename"],
            thumbnail=job["thumb_filename"],
            category=result.category,
            ocr_text=text,
            zone=result.zone,
            captured_at=datetime.utcnow(),
        )
        db.add(shot)
        db.flush()

        saved = {"screenshot_id": shot.id, "category": result.category}

        if result.category == "quest" and result.title:
            q = Quest(
                title=result.title,
                description=result.description,
                status=result.quest_status,
                zone=result.zone,
                screenshot_id=shot.id,
                raw_ocr_text=text,
                captured_at=datetime.utcnow(),
            )
            db.add(q)
            db.flush()
            saved["quest_id"] = q.id
            saved["quest_title"] = q.title
            saved["quest_status"] = q.status
            collab.send_quest(q.title, q.description or "", result.zone)

        elif result.category == "loot" and result.items:
            for item_str in result.items:
                parts = item_str.rsplit(" x", 1)
                name = parts[0].strip()
                qty = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 1
                if name:
                    db.add(LootEntry(
                        item_name=name,
                        quantity=qty,
                        zone=result.zone,
                        screenshot_id=shot.id,
                        captured_at=datetime.utcnow(),
                    ))
            saved["items"] = result.items
            collab.send_loot(result.items, result.zone)

        elif result.category == "npc":
            existing = db.query(NPC).filter(NPC.name == result.npc_name).first() if result.npc_name else None
            if existing:
                existing.dialogue = result.description
                existing.last_seen = datetime.utcnow()
                existing.screenshot_id = shot.id
                if result.zone and not existing.zone:
                    existing.zone = result.zone
            else:
                npc = NPC(
                    name=result.npc_name or "Unknown NPC",
                    zone=result.zone,
                    dialogue=result.description,
                    screenshot_id=shot.id,
                )
                db.add(npc)
            saved["npc_name"] = result.npc_name

        db.commit()
        collab.send_screenshot(job["filename"], result.category, text)

        _emit({
            "type": "ocr_complete",
            "ts": datetime.utcnow().isoformat(),
            **saved,
        })

    except Exception as exc:
        db.rollback()
        _emit({"type": "pipeline_error", "error": str(exc), "ts": datetime.utcnow().isoformat()})
    finally:
        db.close()


def _worker():
    import queue as _queue
    print("[pipeline] Worker started")
    while not _stop_evt.is_set():
        try:
            job = capture_queue.get(timeout=1)
        except _queue.Empty:
            continue
        try:
            _process(job)
        except Exception as exc:
            print(f"[pipeline] Unhandled error: {exc}")
    print("[pipeline] Worker stopped")


def start():
    global _thread
    _stop_evt.clear()
    _thread = threading.Thread(target=_worker, daemon=True, name="pipeline-worker")
    _thread.start()


def stop():
    _stop_evt.set()
