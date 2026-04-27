package com.boardsight.cli;

import com.boardsight.service.PipelineRunResult;
import com.boardsight.service.PythonPipelineRunner;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

public final class BoardSightCli {
    private BoardSightCli() {
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> parsed = parseArgs(args);
        if (parsed.containsKey("help") || !parsed.containsKey("video")) {
            printUsage();
            return;
        }

        Path projectRoot = Paths.get("").toAbsolutePath();
        Path videoPath = Paths.get(parsed.get("video")).toAbsolutePath();
        Path outputRoot = parsed.containsKey("output")
            ? Paths.get(parsed.get("output")).toAbsolutePath()
            : projectRoot.resolve("output").resolve("run-" + Instant.now().toEpochMilli());
        String pythonCommand = parsed.getOrDefault("python", "python");

        PythonPipelineRunner runner = new PythonPipelineRunner(projectRoot, pythonCommand);
        PipelineRunResult result = runner.run(videoPath, outputRoot);

        System.out.println("BoardSight pipeline completed.");
        System.out.println("Output directory: " + result.outputDirectory());
        System.out.println("Main result file: " + result.resultJsonPath());
        System.out.println("Python exit code: " + result.exitCode());
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> values = new HashMap<>();
        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            if ("--help".equals(arg) || "-h".equals(arg)) {
                values.put("help", "true");
                continue;
            }

            if (arg.startsWith("--")) {
                String key = arg.substring(2);
                if (i + 1 < args.length) {
                    values.put(key, args[++i]);
                }
            }
        }
        return values;
    }

    private static void printUsage() {
        System.out.println("Usage:");
        System.out.println("  java -jar boardsight.jar --video <path> [--python python] [--output <dir>]");
    }
}
