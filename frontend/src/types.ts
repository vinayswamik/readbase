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
  source_type?: "repo" | "jira" | "slack";
  repo_id?: string | null;
  repo_url?: string | null;
  source_url?: string | null;
  issue_key?: string | null;
  channel_name?: string | null;
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
