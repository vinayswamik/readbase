from __future__ import annotations

import os

BITBUCKET_AUTHORIZE_URL = "https://bitbucket.org/site/oauth2/authorize"
BITBUCKET_TOKEN_URL = "https://bitbucket.org/site/oauth2/access_token"
BITBUCKET_API_URL = "https://api.bitbucket.org/2.0"
BITBUCKET_CALLBACK_PATH = "/api/me/integrations/bitbucket/callback"
BITBUCKET_OAUTH_STATE_TTL_SECONDS = 600
BITBUCKET_SCOPES = os.getenv("BITBUCKET_OAUTH_SCOPES", "account repository").strip()
