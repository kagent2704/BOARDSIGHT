from __future__ import annotations

import json
from pathlib import Path

from boardsight_ai.agentic_contract import build_agentic_contract
from boardsight_ai.storage import get_meeting_result, list_meeting_results, save_meeting_result


def test_save_meeting_result_round_trips_sqlite_record(tmp_path: Path, sample_pipeline_result) -> None:
    db_path = tmp_path / "meetings.db"
    output_dir = tmp_path / "web-run-123"
    output_dir.mkdir()
    result_file = output_dir / "boardsight_result.json"
    result_file.write_text(json.dumps(sample_pipeline_result.to_dict()), encoding="utf-8")

    meeting_id = save_meeting_result(
        db_path,
        sample_pipeline_result,
        output_dir=output_dir,
        result_file=result_file,
        user_id=7,
        username="admin",
    )

    listing = list_meeting_results(db_path, user_id=7)
    stored = get_meeting_result(db_path, meeting_id, user_id=7)

    assert meeting_id > 0
    assert len(listing) == 1
    assert listing[0]["decision_count"] == 1
    assert listing[0]["execution_task_count"] == 2
    assert stored is not None
    assert stored["username"] == "admin"
    assert stored["result_file"] == str(result_file)


def test_build_agentic_contract_includes_actions_and_risk_signals(sample_pipeline_result) -> None:
    contract = build_agentic_contract(
        sample_pipeline_result,
        analysis_profile="recorded-fast",
        source_mode="recorded",
        contract_version="2026-06-10",
    )

    assert contract["contract_version"] == "2026-06-10"
    assert contract["meeting_digest"]["input_video"] == "demo-meeting.mp4"
    assert len(contract["entities"]["decisions"]) == 1
    assert len(contract["entities"]["actions"]) == 2
    assert len(contract["entities"]["risk_signals"]) >= 2
    assert contract["execution_graph"]["top_decision_id"] == "DM-1"
