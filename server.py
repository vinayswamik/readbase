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
from src.backend.api.security_middleware import SecurityMiddleware
from src.backend.application.services.auth.config import validate_auth_secrets
from src.backend.application.services.confluence_service import start_confluence_sync_scheduler
from src.backend.application.services.notion_service import start_notion_sync_scheduler
from src.backend.application.services.jira_service import start_jira_sync_scheduler
from src.backend.application.services.linear_service import start_linear_sync_scheduler
from src.backend.application.services.slack_service import start_slack_sync_scheduler
from src.backend.infrastructure.database import init_database

# Local dev bind address and where the frontend build writes browser assets.
HOST = "127.0.0.1"
PORT = 8000
PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Readbase", version="0.2.0")
    validate_auth_secrets()
    init_database()
    app.add_middleware(SecurityMiddleware)
    app.include_router(api_router)
    start_jira_sync_scheduler()
    start_slack_sync_scheduler()
    start_linear_sync_scheduler()
    start_confluence_sync_scheduler()
    start_notion_sync_scheduler()
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
            "Frontend build missing. Run `python3 server.py` from the project root.",
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


# CLI entry: `python3 server.py` builds the frontend and starts uvicorn.
def build_frontend() -> None:
    """Build the Vite frontend before serving it from FastAPI."""
    if os.environ.get("READBASE_SKIP_FRONTEND_BUILD"):
        return
    if not (FRONTEND_DIR / "package.json").exists():
        raise RuntimeError(f"Frontend package not found at {FRONTEND_DIR}")
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=FRONTEND_DIR,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("npm is required to build the frontend before starting Readbase.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Frontend build failed. Fix the frontend errors and run again.") from exc


def main() -> None:
    build_frontend()
    release_port(PORT)
    ssl_certfile = os.getenv("READBASE_SSL_CERTFILE", "").strip()
    ssl_keyfile = os.getenv("READBASE_SSL_KEYFILE", "").strip()
    uvicorn_kwargs: dict = {"host": HOST, "port": PORT}
    if ssl_certfile and ssl_keyfile:
        cert_path = Path(ssl_certfile)
        key_path = Path(ssl_keyfile)
        if not cert_path.is_absolute():
            cert_path = PROJECT_ROOT / cert_path
        if not key_path.is_absolute():
            key_path = PROJECT_ROOT / key_path
        uvicorn_kwargs["ssl_certfile"] = str(cert_path)
        uvicorn_kwargs["ssl_keyfile"] = str(key_path)
        print(f"Readbase running at https://{HOST}:{PORT}")
    else:
        print(f"Readbase running at http://{HOST}:{PORT}")
    uvicorn.run(app, **uvicorn_kwargs)


if __name__ == "__main__":
    main()
