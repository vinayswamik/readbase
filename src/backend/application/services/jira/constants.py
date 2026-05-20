from __future__ import annotations

import os

ATLASSIAN_AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
ATLASSIAN_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ATLASSIAN_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
ATLASSIAN_ME_URL = "https://api.atlassian.com/me"
JIRA_CALLBACK_PATH = "/api/me/integrations/jira/callback"
JIRA_OAUTH_STATE_TTL_SECONDS = 600
JIRA_VISIBILITY_CACHE_TTL_SECONDS = int(os.getenv("JIRA_VISIBILITY_CACHE_TTL_SECONDS", "300"))
JIRA_SYNC_LIMIT = int(os.getenv("JIRA_SYNC_LIMIT", "100"))
JIRA_SYNC_INTERVAL_SECONDS = int(os.getenv("JIRA_SYNC_INTERVAL_SECONDS", "900"))
JIRA_SYNC_SCHEDULER_DISABLED = os.getenv("JIRA_SYNC_SCHEDULER_DISABLED", "false").strip().lower() == "true"
JIRA_SCOPES = os.getenv(
    "JIRA_OAUTH_SCOPES",
    "read:jira-work read:jira-user offline_access",
).strip()
