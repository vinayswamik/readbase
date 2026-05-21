from __future__ import annotations

import os

LINEAR_AUTHORIZE_URL = "https://linear.app/oauth/authorize"
LINEAR_TOKEN_URL = "https://api.linear.app/oauth/token"
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
LINEAR_CALLBACK_PATH = "/api/me/integrations/linear/callback"
LINEAR_OAUTH_STATE_TTL_SECONDS = 600
LINEAR_SCOPES = os.getenv("LINEAR_OAUTH_SCOPES", "read").strip()
LINEAR_VISIBILITY_CACHE_TTL_SECONDS = int(os.getenv("LINEAR_VISIBILITY_CACHE_TTL_SECONDS", "300"))
LINEAR_SYNC_LIMIT = int(os.getenv("LINEAR_SYNC_LIMIT", "100"))
LINEAR_SYNC_INTERVAL_SECONDS = int(os.getenv("LINEAR_SYNC_INTERVAL_SECONDS", "900"))
LINEAR_SYNC_SCHEDULER_DISABLED = os.getenv("LINEAR_SYNC_SCHEDULER_DISABLED", "false").strip().lower() == "true"
