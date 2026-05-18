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
}

export interface SessionResponse {
  authenticated: boolean;
  user: AuthUser | null;
}

export interface Workspace {
  workspace_id: string;
  name: string;
  created_at: string;
}

export interface WorkspacesResponse {
  workspaces: Workspace[];
}
