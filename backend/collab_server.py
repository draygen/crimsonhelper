#!/usr/bin/env python3
"""
Collab Server bundled with CrimsonHelper.
Real-time collaboration hub for Claude agents.
REST API + Server-Sent Events. Port 7777.

Original hub lives at /mnt/c/projects/.collab/collab-server.py
This copy is self-contained so crimsonhelper ships with it.
"""
import json, os, time, uuid, threading, signal, sys, queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Use the shared .collab directory so both copies share state
COLLAB_DIR = Path("/mnt/c/projects/.collab")
MSG_DIR    = COLLAB_DIR / "messages"
TASK_DIR   = COLLAB_DIR / "tasks"
LOG_FILE   = COLLAB_DIR / "activity.log"
CTX_FILE   = COLLAB_DIR / "shared" / "context.md"
PORT       = 7777
AGENTS     = ("local", "remote")

subscribers: dict[str, list[queue.Queue]] = {"local": [], "remote": []}
sub_lock = threading.Lock()

_server_instance: HTTPServer | None = None


def ts():
    return datetime.now().isoformat()

def log(entry: dict):
    line = json.dumps({"ts": ts(), **entry})
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def ensure_dirs():
    for a in AGENTS:
        (MSG_DIR / a).mkdir(parents=True, exist_ok=True)
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    (COLLAB_DIR / "shared").mkdir(parents=True, exist_ok=True)

# ── Messages ───────────────────────────────────────────────────────────────────

def push_sse(agent: str, msg: dict):
    with sub_lock:
        dead = []
        for q in subscribers.get(agent, []):
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            subscribers[agent].remove(q)

def save_message(to: str, content: str, from_: str, msg_type="message", extra=None) -> dict:
    msg_id = uuid.uuid4().hex[:8]
    now = ts()
    msg = {"id": msg_id, "ts": now, "from": from_, "to": to,
           "type": msg_type, "content": content, **(extra or {})}
    path = MSG_DIR / to / f"{now}_{msg_id}.json"
    path.write_text(json.dumps(msg, indent=2))
    log({"event": "msg", "id": msg_id, "from": from_, "to": to, "type": msg_type})
    push_sse(to, msg)
    return msg

def pop_messages(agent: str, clear=True) -> list:
    inbox = MSG_DIR / agent
    msgs = []
    for f in sorted(inbox.glob("*.json")):
        try:
            msgs.append(json.loads(f.read_text()))
            if clear:
                f.unlink()
        except Exception:
            pass
    return msgs

# ── Tasks ──────────────────────────────────────────────────────────────────────

def create_task(description: str, from_: str, priority="normal", assigned_to="remote") -> dict:
    task_id = uuid.uuid4().hex[:8]
    task = {"id": task_id, "ts": ts(), "from": from_, "assigned_to": assigned_to,
            "description": description, "status": "pending", "priority": priority}
    (TASK_DIR / f"{task_id}.json").write_text(json.dumps(task, indent=2))
    log({"event": "task_created", "id": task_id})
    for a in AGENTS:
        save_message(a, f"New task [{task_id}] → {assigned_to}: {description}",
                     "system", "task_notify", {"task_id": task_id})
    return task

def update_task(task_id: str, **updates) -> dict | None:
    path = TASK_DIR / f"{task_id}.json"
    if not path.exists():
        return None
    task = json.loads(path.read_text())
    task.update(updates)
    task["updated"] = ts()
    path.write_text(json.dumps(task, indent=2))
    log({"event": "task_updated", "id": task_id, **updates})
    for a in AGENTS:
        push_sse(a, {"type": "task_update", "task": task})
    return task

def list_tasks(status=None) -> list:
    tasks = []
    for f in sorted(TASK_DIR.glob("*.json")):
        try:
            t = json.loads(f.read_text())
            if status is None or t.get("status") == status:
                tasks.append(t)
        except Exception:
            pass
    return tasks

# ── HTTP Handler ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        path = p.path.rstrip("/")
        qs = parse_qs(p.query)

        if path == "/status":
            with sub_lock:
                subs = {k: len(v) for k, v in subscribers.items()}
            self.send_json({
                "status": "running", "ts": ts(),
                "live_connections": subs,
                "pending": {a: len(list((MSG_DIR/a).glob("*.json"))) for a in AGENTS},
                "tasks": {s: len(list_tasks(s)) for s in ("pending","in_progress","done")}
            })

        elif path.startswith("/poll/"):
            agent = path.rsplit("/", 1)[-1]
            if agent not in AGENTS:
                return self.send_json({"error": "unknown agent"}, 400)
            clear = qs.get("clear", ["true"])[0].lower() != "false"
            msgs = pop_messages(agent, clear)
            self.send_json({"messages": msgs, "count": len(msgs)})

        elif path.startswith("/stream/"):
            agent = path.rsplit("/", 1)[-1]
            if agent not in AGENTS:
                return self.send_json({"error": "unknown agent"}, 400)
            self._sse_loop(agent)

        elif path == "/tasks":
            sf = qs.get("status", [None])[0]
            self.send_json({"tasks": list_tasks(sf)})

        elif path.startswith("/task/"):
            tid = path.rsplit("/", 1)[-1]
            f = TASK_DIR / f"{tid}.json"
            self.send_json(json.loads(f.read_text()) if f.exists() else {"error": "not found"},
                           200 if f.exists() else 404)

        elif path == "/context":
            self.send_json({"content": CTX_FILE.read_text() if CTX_FILE.exists() else ""})

        elif path == "/log":
            n = int(qs.get("n", [50])[0])
            lines = []
            if LOG_FILE.exists():
                raw = LOG_FILE.read_text().splitlines()
                lines = [json.loads(l) for l in raw[-n:] if l.strip()]
            self.send_json({"log": lines})

        else:
            self.send_json({"error": "not found"}, 404)

    def _sse_loop(self, agent: str):
        q: queue.Queue = queue.Queue(maxsize=100)
        with sub_lock:
            subscribers[agent].append(q)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        for msg in pop_messages(agent, clear=True):
            self._sse_write(msg)

        try:
            while True:
                try:
                    msg = q.get(timeout=20)
                    self._sse_write(msg)
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with sub_lock:
                try:
                    subscribers[agent].remove(q)
                except ValueError:
                    pass

    def _sse_write(self, msg: dict):
        data = json.dumps(msg)
        self.wfile.write(f"data: {data}\n\n".encode())
        self.wfile.flush()

    def do_POST(self):
        p = urlparse(self.path)
        path = p.path.rstrip("/")
        body = self.read_body()

        if path == "/send":
            to    = body.get("to")
            from_ = body.get("from", "unknown")
            if to not in AGENTS:
                return self.send_json({"error": "to must be local or remote"}, 400)
            msg = save_message(to, body.get("content", ""), from_,
                               body.get("type", "message"), body.get("meta"))
            self.send_json({"ok": True, "message": msg})

        elif path == "/task/create":
            task = create_task(body.get("description", ""), body.get("from", "unknown"),
                               body.get("priority", "normal"), body.get("assigned_to", "remote"))
            self.send_json({"ok": True, "task": task})

        elif path == "/task/update":
            tid = body.pop("id", None)
            if not tid:
                return self.send_json({"error": "id required"}, 400)
            task = update_task(tid, **body)
            self.send_json({"ok": True, "task": task} if task else {"error": "not found"},
                           200 if task else 404)

        elif path == "/context":
            content = body.get("content", "")
            from_   = body.get("from", "unknown")
            if body.get("action") == "append":
                existing = CTX_FILE.read_text() if CTX_FILE.exists() else ""
                content  = existing + f"\n\n---\n*{from_} @ {ts()}*\n\n" + content
            CTX_FILE.write_text(content)
            log({"event": "context_updated", "from": from_})
            for a in AGENTS:
                push_sse(a, {"type": "context_update", "from": from_})
            self.send_json({"ok": True})

        else:
            self.send_json({"error": "not found"}, 404)


def run_server():
    global _server_instance
    ensure_dirs()
    log({"event": "server_start", "port": PORT, "source": "crimsonhelper"})
    _server_instance = HTTPServer(("0.0.0.0", PORT), Handler)
    _server_instance.daemon_threads = True
    print(f"[collab-server] Listening on :{PORT}", flush=True)
    _server_instance.serve_forever()


def start_in_thread() -> threading.Thread:
    t = threading.Thread(target=run_server, daemon=True, name="collab-server")
    t.start()
    return t


def stop():
    if _server_instance:
        _server_instance.shutdown()


if __name__ == "__main__":
    run_server()
