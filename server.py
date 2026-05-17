from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from src.backend.api.routes import api_router

# Local dev bind address and where the frontend build writes browser assets.
HOST = "127.0.0.1"
PORT = 8000
FRONTEND_DIST_DIR = Path(__file__).resolve().parent / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Readbase", version="0.2.0")
    app.include_router(api_router)
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


# CLI entry: `python server.py` starts uvicorn, the ASGI server FastAPI runs on.
def main() -> None:
    print(f"Readbase running at http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
