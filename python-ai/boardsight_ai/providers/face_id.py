from __future__ import annotations

from pathlib import Path

from .runtime import optional_import


def detect_known_faces(video_path: Path, sample_every_seconds: float = 8.0, max_samples: int = 8) -> list[dict]:
    cv2 = optional_import("cv2")
    face_recognition = optional_import("face_recognition")
    if cv2 is None or face_recognition is None:
        return []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    stride = max(1, int(fps * sample_every_seconds))
    identities: list[dict] = []
    known_encodings: list = []

    for frame_index in list(range(0, max(1, frame_count), stride))[:max_samples]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = cap.read()
        if not ret:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, model="cnn")
        encodings = face_recognition.face_encodings(rgb, locations)

        for location, encoding in zip(locations, encodings):
            matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.52) if known_encodings else []
            try:
                index = matches.index(True)
                face_id = f"Face-{index + 1}"
            except ValueError:
                known_encodings.append(encoding)
                face_id = f"Face-{len(known_encodings)}"

            identities.append(
                {
                    "identity_id": face_id,
                    "label": face_id,
                    "tracking_mode": "face-encoding",
                    "timestamp": round(frame_index / fps, 2),
                    "bbox": [int(value) for value in location],
                }
            )

    cap.release()
    return identities
