from __future__ import annotations

from functools import lru_cache

from boardsight_ai.config import AppConfig
from boardsight_ai.models import DecisionMoment, TranscriptSegment, VisualArtifact, WorkflowModel
from boardsight_ai.providers.runtime import optional_import


STAGE_LABELS = ["observe", "discuss", "evaluate", "decide", "assign"]
TASK_LABELS = ["decision record", "governance update", "owner alignment", "follow up", "impact checkpoint"]
BOTTLENECK_LABELS = [
    "missing owner assignment",
    "weak decision closure",
    "insufficient evidence capture",
    "unclear execution path",
    "no major workflow bottleneck",
]

STAGE_KEYWORDS = {
    "observe": ("agenda", "opening", "kickoff", "intro", "update"),
    "evaluate": ("risk", "blocker", "issue", "review", "evaluate", "concern"),
    "decide": ("approve", "approved", "decide", "decision", "agree", "resolved"),
    "assign": ("owner", "will", "follow up", "next step", "by friday", "assign"),
}


@lru_cache(maxsize=2)
def _classifier(model_name: str):
    transformers = optional_import("transformers")
    if transformers is None:
        return None
    try:
        return transformers.pipeline("zero-shot-classification", model=model_name)
    except Exception:
        return None


def _classify(text: str, labels: list[str], config: AppConfig) -> tuple[str, float] | None:
    classifier = _classifier(config.text_classifier_model)
    if classifier is None:
        return None
    try:
        output = classifier(text, labels, multi_label=False)
    except Exception:
        return None
    output_labels = output.get("labels", []) if isinstance(output, dict) else []
    scores = output.get("scores", []) if isinstance(output, dict) else []
    if not output_labels or not scores:
        return None
    return str(output_labels[0]), float(scores[0])


def _classify_many(texts: list[str], labels: list[str], config: AppConfig) -> list[tuple[str, float] | None]:
    classifier = _classifier(config.text_classifier_model)
    if classifier is None:
        return [None for _ in texts]
    try:
        outputs = classifier(texts, labels, multi_label=False, batch_size=8)
    except Exception:
        return [_classify(text, labels, config) for text in texts]
    if isinstance(outputs, dict):
        outputs = [outputs]

    results: list[tuple[str, float] | None] = []
    for output in outputs:
        output_labels = output.get("labels", []) if isinstance(output, dict) else []
        scores = output.get("scores", []) if isinstance(output, dict) else []
        results.append((str(output_labels[0]), float(scores[0])) if output_labels and scores else None)
    return results


def _time_to_seconds(timestamp: str) -> int:
    parts = timestamp.split(":")
    if len(parts) != 2:
        return 0
    return int(parts[0]) * 60 + int(parts[1])


def _overlapping_artifacts(timestamp: float, visual_artifacts: list[VisualArtifact]) -> list[VisualArtifact]:
    return [artifact for artifact in visual_artifacts if artifact.start_time <= timestamp <= artifact.end_time]


def _sample_segments(transcript_segments: list[TranscriptSegment], limit: int) -> list[TranscriptSegment]:
    if len(transcript_segments) <= limit:
        return transcript_segments
    step = max(1, len(transcript_segments) // limit)
    return transcript_segments[::step][:limit]


def _priority(moment: DecisionMoment, artifacts: list[VisualArtifact], config: AppConfig) -> tuple[float, list[str]]:
    labels = ["high impact decision", "medium impact decision", "low impact decision"]
    classification = _classify(moment.text, labels, config)
    if classification is None:
        return 0.0, [f"priority-classifier-unavailable:{config.text_classifier_model}"]
    label, score = classification
    base = {
        "high impact decision": 92.0,
        "medium impact decision": 68.0,
        "low impact decision": 38.0,
    }[label]
    evidence = [f"zero-shot-priority:{label}:{score:.3f}"]
    if artifacts:
        artifact_support = sum(artifact.confidence for artifact in artifacts) / len(artifacts)
        base = (base + artifact_support * 100.0) / 2.0
        evidence.append("visual-model-support:" + ",".join(artifact.artifact_id for artifact in artifacts))
    return round(base * score, 2), evidence


def _make_task(moment: DecisionMoment, priority_score: float, order: int, config: AppConfig) -> dict:
    classification = _classify(moment.text, TASK_LABELS, config)
    task_type, task_confidence = classification if classification is not None else ("model-unavailable", 0.0)
    compact_text = " ".join(moment.text.split())
    title = compact_text[:96]
    due_hint = ""
    for token in (" by ", " before ", " on "):
        lowered = compact_text.lower()
        marker = lowered.find(token)
        if marker >= 0:
            due_hint = compact_text[marker + 1 :][:48]
            break
    return {
        "task_id": f"{moment.event_id}-T1",
        "decision_id": moment.event_id,
        "title": title,
        "owner": moment.speaker,
        "priority_score": round(priority_score, 2),
        "execution_order": order,
        "task_type": task_type.replace(" ", "-"),
        "notes": f"Suggested workflow lane: {task_type}. Confidence {task_confidence:.3f}. {due_hint}".strip(),
    }


def _heuristic_stage_name(text: str, position: int, total: int) -> str:
    lowered = text.lower()
    for stage_name, keywords in STAGE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return stage_name
    if position == 0:
        return "observe"
    if position >= max(1, total - 1):
        return "assign"
    return "discuss"


def _heuristic_priority(moment: DecisionMoment, artifacts: list[VisualArtifact]) -> tuple[float, list[str]]:
    lowered = moment.text.lower()
    score = 58.0
    evidence = ["heuristic-priority"]
    if moment.label.lower().startswith("decision"):
        score += 10.0
        evidence.append("decision-label")
    if moment.label.lower().startswith("action"):
        score += 8.0
        evidence.append("action-label")
    if any(token in lowered for token in ("approve", "approved", "board", "budget", "must", "deadline", "by ")):
        score += 12.0
        evidence.append("high-impact-keywords")
    if artifacts:
        score += min(12.0, sum(artifact.confidence for artifact in artifacts) * 4.0)
        evidence.append("visual-support")
    if moment.evidence:
        score += min(6.0, len(moment.evidence) * 2.0)
        evidence.append("text-evidence")
    return min(round(score, 2), 99.0), evidence


def _fallback_task(moment: DecisionMoment, priority_score: float, order: int) -> dict:
    compact_text = " ".join(moment.text.split())
    return {
        "task_id": f"{moment.event_id}-T1",
        "decision_id": moment.event_id,
        "title": compact_text[:96] or f"Follow up on {moment.event_id}",
        "owner": moment.speaker or "Unassigned",
        "priority_score": round(priority_score, 2),
        "execution_order": order,
        "task_type": "heuristic-follow-through",
        "notes": "Generated from transcript evidence and workflow heuristics.",
    }


def _heuristic_bottlenecks(
    transcript_segments: list[TranscriptSegment],
    decision_moments: list[DecisionMoment],
    execution_plan: list[dict],
) -> list[str]:
    bottlenecks: list[str] = []
    lowered_transcript = " ".join(segment.text.lower() for segment in transcript_segments)
    if any(keyword in lowered_transcript for keyword in ("blocked", "blocker", "dependency", "waiting", "risk")):
        bottlenecks.append("Execution blockers or risks were mentioned in the meeting transcript.")
    if decision_moments and any(not item.speaker for item in decision_moments):
        bottlenecks.append("One or more decisions are missing a clear accountable speaker.")
    if execution_plan and any(not task.get("owner") for task in execution_plan):
        bottlenecks.append("One or more execution tasks are missing an owner.")
    if execution_plan and any(" by " not in str(task.get("title") or "").lower() and "before" not in str(task.get("notes") or "").lower() for task in execution_plan):
        bottlenecks.append("Some workflow tasks do not yet expose a concrete deadline or checkpoint.")
    if not bottlenecks:
        bottlenecks.append("No major workflow bottleneck detected, but follow-through should still be confirmed.")
    return bottlenecks


def _fallback_workflow_model(
    transcript_segments: list[TranscriptSegment],
    decision_moments: list[DecisionMoment],
    visual_artifacts: list[VisualArtifact],
) -> WorkflowModel:
    sampled_segments = _sample_segments(transcript_segments, min(12, max(4, len(transcript_segments) or 4)))
    stages: list[dict] = []
    transitions: list[dict] = []
    previous_stage = None
    total_segments = len(sampled_segments)
    for index, segment in enumerate(sampled_segments):
        stage_name = _heuristic_stage_name(segment.text, index, total_segments)
        stages.append(
            {
                "timestamp": round(segment.start, 2),
                "stage": stage_name,
                "speaker": segment.speaker,
                "summary": " ".join(segment.text.split())[:140],
                "confidence": 0.58,
                "source": "heuristic-workflow-engine",
            }
        )
        if previous_stage is not None:
            transitions.append({"from": previous_stage, "to": stage_name, "speaker": segment.speaker})
        previous_stage = stage_name

    prioritized_decisions: list[dict] = []
    for moment in decision_moments:
        artifacts = _overlapping_artifacts(_time_to_seconds(moment.timestamp), visual_artifacts)
        priority_score, evidence = _heuristic_priority(moment, artifacts)
        prioritized_decisions.append(
            {
                "decision_id": moment.event_id,
                "label": moment.label,
                "speaker": moment.speaker,
                "priority_score": priority_score,
                "execution_rank": 0,
                "reasoning": evidence,
                "text": moment.text,
                "artifact_support": [artifact.artifact_id for artifact in artifacts],
            }
        )
    prioritized_decisions.sort(key=lambda item: item["priority_score"], reverse=True)

    execution_plan: list[dict] = []
    for index, decision in enumerate(prioritized_decisions, start=1):
        decision["execution_rank"] = index
        moment = next(item for item in decision_moments if item.event_id == decision["decision_id"])
        task = _fallback_task(moment, decision["priority_score"], index)
        task["notes"] = f"Generated from transcript evidence. {' | '.join(decision['reasoning'])}"
        execution_plan.append(task)

    bottlenecks = _heuristic_bottlenecks(transcript_segments, decision_moments, execution_plan)
    workflow_summary = {
        "total_stages": len(stages),
        "total_decisions": len(decision_moments),
        "total_execution_tasks": len(execution_plan),
        "top_priority_decision": prioritized_decisions[0]["decision_id"] if prioritized_decisions else "None",
        "source": "heuristic-workflow-engine",
        "status": "heuristic-fallback",
    }
    return WorkflowModel(stages, transitions, bottlenecks, prioritized_decisions, execution_plan, workflow_summary)


def run(
    transcript_segments: list[TranscriptSegment],
    decision_moments: list[DecisionMoment],
    visual_artifacts: list[VisualArtifact],
    config: AppConfig,
) -> WorkflowModel:
    classifier = _classifier(config.text_classifier_model)
    if classifier is None:
        fallback = _fallback_workflow_model(transcript_segments, decision_moments, visual_artifacts)
        fallback.bottlenecks.insert(0, f"Workflow classifier '{config.text_classifier_model}' is unavailable, so BoardSight used heuristic workflow modelling.")
        return fallback

    stages: list[dict] = []
    transitions: list[dict] = []
    previous_stage = None
    sampled_segments = _sample_segments(transcript_segments, config.max_workflow_segments)
    stage_classifications = _classify_many([segment.text for segment in sampled_segments], STAGE_LABELS, config)
    for segment, classification in zip(sampled_segments, stage_classifications):
        if classification is None:
            continue
        stage_name, stage_score = classification
        stages.append(
            {
                "timestamp": round(segment.start, 2),
                "stage": stage_name,
                "speaker": segment.speaker,
                "summary": " ".join(segment.text.split())[:120],
                "confidence": round(stage_score, 3),
                "source": f"zero-shot-classifier:{config.text_classifier_model}",
            }
        )
        if previous_stage is not None:
            transitions.append({"from": previous_stage, "to": stage_name, "speaker": segment.speaker})
        previous_stage = stage_name

    prioritized_decisions: list[dict] = []
    for moment in decision_moments:
        artifacts = _overlapping_artifacts(_time_to_seconds(moment.timestamp), visual_artifacts)
        priority_score, evidence = _priority(moment, artifacts, config)
        prioritized_decisions.append(
            {
                "decision_id": moment.event_id,
                "label": moment.label,
                "speaker": moment.speaker,
                "priority_score": priority_score,
                "execution_rank": 0,
                "reasoning": evidence,
                "text": moment.text,
                "artifact_support": [artifact.artifact_id for artifact in artifacts],
            }
        )

    prioritized_decisions.sort(key=lambda item: item["priority_score"], reverse=True)
    execution_plan = []
    for index, decision in enumerate(prioritized_decisions, start=1):
        decision["execution_rank"] = index
        moment = next(item for item in decision_moments if item.event_id == decision["decision_id"])
        execution_plan.append(_make_task(moment, decision["priority_score"], index, config))

    bottlenecks: list[str] = []
    transcript_text = " ".join(segment.text for segment in transcript_segments)
    bottleneck_prediction = _classify(transcript_text or "empty transcript", BOTTLENECK_LABELS, config)
    if bottleneck_prediction is not None:
        bottleneck, confidence = bottleneck_prediction
        bottlenecks.append(f"{bottleneck} ({config.text_classifier_model}, confidence={confidence:.3f})")

    workflow_summary = {
        "total_stages": len(stages),
        "total_decisions": len(decision_moments),
        "total_execution_tasks": len(execution_plan),
        "top_priority_decision": prioritized_decisions[0]["decision_id"] if prioritized_decisions else "None",
        "source": f"zero-shot-classifier:{config.text_classifier_model}",
    }
    model = WorkflowModel(stages, transitions, bottlenecks, prioritized_decisions, execution_plan, workflow_summary)
    if not model.stages and (decision_moments or transcript_segments):
        fallback = _fallback_workflow_model(transcript_segments, decision_moments, visual_artifacts)
        fallback.bottlenecks.insert(0, "Zero-shot stage detection produced no usable workflow stages, so BoardSight used heuristic workflow modelling.")
        return fallback
    return model
