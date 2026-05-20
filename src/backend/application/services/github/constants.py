from __future__ import annotations

import os

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"
GITHUB_CALLBACK_PATH = "/api/me/integrations/github/callback"
GITHUB_OAUTH_STATE_TTL_SECONDS = 600
GITHUB_SCOPES = os.getenv("GITHUB_OAUTH_SCOPES", "repo read:user").strip()
