"""
Real-time Voice Activity Detection (VAD) for interview answers.
The answer window is capped at 60 seconds per question.
"""
from __future__ import annotations

import tempfile
import threading
import time
from typing import List, Optional

import numpy as np

# Threshold below which audio is considered silence (RMS of normalized samples).
SPEECH_THRESHOLD = 0.01
MAX_ANSWER_DURATION_SEC = 60
SILENCE_TIMEOUT_SEC = MAX_ANSWER_DURATION_SEC
NO_SPEECH_TIMEOUT_SEC = MAX_ANSWER_DURATION_SEC  # If candidate never speaks, advance after this.


class RealtimeVADState:
    """
    Thread-safe state shared between the audio callback and the main app.
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.last_speech_time: Optional[float] = None
        self.question_start_time: Optional[float] = None
        self.silence_timeout_triggered: bool = False
        self.audio_frames: List[np.ndarray] = []
        self.sample_rate: int = 16000
        self._has_ever_spoken: bool = False

    def reset_for_new_question(self) -> None:
        with self._lock:
            self.last_speech_time = None
            self.silence_timeout_triggered = False
            self.audio_frames = []
            self._has_ever_spoken = False
            self.question_start_time = time.time()

    def process_frame(self, samples: np.ndarray, sample_rate: int = 16000) -> None:
        """Process one audio frame: update VAD state and accumulate for transcription."""
        with self._lock:
            if self.silence_timeout_triggered:
                return
            now = time.time()
            self.sample_rate = sample_rate
            if self.question_start_time is not None:
                elapsed = now - self.question_start_time
                if elapsed >= MAX_ANSWER_DURATION_SEC:
                    self.silence_timeout_triggered = True
                    return
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            is_speech = rms > SPEECH_THRESHOLD

            if is_speech:
                self.last_speech_time = now
                self._has_ever_spoken = True
                self.audio_frames.append(samples.copy())
            else:
                if self._has_ever_spoken and self.last_speech_time is not None:
                    silence_duration = now - self.last_speech_time
                    if silence_duration >= SILENCE_TIMEOUT_SEC:
                        self.silence_timeout_triggered = True
                else:
                    if self.question_start_time is not None:
                        elapsed = now - self.question_start_time
                        if elapsed >= NO_SPEECH_TIMEOUT_SEC:
                            self.silence_timeout_triggered = True

    def pop_triggered_and_audio_path(self) -> tuple[bool, Optional[str]]:
        """
        If timeout was triggered, return (True, path_to_wav) for transcription.
        Otherwise (False, None). Clears state for next question.
        """
        with self._lock:
            triggered = self.silence_timeout_triggered
            path: Optional[str] = None
            if not triggered:
                return False, None
            if self.audio_frames and self.sample_rate > 0:
                try:
                    import soundfile as sf
                    arr = np.concatenate(self.audio_frames)
                    if arr.dtype != np.float32:
                        arr = arr.astype(np.float32)
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        sf.write(f.name, arr, self.sample_rate)
                        path = f.name
                except Exception:
                    path = None
            self.silence_timeout_triggered = False
            self.audio_frames = []
            return True, path

    def get_silence_seconds(self) -> float:
        """Seconds of continuous silence so far (0 if currently speaking)."""
        with self._lock:
            if not self._has_ever_spoken:
                return 0.0
            if self.last_speech_time is None:
                return 0.0
            return time.time() - self.last_speech_time

    def get_elapsed_seconds(self) -> float:
        """Seconds elapsed since the question started."""
        with self._lock:
            if self.question_start_time is None:
                return 0.0
            return time.time() - self.question_start_time

    def is_speaking(self) -> bool:
        """True if candidate spoke in the last 2 seconds (brief pause still counts as speaking)."""
        with self._lock:
            return self._has_ever_spoken and (
                self.last_speech_time is not None
                and (time.time() - self.last_speech_time) < 2.0
            )


_vad_state = RealtimeVADState()


def get_vad_state() -> RealtimeVADState:
    return _vad_state


def create_audio_frame_callback():
    """Create a callback for streamlit-webrtc that runs VAD on each frame."""
    state = get_vad_state()

    def callback(frame):
        import av
        samples = frame.to_ndarray()
        if samples.size > 0:
            if len(samples.shape) > 1:
                samples = samples.mean(axis=1)
            if samples.dtype == np.int16:
                samples = samples.astype(np.float32) / 32768.0
            state.process_frame(samples, getattr(frame, "sample_rate", 16000))
        return frame

    return callback
