from __future__ import annotations

from pathlib import Path

from boardsight_ai.config import AppConfig
from boardsight_ai.features import workflow_engine


def test_workflow_engine_falls_back_to_heuristics_when_classifier_is_unavailable(sample_pipeline_result, monkeypatch) -> None:
    config = AppConfig(
        project_root=Path.cwd(),
        output_root=Path.cwd() / "output",
    )
    monkeypatch.setattr(workflow_engine, "_classifier", lambda _model_name: None)

    model = workflow_engine.run(
        sample_pipeline_result.transcript.segments,
        sample_pipeline_result.decision_moments,
        sample_pipeline_result.visual_artifacts,
        config,
    )

    assert model.workflow_summary["status"] == "heuristic-fallback"
    assert len(model.stages) > 0
    assert len(model.prioritized_decisions) > 0
    assert len(model.execution_plan) > 0
    assert "heuristic workflow modelling" in model.bottlenecks[0].lower()
