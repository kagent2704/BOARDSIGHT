from __future__ import annotations

from functools import lru_cache

from boardsight_ai.config import AppConfig
from boardsight_ai.models import AttentionSentimentResult, DecisionMoment, MeetingScores, SpeakerDominanceResult, WorkflowModel
from boardsight_ai.providers.runtime import optional_import


IMPACT_LABELS = ["high meeting impact", "medium meeting impact", "low meeting impact"]
PRODUCTIVITY_LABELS = ["high meeting productivity", "medium meeting productivity", "low meeting productivity"]
READINESS_LABELS = ["high execution readiness", "medium execution readiness", "low execution readiness"]
ALL_SCORE_LABELS = IMPACT_LABELS + PRODUCTIVITY_LABELS + READINESS_LABELS


@lru_cache(maxsize=2)
def _classifier(model_name: str):
    transformers = optional_import("transformers")
    if transformers is None:
        return None
    try:
        return transformers.pipeline("zero-shot-classification", model=model_name)
    except Exception:
        return None


def _model_score(text: str, labels: list[str], config: AppConfig) -> tuple[float, str]:
    classifier = _classifier(config.text_classifier_model)
    if classifier is None:
        return 0.0, "model-unavailable"
    try:
        output = classifier(text, labels, multi_label=False)
    except Exception:
        return 0.0, "model-inference-failed"
    label = str(output["labels"][0])
    confidence = float(output["scores"][0])
    level = 100.0 if label.startswith("high") else 65.0 if label.startswith("medium") else 30.0
    return round(level * confidence, 2), f"{label}:{confidence:.3f}"


def _model_scores(text: str, config: AppConfig) -> dict[str, tuple[float, str]]:
    classifier = _classifier(config.text_classifier_model)
    if classifier is None:
        return {
            "impact": (0.0, "model-unavailable"),
            "productivity": (0.0, "model-unavailable"),
            "readiness": (0.0, "model-unavailable"),
        }
    try:
        output = classifier(text, ALL_SCORE_LABELS, multi_label=True)
    except Exception:
        return {
            "impact": _model_score(text, IMPACT_LABELS, config),
            "productivity": _model_score(text, PRODUCTIVITY_LABELS, config),
            "readiness": _model_score(text, READINESS_LABELS, config),
        }

    label_scores = dict(zip(output.get("labels", []), output.get("scores", [])))

    def pick(labels: list[str]) -> tuple[float, str]:
        label = max(labels, key=lambda item: float(label_scores.get(item, 0.0)))
        confidence = float(label_scores.get(label, 0.0))
        level = 100.0 if label.startswith("high") else 65.0 if label.startswith("medium") else 30.0
        return round(level * confidence, 2), f"{label}:{confidence:.3f}"

    return {
        "impact": pick(IMPACT_LABELS),
        "productivity": pick(PRODUCTIVITY_LABELS),
        "readiness": pick(READINESS_LABELS),
    }


def run(
    speaker_dominance: SpeakerDominanceResult,
    decision_moments: list[DecisionMoment],
    attention_sentiment: AttentionSentimentResult,
    workflow_model: WorkflowModel,
    config: AppConfig,
) -> MeetingScores:
    evidence_text = " ".join(
        [
            "Decisions:",
            " ".join(f"{item.label} {item.confidence:.3f} {item.text}" for item in decision_moments),
            "Workflow:",
            " ".join(str(item) for item in workflow_model.prioritized_decisions[:5]),
            "Attention:",
            str(attention_sentiment.cognitive_rating),
            "Speakers:",
            " ".join(str(item) for item in speaker_dominance.speakers[:5]),
        ]
    )[:3000]

    scores = _model_scores(evidence_text or "empty meeting analysis", config)
    impact_score, impact_label = scores["impact"]
    productivity_score, productivity_label = scores["productivity"]
    execution_readiness, readiness_label = scores["readiness"]
    speaker_rating = {
        item["speaker"]: round(float(item.get("dominance_ratio", 0.0)), 2)
        for item in speaker_dominance.speakers
    }
    cognitive_rating = {
        "meeting_focus": attention_sentiment.cognitive_rating["focus"],
        "meeting_clarity": attention_sentiment.cognitive_rating["clarity"],
        "overload_risk": attention_sentiment.cognitive_rating["overload_risk"],
        "source": ",".join(attention_sentiment.model_sources) or "model-unavailable",
    }
    conclusion = (
        f"Model-backed meeting assessment: impact={impact_label}; "
        f"productivity={productivity_label}; readiness={readiness_label}."
    )

    return MeetingScores(
        impact_score=impact_score,
        productivity_score=productivity_score,
        execution_readiness=execution_readiness,
        speaker_rating=speaker_rating,
        cognitive_rating=cognitive_rating,
        meeting_conclusion=conclusion,
    )
