#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backend.infrastructure.database import init_database, session_scope
from src.backend.infrastructure.models import (
    OrgSource,
    Workspace,
    WorkspaceConfluenceSource,
    WorkspaceJiraSource,
    WorkspaceLinearSource,
    WorkspaceNotionSource,
    WorkspaceSlackSource,
    WorkspaceSourceSubscription,
    utc_now,
)


@dataclass
class SourceRecord:
    provider: str
    workspace_id: str
    added_by_user_id: str
    display_name: str
    source_url: str | None
    external_key: str
    metadata: dict
    legacy_source_id: str | None = None


def stable_source_id(org_id: str, provider: str, external_key: str) -> str:
    digest = hashlib.sha1(f"{org_id}:{provider}:{external_key}".encode("utf-8")).hexdigest()
    return f"orgsrc-{digest[:24]}"


def collect_workspace_sources() -> list[SourceRecord]:
    records: list[SourceRecord] = []
    with session_scope() as session:
        for row in session.scalars(select(WorkspaceSlackSource)).all():
            records.append(
                SourceRecord(
                    provider="slack",
                    workspace_id=row.workspace_id,
                    added_by_user_id=row.added_by_user_id,
                    display_name=f"{row.team_name} #{row.channel_name}",
                    source_url=None,
                    external_key=f"{row.team_id}:{row.channel_id}",
                    metadata={
                        "team_id": row.team_id,
                        "team_name": row.team_name,
                        "team_domain": row.team_domain,
                        "channel_id": row.channel_id,
                        "channel_name": row.channel_name,
                        "channel_is_private": row.channel_is_private,
                        "last_message_ts": row.last_message_ts or "",
                    },
                    legacy_source_id=row.source_id,
                )
            )
        for row in session.scalars(select(WorkspaceJiraSource)).all():
            records.append(
                SourceRecord(
                    provider="jira",
                    workspace_id=row.workspace_id,
                    added_by_user_id=row.added_by_user_id,
                    display_name=f"{row.site_name} {row.project_key}",
                    source_url=row.site_url,
                    external_key=f"{row.cloud_id}:{row.project_id}",
                    metadata={
                        "cloud_id": row.cloud_id,
                        "site_name": row.site_name,
                        "site_url": row.site_url,
                        "project_id": row.project_id,
                        "project_key": row.project_key,
                        "project_name": row.project_name,
                    },
                )
            )
        for row in session.scalars(select(WorkspaceLinearSource)).all():
            records.append(
                SourceRecord(
                    provider="linear",
                    workspace_id=row.workspace_id,
                    added_by_user_id=row.added_by_user_id,
                    display_name=f"{row.team_name} / {row.project_name or 'all issues'}",
                    source_url=None,
                    external_key=f"{row.linear_team_id}:{row.linear_project_id or ''}",
                    metadata={
                        "linear_team_id": row.linear_team_id,
                        "team_name": row.team_name,
                        "linear_project_id": row.linear_project_id,
                        "project_name": row.project_name,
                    },
                )
            )
        for row in session.scalars(select(WorkspaceConfluenceSource)).all():
            records.append(
                SourceRecord(
                    provider="confluence",
                    workspace_id=row.workspace_id,
                    added_by_user_id=row.added_by_user_id,
                    display_name=f"{row.site_name} {row.space_key}",
                    source_url=row.site_url,
                    external_key=f"{row.cloud_id}:{row.space_id}",
                    metadata={
                        "cloud_id": row.cloud_id,
                        "site_name": row.site_name,
                        "site_url": row.site_url,
                        "space_id": row.space_id,
                        "space_key": row.space_key,
                        "space_name": row.space_name,
                    },
                )
            )
        for row in session.scalars(select(WorkspaceNotionSource)).all():
            records.append(
                SourceRecord(
                    provider="notion",
                    workspace_id=row.workspace_id,
                    added_by_user_id=row.added_by_user_id,
                    display_name=row.database_title,
                    source_url=None,
                    external_key=f"{row.notion_workspace_id}:{row.database_id}",
                    metadata={
                        "notion_workspace_id": row.notion_workspace_id,
                        "database_id": row.database_id,
                        "database_title": row.database_title,
                    },
                )
            )
    return records


def migrate_workspace_sources(*, apply: bool) -> dict[str, int]:
    records = collect_workspace_sources()
    counters = {
        "processed": 0,
        "skipped_no_org": 0,
        "org_sources_created": 0,
        "subscriptions_created": 0,
    }
    with session_scope() as session:
        for record in records:
            counters["processed"] += 1
            workspace = session.get(Workspace, record.workspace_id)
            org_id = (workspace.organization_id if workspace else None) or ""
            if not org_id:
                counters["skipped_no_org"] += 1
                continue
            existing_source = session.scalar(
                select(OrgSource).where(
                    OrgSource.org_id == org_id,
                    OrgSource.provider == record.provider,
                    OrgSource.external_key == record.external_key,
                )
            )
            if existing_source is None:
                existing_source = OrgSource(
                    source_id=record.legacy_source_id or stable_source_id(org_id, record.provider, record.external_key),
                    org_id=org_id,
                    provider=record.provider,
                    external_key=record.external_key,
                    display_name=record.display_name,
                    source_url=record.source_url,
                    metadata_json=json.dumps(record.metadata, sort_keys=True),
                    added_by_user_id=record.added_by_user_id,
                    sync_owner_user_id=record.added_by_user_id,
                    sync_status="idle",
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                counters["org_sources_created"] += 1
                if apply:
                    session.add(existing_source)
                    session.flush()
            existing_sub = session.scalar(
                select(WorkspaceSourceSubscription).where(
                    WorkspaceSourceSubscription.workspace_id == record.workspace_id,
                    WorkspaceSourceSubscription.source_id == existing_source.source_id,
                )
            )
            if existing_sub is None:
                counters["subscriptions_created"] += 1
                if apply:
                    session.add(
                        WorkspaceSourceSubscription(
                            workspace_id=record.workspace_id,
                            source_id=existing_source.source_id,
                            added_by_user_id=record.added_by_user_id,
                            created_at=utc_now(),
                            updated_at=utc_now(),
                        )
                    )
    return counters


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill org-level source registry from existing workspace source tables."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag, prints a dry-run summary.",
    )
    args = parser.parse_args()

    init_database()
    counters = migrate_workspace_sources(apply=args.apply)
    print("org-source backfill summary:")
    for key, value in counters.items():
        print(f"- {key}: {value}")
    print(f"- mode: {'apply' if args.apply else 'dry-run'}")


if __name__ == "__main__":
    main()
