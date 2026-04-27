from __future__ import annotations

from functools import lru_cache

from boardsight_ai.config import AppConfig
from boardsight_ai.models import DecisionMoment, TranscriptSegment
from boardsight_ai.providers.runtime import optional_import


DECISION_LABELS = [
    "decision",
    "approval",
    "action item",
    "follow up",
    "commitment",
    "discussion only",
]


def seconds_to_timestamp(value: float) -> str:
    minutes = int(value // 60)
    seconds = int(value % 60)
    return f"{minutes:02d}:{seconds:02d}"


@lru_cache(maxsize=2)
def _classifier(model_name: str):
    transformers = optional_import("transformers")
    if transformers is None:
        return None

    try:
        return transformers.pipeline("zero-shot-classification", model=model_name)
    except Exception:
        return None


def _classify(text: str, config: AppConfig) -> tuple[str, float] | None:
    classifier = _classifier(config.text_classifier_model)
    if classifier is None:
        return None

    try:
        output = classifier(text, DECISION_LABELS, multi_label=False)
    except Exception:
        return None

    labels = output.get("labels", []) if isinstance(output, dict) else []
    scores = output.get("scores", []) if isinstance(output, dict) else []
    if not labels or not scores:
        return None
    return str(labels[0]), float(scores[0])


def _classify_many(texts: list[str], config: AppConfig) -> list[tuple[str, float] | None]:
    classifier = _classifier(config.text_classifier_model)
    if classifier is None:
        return [None for _ in texts]

    try:
        outputs = classifier(texts, DECISION_LABELS, multi_label=False, batch_size=8)
    except Exception:
        return [_classify(text, config) for text in texts]

    if isinstance(outputs, dict):
        outputs = [outputs]

    results: list[tuple[str, float] | None] = []
    for output in outputs:
        labels = output.get("labels", []) if isinstance(output, dict) else []
        scores = output.get("scores", []) if isinstance(output, dict) else []
        results.append((str(labels[0]), float(scores[0])) if labels and scores else None)
    return results


def run(transcript_segments: list[TranscriptSegment], config: AppConfig) -> tuple[list[DecisionMoment], list[str]]:
    warnings: list[str] = []
    if _classifier(config.text_classifier_model) is None:
        return [], [f"Decision detection unavailable: transformer classifier '{config.text_classifier_model}' is not loaded."]

    events: list[DecisionMoment] = []
    event_index = 1
    classifications = _classify_many([segment.text for segment in transcript_segments], config)
    for segment, classification in zip(transcript_segments, classifications):
        if classification is None:
            warnings.append("Decision detection skipped one segment because model inference failed.")
            continue

        label, confidence = classification
        if label == "discussion only":
            continue

        normalized_label = "action" if label == "action item" else "follow-up" if label == "follow up" else label
        events.append(
            DecisionMoment(
                event_id=f"DM-{event_index}",
                timestamp=seconds_to_timestamp(segment.start),
                speaker=segment.speaker,
                text=segment.text,
                confidence=round(confidence, 3),
                label=normalized_label,
                evidence=[f"zero-shot-classifier:{config.text_classifier_model}:{label}:{confidence:.3f}"],
            )
        )
        event_index += 1

    return events, warnings
