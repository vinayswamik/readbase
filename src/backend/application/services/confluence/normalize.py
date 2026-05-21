from __future__ import annotations

import hashlib
import re
from datetime import datetime
from html import unescape

from src.backend.infrastructure.models import WorkspaceConfluenceSource, utc_now


TAG_RE = re.compile(r"<[^>]+>")


def normalize_pages(source: WorkspaceConfluenceSource, pages: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for page in pages:
        page_id = str(page.get("id") or "")
        title = str(page.get("title") or page_id)
        body = page_body(page)
        if not page_id or not body:
            continue
        url = page_url(source.site_url, page_id)
        rows.append(
            {
                "source_id": source.source_id,
                "workspace_id": source.workspace_id,
                "cloud_id": source.cloud_id,
                "space_id": source.space_id,
                "space_key": source.space_key,
                "page_id": page_id,
                "item_type": "page",
                "item_id": page_id,
                "title": title[:500],
                "body": body,
                "source_url": url,
                "remote_updated_at": parse_time(page.get("version", {}).get("createdAt") if isinstance(page.get("version"), dict) else None),
                "content_hash": hashlib.sha256(f"{title}\n{body}".encode("utf-8")).hexdigest(),
                "indexed_at": utc_now(),
            }
        )
    return rows


def page_body(page: dict) -> str:
    body = page.get("body") if isinstance(page.get("body"), dict) else {}
    storage = body.get("storage") if isinstance(body.get("storage"), dict) else {}
    value = str(storage.get("value") or "")
    text = unescape(TAG_RE.sub(" ", value))
    return " ".join(text.split())


def page_url(site_url: str, page_id: str) -> str:
    return f"{site_url.rstrip('/').replace('/wiki', '')}/wiki/spaces/pages/{page_id}"


def parse_time(value: object):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
