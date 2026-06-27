from __future__ import annotations

import importlib
from pathlib import Path

import boardsight_ai.config as config_module


def test_default_config_loads_local_env_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BOARDSIGHT_FASTER_WHISPER_MODEL", raising=False)
    monkeypatch.delenv("BOARDSIGHT_GEMINI_MODEL", raising=False)

    project_root = tmp_path / "project"
    env_dir = project_root / "python-ai"
    env_dir.mkdir(parents=True)
    (env_dir / ".env").write_text(
        "BOARDSIGHT_FASTER_WHISPER_MODEL=base.en\n"
        "BOARDSIGHT_GEMINI_MODEL=gemini-test-fast\n",
        encoding="utf-8",
    )

    reloaded = importlib.reload(config_module)
    config = reloaded.default_config(project_root=project_root)

    assert config.project_root == project_root.resolve()
    assert config.output_root.exists()
    assert config.faster_whisper_model == "base.en"
    assert config.gemini_model == "gemini-test-fast"


def test_resolve_runtime_config_applies_profile_overrides(tmp_path: Path) -> None:
    config = config_module.default_config(project_root=tmp_path / "project")

    fast = config_module.resolve_runtime_config(config, analysis_profile="recorded-fast", source_mode="recorded")
    deep = config_module.resolve_runtime_config(config, analysis_profile="recorded-deep", source_mode="recorded")
    live = config_module.resolve_runtime_config(config, analysis_profile="live", source_mode="live")

    assert fast.max_visual_samples == 1
    assert fast.enable_visual_caption is False
    assert deep.enable_visual_ocr is True
    assert deep.max_workflow_segments == 24
    assert live.default_analysis_profile == "live"
    assert live.video_sample_seconds == 10.0
