from __future__ import annotations

import json
from pathlib import Path

from boardsight_ai.database import execute
from boardsight_ai.service import MEETING_DB_PATH, _regenerate_meeting_report_from_record
from boardsight_ai.storage import get_meeting_result, init_storage


def test_regenerate_meeting_report_from_record_without_original_output_dir(tmp_path: Path, sample_pipeline_result, monkeypatch) -> None:
    db_path = tmp_path / "meetings.db"
    init_storage(db_path)
    payload = sample_pipeline_result.to_dict()
    execute(
        db_path,
        """
        INSERT INTO meetings (
            user_id, username, run_name, input_video, output_dir, result_file, transcript_text,
            speaker_count, decision_count, visual_artifact_count, top_decision_id, overall_attention,
            overall_sentiment, impact_score, productivity_score, execution_readiness, dominance_ratio,
            runtime_profile, data_contract_version, analysis_profile, source_mode, run_status,
            execution_task_count, risk_signal_count, contract_version, result_json
        ) VALUES (
            7, 'tester', 'restored-run', :input_video, '', '', :transcript_text,
            1, 1, 1, 'DM-1', 41.5, 'focused', 0.82, 0.76, 0.81, 57.0,
            'test', 'v1', 'recorded-fast', 'recorded', 'completed', 2, 1, '2026-06-10', :result_json
        )
        """,
        {
            "input_video": sample_pipeline_result.input_video,
            "transcript_text": sample_pipeline_result.transcript.full_text,
            "result_json": json.dumps(payload),
        },
    )
    record = get_meeting_result(db_path, 1, user_id=7)
    assert record is not None

    monkeypatch.setattr("boardsight_ai.service.MEETING_DB_PATH", db_path)
    regenerated = _regenerate_meeting_report_from_record(record, "structured_report.pdf")

    assert regenerated is not None
    assert regenerated.exists()
    assert regenerated.name == "structured_report.pdf"

