from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_local_env(project_root: Path) -> None:
    env_path = project_root / "python-ai" / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    output_root: Path
    active_speaker_weight_audio: float = 0.7
    active_speaker_weight_visual: float = 0.3
    yolo_model_name: str = "yolov8n.pt"
    text_classifier_model: str = os.getenv("BOARDSIGHT_TEXT_CLASSIFIER_MODEL", "typeform/distilbert-base-uncased-mnli")
    image_classifier_model: str = os.getenv("BOARDSIGHT_IMAGE_CLASSIFIER_MODEL", "openai/clip-vit-base-patch32")
    deepface_detector_backend: str = os.getenv("BOARDSIGHT_DEEPFACE_DETECTOR", "opencv")
    video_sample_seconds: float = float(os.getenv("BOARDSIGHT_VIDEO_SAMPLE_SECONDS", "20.0"))
    visual_sample_seconds: float = float(os.getenv("BOARDSIGHT_VISUAL_SAMPLE_SECONDS", "45.0"))
    max_visual_samples: int = int(os.getenv("BOARDSIGHT_MAX_VISUAL_SAMPLES", "2"))
    max_attention_samples: int = int(os.getenv("BOARDSIGHT_MAX_ATTENTION_SAMPLES", "1"))
    max_face_samples: int = int(os.getenv("BOARDSIGHT_MAX_FACE_SAMPLES", "1"))
    max_workflow_segments: int = int(os.getenv("BOARDSIGHT_MAX_WORKFLOW_SEGMENTS", "12"))
    faster_whisper_model: str = os.getenv("BOARDSIGHT_FASTER_WHISPER_MODEL", "tiny.en")
    enable_diarization: bool = os.getenv("BOARDSIGHT_ENABLE_DIARIZATION", "false").lower() in {"1", "true", "yes", "on"}
    llm_provider: str = os.getenv("BOARDSIGHT_LLM_PROVIDER", "transformers")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")


def default_config(project_root: Path | None = None, output_root: Path | None = None) -> AppConfig:
    resolved_root = (project_root or Path(__file__).resolve().parents[2]).resolve()
    _load_local_env(resolved_root)
    resolved_output = (output_root or resolved_root / "output").resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    return AppConfig(project_root=resolved_root, output_root=resolved_output)
