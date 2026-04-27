package com.boardsight.web;

import com.boardsight.web.api.ApiHandlers;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.Executors;

public final class BoardSightWebApp {
    private BoardSightWebApp() {
    }

    public static void main(String[] args) throws IOException {
        int port = parsePort(args);
        Path projectRoot = Paths.get("").toAbsolutePath();

        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        ApiHandlers.register(server, projectRoot);
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();

        System.out.println("BoardSight web app running on http://localhost:" + port);
    }

    private static int parsePort(String[] args) {
        for (int index = 0; index < args.length - 1; index++) {
            if ("--port".equals(args[index])) {
                return Integer.parseInt(args[index + 1]);
            }
        }
        return 8080;
    }
}
