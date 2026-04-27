from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from boardsight_ai.models import PipelineResult


@dataclass
class EvaluationResult:
    transcript_coverage: float
    decision_density: float
    speaker_balance_score: float
    note: str

    def to_dict(self) -> dict:
        return {
            "transcript_coverage": self.transcript_coverage,
            "decision_density": self.decision_density,
            "speaker_balance_score": self.speaker_balance_score,
            "note": self.note,
        }


def evaluate_pipeline_result(result: PipelineResult) -> EvaluationResult:
    transcript_chars = len(result.transcript.full_text.strip())
    transcript_coverage = round(min(100.0, transcript_chars / 12.0), 2)
    decision_density = round(len(result.decision_moments) / max(1, len(result.transcript.segments)) * 100.0, 2)
    top_ratio = result.speaker_dominance.speakers[0]["dominance_ratio"] if result.speaker_dominance.speakers else 100.0
    speaker_balance_score = round(max(0.0, 100.0 - abs(top_ratio - 50.0)), 2)
    return EvaluationResult(
        transcript_coverage=transcript_coverage,
        decision_density=decision_density,
        speaker_balance_score=speaker_balance_score,
        note="This is an internal pipeline-quality snapshot, not a formal benchmark against labeled ground truth.",
    )


def write_evaluation(result: PipelineResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    evaluation = evaluate_pipeline_result(result)
    output_path = output_dir / "performance_report.json"
    output_path.write_text(json.dumps(evaluation.to_dict(), indent=2), encoding="utf-8")
    return output_path
