from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from .utils import display_name, name_field, parse_datetime


def normalize_issues(source: dict, issues: list[dict]) -> list[dict]:
    items: list[dict] = []
    for issue in issues:
        issue_id = str(issue.get("id") or "")
        issue_key = str(issue.get("key") or "")
        fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
        if not issue_id or not issue_key:
            continue
        summary = str(fields.get("summary") or issue_key)
        updated = parse_datetime(fields.get("updated"))
        issue_url = f'{source["site_url"].rstrip("/")}/browse/{issue_key}'
        issue_body = issue_body_text(issue_key, summary, fields)
        items.append(item(source, issue_id, issue_key, "issue", issue_id, summary, issue_body, issue_url, updated))

        comment_data = fields.get("comment") if isinstance(fields.get("comment"), dict) else {}
        for comment in comment_data.get("comments", []) if isinstance(comment_data.get("comments"), list) else []:
            comment_id = str(comment.get("id") or "")
            body = adf_to_text(comment.get("body"))
            if comment_id and body:
                author = display_name(comment.get("author"))
                title = f"{issue_key} comment by {author or 'Jira user'}"
                text = f"Issue: {issue_key} {summary}\nComment author: {author}\n\n{body}"
                items.append(item(source, issue_id, issue_key, "comment", comment_id, title, text, issue_url, parse_datetime(comment.get("updated"))))

        worklog_data = fields.get("worklog") if isinstance(fields.get("worklog"), dict) else {}
        for worklog in worklog_data.get("worklogs", []) if isinstance(worklog_data.get("worklogs"), list) else []:
            worklog_id = str(worklog.get("id") or "")
            body = adf_to_text(worklog.get("comment"))
            if worklog_id and body:
                author = display_name(worklog.get("author"))
                title = f"{issue_key} worklog by {author or 'Jira user'}"
                text = f"Issue: {issue_key} {summary}\nWorklog author: {author}\n\n{body}"
                items.append(item(source, issue_id, issue_key, "worklog", worklog_id, title, text, issue_url, parse_datetime(worklog.get("updated"))))

        attachments = fields.get("attachment") if isinstance(fields.get("attachment"), list) else []
        for attachment in attachments:
            attachment_id = str(attachment.get("id") or "")
            filename = str(attachment.get("filename") or "")
            if attachment_id and filename:
                author = display_name(attachment.get("author"))
                title = f"{issue_key} attachment {filename}"
                text = f"Issue: {issue_key} {summary}\nAttachment: {filename}\nAuthor: {author}"
                items.append(item(source, issue_id, issue_key, "attachment", attachment_id, title, text, issue_url, parse_datetime(attachment.get("created"))))
    return items


def item(
    source: dict,
    issue_id: str,
    issue_key: str,
    item_type: str,
    item_id: str,
    title: str,
    body: str,
    source_url: str,
    remote_updated_at: datetime | None,
) -> dict:
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return {
        "source_id": source["source_id"],
        "workspace_id": source["workspace_id"],
        "cloud_id": source["cloud_id"],
        "project_id": source["project_id"],
        "project_key": source["project_key"],
        "issue_id": issue_id,
        "issue_key": issue_key,
        "item_type": item_type,
        "item_id": item_id,
        "title": title[:500],
        "body": body,
        "source_url": source_url,
        "remote_updated_at": remote_updated_at,
        "content_hash": content_hash,
    }


def issue_body_text(issue_key: str, summary: str, fields: dict) -> str:
    parts = [f"Issue: {issue_key}", f"Summary: {summary}"]
    description = adf_to_text(fields.get("description"))
    if description:
        parts.append(f"Description:\n{description}")
    for label, value in (
        ("Status", name_field(fields.get("status"))),
        ("Assignee", display_name(fields.get("assignee"))),
        ("Reporter", display_name(fields.get("reporter"))),
        ("Priority", name_field(fields.get("priority"))),
    ):
        if value:
            parts.append(f"{label}: {value}")
    labels = fields.get("labels")
    if isinstance(labels, list) and labels:
        parts.append(f"Labels: {', '.join(str(label) for label in labels)}")
    return "\n".join(parts)


def adf_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(adf_to_text(item) for item in value).strip()
    if not isinstance(value, dict):
        return str(value).strip()
    if isinstance(value.get("text"), str):
        return value["text"]
    content = value.get("content")
    if isinstance(content, list):
        return "\n".join(part for part in (adf_to_text(item) for item in content) if part).strip()
    return ""
