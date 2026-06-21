"""
Voice command listener and dispatcher.
Runs in a daemon thread; parsed commands are dispatched to the action registry.
Uses SpeechRecognition (Google Web Speech by default).
"""
import json
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Callable

try:
    import speech_recognition as sr
    _sr_available = True
except ImportError:
    _sr_available = False

try:
    import pyttsx3
    _tts_engine = pyttsx3.init()
    _tts_engine.setProperty("rate", 160)
    _tts_available = True
except Exception:
    _tts_available = False

_root = Path(__file__).resolve().parents[1]
with open(_root / "config.json") as _f:
    _cfg = json.load(_f)

_active = False
_stop_evt = threading.Event()
_thread: threading.Thread | None = None

# Registered by main.py after DB session factory is available
_dispatch: Callable[[str], str] | None = None
_ws_broadcast: Callable[[dict], None] | None = None


def register_dispatch(fn: Callable[[str], str]):
    global _dispatch
    _dispatch = fn


def register_broadcast(fn: Callable[[dict], None]):
    global _ws_broadcast
    _ws_broadcast = fn


def speak(text: str):
    if _tts_available:
        try:
            _tts_engine.say(text)
            _tts_engine.runAndWait()
        except Exception:
            pass


def _handle_command(cmd: str) -> str:
    """Parse and route a voice command. Returns a result string."""
    cmd = cmd.lower().strip()

    if _dispatch:
        result = _dispatch(cmd)
        if result:
            return result

    if re.search(r"\bopen dashboard\b", cmd):
        import webbrowser
        webbrowser.open(f"http://localhost:{_cfg.get('server_port', 8000)}")
        return "Opening dashboard."

    if re.search(r"\bcapture\b|\bscreenshot\b|\bsave screen\b", cmd):
        from capture import trigger_capture
        trigger_capture(source="voice")
        return "Capturing screen."

    if re.search(r"\bstop listening\b|\bquiet\b|\bsilence\b", cmd):
        stop_listener()
        return "Voice commands paused."

    return f"Command not recognised: {cmd}"


def _listen_loop():
    global _active
    if not _sr_available:
        print("[voice] SpeechRecognition not installed — voice disabled")
        return

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    print("[voice] Listening for commands...")
    while not _stop_evt.is_set():
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = recognizer.recognize_google(audio)
            print(f"[voice] Heard: {text}")
            result = _handle_command(text)
            speak(result)
            if _ws_broadcast:
                _ws_broadcast({
                    "type": "voice_command",
                    "command": text,
                    "result": result,
                    "ts": datetime.utcnow().isoformat(),
                })
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except sr.RequestError as exc:
            print(f"[voice] Speech API error: {exc}")
            _stop_evt.wait(5)
        except Exception as exc:
            print(f"[voice] Error: {exc}")
            _stop_evt.wait(2)

    _active = False
    print("[voice] Listener stopped.")


def start_listener():
    global _thread, _active
    if _active:
        return
    _stop_evt.clear()
    _active = True
    _thread = threading.Thread(target=_listen_loop, daemon=True, name="voice-listener")
    _thread.start()


def stop_listener():
    global _active
    _active = False
    _stop_evt.set()


def is_active() -> bool:
    return _active


def is_available() -> bool:
    return _sr_available
