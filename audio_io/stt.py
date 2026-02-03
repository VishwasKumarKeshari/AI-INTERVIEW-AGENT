from __future__ import annotations

from typing import Optional

import whisper

from config import audio_config


_model_cache: Optional[whisper.Whisper] = None


def _get_model() -> whisper.Whisper:
    global _model_cache
    if _model_cache is None:
        _model_cache = whisper.load_model(audio_config.whisper_model)
    return _model_cache


def transcribe_audio_file(file_path: str) -> str:
    """
    Transcribe an audio file using Whisper.
    """
    model = _get_model()
    result = model.transcribe(file_path)
    return result.get("text", "").strip()

