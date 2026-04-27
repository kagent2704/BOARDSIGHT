from __future__ import annotations

import os
from pathlib import Path

from boardsight_ai.config import AppConfig

from .runtime import optional_import

_DIARIZER = None


def _get_diarizer(config: AppConfig):
    global _DIARIZER
    if _DIARIZER is not None:
        return _DIARIZER

    pyannote_audio = optional_import("pyannote.audio")
    if pyannote_audio is None:
        return None

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not token:
        return None

    try:
        pipeline_class = pyannote_audio.Pipeline
        _DIARIZER = pipeline_class.from_pretrained("pyannote/speaker-diarization-3.1", token=token)
        return _DIARIZER
    except Exception:
        return None


def diarize_audio(audio_path: Path, config: AppConfig) -> list[dict]:
    diarizer = _get_diarizer(config)
    if diarizer is None:
        return []

    try:
        diarization = diarizer(str(audio_path))
        annotation = getattr(diarization, "speaker_diarization", diarization)
        segments: list[dict] = []
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            segments.append(
                {
                    "start": float(turn.start),
                    "end": float(turn.end),
                    "speaker": str(speaker),
                }
            )
        return segments
    except Exception:
        return []
