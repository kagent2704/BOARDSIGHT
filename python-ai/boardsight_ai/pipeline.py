from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from boardsight_ai.agentic_contract import build_agentic_contract
from boardsight_ai.config import AppConfig, default_config, resolve_runtime_config
from boardsight_ai.data_protection import write_protected_json
from boardsight_ai.evaluation import write_evaluation
from boardsight_ai.lightweight_pipeline import run_lightweight_pipeline
from boardsight_ai.models import PipelineResult
from boardsight_ai.reporting import write_structured_reports


def run_pipeline(
    video_path: Path,
    output_dir: Path,
    config: AppConfig | None = None,
    analysis_range: dict[str, float | None] | None = None,
    analysis_profile: str | None = None,
    source_mode: str = "recorded",
) -> PipelineResult:
    if config is None:
        runtime_config = resolve_runtime_config(
            default_config(output_root=output_dir),
            analysis_profile=analysis_profile,
            source_mode=source_mode,
        )
    else:
        runtime_config = config
    result = run_lightweight_pipeline(
        video_path,
        output_dir,
        runtime_config,
        analysis_range=analysis_range,
        requested_profile=analysis_profile or runtime_config.default_analysis_profile,
    )
    result.metadata["analysis_profile"] = analysis_profile or runtime_config.default_analysis_profile
    result.metadata["source_mode"] = source_mode
    result.metadata["agentic_contract"] = build_agentic_contract(
        result,
        analysis_profile=(analysis_profile or runtime_config.default_analysis_profile or "recorded-fast"),
        source_mode=source_mode,
        contract_version=runtime_config.analysis_contract_version,
    )
    return result


def write_result(result: PipelineResult, result_file: Path) -> Path:
    result_file.parent.mkdir(parents=True, exist_ok=True)
    report_files = write_structured_reports(result, result_file.parent)
    performance_report_path = write_evaluation(result, result_file.parent)
    payload: dict[str, Any] = result.to_dict()
    payload.setdefault("metadata", {})
    payload["metadata"]["report_files"] = report_files
    payload["metadata"]["performance_report_file"] = str(performance_report_path)
    return write_protected_json(result_file, payload)
