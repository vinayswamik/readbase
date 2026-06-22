#!/usr/bin/env python3
from __future__ import annotations

import argparse

from src.backend.infrastructure.database import init_database
from src.backend.infrastructure.storage.migrate_layout import migrate_legacy_layout


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy workspace storage to owner-based layout.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move directories. Without this flag the command only prints the migration plan.",
    )
    args = parser.parse_args()

    init_database()
    results = migrate_legacy_layout(dry_run=not args.apply)
    for item in results:
        status = "move" if item.moved else "skip"
        reason = f" ({item.skipped_reason})" if item.skipped_reason else ""
        print(f"[{status}] {item.workspace_id}: {item.source} -> {item.destination}{reason}")


if __name__ == "__main__":
    main()
