package com.boardsight.web.data;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class MeetingRepository {
    private static final Pattern IMPACT_PATTERN = Pattern.compile("\"impact_score\"\\s*:\\s*([0-9.]+)");
    private static final Pattern PRODUCTIVITY_PATTERN = Pattern.compile("\"productivity_score\"\\s*:\\s*([0-9.]+)");
    private static final Pattern EXECUTION_PATTERN = Pattern.compile("\"execution_readiness\"\\s*:\\s*([0-9.]+)");
    private static final Pattern CONCLUSION_PATTERN = Pattern.compile("\"meeting_conclusion\"\\s*:\\s*\"([^\"]*)\"");
    private static final Pattern ATTENTION_PATTERN = Pattern.compile("\"overall_attention\"\\s*:\\s*([0-9.]+)");
    private static final Pattern DOMINANCE_PATTERN = Pattern.compile("\"dominance_ratio\"\\s*:\\s*([0-9.]+)");
    private static final Pattern DECISION_EVENT_PATTERN = Pattern.compile("\"event_id\"\\s*:\\s*\"DM-");

    private final Path outputRoot;

    public MeetingRepository(Path outputRoot) {
        this.outputRoot = outputRoot;
    }

    public void refresh() {
        // no-op, filesystem-backed repository
    }

    public String listMeetingsJson() throws IOException {
        List<String> items = new ArrayList<>();
        for (MeetingSummary summary : listMeetings()) {
            items.add(summary.toJson());
        }
        return "{\"items\":[" + String.join(",", items) + "]}";
    }

    public List<MeetingSummary> listMeetings() throws IOException {
        List<MeetingSummary> items = new ArrayList<>();
        if (!Files.exists(outputRoot)) {
            return items;
        }

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(outputRoot)) {
            for (Path path : stream) {
                if (!Files.isDirectory(path)) {
                    continue;
                }
                Path jsonPath = path.resolve("boardsight_result.json");
                if (!Files.exists(jsonPath)) {
                    continue;
                }
                String content = Files.readString(jsonPath, StandardCharsets.UTF_8);
                items.add(
                    new MeetingSummary(
                        path.getFileName().toString(),
                        path.getFileName().toString().replace('-', ' '),
                        extractNumber(DECISION_EVENT_PATTERN.matcher(content).results().count()),
                        extractNumber(IMPACT_PATTERN, content),
                        extractNumber(PRODUCTIVITY_PATTERN, content),
                        extractNumber(EXECUTION_PATTERN, content),
                        extractNumber(ATTENTION_PATTERN, content),
                        extractNumber(DOMINANCE_PATTERN, content),
                        extractString(CONCLUSION_PATTERN, content),
                        Files.getLastModifiedTime(jsonPath).toInstant().toString()
                    )
                );
            }
        }

        items.sort(Comparator.comparing(MeetingSummary::createdAt).reversed());
        return items;
    }

    public String loadMeetingJson(String id) throws IOException {
        Path path = outputRoot.resolve(id).resolve("boardsight_result.json");
        if (!Files.exists(path)) {
            return null;
        }
        return Files.readString(path, StandardCharsets.UTF_8);
    }

    public Path resolveReport(String id, String fileName) {
        Path candidate = outputRoot.resolve(id).resolve(fileName);
        if (!candidate.normalize().startsWith(outputRoot.normalize())) {
            return null;
        }
        return candidate;
    }

    private static double extractNumber(Pattern pattern, String content) {
        Matcher matcher = pattern.matcher(content);
        if (matcher.find()) {
            return Double.parseDouble(matcher.group(1));
        }
        return 0.0;
    }

    private static double extractNumber(long count) {
        return (double) count;
    }

    private static String extractString(Pattern pattern, String content) {
        Matcher matcher = pattern.matcher(content);
        if (matcher.find()) {
            return matcher.group(1).replace("\\\"", "\"");
        }
        return "BoardSight analysis ready.";
    }
}
