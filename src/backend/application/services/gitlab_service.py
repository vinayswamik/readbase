from __future__ import annotations

from src.backend.application.services.gitlab import (
    GITLAB_OAUTH_STATE_TTL_SECONDS,
    build_gitlab_authorize_url,
    can_user_access_gitlab_project,
    create_gitlab_oauth_state,
    disconnect_gitlab,
    exchange_gitlab_code_for_connection,
    get_gitlab_connection_status,
    get_valid_gitlab_access_token,
    list_visible_gitlab_projects,
    require_user_can_access_gitlab_project,
)

__all__ = [
    "GITLAB_OAUTH_STATE_TTL_SECONDS",
    "build_gitlab_authorize_url",
    "can_user_access_gitlab_project",
    "create_gitlab_oauth_state",
    "disconnect_gitlab",
    "exchange_gitlab_code_for_connection",
    "get_gitlab_connection_status",
    "get_valid_gitlab_access_token",
    "list_visible_gitlab_projects",
    "require_user_can_access_gitlab_project",
]
