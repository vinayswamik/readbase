import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchJson, getErrorMessage, isSessionExpiredMessage, postJson } from "../../../api";
import type {
  AskResponse,
  ChatMessage,
  IndexedRepo,
  ReposResponse,
  SourceMatch,
  Workspace,
} from "../../../types";

export function useWorkspaceApiError(onSessionExpired: () => void) {
  return useCallback(
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
}

export function createMessage(
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

export function slackOauthErrorMessage(error: string): string {
  if (error === "invalid_state") {
    return "Slack authorization expired. Try connecting Slack again.";
  }
  if (error === "connect_failed") {
    return "Slack authorization failed. Try another Slack workspace or check the Slack app settings.";
  }
  return "Slack authorization was not completed.";
}

type UseWorkspaceReposArgs = {
  workspace: Workspace;
  onBack: () => void;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
};

export function useWorkspaceRepos({
  workspace,
  onBack,
  handleApiError,
}: UseWorkspaceReposArgs) {
  const [repoId, setRepoId] = useState<string | null>(null);
  const [repos, setRepos] = useState<IndexedRepo[]>([]);
  const [repoListError, setRepoListError] = useState<string | null>(null);

  const selectedRepo = useMemo(
    () => repos.find((repo) => repo.repo_id === repoId) ?? null,
    [repoId, repos],
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
          if (
            currentRepoId &&
            fetchedRepos.some((repo) => repo.repo_id === currentRepoId)
          ) {
            return currentRepoId;
          }
          return fetchedRepos[0]?.repo_id ?? null;
        });
      } catch (error) {
        handleApiError(error, setRepoListError);
        if (
          getErrorMessage(error).toLowerCase().includes("workspace not found")
        ) {
          onBack();
        }
      }
    },
    [handleApiError, onBack, workspace.workspace_id],
  );

  useEffect(() => {
    void loadRepos();
  }, [loadRepos]);

  return {
    repoId,
    setRepoId,
    repos,
    repoListError,
    selectedRepo,
    loadRepos,
  };
}

type UseWorkspaceChatArgs = {
  workspace: Workspace;
  repoId: string | null;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
};

export function useWorkspaceChat({
  workspace,
  repoId,
  handleApiError,
}: UseWorkspaceChatArgs) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, setMode] = useState("retrieval");
  const [asking, setAsking] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, chatOpen]);

  async function handleAskSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }
    setChatOpen(true);
    setMessages((currentMessages) => [
      ...currentMessages,
      createMessage("user", trimmedQuestion),
    ]);
    setQuestion("");
    setAsking(true);
    try {
      const result = await postJson<
        { repo_id?: string; question: string; top_k: number },
        AskResponse
      >(`/api/workspaces/${workspace.workspace_id}/ask`, {
        repo_id: repoId || undefined,
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

  const canAsk = Boolean(question.trim() && !asking);

  return {
    question,
    setQuestion,
    messages,
    mode,
    asking,
    chatOpen,
    setChatOpen,
    messageEndRef,
    handleAskSubmit,
    canAsk,
  };
}
