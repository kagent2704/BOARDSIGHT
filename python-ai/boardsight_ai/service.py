from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime
from urllib.parse import unquote
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = CURRENT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
    from fastapi.responses import FileResponse
    import uvicorn
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "FastAPI service dependencies are missing. Install python-ai/requirements-core.txt first."
    ) from exc

from boardsight_ai.pipeline import run_pipeline, write_result
from boardsight_ai.providers.media import clip_video_fast
from boardsight_ai.auth import authenticate_user, create_user, get_session_user, init_auth_storage
from boardsight_ai.config import default_config
from boardsight_ai.features import decision_moments, visual_artifacts, workflow_engine
from boardsight_ai.features.scoring import _classifier as _scoring_classifier
from boardsight_ai.providers.llm import _summarizer
from boardsight_ai.providers.speech import _faster_whisper_model
from boardsight_ai.storage import get_meeting_result, init_storage, list_meeting_results, save_meeting_result

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "output" / "appdata"
AUTH_DB_PATH = DATA_DIR / "boardsight_auth.db"
MEETING_DB_PATH = DATA_DIR / "boardsight_meetings.db"
init_auth_storage(AUTH_DB_PATH)
init_storage(MEETING_DB_PATH)
create_user(
    AUTH_DB_PATH,
    "admin",
    "boardsight123",
    "admin",
    display_name="BoardSight Admin",
    email="admin@boardsight.local",
)


def _assign_orphaned_runs_to_admin() -> None:
    with sqlite3.connect(AUTH_DB_PATH) as auth_connection:
        admin_row = auth_connection.execute(
            "SELECT id, username FROM users WHERE username = ?",
            ("admin",),
        ).fetchone()
    if admin_row is None:
        return

    with sqlite3.connect(MEETING_DB_PATH) as meeting_connection:
        meeting_connection.execute(
            """
            UPDATE meetings
            SET user_id = ?, username = COALESCE(username, ?)
            WHERE user_id IS NULL
            """,
            (int(admin_row[0]), str(admin_row[1])),
        )
        meeting_connection.commit()


_assign_orphaned_runs_to_admin()

app = FastAPI(title="BoardSight AI Service", version="0.1.0")
WARM_MODELS_ON_STARTUP = os.getenv("BOARDSIGHT_WARM_MODELS", "0").strip().lower() in {"1", "true", "yes", "on"}
WARMUP_STATE: dict[str, object] = {
    "enabled": WARM_MODELS_ON_STARTUP,
    "completed": False,
    "in_progress": False,
    "steps": [],
}


def _warm_model_caches() -> None:
    WARMUP_STATE["in_progress"] = True
    config = default_config()
    steps: list[dict[str, str]] = []

    def record_step(name: str, loaded: bool) -> None:
        steps.append({"name": name, "status": "loaded" if loaded else "unavailable"})

    whisper_model = _faster_whisper_model(config.faster_whisper_model)
    record_step(f"faster-whisper:{config.faster_whisper_model}", whisper_model is not None)

    text_classifier = decision_moments._classifier(config.text_classifier_model)
    record_step(f"text-classifier:{config.text_classifier_model}", text_classifier is not None)
    record_step(f"workflow-classifier:{config.text_classifier_model}", workflow_engine._classifier(config.text_classifier_model) is not None)
    record_step(f"scoring-classifier:{config.text_classifier_model}", _scoring_classifier(config.text_classifier_model) is not None)

    image_classifier = visual_artifacts._image_classifier(config.image_classifier_model)
    record_step(f"image-classifier:{config.image_classifier_model}", image_classifier is not None)
    record_step("ocr:trocr-small-printed", visual_artifacts._ocr_components() is not None)
    record_step("image-captioning:blip-base", visual_artifacts._image_captioner() is not None)
    record_step("presentation-summary:flan-t5-small", _summarizer() is not None)

    WARMUP_STATE["completed"] = True
    WARMUP_STATE["in_progress"] = False
    WARMUP_STATE["steps"] = steps


@app.on_event("startup")
def warm_models_on_startup() -> None:
    if not WARM_MODELS_ON_STARTUP:
        return

    def _run_background_warmup() -> None:
        try:
            _warm_model_caches()
        except Exception as exc:
            WARMUP_STATE["completed"] = False
            WARMUP_STATE["in_progress"] = False
            WARMUP_STATE["error"] = str(exc)

    threading.Thread(target=_run_background_warmup, name="boardsight-model-warmup", daemon=True).start()


@app.get("/health")
def health() -> dict[str, str]:
    payload = {"status": "ok"}
    if WARM_MODELS_ON_STARTUP:
        if WARMUP_STATE.get("completed"):
            payload["model_warmup"] = "complete"
        elif WARMUP_STATE.get("in_progress"):
            payload["model_warmup"] = "warming"
        else:
            payload["model_warmup"] = "pending"
    return payload


async def _collect_request_payload(request: Request, payload: dict | None = None) -> dict:
    request_payload = dict(payload or {})
    if request_payload:
        return request_payload

    try:
        parsed_json = await request.json()
        if isinstance(parsed_json, dict):
            request_payload.update(parsed_json)
    except Exception:
        pass

    if not request_payload:
        try:
            raw_body = await request.body()
            if raw_body:
                parsed_raw = json.loads(raw_body.decode("utf-8"))
                if isinstance(parsed_raw, dict):
                    request_payload.update(parsed_raw)
        except Exception:
            pass

    if not request_payload:
        try:
            form = await request.form()
            request_payload.update({str(key): str(value) for key, value in form.items()})
        except Exception:
            pass

    if request.query_params:
        for key, value in request.query_params.items():
            request_payload.setdefault(str(key), str(value))

    return request_payload


@app.post("/api/v1/auth/login")
async def login(request: Request, payload: dict | None = None) -> dict:
    request_payload = await _collect_request_payload(request, payload)
    identifier = str(request_payload.get("identifier", "") or request_payload.get("username", "") or request_payload.get("email", ""))
    password = str(request_payload.get("password", ""))
    session = authenticate_user(AUTH_DB_PATH, identifier, password)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid username, email, or password.")
    return session


@app.post("/api/v1/auth/register")
async def register(request: Request, payload: dict | None = None) -> dict:
    request_payload = await _collect_request_payload(request, payload)
    username = str(request_payload.get("username", "")).strip()
    email = str(request_payload.get("email", "")).strip().lower()
    password = str(request_payload.get("password", "")).strip()
    confirm_password = str(request_payload.get("confirm_password", "")).strip()
    role = str(request_payload.get("role", "analyst")).strip() or "analyst"
    display_name = str(request_payload.get("display_name", username)).strip() or username
    if not username or not email or not password or not confirm_password:
        raise HTTPException(status_code=400, detail="Username, email, password, and confirmation are required.")
    if confirm_password != password:
        raise HTTPException(status_code=400, detail="Password confirmation does not match.")
    created = create_user(AUTH_DB_PATH, username, password, role, display_name=display_name, email=email)
    if not created:
        raise HTTPException(status_code=409, detail="An account with that username or email already exists.")
    return {"status": "created", "username": username, "email": email, "display_name": display_name, "role": role}


def _require_session_user(request: Request) -> dict:
    auth_header = request.headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip() if auth_header else ""
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token.")
    user = get_session_user(AUTH_DB_PATH, token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")
    return user


def _summarize_meeting_row(row: dict) -> dict:
    meeting_id = int(row["id"])
    run_name = str(row.get("run_name") or f"meeting-{meeting_id}")
    sentiment = str(row.get("overall_sentiment") or "analysis ready").strip()
    return {
        "id": str(meeting_id),
        "meetingId": meeting_id,
        "title": run_name.replace("-", " ").replace("_", " ").strip().title() or f"Meeting {meeting_id}",
        "conclusion": f"Sentiment: {sentiment.capitalize()} | Attention {float(row.get('overall_attention') or 0):.1f}% | Impact {float(row.get('impact_score') or 0):.1f}",
        "decisions": int(row.get("decision_count") or 0),
        "createdAt": str(row.get("created_at") or datetime.utcnow().isoformat()),
        "speakerCount": int(row.get("speaker_count") or 0),
        "visualArtifactCount": int(row.get("visual_artifact_count") or 0),
        "overallAttention": float(row.get("overall_attention") or 0),
        "overallSentiment": row.get("overall_sentiment"),
        "impactScore": float(row.get("impact_score") or 0),
        "productivityScore": float(row.get("productivity_score") or 0),
        "executionReadiness": float(row.get("execution_readiness") or 0),
    }


def _resolve_owned_meeting_record(meeting_id: int, user: dict) -> dict:
    record = get_meeting_result(MEETING_DB_PATH, meeting_id, user_id=int(user["user_id"]))
    if record is None:
        raise HTTPException(status_code=404, detail="Stored analysis not found.")
    return record


@app.get("/api/v1/me")
def me(request: Request) -> dict:
    return _require_session_user(request)


@app.get("/api/v1/meetings")
def meetings(request: Request) -> dict:
    user = _require_session_user(request)
    rows = list_meeting_results(MEETING_DB_PATH, user_id=int(user["user_id"]))
    return {"items": [_summarize_meeting_row(row) for row in rows]}


@app.get("/api/v1/meetings/{meeting_id}")
def meeting_detail(meeting_id: int, request: Request) -> dict:
    user = _require_session_user(request)
    record = _resolve_owned_meeting_record(meeting_id, user)
    payload = json.loads(str(record.get("result_json") or "{}"))
    payload["storage"] = {
        "meeting_id": int(record["id"]),
        "output_dir": str(record.get("output_dir") or ""),
        "result_file": str(record.get("result_file") or ""),
        "created_at": str(record.get("created_at") or ""),
        "username": str(record.get("username") or ""),
    }
    return payload


@app.get("/api/v1/meetings/{meeting_id}/reports/{file_name}")
def meeting_report(meeting_id: int, file_name: str, request: Request):
    user = _require_session_user(request)
    record = _resolve_owned_meeting_record(meeting_id, user)
    output_dir = Path(str(record.get("output_dir") or "")).resolve()
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Stored analysis output directory is missing.")
    candidate = (output_dir / file_name).resolve()
    if not str(candidate).startswith(str(output_dir)):
        raise HTTPException(status_code=400, detail="Invalid report path.")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Requested report file was not found.")
    return FileResponse(candidate, filename=candidate.name)


def _build_output_payload(result, output_dir: Path, user: dict | None = None) -> dict:
    result_path = write_result(result, output_dir / "boardsight_result.json")
    meeting_id = save_meeting_result(
        MEETING_DB_PATH,
        result,
        output_dir=output_dir,
        result_file=result_path,
        user_id=int(user["user_id"]) if user is not None else None,
        username=str(user["username"]) if user is not None else None,
    )
    payload = result.to_dict()
    payload["storage"] = {
        "meeting_id": meeting_id,
        "auth_db": str(AUTH_DB_PATH),
        "meeting_db": str(MEETING_DB_PATH),
        "output_dir": str(output_dir),
        "result_file": str(result_path),
    }
    return payload


def _resolve_output_dir(output_dir_name: str | None) -> Path:
    output_root = PROJECT_ROOT / "output"
    run_name = (output_dir_name or f"service-run-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}").strip()
    safe_run_name = "".join(char if char.isalnum() or char in "-_." else "_" for char in run_name) or "service-run"
    output_dir = output_root / safe_run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _parse_optional_float(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def _resolve_analysis_input(
    source_video_path: Path,
    output_dir: Path,
    start_seconds: float | None,
    end_seconds: float | None,
) -> tuple[Path, dict | None]:
    if start_seconds is None and end_seconds is None:
        return source_video_path, None
    clipped_path = output_dir / "analysis_input.mp4"
    analysis_range = clip_video_fast(source_video_path, clipped_path, start_seconds, end_seconds)
    return Path(str(analysis_range["output_path"])).resolve(), analysis_range


def _run_pipeline_for_shared_path(
    shared_file_path: str,
    output_dir_name: str | None,
    user: dict | None = None,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> dict:
    candidate_path = Path(unquote(shared_file_path)).resolve()
    output_root = PROJECT_ROOT / "output"
    if not str(candidate_path).startswith(str(output_root.resolve())):
        raise HTTPException(status_code=400, detail="Shared file path must be inside the output directory.")
    if not candidate_path.exists():
        raise HTTPException(status_code=400, detail="Shared file path does not exist for AI processing.")
    output_dir = _resolve_output_dir(output_dir_name)
    analysis_input_path, analysis_range = _resolve_analysis_input(candidate_path, output_dir, start_seconds, end_seconds)
    result = run_pipeline(analysis_input_path, output_dir, analysis_range=analysis_range)
    return _build_output_payload(result, output_dir, user=user)


@app.post("/api/v1/pipeline/run-path")
async def run_pipeline_path_endpoint(request: Request, payload: dict | None = None) -> dict:
    user = _require_session_user(request)
    request_payload = payload or {}
    if not request_payload:
        try:
            request_payload = await request.json()
        except Exception:
            request_payload = {}

    file_path = str(request_payload.get("file_path", "")).strip() or str(request.query_params.get("file_path", "")).strip()
    output_dir_name = (
        str(request_payload.get("output_dir_name", "")).strip()
        or str(request.query_params.get("output_dir_name", "")).strip()
        or None
    )
    start_seconds = _parse_optional_float(request_payload.get("start_seconds", request.query_params.get("start_seconds")))
    end_seconds = _parse_optional_float(request_payload.get("end_seconds", request.query_params.get("end_seconds")))
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required.")
    return _run_pipeline_for_shared_path(
        file_path,
        output_dir_name,
        user=user,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )


@app.post("/api/v1/pipeline/run")
async def run_pipeline_endpoint(
    request: Request,
    file: UploadFile | None = File(default=None),
    upload: UploadFile | None = File(default=None),
    meeting_file: UploadFile | None = File(default=None),
    output_dir_name: str | None = Form(default=None),
) -> dict:
    user = _require_session_user(request)
    resolved_upload = file or upload or meeting_file
    request_query = request.query_params
    request_payload: dict = {}

    if output_dir_name is None:
        output_dir_name = request_query.get("output_dir_name")

    request_content_type = request.headers.get("content-type", "")
    if "application/json" in request_content_type.lower():
        try:
            request_payload = await request.json()
        except Exception:
            request_payload = {}
        if output_dir_name is None:
            output_dir_name = str(request_payload.get("output_dir_name", "")).strip() or None

    if resolved_upload is None:
        try:
            form = await request.form()
        except Exception:
            form = None
        if form is not None:
            for field_name in ("file", "upload", "meeting_file"):
                candidate = form.get(field_name)
                if candidate is not None and hasattr(candidate, "filename") and hasattr(candidate, "read"):
                    resolved_upload = candidate
                    break

    raw_upload_bytes = b""
    raw_upload_name = request.headers.get("X-Filename") or request_query.get("filename") or "meeting.mp4"
    shared_file_path = str(request_payload.get("file_path", "")).strip() or request_query.get("file_path")
    start_seconds = _parse_optional_float(request_payload.get("start_seconds", request_query.get("start_seconds")))
    end_seconds = _parse_optional_float(request_payload.get("end_seconds", request_query.get("end_seconds")))
    if resolved_upload is None:
        if shared_file_path:
            return _run_pipeline_for_shared_path(
                shared_file_path,
                output_dir_name,
                user=user,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )

        try:
            raw_upload_bytes = await request.body()
        except Exception:
            raw_upload_bytes = b""
        if not raw_upload_bytes:
            raise HTTPException(status_code=400, detail="No uploaded file was provided to the AI service.")

    resolved_name = resolved_upload.filename if resolved_upload is not None else unquote(raw_upload_name)
    suffix = Path(resolved_name or "meeting.mp4").suffix or ".mp4"
    output_dir = _resolve_output_dir(output_dir_name)

    with tempfile.TemporaryDirectory(prefix="boardsight-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        video_path = temp_dir / f"upload{suffix}"
        if resolved_upload is not None:
            video_path.write_bytes(await resolved_upload.read())
        else:
            video_path.write_bytes(raw_upload_bytes)

        if not video_path.exists():
            raise HTTPException(status_code=400, detail="Failed to persist uploaded file.")

        analysis_input_path, analysis_range = _resolve_analysis_input(video_path, output_dir, start_seconds, end_seconds)
        result = run_pipeline(analysis_input_path, output_dir, analysis_range=analysis_range)
        return _build_output_payload(result, output_dir, user=user)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
