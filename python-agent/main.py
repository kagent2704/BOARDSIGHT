from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app


AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_SERVICE_URI = os.getenv("BOARDSIGHT_AGENT_SESSION_URI", "sqlite+aiosqlite:///./sessions.db")
SERVE_WEB_INTERFACE = os.getenv("BOARDSIGHT_AGENT_SERVE_WEB", "true").strip().lower() in {"1", "true", "yes", "on"}

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=["*"],
    web=SERVE_WEB_INTERFACE,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "boardsight-adk-agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
