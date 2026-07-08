from __future__ import annotations

from pathlib import Path

from boardsight_ai.auth import authenticate_user, create_user, get_session_user, get_user_by_username


def test_create_user_and_authenticate_by_username_and_email(tmp_path: Path) -> None:
    db_path = tmp_path / "auth.db"

    created = create_user(
        db_path,
        username="admin",
        password="boardsight123",
        role="admin",
        display_name="BoardSight Admin",
        email="admin@example.com",
    )

    assert created is True
    assert create_user(db_path, "admin", "boardsight123") is False

    by_username = authenticate_user(db_path, "admin", "boardsight123")
    assert by_username is not None
    assert by_username["username"] == "admin"
    assert by_username["display_name"] == "BoardSight Admin"

    by_email = authenticate_user(db_path, "admin@example.com", "boardsight123")
    assert by_email is not None
    assert by_email["email"] == "admin@example.com"

    session_user = get_session_user(db_path, by_email["token"])
    assert session_user is not None
    assert session_user["role"] == "admin"


def test_get_user_by_username_is_case_insensitive(tmp_path: Path) -> None:
    db_path = tmp_path / "auth.db"
    create_user(db_path, "Kash", "secret", display_name="Kash Mira", email="kash@example.com")

    user = get_user_by_username(db_path, "kash")

    assert user is not None
    assert user["username"] == "Kash"
    assert user["display_name"] == "Kash Mira"
