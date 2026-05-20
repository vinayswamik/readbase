from __future__ import annotations

import os

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_API_URL = "https://slack.com/api"
SLACK_CALLBACK_PATH = "/api/me/integrations/slack/callback"
SLACK_OAUTH_STATE_TTL_SECONDS = 600
SLACK_VISIBILITY_CACHE_TTL_SECONDS = int(os.getenv("SLACK_VISIBILITY_CACHE_TTL_SECONDS", "300"))
SLACK_SYNC_INTERVAL_SECONDS = int(os.getenv("SLACK_SYNC_INTERVAL_SECONDS", os.getenv("JIRA_SYNC_INTERVAL_SECONDS", "900")))
SLACK_SYNC_LIMIT = int(os.getenv("SLACK_SYNC_LIMIT", "50"))
SLACK_THREAD_SYNC_LIMIT = int(os.getenv("SLACK_THREAD_SYNC_LIMIT", "20"))
SLACK_SYNC_SCHEDULER_DISABLED = os.getenv("SLACK_SYNC_SCHEDULER_DISABLED", "false").strip().lower() == "true"
SLACK_USER_SCOPES = os.getenv(
    "SLACK_USER_SCOPES",
    "channels:read,groups:read,channels:history,groups:history,users:read,team:read",
).strip()
