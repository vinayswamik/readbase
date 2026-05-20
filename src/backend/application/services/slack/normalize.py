from __future__ import annotations

import hashlib
import re

from src.backend.infrastructure.models import utc_now

from .utils import slack_ts_to_datetime

MENTION_RE = re.compile(r"<@([A-Z0-9]+)>")
LINK_RE = re.compile(r"<([^|>]+)\|?([^>]*)>")


def normalize_messages(source: dict, messages: list[dict]) -> list[dict]:
    items: list[dict] = []
    for message in messages:
        text = normalize_text(str(message.get("text") or ""))
        message_ts = str(message.get("ts") or "")
        if not text or not message_ts or message.get("subtype") in {"message_deleted"}:
            continue
        thread_ts = str(message.get("thread_ts") or "") or None
        item_type = "thread_reply" if thread_ts and thread_ts != message_ts else "message"
        item_id = f"{source['channel_id']}:{message_ts}"
        title = f"#{source['channel_name']} Slack {item_type.replace('_', ' ')}"
        body = build_body(message, text)
        items.append(
            {
                "source_id": source["source_id"],
                "workspace_id": source["workspace_id"],
                "team_id": source["team_id"],
                "team_name": source["team_name"],
                "channel_id": source["channel_id"],
                "channel_name": source["channel_name"],
                "message_ts": message_ts,
                "thread_ts": thread_ts,
                "item_type": item_type,
                "item_id": item_id,
                "title": title,
                "body": body,
                "source_url": slack_message_url(source, message_ts),
                "remote_updated_at": slack_ts_to_datetime(message_ts),
                "content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "indexed_at": utc_now(),
            }
        )
    return items


def build_body(message: dict, text: str) -> str:
    user = str(message.get("user") or message.get("bot_id") or "unknown")
    timestamp = str(message.get("ts") or "")
    return f"user: {user}\nts: {timestamp}\n\n{text}"


def normalize_text(text: str) -> str:
    text = MENTION_RE.sub(r"@\1", text)
    text = LINK_RE.sub(lambda match: match.group(2) or match.group(1), text)
    return text.strip()


def slack_message_url(source: dict, message_ts: str) -> str:
    compact_ts = message_ts.replace(".", "")
    domain = source.get("team_domain")
    if domain:
        return f"https://{domain}.slack.com/archives/{source['channel_id']}/p{compact_ts}"
    return f"slack://{source['team_id']}/{source['channel_id']}/{message_ts}"
