package com.boardsight.service;

import java.nio.file.Path;

public record PipelineRunResult(
    int exitCode,
    Path outputDirectory,
    Path resultJsonPath
) {
}
