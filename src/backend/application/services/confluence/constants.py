from __future__ import annotations

import os

ATLASSIAN_AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
ATLASSIAN_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ATLASSIAN_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
ATLASSIAN_ME_URL = "https://api.atlassian.com/me"
CONFLUENCE_CALLBACK_PATH = "/api/me/integrations/confluence/callback"
CONFLUENCE_OAUTH_STATE_TTL_SECONDS = 600
CONFLUENCE_VISIBILITY_CACHE_TTL_SECONDS = int(os.getenv("CONFLUENCE_VISIBILITY_CACHE_TTL_SECONDS", "300"))
CONFLUENCE_SYNC_LIMIT = int(os.getenv("CONFLUENCE_SYNC_LIMIT", "100"))
CONFLUENCE_SYNC_INTERVAL_SECONDS = int(os.getenv("CONFLUENCE_SYNC_INTERVAL_SECONDS", "900"))
CONFLUENCE_SYNC_SCHEDULER_DISABLED = os.getenv("CONFLUENCE_SYNC_SCHEDULER_DISABLED", "false").strip().lower() == "true"
CONFLUENCE_SCOPES = os.getenv(
    "CONFLUENCE_OAUTH_SCOPES",
    "read:space:confluence read:page:confluence read:confluence-space.summary read:confluence-content.all offline_access",
).strip()
