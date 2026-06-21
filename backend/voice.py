"""
Voice command listener and dispatcher.
Runs in a daemon thread; parsed commands are dispatched to the action registry.
Uses SpeechRecognition (Google Web Speech by default).
"""
import ctypes
import json
import os
import re
import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Callable

# ── Silence ALSA + JACK before any audio library loads ───────────────────────
# WSL2 has no audio device; pyaudio probes every ALSA/JACK backend and floods
# stderr with dozens of "Unknown PCM" / "Cannot connect to server" lines.
# Strategy: set ALSA C-level error handler to a no-op (must hold a reference
# so GC doesn't collect it before ALSA next needs it), then wrap the pyaudio
# device probe in an fd-level stderr redirect to catch JACK's direct writes.
try:
    _asound = ctypes.cdll.LoadLibrary("libasound.so.2")
    _alsa_cb_t = ctypes.CFUNCTYPE(
        None, ctypes.c_char_p, ctypes.c_int,
        ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
    )
    _alsa_cb = _alsa_cb_t(lambda *_: None)   # held at module scope — must not be GC'd
    _asound.snd_lib_error_set_handler(_alsa_cb)
except Exception:
    pass


def _probe_audio() -> bool:
    """Return True if at least one audio input device exists, silently."""
    try:
        import pyaudio
    except ImportError:
        return False

    # Redirect fd 2 at the OS level so JACK's direct stderr writes are swallowed
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        pa = pyaudio.PyAudio()
        has_input = any(
            pa.get_device_info_by_index(i).get("maxInputChannels", 0) > 0
            for i in range(pa.get_device_count())
        )
        pa.terminate()
        return has_input
    except Exception:
        return False
    finally:
        sys.stderr.flush()
        os.dup2(saved, 2)
        os.close(saved)


# ── Speech recognition availability ──────────────────────────────────────────
try:
    import speech_recognition as sr
    _sr_available = _probe_audio()
    if not _sr_available:
        print("[voice] No audio input device found — voice commands disabled")
except ImportError:
    _sr_available = False

# ── TTS ───────────────────────────────────────────────────────────────────────
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
    cmd = cmd.lower().strip()

    if _dispatch:
        result = _dispatch(cmd)
        if result:
            return result

    if re.search(r"\bopen dashboard\b", cmd):
        import webbrowser
        webbrowser.open(f"http://localhost:{_cfg.get('server_port', 8765)}")
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
    try:
        if not _sr_available:
            print("[voice] Voice unavailable — skipping listener")
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

    except Exception as exc:
        print(f"[voice] Listener startup failed: {exc}")
    finally:
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
