from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TranscriptSegment:
    start: float
    end: float
    speaker: str
    text: str
    confidence: float = 0.0


@dataclass
class SpeakerDominanceResult:
    speakers: list[dict[str, Any]]
    active_speaker_timeline: list[dict[str, Any]]
    visual_identities: list[dict[str, Any]]


@dataclass
class AttentionSentimentResult:
    overall_attention: float
    overall_sentiment: str
    engagement_timeline: list[dict[str, Any]]
    sentiment_timeline: list[dict[str, Any]]
    cognitive_rating: dict[str, Any]
    participant_states: list[dict[str, Any]] = field(default_factory=list)
    model_sources: list[str] = field(default_factory=list)
    coverage_ratio: float = 0.0


@dataclass
class DecisionMoment:
    event_id: str
    timestamp: str
    speaker: str
    text: str
    confidence: float
    label: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class VisualArtifact:
    artifact_id: str
    start_time: float
    end_time: float
    artifact_type: str
    confidence: float
    detections: list[dict[str, Any]] = field(default_factory=list)
    display_mode: str = ""
    content_summary: str = ""
    content_text: str = ""
    content_insight: str = ""


@dataclass
class WorkflowModel:
    stages: list[dict[str, Any]]
    transitions: list[dict[str, Any]]
    bottlenecks: list[str]
    prioritized_decisions: list[dict[str, Any]] = field(default_factory=list)
    execution_plan: list[dict[str, Any]] = field(default_factory=list)
    workflow_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionTrace:
    trace_id: str
    title: str
    summary: str
    owner: str
    rationale: list[str]
    next_steps: list[str]
    related_artifacts: list[str]
    priority_score: float = 0.0
    decision_type: str = ""
    supporting_speakers: list[str] = field(default_factory=list)
    execution_tasks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TranscriptResult:
    full_text: str
    segments: list[TranscriptSegment]
    speaker_directory: list[dict[str, Any]]


@dataclass
class MeetingScores:
    impact_score: float
    productivity_score: float
    execution_readiness: float
    speaker_rating: dict[str, Any]
    cognitive_rating: dict[str, Any]
    meeting_conclusion: str


@dataclass
class PipelineResult:
    input_video: str
    transcript: TranscriptResult
    speaker_dominance: SpeakerDominanceResult
    decision_moments: list[DecisionMoment]
    visual_artifacts: list[VisualArtifact]
    workflow_model: WorkflowModel
    decision_traces: list[DecisionTrace]
    attention_sentiment: AttentionSentimentResult
    meeting_scores: MeetingScores
    warnings: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def pipeline_result_from_dict(payload: dict[str, Any]) -> PipelineResult:
    transcript_payload = dict(payload.get("transcript") or {})
    transcript_segments = [
        TranscriptSegment(
            start=float(item.get("start") or 0.0),
            end=float(item.get("end") or 0.0),
            speaker=str(item.get("speaker") or ""),
            text=str(item.get("text") or ""),
            confidence=float(item.get("confidence") or 0.0),
        )
        for item in (transcript_payload.get("segments") or [])
    ]
    decision_moments = [
        DecisionMoment(
            event_id=str(item.get("event_id") or item.get("eventId") or ""),
            timestamp=str(item.get("timestamp") or ""),
            speaker=str(item.get("speaker") or ""),
            text=str(item.get("text") or ""),
            confidence=float(item.get("confidence") or 0.0),
            label=str(item.get("label") or ""),
            evidence=list(item.get("evidence") or []),
        )
        for item in (payload.get("decision_moments") or payload.get("decisionMoments") or [])
    ]
    visual_artifacts = [
        VisualArtifact(
            artifact_id=str(item.get("artifact_id") or item.get("artifactId") or ""),
            start_time=float(item.get("start_time") or item.get("startTime") or 0.0),
            end_time=float(item.get("end_time") or item.get("endTime") or 0.0),
            artifact_type=str(item.get("artifact_type") or item.get("artifactType") or ""),
            confidence=float(item.get("confidence") or 0.0),
            detections=list(item.get("detections") or []),
            display_mode=str(item.get("display_mode") or item.get("displayMode") or ""),
            content_summary=str(item.get("content_summary") or item.get("contentSummary") or ""),
            content_text=str(item.get("content_text") or item.get("contentText") or ""),
            content_insight=str(item.get("content_insight") or item.get("contentInsight") or ""),
        )
        for item in (payload.get("visual_artifacts") or payload.get("visualArtifacts") or [])
    ]
    decision_traces = [
        DecisionTrace(
            trace_id=str(item.get("trace_id") or item.get("traceId") or ""),
            title=str(item.get("title") or ""),
            summary=str(item.get("summary") or ""),
            owner=str(item.get("owner") or ""),
            rationale=list(item.get("rationale") or []),
            next_steps=list(item.get("next_steps") or item.get("nextSteps") or []),
            related_artifacts=list(item.get("related_artifacts") or item.get("relatedArtifacts") or []),
            priority_score=float(item.get("priority_score") or item.get("priorityScore") or 0.0),
            decision_type=str(item.get("decision_type") or item.get("decisionType") or ""),
            supporting_speakers=list(item.get("supporting_speakers") or item.get("supportingSpeakers") or []),
            execution_tasks=list(item.get("execution_tasks") or item.get("executionTasks") or []),
        )
        for item in (payload.get("decision_traces") or payload.get("decisionTraces") or [])
    ]
    workflow_payload = dict(payload.get("workflow_model") or payload.get("workflowModel") or {})
    attention_payload = dict(payload.get("attention_sentiment") or payload.get("attentionSentiment") or {})
    scores_payload = dict(payload.get("meeting_scores") or payload.get("meetingScores") or {})
    speaker_payload = dict(payload.get("speaker_dominance") or payload.get("speakerDominance") or {})
    return PipelineResult(
        input_video=str(payload.get("input_video") or payload.get("inputVideo") or ""),
        transcript=TranscriptResult(
            full_text=str(transcript_payload.get("full_text") or transcript_payload.get("fullText") or ""),
            segments=transcript_segments,
            speaker_directory=list(transcript_payload.get("speaker_directory") or transcript_payload.get("speakerDirectory") or []),
        ),
        speaker_dominance=SpeakerDominanceResult(
            speakers=list(speaker_payload.get("speakers") or []),
            active_speaker_timeline=list(speaker_payload.get("active_speaker_timeline") or speaker_payload.get("activeSpeakerTimeline") or []),
            visual_identities=list(speaker_payload.get("visual_identities") or speaker_payload.get("visualIdentities") or []),
        ),
        decision_moments=decision_moments,
        visual_artifacts=visual_artifacts,
        workflow_model=WorkflowModel(
            stages=list(workflow_payload.get("stages") or []),
            transitions=list(workflow_payload.get("transitions") or []),
            bottlenecks=list(workflow_payload.get("bottlenecks") or []),
            prioritized_decisions=list(workflow_payload.get("prioritized_decisions") or workflow_payload.get("prioritizedDecisions") or []),
            execution_plan=list(workflow_payload.get("execution_plan") or workflow_payload.get("executionPlan") or []),
            workflow_summary=dict(workflow_payload.get("workflow_summary") or workflow_payload.get("workflowSummary") or {}),
        ),
        decision_traces=decision_traces,
        attention_sentiment=AttentionSentimentResult(
            overall_attention=float(attention_payload.get("overall_attention") or attention_payload.get("overallAttention") or 0.0),
            overall_sentiment=str(attention_payload.get("overall_sentiment") or attention_payload.get("overallSentiment") or ""),
            engagement_timeline=list(attention_payload.get("engagement_timeline") or attention_payload.get("engagementTimeline") or []),
            sentiment_timeline=list(attention_payload.get("sentiment_timeline") or attention_payload.get("sentimentTimeline") or []),
            cognitive_rating=dict(attention_payload.get("cognitive_rating") or attention_payload.get("cognitiveRating") or {}),
            participant_states=list(attention_payload.get("participant_states") or attention_payload.get("participantStates") or []),
            model_sources=list(attention_payload.get("model_sources") or attention_payload.get("modelSources") or []),
            coverage_ratio=float(attention_payload.get("coverage_ratio") or attention_payload.get("coverageRatio") or 0.0),
        ),
        meeting_scores=MeetingScores(
            impact_score=float(scores_payload.get("impact_score") or scores_payload.get("impactScore") or 0.0),
            productivity_score=float(scores_payload.get("productivity_score") or scores_payload.get("productivityScore") or 0.0),
            execution_readiness=float(scores_payload.get("execution_readiness") or scores_payload.get("executionReadiness") or 0.0),
            speaker_rating=dict(scores_payload.get("speaker_rating") or scores_payload.get("speakerRating") or {}),
            cognitive_rating=dict(scores_payload.get("cognitive_rating") or scores_payload.get("cognitiveRating") or {}),
            meeting_conclusion=str(scores_payload.get("meeting_conclusion") or scores_payload.get("meetingConclusion") or ""),
        ),
        warnings=list(payload.get("warnings") or []),
        metadata=dict(payload.get("metadata") or {}),
    )
