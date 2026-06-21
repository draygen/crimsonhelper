"""
Detects whether the Crimson Desert game process is running.
Results are cached for TTL seconds so back-to-back captures pay zero cost.
Works in WSL (calls tasklist.exe) and falls back to pgrep on native Linux.
"""
import subprocess
import threading
import time

_TTL = 5.0  # seconds between OS process-list queries
_lock = threading.Lock()
_cached_result: bool = True  # fail-open default
_cached_at: float = 0.0


def is_running(process_name: str) -> bool:
    """Return True if the named Windows process is running. Thread-safe."""
    global _cached_result, _cached_at
    now = time.monotonic()
    with _lock:
        if now - _cached_at < _TTL:
            return _cached_result
        result = _detect(process_name)
        _cached_result = result
        _cached_at = now
        return result


def _detect(process_name: str) -> bool:
    # WSL / Windows: tasklist.exe is always available
    try:
        r = subprocess.run(
            ["tasklist.exe", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            return process_name.lower() in r.stdout.lower()
    except FileNotFoundError:
        pass  # not on Windows / WSL
    except Exception:
        pass

    # Native Linux fallback: strip .exe suffix for pgrep
    bare = process_name.removesuffix(".exe").removesuffix(".EXE")
    try:
        r = subprocess.run(
            ["pgrep", "-ix", bare],
            capture_output=True, timeout=3,
        )
        return r.returncode == 0
    except Exception:
        return True  # can't determine → allow captures
