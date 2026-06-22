from __future__ import annotations

import os

NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_CALLBACK_PATH = "/api/me/integrations/notion/callback"
NOTION_OAUTH_STATE_TTL_SECONDS = 600
NOTION_API_VERSION = os.getenv("NOTION_API_VERSION", "2022-06-28").strip()
NOTION_VISIBILITY_CACHE_TTL_SECONDS = int(os.getenv("NOTION_VISIBILITY_CACHE_TTL_SECONDS", "300"))
NOTION_SYNC_LIMIT = int(os.getenv("NOTION_SYNC_LIMIT", "100"))
NOTION_SYNC_INTERVAL_SECONDS = int(os.getenv("NOTION_SYNC_INTERVAL_SECONDS", "900"))
NOTION_SYNC_SCHEDULER_DISABLED = os.getenv("NOTION_SYNC_SCHEDULER_DISABLED", "false").strip().lower() == "true"
