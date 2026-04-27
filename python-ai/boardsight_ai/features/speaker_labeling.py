from __future__ import annotations

from boardsight_ai.config import AppConfig
from boardsight_ai.models import TranscriptResult, TranscriptSegment
from boardsight_ai.providers.speaker_directory import load_speaker_directory


def run(transcript_segments: list[TranscriptSegment], config: AppConfig) -> TranscriptResult:
    directory = load_speaker_directory(config.project_root)
    enriched_segments: list[TranscriptSegment] = []
    speaker_directory: list[dict] = []
    seen: set[str] = set()

    for segment in transcript_segments:
        profile = directory.get(segment.speaker, {"display_name": segment.speaker, "designation": "Participant"})
        labeled_speaker = f"{profile['display_name']} ({profile['designation']})"
        enriched_segments.append(
            TranscriptSegment(
                start=segment.start,
                end=segment.end,
                speaker=labeled_speaker,
                text=segment.text,
                confidence=segment.confidence,
            )
        )
        if labeled_speaker not in seen:
            speaker_directory.append(
                {
                    "speaker_id": segment.speaker,
                    "display_name": profile["display_name"],
                    "designation": profile["designation"],
                    "report_label": labeled_speaker,
                }
            )
            seen.add(labeled_speaker)

    full_text = "\n".join(f"[{segment.start:.1f}-{segment.end:.1f}] {segment.speaker}: {segment.text}" for segment in enriched_segments)
    return TranscriptResult(full_text=full_text, segments=enriched_segments, speaker_directory=speaker_directory)
