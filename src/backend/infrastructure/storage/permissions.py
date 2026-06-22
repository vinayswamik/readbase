from __future__ import annotations

from src.backend.application.services.workspace_connector_permissions import (
    user_can_manage_workspace_connectors,
)


def user_can_write_workspace_storage(user_id: str, user_email: str, workspace_id: str) -> bool:
    return user_can_manage_workspace_connectors(user_id, user_email, workspace_id)
