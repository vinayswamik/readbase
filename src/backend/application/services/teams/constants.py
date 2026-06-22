from __future__ import annotations

import os

TEAMS_TENANT = os.getenv("MICROSOFT_TENANT_ID", "organizations").strip() or "organizations"
MICROSOFT_AUTHORIZE_URL = f"https://login.microsoftonline.com/{TEAMS_TENANT}/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = f"https://login.microsoftonline.com/{TEAMS_TENANT}/oauth2/v2.0/token"
MICROSOFT_GRAPH_URL = "https://graph.microsoft.com/v1.0"
TEAMS_CALLBACK_PATH = "/api/me/integrations/teams/callback"
TEAMS_OAUTH_STATE_TTL_SECONDS = 600
TEAMS_OAUTH_SCOPES = os.getenv(
    "MICROSOFT_TEAMS_OAUTH_SCOPES",
    "User.Read Team.ReadBasic.All offline_access",
).strip()
