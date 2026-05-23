export type MessageRole = "user" | "assistant";

export interface IndexedRepo {
  repo_id: string;
  workspace_id?: string | null;
  repo_url: string;
  file_count: number;
  chunk_count: number;
}

export type IndexResponse = IndexedRepo;

export interface ReposResponse {
  repos: IndexedRepo[];
}

export interface SourceMatch {
  score: number;
  id: string;
  path: string;
  start_line: number;
  end_line: number;
  text: string;
  source_type?: "repo" | "jira" | "slack" | "linear" | "confluence";
  repo_id?: string | null;
  repo_url?: string | null;
  source_url?: string | null;
  issue_key?: string | null;
  linear_team_id?: string | null;
  linear_project_id?: string | null;
  channel_name?: string | null;
  space_key?: string | null;
  page_id?: string | null;
  item_type?: string | null;
}

export interface AskResponse {
  repo_id?: string | null;
  workspace_id?: string | null;
  question: string;
  answer: string;
  mode: string;
  sources: SourceMatch[];
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  sources?: SourceMatch[];
  mode?: string;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: "admin" | "member";
}

export interface SessionResponse {
  authenticated: boolean;
  user: AuthUser | null;
}

export interface Workspace {
  workspace_id: string;
  owner_user_id: string;
  name: string;
  created_at: string;
  can_manage: boolean;
}

export interface WorkspacesResponse {
  workspaces: Workspace[];
}

export interface WorkspaceMember {
  email: string;
  user_id?: string | null;
  added_at: string;
  is_owner: boolean;
  connector_manager: boolean;
}

export interface WorkspaceMembersResponse {
  members: WorkspaceMember[];
}

export interface JiraSite {
  cloud_id: string;
  name: string;
  url: string;
  scopes: string[];
  avatar_url?: string | null;
}

export interface JiraConnection {
  connected: boolean;
  account_id?: string | null;
  account_email?: string | null;
  account_name?: string | null;
  scopes: string[];
  sites: JiraSite[];
}

export interface GithubConnection {
  connected: boolean;
  configured: boolean;
  github_user_id?: string | null;
  login?: string | null;
  name?: string | null;
  avatar_url?: string | null;
  scopes: string[];
}

export interface GithubRepository {
  id: string;
  name: string;
  full_name: string;
  html_url: string;
  private: boolean;
  description?: string | null;
  owner_login?: string | null;
  updated_at?: string | null;
}

export interface GithubRepositoriesResponse {
  repositories: GithubRepository[];
}

export interface BitbucketConnection {
  connected: boolean;
  configured: boolean;
  bitbucket_account_id?: string | null;
  username?: string | null;
  display_name?: string | null;
  avatar_url?: string | null;
  scopes: string[];
}

export interface BitbucketRepository {
  id: string;
  name: string;
  full_name: string;
  html_url: string;
  clone_url: string;
  private: boolean;
  description?: string | null;
  workspace_slug?: string | null;
  updated_at?: string | null;
}

export interface BitbucketRepositoriesResponse {
  repositories: BitbucketRepository[];
}

export interface GitlabConnection {
  connected: boolean;
  configured: boolean;
  gitlab_user_id?: string | null;
  username?: string | null;
  name?: string | null;
  avatar_url?: string | null;
  scopes: string[];
}

export interface GitlabProject {
  id: string;
  name: string;
  path_with_namespace: string;
  web_url: string;
  clone_url: string;
  visibility: string;
  description?: string | null;
  namespace?: string | null;
  updated_at?: string | null;
}

export interface GitlabProjectsResponse {
  projects: GitlabProject[];
}

export interface SlackTeam {
  team_id: string;
  team_name: string;
  team_domain?: string | null;
  slack_user_id: string;
  scopes: string[];
}

export interface SlackConnection {
  connected: boolean;
  configured: boolean;
  teams: SlackTeam[];
}

export interface TeamsTeam {
  team_id: string;
  display_name: string;
  description?: string | null;
  web_url?: string | null;
}

export interface TeamsConnection {
  connected: boolean;
  configured: boolean;
  microsoft_user_id?: string | null;
  tenant_id?: string | null;
  display_name?: string | null;
  user_principal_name?: string | null;
  mail?: string | null;
  scopes: string[];
  teams: TeamsTeam[];
}

export interface SlackChannel {
  team_id: string;
  team_name: string;
  team_domain?: string | null;
  channel_id: string;
  channel_name: string;
  is_private: boolean;
  is_archived: boolean;
}

export interface SlackChannelsResponse {
  channels: SlackChannel[];
}

export interface WorkspaceSlackSource {
  source_id: string;
  workspace_id: string;
  team_id: string;
  team_name: string;
  team_domain?: string | null;
  channel_id: string;
  channel_name: string;
  channel_is_private: boolean;
  added_by_user_id: string;
  sync_owner_user_id: string;
  sync_status: string;
  sync_error?: string | null;
  last_synced_at?: string | null;
  last_message_ts?: string | null;
  next_sync_at?: string | null;
  created_at: string;
  updated_at: string;
  user_access: string;
}

export interface WorkspaceSlackSourcesResponse {
  sources: WorkspaceSlackSource[];
}

export interface LinearConnection {
  connected: boolean;
  configured: boolean;
  linear_user_id?: string | null;
  workspace_id?: string | null;
  workspace_name?: string | null;
  name?: string | null;
  email?: string | null;
  scopes: string[];
}

export interface LinearSelectableSource {
  kind: string;
  team_id: string;
  team_name: string;
  project_id?: string | null;
  project_name?: string | null;
}

export interface LinearSelectableSourcesResponse {
  sources: LinearSelectableSource[];
}

export interface WorkspaceLinearSource {
  source_id: string;
  workspace_id: string;
  linear_team_id: string;
  team_name: string;
  linear_project_id?: string | null;
  project_name?: string | null;
  added_by_user_id: string;
  sync_owner_user_id: string;
  sync_status: string;
  sync_error?: string | null;
  last_synced_at?: string | null;
  next_sync_at?: string | null;
  created_at: string;
  updated_at: string;
  user_access: string;
}

export interface WorkspaceLinearSourcesResponse {
  sources: WorkspaceLinearSource[];
}

export interface ConfluenceConnection {
  connected: boolean;
  configured: boolean;
  account_id?: string | null;
  account_email?: string | null;
  account_name?: string | null;
  scopes: string[];
  sites: JiraSite[];
}

export interface ConfluenceSpace {
  cloud_id: string;
  site_name: string;
  site_url: string;
  space_id: string;
  space_key: string;
  space_name: string;
}

export interface ConfluenceSpacesResponse {
  spaces: ConfluenceSpace[];
}

export interface WorkspaceConfluenceSource {
  source_id: string;
  workspace_id: string;
  cloud_id: string;
  site_name: string;
  site_url: string;
  space_id: string;
  space_key: string;
  space_name: string;
  added_by_user_id: string;
  sync_owner_user_id: string;
  sync_status: string;
  sync_error?: string | null;
  last_synced_at?: string | null;
  next_sync_at?: string | null;
  created_at: string;
  updated_at: string;
  user_access: string;
}

export interface WorkspaceConfluenceSourcesResponse {
  sources: WorkspaceConfluenceSource[];
}

export interface JiraProject {
  cloud_id: string;
  site_name: string;
  site_url: string;
  project_id: string;
  project_key: string;
  project_name: string;
}

export interface JiraProjectsResponse {
  projects: JiraProject[];
}

export interface WorkspaceJiraSource {
  source_id: string;
  workspace_id: string;
  cloud_id: string;
  site_name: string;
  site_url: string;
  project_id: string;
  project_key: string;
  project_name: string;
  added_by_user_id: string;
  sync_owner_user_id: string;
  sync_status: string;
  sync_error?: string | null;
  last_synced_at?: string | null;
  next_sync_at?: string | null;
  created_at: string;
  updated_at: string;
  user_access: string;
}

export interface WorkspaceJiraSourcesResponse {
  sources: WorkspaceJiraSource[];
}

export interface HierarchyNode {
  node_id: string;
  workspace_id: string;
  display_name: string;
  assigned_user_id: string;
  assigned_user_email?: string | null;
  assigned_user_name?: string | null;
  x: number;
  y: number;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface HierarchyConnection {
  connection_id: string;
  workspace_id: string;
  parent_node_id: string;
  child_node_id: string;
  created_by_user_id: string;
  created_at: string;
}

export interface HierarchyGraphResponse {
  nodes: HierarchyNode[];
  connections: HierarchyConnection[];
  assignable_users: HierarchyAssignableUser[];
}

export interface CreateHierarchyNodeResponse {
  node: HierarchyNode;
  connection: HierarchyConnection | null;
}

export interface HierarchyAssignableUser {
  user_id: string;
  email: string;
  name: string;
  is_owner: boolean;
}
