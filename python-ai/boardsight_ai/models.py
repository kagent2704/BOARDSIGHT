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
