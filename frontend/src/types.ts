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
}

export interface AskResponse {
  repo_id: string;
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
}

export interface WorkspaceMembersResponse {
  members: WorkspaceMember[];
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
