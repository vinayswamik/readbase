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
    role: str


class SessionResponse(BaseModel):
    authenticated: bool
    user: AuthUserResponse | None = None


class CreateWorkspaceRequest(BaseModel):
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


class JiraProjectResponse(BaseModel):
    cloud_id: str
    site_name: str
    site_url: str
    project_id: str
    project_key: str
    project_name: str


class JiraProjectsResponse(BaseModel):
    projects: list[JiraProjectResponse]


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
    assigned_user_id: str
    x: float = 0
    y: float = 0
    parent_node_id: str | None = None


class CreateHierarchyNodeResponse(BaseModel):
    node: HierarchyNodeResponse
    connection: HierarchyConnectionResponse | None = None


class UpdateHierarchyNodeRequest(BaseModel):
    display_name: str | None = None
    assigned_user_id: str | None = None
    parent_node_id: str | None = None
    x: float | None = None
    y: float | None = None


class CreateHierarchyConnectionRequest(BaseModel):
    parent_node_id: str
    child_node_id: str
