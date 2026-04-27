package com.boardsight.web.http;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public record MultipartFormData(String fileName, byte[] bytes) {
    public static MultipartFormData parse(InputStream input, String contentType) throws IOException {
        if (contentType == null || !contentType.contains("boundary=")) {
            return null;
        }
        String boundary = "--" + contentType.substring(contentType.indexOf("boundary=") + 9).trim();
        byte[] body = readAllBytes(input);
        String text = new String(body, StandardCharsets.ISO_8859_1);
        String[] parts = text.split(boundary);
        for (String part : parts) {
            if (!part.contains("filename=\"")) {
                continue;
            }
            int nameStart = part.indexOf("filename=\"") + 10;
            int nameEnd = part.indexOf("\"", nameStart);
            String fileName = part.substring(nameStart, nameEnd);

            int dataStart = part.indexOf("\r\n\r\n");
            if (dataStart < 0) {
                continue;
            }
            dataStart += 4;
            int dataEnd = part.lastIndexOf("\r\n");
            if (dataEnd < dataStart) {
                continue;
            }
            byte[] bytes = part.substring(dataStart, dataEnd).getBytes(StandardCharsets.ISO_8859_1);
            return new MultipartFormData(fileName, bytes);
        }
        return null;
    }

    private static byte[] readAllBytes(InputStream input) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        input.transferTo(output);
        return output.toByteArray();
    }
}
