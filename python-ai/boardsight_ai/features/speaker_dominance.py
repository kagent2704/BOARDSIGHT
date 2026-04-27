from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from boardsight_ai.config import AppConfig
from boardsight_ai.models import SpeakerDominanceResult, TranscriptSegment
from boardsight_ai.providers.face_id import detect_known_faces
from boardsight_ai.providers.vision import face_capabilities


def _visual_active_speakers(video_path: Path) -> tuple[list[dict], list[dict]]:
    encoding_identities = detect_known_faces(video_path)
    return [], encoding_identities


def run(transcript_segments: list[TranscriptSegment], config: AppConfig, video_path: Path | None = None) -> SpeakerDominanceResult:
    talk_times: dict[str, float] = defaultdict(float)
    timeline: list[dict] = []

    for segment in transcript_segments:
        duration = max(0.0, segment.end - segment.start)
        talk_times[segment.speaker] += duration
        timeline.append(
            {
                "start": segment.start,
                "end": segment.end,
                "speaker": segment.speaker,
                "source": "audio-dominance",
            }
        )

    total = sum(talk_times.values()) or 1.0
    visual_timeline, visual_identities = (
        ([], detect_known_faces(video_path, max_samples=config.max_face_samples))
        if video_path
        else ([], [])
    )
    speakers = [
        {
            "speaker": speaker,
            "talk_time_sec": round(talk_time, 2),
            "dominance_ratio": round((talk_time / total) * 100, 2),
            "face_recognition_ready": face_capabilities()["face_recognition"],
        }
        for speaker, talk_time in sorted(talk_times.items(), key=lambda item: item[1], reverse=True)
    ]

    return SpeakerDominanceResult(
        speakers=speakers,
        active_speaker_timeline=timeline + visual_timeline,
        visual_identities=visual_identities,
    )
