from __future__ import annotations

from boardsight_ai.gitlab_execution import (
    _extract_action_clauses,
    _normalize_due_date,
    build_gitlab_execution_plan,
)


def test_extract_action_clauses_splits_multi_owner_statement() -> None:
    clauses = _extract_action_clauses(
        "Kash will prepare the model evaluation report by 2026-06-30, and Akanksha will clean the dataset before that."
    )

    assert len(clauses) == 2
    assert clauses[0]["owner"] == "Kash"
    assert clauses[0]["due_date"] == "2026-06-30"
    assert clauses[1]["owner"] == "Akanksha"


def test_normalize_due_date_returns_iso_date_when_present() -> None:
    assert _normalize_due_date("submit by 2026-07-04") == "2026-07-04"


def test_build_gitlab_execution_plan_creates_traceable_issues() -> None:
    source = {
        "decisions": [
            {
                "decision_id": "DM-1",
                "text": "Kash will prepare the model evaluation report by 2026-06-30, and Akanksha will clean the dataset before that.",
            }
        ],
        "action_items": [
            {
                "decision_id": "DM-1",
                "title": "Prepare model evaluation report",
                "owner": "Kash",
                "notes": "Depends on cleaned dataset by 2026-06-30",
            }
        ],
        "problems": [
            {
                "text": "Dataset quality is still inconsistent.",
                "timestamp": "00:01:10",
                "speaker": "Akanksha",
                "category": "blocker",
            }
        ],
        "discussion_points": ["Akanksha will clean the dataset before that."],
    }

    plan = build_gitlab_execution_plan(
        source,
        source_kind="meeting",
        source_id="18",
        meeting_title="Storage Check",
        assignee_map={"kash": 101, "akanksha": 202},
    )

    assert plan["meeting_title"] == "Storage Check"
    assert len(plan["issues"]) >= 2
    assert any(issue["kind"] == "blocker" for issue in plan["issues"])
    assert any(issue["assignee_id"] == 101 for issue in plan["issues"])
    assert any(link["link_type"] == "blocks" for link in plan["issue_links"])
