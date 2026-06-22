#!/usr/bin/env python3
"""Regenerate openapi.json and frontend TypeScript API types."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "openapi.json"
GENERATED = ROOT / "frontend" / "src" / "api" / "generated.ts"


def main() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "export_openapi.py")], check=True, cwd=ROOT)
    subprocess.run(
        [
            "npx",
            "--yes",
            "openapi-typescript@7.13.0",
            str(OPENAPI),
            "-o",
            str(GENERATED),
        ],
        check=True,
        cwd=ROOT,
    )
    print(f"Updated {OPENAPI.name} and {GENERATED.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
