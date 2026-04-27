from __future__ import annotations

import subprocess
from pathlib import Path

from .runtime import optional_import


def probe_video(video_path: Path) -> dict:
    cv2 = optional_import("cv2")
    if cv2 is None:
        return {
            "path": str(video_path),
            "fps": None,
            "frame_count": None,
            "duration_sec": None,
            "width": None,
            "height": None,
            "mode": "metadata-unavailable",
        }

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {
            "path": str(video_path),
            "fps": None,
            "frame_count": None,
            "duration_sec": None,
            "width": None,
            "height": None,
            "mode": "open-failed",
        }

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    duration = round(frame_count / fps, 2) if fps else None

    return {
        "path": str(video_path),
        "fps": fps,
        "frame_count": frame_count,
        "duration_sec": duration,
        "width": width,
        "height": height,
        "mode": "opencv",
    }


def clip_video_fast(
    input_path: Path,
    output_path: Path,
    start_seconds: float | None,
    end_seconds: float | None,
) -> dict:
    probe = probe_video(input_path)
    duration = probe.get("duration_sec")
    resolved_start = max(0.0, float(start_seconds or 0.0))
    resolved_end = float(end_seconds) if end_seconds is not None else None

    if resolved_end is not None and duration is not None:
        resolved_end = min(resolved_end, float(duration))
    if resolved_end is not None and resolved_end <= resolved_start:
        raise ValueError("End time must be greater than start time.")

    if resolved_start <= 0.0 and (resolved_end is None or (duration is not None and resolved_end >= float(duration))):
        return {
            "mode": "full-video",
            "source_path": str(input_path),
            "output_path": str(input_path),
            "start_seconds": 0.0,
            "end_seconds": float(duration) if duration is not None else None,
            "duration_seconds": float(duration) if duration is not None else None,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{resolved_start:.3f}",
        "-i",
        str(input_path),
    ]
    if resolved_end is not None:
        command.extend(["-to", f"{resolved_end:.3f}"])
    command.extend([
        "-c",
        "copy",
        "-avoid_negative_ts",
        "make_zero",
        str(output_path),
    ])
    subprocess.run(command, check=True, capture_output=True)

    clipped_probe = probe_video(output_path)
    return {
        "mode": "ffmpeg-fast-seek-copy",
        "source_path": str(input_path),
        "output_path": str(output_path),
        "start_seconds": resolved_start,
        "end_seconds": resolved_end,
        "duration_seconds": clipped_probe.get("duration_sec"),
    }
