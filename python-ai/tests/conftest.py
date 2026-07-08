from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_AI_ROOT = PROJECT_ROOT / "python-ai"

if str(PYTHON_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_AI_ROOT))

from boardsight_ai.models import (  # noqa: E402
    AttentionSentimentResult,
    DecisionMoment,
    DecisionTrace,
    MeetingScores,
    PipelineResult,
    SpeakerDominanceResult,
    TranscriptResult,
    TranscriptSegment,
    VisualArtifact,
    WorkflowModel,
)


@pytest.fixture
def sample_pipeline_result() -> PipelineResult:
    return PipelineResult(
        input_video="demo-meeting.mp4",
        transcript=TranscriptResult(
            full_text="Kash will prepare the report. Akanksha will clean the dataset.",
            segments=[
                TranscriptSegment(start=0.0, end=4.0, speaker="Kash", text="Kash will prepare the report."),
                TranscriptSegment(start=4.0, end=8.0, speaker="Akanksha", text="Akanksha will clean the dataset."),
            ],
            speaker_directory=[{"speaker": "Kash"}, {"speaker": "Akanksha"}],
        ),
        speaker_dominance=SpeakerDominanceResult(
            speakers=[
                {"speaker": "Kash", "dominance_ratio": 57.0},
                {"speaker": "Akanksha", "dominance_ratio": 43.0},
            ],
            active_speaker_timeline=[],
            visual_identities=[],
        ),
        decision_moments=[
            DecisionMoment(
                event_id="DM-1",
                timestamp="00:00:04",
                speaker="Kash",
                text="Kash will prepare the report by 2026-06-30.",
                confidence=0.92,
                label="action",
                evidence=["report by 2026-06-30"],
            )
        ],
        visual_artifacts=[
            VisualArtifact(
                artifact_id="VA-1",
                start_time=0.0,
                end_time=5.0,
                artifact_type="slide",
                confidence=0.88,
                display_mode="screen-share",
                content_summary="Project planning slide",
                content_text="Launch checklist",
                content_insight="Planning meeting context",
            )
        ],
        workflow_model=WorkflowModel(
            stages=[{"name": "Planning"}],
            transitions=[{"from": "Planning", "to": "Execution"}],
            bottlenecks=["Dataset dependency still unresolved."],
            prioritized_decisions=[
                {
                    "decision_id": "DM-1",
                    "priority_score": 0.91,
                    "execution_rank": 1,
                    "artifact_support": ["VA-1"],
                }
            ],
            execution_plan=[
                {
                    "task_id": "TASK-1",
                    "decision_id": "DM-1",
                    "title": "Prepare model evaluation report",
                    "owner": "Kash",
                    "priority_score": 0.91,
                    "execution_order": 1,
                    "task_type": "report",
                    "notes": "Depends on dataset cleaning",
                },
                {
                    "task_id": "TASK-2",
                    "decision_id": "DM-1",
                    "title": "Clean dataset",
                    "owner": "Akanksha",
                    "priority_score": 0.85,
                    "execution_order": 2,
                    "task_type": "data",
                    "notes": "Complete before report generation",
                },
            ],
            workflow_summary={"top_priority_decision": "DM-1"},
        ),
        decision_traces=[
            DecisionTrace(
                trace_id="TRACE-1",
                title="Dataset cleanup before evaluation",
                summary="The team agreed to clean the dataset first.",
                owner="Akanksha",
                rationale=["Data quality risk"],
                next_steps=["Clean dataset", "Prepare report"],
                related_artifacts=["VA-1"],
                priority_score=0.9,
                execution_tasks=[],
            )
        ],
        attention_sentiment=AttentionSentimentResult(
            overall_attention=41.5,
            overall_sentiment="focused",
            engagement_timeline=[],
            sentiment_timeline=[],
            cognitive_rating={"score": 0.7},
            participant_states=[],
            model_sources=["demo"],
            coverage_ratio=1.0,
        ),
        meeting_scores=MeetingScores(
            impact_score=0.82,
            productivity_score=0.76,
            execution_readiness=0.81,
            speaker_rating={"score": 0.8},
            cognitive_rating={"score": 0.7},
            meeting_conclusion="The team aligned on data cleanup and report preparation.",
        ),
        warnings=[],
        metadata={
            "analysis_profile": "recorded-fast",
            "source_mode": "recorded",
            "agentic_contract": {
                "contract_version": "2026-06-10",
                "entities": {
                    "risk_signals": [{"risk_id": "RS-1", "kind": "workflow-bottleneck"}]
                },
            },
        },
    )
