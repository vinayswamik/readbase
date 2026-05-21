from __future__ import annotations

import os

GITLAB_AUTHORIZE_URL = "https://gitlab.com/oauth/authorize"
GITLAB_TOKEN_URL = "https://gitlab.com/oauth/token"
GITLAB_API_URL = "https://gitlab.com/api/v4"
GITLAB_CALLBACK_PATH = "/api/me/integrations/gitlab/callback"
GITLAB_OAUTH_STATE_TTL_SECONDS = 600
GITLAB_SCOPES = os.getenv("GITLAB_OAUTH_SCOPES", "read_user read_api read_repository").strip()
