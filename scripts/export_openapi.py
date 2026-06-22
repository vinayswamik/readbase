#!/usr/bin/env python3
"""Export the FastAPI OpenAPI schema for frontend type generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI

from src.backend.api.routes import api_router


def build_openapi_app() -> FastAPI:
    app = FastAPI(title="Readbase", version="0.2.0")
    app.include_router(api_router)
    return app


def main() -> None:
    output = ROOT / "openapi.json"
    output.write_text(json.dumps(build_openapi_app().openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
