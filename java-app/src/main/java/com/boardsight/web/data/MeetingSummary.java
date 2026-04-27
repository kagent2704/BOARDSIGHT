package com.boardsight.web.data;

public record MeetingSummary(
    String id,
    String title,
    double decisions,
    double impactScore,
    double productivityScore,
    double executionReadiness,
    double overallAttention,
    double dominanceRatio,
    String conclusion,
    String createdAt
) {
    public String toJson() {
        return "{"
            + "\"id\":\"" + escape(id) + "\","
            + "\"title\":\"" + escape(title) + "\","
            + "\"decisions\":" + decisions + ","
            + "\"impactScore\":" + impactScore + ","
            + "\"productivityScore\":" + productivityScore + ","
            + "\"executionReadiness\":" + executionReadiness + ","
            + "\"overallAttention\":" + overallAttention + ","
            + "\"dominanceRatio\":" + dominanceRatio + ","
            + "\"conclusion\":\"" + escape(conclusion) + "\","
            + "\"createdAt\":\"" + escape(createdAt) + "\""
            + "}";
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
