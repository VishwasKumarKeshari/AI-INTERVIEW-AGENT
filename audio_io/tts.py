from __future__ import annotations

import threading

import pyttsx3


_engine = pyttsx3.init()
_lock = threading.Lock()


def speak_text(text: str) -> None:
    """
    Speak text using a local TTS engine (pyttsx3).
    Runs synchronously; for Streamlit we recommend calling this
    outside of the main request/response path if used.
    """
    if not text.strip():
        return
    with _lock:
        _engine.say(text)
        _engine.runAndWait()

