from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .runtime import dependency_available, optional_import


def face_capabilities() -> dict[str, bool]:
    return {
        "opencv": dependency_available("cv2"),
        "face_recognition": dependency_available("face_recognition"),
    }


def yolo_capabilities() -> dict[str, bool]:
    return {
        "opencv": dependency_available("cv2"),
        "ultralytics": dependency_available("ultralytics"),
    }


@lru_cache(maxsize=2)
def _yolo_model(model_name: str):
    ultralytics = optional_import("ultralytics")
    if ultralytics is None:
        return None
    try:
        return ultralytics.YOLO(model_name)
    except Exception:
        return None


def detect_chart_like_objects(frame, model_name: str) -> list[dict]:
    model = _yolo_model(model_name)
    if model is None:
        return []

    try:
        results = model.predict(frame, verbose=False)
        detections: list[dict] = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                label = result.names[class_id]
                if label.lower() in {"tv", "laptop", "book", "cell phone", "monitor"}:
                    detections.append(
                        {
                            "label": label,
                            "confidence": round(float(box.conf[0]), 3),
                        }
                    )
        return detections
    except Exception:
        return []


def safe_open_video(video_path: Path):
    cv2 = optional_import("cv2")
    if cv2 is None:
        return None, None
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None, cv2
    return cap, cv2
