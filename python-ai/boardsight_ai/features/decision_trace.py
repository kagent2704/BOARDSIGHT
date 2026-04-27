from __future__ import annotations

from boardsight_ai.config import AppConfig
from boardsight_ai.models import DecisionMoment, DecisionTrace, TranscriptSegment, VisualArtifact, WorkflowModel
from boardsight_ai.providers.llm import summarize


def _title_from_text(text: str, label: str) -> str:
    words = text.split()
    if not words:
        return f"{label.title()} trace"
    preview = " ".join(words[:8]).rstrip(",.")
    return f"{label.title()}: {preview}"


def _related_artifacts(moment: DecisionMoment, visual_artifacts: list[VisualArtifact]) -> list[str]:
    minute, second = moment.timestamp.split(":")
    current_time = int(minute) * 60 + int(second)
    return [
        artifact.artifact_id
        for artifact in visual_artifacts
        if artifact.start_time <= current_time <= artifact.end_time
    ][:4]


def _supporting_speakers(moment: DecisionMoment, transcript_segments: list[TranscriptSegment]) -> list[str]:
    support: list[str] = []
    for segment in transcript_segments:
        if abs(segment.start - float(moment.timestamp.split(":")[0]) * 60 - float(moment.timestamp.split(":")[1])) > 20:
            continue
        if segment.speaker not in support:
            support.append(segment.speaker)
    return support[:4]


def run(
    transcript_segments: list[TranscriptSegment],
    decision_moments: list[DecisionMoment],
    visual_artifacts: list[VisualArtifact],
    workflow_model: WorkflowModel,
    config: AppConfig,
) -> list[DecisionTrace]:
    traces: list[DecisionTrace] = []

    if not decision_moments:
        summary, summary_mode = summarize(
            "The current transcript pass did not identify explicit decision moments.",
            config,
        )
        return [
            DecisionTrace(
                trace_id="DT-0",
                title="No explicit decisions detected",
                summary=summary,
                owner="Unassigned",
                rationale=[
                    "Run with a full ASR and diarization stack for stronger decision capture.",
                    f"Summary mode: {summary_mode}.",
                ],
                next_steps=["Review the transcript manually and confirm action items."],
                related_artifacts=[artifact.artifact_id for artifact in visual_artifacts[:3]],
                decision_type="none",
            )
        ]

    decision_lookup = {item["decision_id"]: item for item in workflow_model.prioritized_decisions}
    task_lookup: dict[str, list[dict]] = {}
    for task in workflow_model.execution_plan:
        task_lookup.setdefault(task["decision_id"], []).append(task)

    for index, moment in enumerate(decision_moments, start=1):
        priority_entry = decision_lookup.get(moment.event_id, {})
        execution_tasks = task_lookup.get(moment.event_id, [])
        summary, summary_mode = summarize(moment.text, config)
        traces.append(
            DecisionTrace(
                trace_id=f"DT-{index}",
                title=_title_from_text(moment.text, moment.label),
                summary=summary,
                owner=moment.speaker or "Unassigned",
                rationale=[
                    f"Detected as {moment.label} with confidence {moment.confidence:.2f}.",
                    f"Priority score: {priority_entry.get('priority_score', 0.0):.2f}.",
                    f"Evidence: {', '.join(moment.evidence[:3]) or 'semantic context'}.",
                    f"Execution tasks generated: {len(execution_tasks)}.",
                    f"Summary mode: {summary_mode}.",
                ],
                next_steps=[task["title"] for task in execution_tasks[:3]] or ["Validate the decision and assign owners."],
                related_artifacts=_related_artifacts(moment, visual_artifacts),
                priority_score=float(priority_entry.get("priority_score", 0.0)),
                decision_type=moment.label,
                supporting_speakers=_supporting_speakers(moment, transcript_segments),
                execution_tasks=execution_tasks,
            )
        )

    traces.sort(key=lambda item: item.priority_score, reverse=True)
    return traces
