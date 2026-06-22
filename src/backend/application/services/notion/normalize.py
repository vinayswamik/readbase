from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from src.backend.infrastructure.models import utc_now


def normalize_pages(source: dict[str, Any], pages: list[dict], bodies: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    for page in pages:
        page_id = str(page.get("id") or "")
        title = page_title(page)
        body = bodies.get(page_id, "")
        if not page_id or not body:
            continue
        url = str(page.get("url") or notion_page_url(page_id))
        rows.append(
            {
                "source_id": str(source.get("source_id") or ""),
                "workspace_id": str(source.get("workspace_id") or ""),
                "notion_workspace_id": str(source.get("notion_workspace_id") or ""),
                "database_id": str(source.get("database_id") or ""),
                "page_id": page_id,
                "item_type": "page",
                "item_id": page_id,
                "title": title[:500],
                "body": body,
                "source_url": url,
                "remote_updated_at": parse_time(page.get("last_edited_time")),
                "content_hash": hashlib.sha256(f"{title}\n{body}".encode("utf-8")).hexdigest(),
                "indexed_at": utc_now(),
            }
        )
    return rows


def page_title(page: dict) -> str:
    properties = page.get("properties") if isinstance(page.get("properties"), dict) else {}
    for value in properties.values():
        if not isinstance(value, dict):
            continue
        if value.get("type") == "title":
            title = value.get("title")
            if isinstance(title, list):
                parts = [str(item.get("plain_text") or "") for item in title if isinstance(item, dict)]
                text = "".join(parts).strip()
                if text:
                    return text
    return str(page.get("id") or "Untitled")


def rich_text_to_plain(rich_text: list) -> str:
    return "".join(str(item.get("plain_text") or "") for item in rich_text if isinstance(item, dict))


def blocks_to_text(blocks: list[dict]) -> str:
    parts: list[str] = []
    for block in blocks:
        block_type = str(block.get("type") or "")
        payload = block.get(block_type) if isinstance(block.get(block_type), dict) else {}
        rich_text = payload.get("rich_text") if isinstance(payload.get("rich_text"), list) else []
        text = rich_text_to_plain(rich_text).strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def notion_page_url(page_id: str) -> str:
    return f"https://www.notion.so/{page_id.replace('-', '')}"


def parse_time(value: object):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
