from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from src.backend.api.routes import api_router
from src.backend.application.services.confluence_service import start_confluence_sync_scheduler
from src.backend.application.services.jira_service import start_jira_sync_scheduler
from src.backend.application.services.linear_service import start_linear_sync_scheduler
from src.backend.application.services.slack_service import start_slack_sync_scheduler
from src.backend.infrastructure.database import init_database

# Local dev bind address and where the frontend build writes browser assets.
HOST = "127.0.0.1"
PORT = 8000
FRONTEND_DIST_DIR = Path(__file__).resolve().parent / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Readbase", version="0.2.0")
    init_database()
    app.include_router(api_router)
    start_jira_sync_scheduler()
    start_slack_sync_scheduler()
    start_linear_sync_scheduler()
    start_confluence_sync_scheduler()
    app.get("/", response_model=None)(frontend_root)
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST_DIR / "assets", check_dir=False),
        name="assets",
    )
    return app


# Root route serves the Vite-built browser UI.
def frontend_root() -> Response:
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.exists():
        return PlainTextResponse(
            "Frontend build missing. Run `npm install` and `npm run build` from frontend/.",
            status_code=503,
        )
    return FileResponse(
        index_file,
        headers={"Cache-Control": "no-store"},
    )


app = create_app()


def release_port(port: int) -> None:
    """Stop any process already listening on `port` (typical stale server)."""
    if os.environ.get("READBASE_SKIP_PORT_FREE"):
        return
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f"TCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return
    my_pid = os.getpid()
    pids: list[int] = []
    for line in out.splitlines():
        pid = int(line.strip())
        if pid != my_pid:
            pids.append(pid)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(0.3)
    try:
        still = subprocess.check_output(
            ["lsof", "-ti", f"TCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return
    for line in still.splitlines():
        pid = int(line.strip())
        if pid == my_pid:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(0.1)


# CLI entry: `python server.py` starts uvicorn, the ASGI server FastAPI runs on.
def main() -> None:
    release_port(PORT)
    print(f"Readbase running at http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
