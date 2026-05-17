export type MessageRole = "user" | "assistant";

export interface IndexedRepo {
  repo_id: string;
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
