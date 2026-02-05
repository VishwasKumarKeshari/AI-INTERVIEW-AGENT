from __future__ import annotations

import threading

import pyttsx3


_engine = None
_lock = threading.Lock()


def _ensure_engine() -> None:
    """Lazily and safely initialize the TTS engine.

    On environments without audio support (e.g. Streamlit Cloud),
    initialization may fail; in that case we simply disable TTS.
    """
    global _engine
    if _engine is not None:
        return
    try:
        _engine = pyttsx3.init()
    except Exception:
        # Disable TTS gracefully when audio backends are unavailable.
        _engine = None


def speak_text(text: str) -> None:
    """
    Speak text using a local TTS engine (pyttsx3) when available.
    If initialization fails (e.g. in headless/cloud environments),
    this becomes a no-op so the app continues to work.
    """
    if not text.strip():
        return
    _ensure_engine()
    if _engine is None:
        return
    with _lock:
        _engine.say(text)
        _engine.runAndWait()


def speak_text_async(text: str) -> None:
    """
    Speak text in a background thread so the UI does not block.
    Use this when the interviewer reads questions aloud.
    """
    if not text.strip():
        return

    def _speak():
        try:
            speak_text(text)
        except Exception:
            pass

    thread = threading.Thread(target=_speak, daemon=True)
    thread.start()

