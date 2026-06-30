from __future__ import annotations

from pydantic import BaseModel

from src.backend.config.settings import DEFAULT_TOP_K


class IndexRequest(BaseModel):
    repo_url: str
    refresh: bool = False


class IndexedRepoResponse(BaseModel):
    repo_id: str
    workspace_id: str | None = None
    repo_url: str
    file_count: int
    chunk_count: int


class ReposResponse(BaseModel):
    repos: list[IndexedRepoResponse]


class AskRequest(BaseModel):
    repo_id: str | None = None
    question: str
    top_k: int = DEFAULT_TOP_K


class SourceMatchResponse(BaseModel):
    score: float
    id: str
    path: str
    start_line: int
    end_line: int
    text: str
    source_type: str = "repo"
    repo_id: str | None = None
    repo_url: str | None = None
    source_url: str | None = None
    issue_key: str | None = None
    linear_team_id: str | None = None
    linear_project_id: str | None = None
    channel_name: str | None = None
    space_key: str | None = None
    page_id: str | None = None
    item_type: str | None = None


class AskResponse(BaseModel):
    repo_id: str | None = None
    workspace_id: str | None = None
    question: str
    answer: str
    mode: str
    sources: list[SourceMatchResponse]


class AuthUserResponse(BaseModel):
    id: str
    email: str
    name: str


class SessionResponse(BaseModel):
    authenticated: bool
    user: AuthUserResponse | None = None


class CreateWorkspaceRequest(BaseModel):
    name: str


class UpdateWorkspaceRequest(BaseModel):
    name: str


class AddWorkspaceMemberRequest(BaseModel):
    email: str


class WorkspaceMemberResponse(BaseModel):
    email: str
    user_id: str | None = None
    added_at: str
    is_owner: bool
    connector_manager: bool = False


class WorkspaceMembersResponse(BaseModel):
    members: list[WorkspaceMemberResponse]


class WorkspaceInvitesResponse(BaseModel):
    received: list["WorkspaceInviteListItemResponse"]
    sent: list["WorkspaceInviteListItemResponse"]


class NotificationResponse(BaseModel):
    notification_id: str
    type: str
    title: str
    body: str
    workspace_id: str
    workspace_name: str
    actor_user_id: str
    actor_name: str
    read: bool
    created_at: str


class NotificationsResponse(BaseModel):
    notifications: list[NotificationResponse]


class WorkspaceInviteListItemResponse(BaseModel):
    invite_id: str
    workspace_id: str
    workspace_name: str
    direction: str
    invitee_email: str
    invitee_name: str
    invitee_user_id: str | None = None
    invitor_user_id: str
    invitor_name: str
    invitor_designation: str
    relation: str
    reason: str
    node_display_name: str
    node_id: str | None = None
    status: str
    can_accept: bool = False
    can_reject: bool = False
    can_revert: bool = False
    invite_method: str = "email"
    join_token: str | None = None
    join_path: str | None = None
    created_at: str


class UpdateWorkspaceMemberConnectorManagerRequest(BaseModel):
    connector_manager: bool


class JiraSiteResponse(BaseModel):
    cloud_id: str
    name: str
    url: str
    scopes: list[str] = []
    avatar_url: str | None = None


class JiraConnectionResponse(BaseModel):
    connected: bool
    account_id: str | None = None
    account_email: str | None = None
    account_name: str | None = None
    scopes: list[str] = []
    sites: list[JiraSiteResponse] = []


class GithubConnectionResponse(BaseModel):
    connected: bool
    configured: bool = False
    github_user_id: str | None = None
    login: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    scopes: list[str] = []


class GithubRepositoryResponse(BaseModel):
    id: str
    name: str
    full_name: str
    html_url: str
    private: bool
    description: str | None = None
    owner_login: str | None = None
    updated_at: str | None = None


class GithubRepositoriesResponse(BaseModel):
    repositories: list[GithubRepositoryResponse]


class BitbucketConnectionResponse(BaseModel):
    connected: bool
    configured: bool = False
    bitbucket_account_id: str | None = None
    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    scopes: list[str] = []


class BitbucketRepositoryResponse(BaseModel):
    id: str
    name: str
    full_name: str
    html_url: str
    clone_url: str
    private: bool
    description: str | None = None
    workspace_slug: str | None = None
    updated_at: str | None = None


class BitbucketRepositoriesResponse(BaseModel):
    repositories: list[BitbucketRepositoryResponse]


class GitlabConnectionResponse(BaseModel):
    connected: bool
    configured: bool = False
    gitlab_user_id: str | None = None
    username: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    scopes: list[str] = []


class GitlabProjectResponse(BaseModel):
    id: str
    name: str
    path_with_namespace: str
    web_url: str
    clone_url: str
    visibility: str
    description: str | None = None
    namespace: str | None = None
    updated_at: str | None = None


class GitlabProjectsResponse(BaseModel):
    projects: list[GitlabProjectResponse]


class SlackTeamResponse(BaseModel):
    team_id: str
    team_name: str
    team_domain: str | None = None
    slack_user_id: str
    scopes: list[str] = []


class SlackConnectionResponse(BaseModel):
    connected: bool
    configured: bool = False
    teams: list[SlackTeamResponse] = []


class SlackChannelResponse(BaseModel):
    team_id: str
    team_name: str
    team_domain: str | None = None
    channel_id: str
    channel_name: str
    is_private: bool
    is_archived: bool = False


class SlackChannelsResponse(BaseModel):
    channels: list[SlackChannelResponse]


class TeamsTeamResponse(BaseModel):
    team_id: str
    display_name: str
    description: str | None = None
    web_url: str | None = None


class TeamsConnectionResponse(BaseModel):
    connected: bool
    configured: bool = False
    microsoft_user_id: str | None = None
    tenant_id: str | None = None
    display_name: str | None = None
    user_principal_name: str | None = None
    mail: str | None = None
    scopes: list[str] = []
    teams: list[TeamsTeamResponse] = []


class AddWorkspaceSlackChannelRequest(BaseModel):
    team_id: str
    team_name: str
    team_domain: str | None = None
    channel_id: str
    channel_name: str
    is_private: bool = False


class WorkspaceSlackSourceResponse(BaseModel):
    source_id: str
    workspace_id: str
    team_id: str
    team_name: str
    team_domain: str | None = None
    channel_id: str
    channel_name: str
    channel_is_private: bool
    added_by_user_id: str
    sync_owner_user_id: str
    sync_status: str
    sync_error: str | None = None
    last_synced_at: str | None = None
    last_message_ts: str | None = None
    next_sync_at: str | None = None
    created_at: str
    updated_at: str
    user_access: str = "unknown"


class WorkspaceSlackSourcesResponse(BaseModel):
    sources: list[WorkspaceSlackSourceResponse]


class WorkspaceSlackTeamResponse(BaseModel):
    team_id: str
    team_name: str
    team_domain: str | None = None
    linked_by_user_id: str
    linked_at: str
    updated_at: str
    user_oauth_connected: bool = False


class WorkspaceSlackTeamsResponse(BaseModel):
    teams: list[WorkspaceSlackTeamResponse]


class LinkWorkspaceSlackTeamRequest(BaseModel):
    team_id: str


class LinearConnectionResponse(BaseModel):
    connected: bool
    configured: bool = False
    linear_user_id: str | None = None
    workspace_id: str | None = None
    workspace_name: str | None = None
    name: str | None = None
    email: str | None = None
    scopes: list[str] = []


class LinearSelectableSourceResponse(BaseModel):
    kind: str
    team_id: str
    team_name: str
    project_id: str | None = None
    project_name: str | None = None


class LinearSelectableSourcesResponse(BaseModel):
    sources: list[LinearSelectableSourceResponse]


class AddWorkspaceLinearSourceRequest(BaseModel):
    team_id: str
    team_name: str
    project_id: str | None = None
    project_name: str | None = None


class WorkspaceLinearSourceResponse(BaseModel):
    source_id: str
    workspace_id: str
    linear_team_id: str
    team_name: str
    linear_project_id: str | None = None
    project_name: str | None = None
    added_by_user_id: str
    sync_owner_user_id: str
    sync_status: str
    sync_error: str | None = None
    last_synced_at: str | None = None
    next_sync_at: str | None = None
    created_at: str
    updated_at: str
    user_access: str = "unknown"


class WorkspaceLinearSourcesResponse(BaseModel):
    sources: list[WorkspaceLinearSourceResponse]


class ConfluenceSiteResponse(BaseModel):
    cloud_id: str
    name: str
    url: str
    scopes: list[str] = []
    avatar_url: str | None = None


class ConfluenceConnectionResponse(BaseModel):
    connected: bool
    configured: bool = False
    account_id: str | None = None
    account_email: str | None = None
    account_name: str | None = None
    scopes: list[str] = []
    sites: list[ConfluenceSiteResponse] = []


class ConfluenceSpaceResponse(BaseModel):
    cloud_id: str
    site_name: str
    site_url: str
    space_id: str
    space_key: str
    space_name: str


class ConfluenceSpacesResponse(BaseModel):
    spaces: list[ConfluenceSpaceResponse]


class AddWorkspaceConfluenceSpaceRequest(BaseModel):
    cloud_id: str
    site_name: str
    site_url: str
    space_id: str
    space_key: str
    space_name: str


class WorkspaceConfluenceSourceResponse(BaseModel):
    source_id: str
    workspace_id: str
    cloud_id: str
    site_name: str
    site_url: str
    space_id: str
    space_key: str
    space_name: str
    added_by_user_id: str
    sync_owner_user_id: str
    sync_status: str
    sync_error: str | None = None
    last_synced_at: str | None = None
    next_sync_at: str | None = None
    created_at: str
    updated_at: str
    user_access: str = "unknown"


class WorkspaceConfluenceSourcesResponse(BaseModel):
    sources: list[WorkspaceConfluenceSourceResponse]


class NotionConnectionResponse(BaseModel):
    connected: bool
    configured: bool = False
    workspace_id: str | None = None
    workspace_name: str | None = None
    workspace_icon: str | None = None
    bot_id: str | None = None
    owner_type: str | None = None
    owner_name: str | None = None


class NotionDatabaseResponse(BaseModel):
    notion_workspace_id: str
    workspace_name: str
    database_id: str
    database_title: str


class NotionDatabasesResponse(BaseModel):
    databases: list[NotionDatabaseResponse]


class AddWorkspaceNotionDatabaseRequest(BaseModel):
    notion_workspace_id: str
    database_id: str
    database_title: str


class WorkspaceNotionSourceResponse(BaseModel):
    source_id: str
    workspace_id: str
    notion_workspace_id: str
    database_id: str
    database_title: str
    added_by_user_id: str
    sync_owner_user_id: str
    sync_status: str
    sync_error: str | None = None
    last_synced_at: str | None = None
    next_sync_at: str | None = None
    created_at: str
    updated_at: str
    user_access: str = "unknown"


class WorkspaceNotionSourcesResponse(BaseModel):
    sources: list[WorkspaceNotionSourceResponse]


class JiraProjectResponse(BaseModel):
    cloud_id: str
    site_name: str
    site_url: str
    project_id: str
    project_key: str
    project_name: str


class JiraProjectsResponse(BaseModel):
    projects: list[JiraProjectResponse]


class WorkspaceJiraSiteResponse(BaseModel):
    cloud_id: str
    name: str
    url: str


class WorkspaceJiraSiteStatusResponse(BaseModel):
    connected: bool
    site: WorkspaceJiraSiteResponse | None = None


class ConnectWorkspaceJiraSiteRequest(BaseModel):
    cloud_id: str


class AddWorkspaceJiraProjectRequest(BaseModel):
    cloud_id: str
    project_id: str
    project_key: str
    project_name: str
    site_name: str
    site_url: str


class WorkspaceJiraSourceResponse(BaseModel):
    source_id: str
    workspace_id: str
    cloud_id: str
    site_name: str
    site_url: str
    project_id: str
    project_key: str
    project_name: str
    added_by_user_id: str
    sync_owner_user_id: str
    sync_status: str
    sync_error: str | None = None
    last_synced_at: str | None = None
    next_sync_at: str | None = None
    created_at: str
    updated_at: str
    user_access: str = "unknown"


class WorkspaceJiraSourcesResponse(BaseModel):
    sources: list[WorkspaceJiraSourceResponse]


class WorkspaceResponse(BaseModel):
    workspace_id: str
    owner_user_id: str
    name: str
    created_at: str
    can_manage: bool


class WorkspacesResponse(BaseModel):
    workspaces: list[WorkspaceResponse]


class HierarchyNodeResponse(BaseModel):
    node_id: str
    workspace_id: str
    display_name: str
    assigned_user_id: str
    assigned_user_email: str | None = None
    assigned_user_name: str | None = None
    x: float
    y: float
    created_by_user_id: str
    created_at: str
    updated_at: str


class HierarchyConnectionResponse(BaseModel):
    connection_id: str
    workspace_id: str
    parent_node_id: str
    child_node_id: str
    created_by_user_id: str
    created_at: str


class HierarchyAssignableUserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    is_owner: bool


class HierarchyGraphResponse(BaseModel):
    nodes: list[HierarchyNodeResponse]
    connections: list[HierarchyConnectionResponse]
    assignable_users: list[HierarchyAssignableUserResponse] = []


class CreateHierarchyNodeRequest(BaseModel):
    display_name: str
    assigned_user_id: str | None = None
    invitee_email: str | None = None
    invite_method: str = "email"
    invitor_designation: str = ""
    relation: str = ""
    reason: str = ""
    x: float = 0
    y: float = 0
    parent_node_id: str | None = None


class WorkspaceInviteResponse(BaseModel):
    invite_id: str
    workspace_id: str
    workspace_name: str = ""
    invitee_email: str
    invitee_name: str
    invitee_user_id: str | None = None
    invitor_user_id: str
    invitor_name: str
    invitor_designation: str
    relation: str
    reason: str
    node_display_name: str
    node_id: str | None = None
    status: str
    can_accept: bool = False
    can_reject: bool = False
    can_revert: bool = False
    invite_method: str = "email"
    join_token: str | None = None
    join_path: str | None = None
    created_at: str


class CreateHierarchyNodeResponse(BaseModel):
    node: HierarchyNodeResponse | None = None
    connection: HierarchyConnectionResponse | None = None
    invite: WorkspaceInviteResponse | None = None


class UpdateHierarchyNodeRequest(BaseModel):
    display_name: str | None = None
    assigned_user_id: str | None = None
    parent_node_id: str | None = None
    x: float | None = None
    y: float | None = None


class CreateHierarchyConnectionRequest(BaseModel):
    parent_node_id: str
    child_node_id: str


class OrganizationStorageResponse(BaseModel):
    blob_backend: str
    storage_root: str


class OrganizationResponse(BaseModel):
    org_id: str
    name: str
    role: str
    storage: OrganizationStorageResponse


class CreateOrganizationRequest(BaseModel):
    name: str
    storage_root: str
    blob_backend: str = "local"


class UpdateOrganizationStorageRequest(BaseModel):
    storage_root: str
    blob_backend: str | None = None


class AssignWorkspaceOrganizationRequest(BaseModel):
    workspace_id: str


class WorkspaceOrganizationResponse(BaseModel):
    workspace_id: str
    organization_id: str
