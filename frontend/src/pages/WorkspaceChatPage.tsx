import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchJson, getErrorMessage, isSessionExpiredMessage, postJson } from "../api";
import type {
  AskResponse,
  ChatMessage,
  IndexedRepo,
  IndexResponse,
  ReposResponse,
  SourceMatch,
  Workspace,
} from "../types";

export function WorkspaceChatPage({
  workspace,
  onBack,
  onSessionExpired,
}: {
  workspace: Workspace;
  onBack: () => void;
  onSessionExpired: () => void;
}) {
  const [repoId, setRepoId] = useState<string | null>(null);
  const [repos, setRepos] = useState<IndexedRepo[]>([]);
  const [repoUrl, setRepoUrl] = useState("");
  const [refreshRepo, setRefreshRepo] = useState(false);
  const [repoStatus, setRepoStatus] = useState("No repository indexed in this workspace.");
  const [repoListError, setRepoListError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, setMode] = useState("retrieval");
  const [indexing, setIndexing] = useState(false);
  const [asking, setAsking] = useState(false);
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  const selectedRepo = useMemo(
    () => repos.find((repo) => repo.repo_id === repoId) ?? null,
    [repoId, repos],
  );

  const handleApiError = useCallback(
    (error: unknown, setMessage?: (message: string) => void) => {
      const message = getErrorMessage(error);
      if (setMessage) {
        setMessage(message);
      }
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    },
    [onSessionExpired],
  );

  const loadRepos = useCallback(
    async (preferredRepoId?: string) => {
      try {
        const result = await fetchJson<ReposResponse>(
          `/api/workspaces/${workspace.workspace_id}/repos`,
        );
        const fetchedRepos = result.repos || [];
        setRepos(fetchedRepos);
        setRepoListError(null);
        setRepoId((currentRepoId) => {
          if (preferredRepoId) {
            return preferredRepoId;
          }
          if (currentRepoId && fetchedRepos.some((repo) => repo.repo_id === currentRepoId)) {
            return currentRepoId;
          }
          return fetchedRepos[0]?.repo_id ?? null;
        });
      } catch (error) {
        handleApiError(error, setRepoListError);
        if (getErrorMessage(error).toLowerCase().includes("workspace not found")) {
          onBack();
        }
      }
    },
    [handleApiError, onBack, workspace.workspace_id],
  );

  useEffect(() => {
    void loadRepos();
  }, [loadRepos]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  async function handleIndexSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedUrl = repoUrl.trim();
    if (!trimmedUrl) {
      return;
    }

    setIndexing(true);
    setRepoStatus("Cloning and indexing repository. This can take a minute.");

    try {
      const result = await postJson<
        { repo_url: string; refresh: boolean },
        IndexResponse
      >(`/api/workspaces/${workspace.workspace_id}/index`, {
        repo_url: trimmedUrl,
        refresh: refreshRepo,
      });
      setRepoId(result.repo_id);
      setRepoStatus(formatRepoStatus(result));
      await loadRepos(result.repo_id);
    } catch (error) {
      handleApiError(error, setRepoStatus);
    } finally {
      setIndexing(false);
    }
  }

  async function handleAskSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || !repoId) {
      return;
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      createMessage("user", trimmedQuestion),
    ]);
    setQuestion("");
    setAsking(true);

    try {
      const result = await postJson<
        { repo_id: string; question: string; top_k: number },
        AskResponse
      >(`/api/workspaces/${workspace.workspace_id}/ask`, {
        repo_id: repoId,
        question: trimmedQuestion,
        top_k: 8,
      });
      setMode(result.mode);
      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage("assistant", result.answer, result.sources, result.mode),
      ]);
    } catch (error) {
      handleApiError(error, (message) => {
        setMessages((currentMessages) => [
          ...currentMessages,
          createMessage("assistant", message),
        ]);
      });
    } finally {
      setAsking(false);
    }
  }

  function handleRepoSelect(repo: IndexedRepo) {
    setRepoId(repo.repo_id);
    setRepoUrl(repo.repo_url);
    setRepoStatus(formatRepoStatus(repo));
  }

  const canAsk = Boolean(repoId && question.trim() && !asking);

  return (
    <section className="app-shell">
      <aside className="sidebar">
        <button type="button" className="back-button" onClick={onBack}>
          Back to workspaces
        </button>
        <header className="brand">
          <div>
            <h1>{workspace.name}</h1>
            <p>Codebase Q&amp;A</p>
          </div>
          <span className="status-chip">{mode}</span>
        </header>

        <section className="panel" aria-labelledby="repository-heading">
          <h2 id="repository-heading">Repository</h2>
          <form className="index-form" onSubmit={handleIndexSubmit}>
            <label htmlFor="repoUrl">GitHub URL</label>
            <input
              id="repoUrl"
              name="repoUrl"
              type="url"
              value={repoUrl}
              placeholder="https://github.com/owner/repo"
              required
              onChange={(event) => setRepoUrl(event.target.value)}
            />
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={refreshRepo}
                onChange={(event) => setRefreshRepo(event.target.checked)}
              />
              <span>Re-clone existing index</span>
            </label>
            <button type="submit" disabled={indexing} className="primary-button">
              {indexing ? "Indexing..." : "Index repository"}
            </button>
          </form>
          <div className="status-text" aria-live="polite">
            {repoStatus}
          </div>
        </section>

        <section className="panel" aria-labelledby="indexed-repos-heading">
          <h2 id="indexed-repos-heading">Indexed Repos</h2>
          <RepoList
            repos={repos}
            selectedRepoId={repoId}
            error={repoListError}
            onSelect={handleRepoSelect}
          />
        </section>
      </aside>

      <section className="chat-workspace" aria-label="Question and answer workspace">
        <div className="messages">
          {messages.length ? (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          ) : (
            <article className="message assistant">
              <div className="message-body empty-message">No questions yet.</div>
            </article>
          )}
          <div ref={messageEndRef} />
        </div>

        <form className="ask-form" onSubmit={handleAskSubmit}>
          <textarea
            rows={2}
            value={question}
            placeholder={
              selectedRepo
                ? `Ask about ${repoLabel(selectedRepo)}`
                : "Select a repository first"
            }
            required
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button type="submit" disabled={!canAsk} className="primary-button">
            {asking ? "Thinking..." : "Ask"}
          </button>
        </form>
      </section>
    </section>
  );
}

function RepoList({
  repos,
  selectedRepoId,
  error,
  onSelect,
}: {
  repos: IndexedRepo[];
  selectedRepoId: string | null;
  error: string | null;
  onSelect: (repo: IndexedRepo) => void;
}) {
  if (error) {
    return <div className="status-text">{error}</div>;
  }

  if (!repos.length) {
    return <div className="status-text">No indexed repositories yet.</div>;
  }

  return (
    <div className="repo-list">
      {repos.map((repo) => (
        <button
          key={repo.repo_id}
          type="button"
          className={`repo-item${repo.repo_id === selectedRepoId ? " active" : ""}`}
          onClick={() => onSelect(repo)}
        >
          <span className="repo-url">{repo.repo_url}</span>
          <span className="repo-meta">
            {repo.file_count} files, {repo.chunk_count} chunks
          </span>
        </button>
      ))}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="message-body">
        {message.text}
        <SourceList sources={message.sources || []} mode={message.mode || "retrieval"} />
      </div>
    </article>
  );
}

function SourceList({ sources, mode }: { sources: SourceMatch[]; mode: string }) {
  if (!sources.length) {
    return null;
  }

  return (
    <div className="sources">
      {sources.slice(0, 4).map((source) => (
        <div
          key={source.id}
          className={`source${mode === "anthropic" ? " compact" : ""}`}
        >
          <div className="source-title">
            {source.path}:{source.start_line}-{source.end_line} · score{" "}
            {formatScore(source.score)}
          </div>
          {mode !== "anthropic" ? <pre>{source.text}</pre> : null}
        </div>
      ))}
    </div>
  );
}

function createMessage(
  role: ChatMessage["role"],
  text: string,
  sources?: SourceMatch[],
  mode?: string,
): ChatMessage {
  return {
    id:
      typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    sources,
    mode,
  };
}

function formatRepoStatus(repo: IndexedRepo): string {
  return `${repo.file_count} files indexed into ${repo.chunk_count} chunks.`;
}

function repoLabel(repo: IndexedRepo): string {
  return repo.repo_url.replace(/^https?:\/\/github\.com\//, "");
}

function formatScore(score: number): string {
  return Number.isFinite(score) ? score.toFixed(3) : String(score);
}
