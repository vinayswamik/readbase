import { FormEvent } from "react";

import { deleteJson, postJson } from "../../../api";
import { startOAuthFlow } from "../../../mock/dev";
import type {
  BitbucketConnection,
  GitlabConnection,
  GithubConnection,
  IndexResponse,
  Workspace,
} from "../../../types";
import type { ConnectorConfig, ConnectorId } from "./connectors";
import type { ConnectorLoads } from "./useWorkspaceConnectorData";
import { useWorkspaceConnectorHandlersIntegrations } from "./useWorkspaceConnectors";

export type { ConnectorLoads };

function connectorHandlerBindings(loads: ConnectorLoads) {
  return {
    setActiveConnectorId: loads.setActiveConnectorId,
    setConnectorStatus: loads.setConnectorStatus,
    setConnectorError: loads.setConnectorError,
    connectorRepoUrl: loads.connectorRepoUrl,
    connectorRefreshRepo: loads.connectorRefreshRepo,
    setIndexing: loads.setIndexing,
    setGithubConnection: loads.setGithubConnection,
    setGithubRepositories: loads.setGithubRepositories,
    setBitbucketConnection: loads.setBitbucketConnection,
    setBitbucketRepositories: loads.setBitbucketRepositories,
    setBitbucketLoading: loads.setBitbucketLoading,
    setGitlabConnection: loads.setGitlabConnection,
    setGitlabProjects: loads.setGitlabProjects,
    setGitlabLoading: loads.setGitlabLoading,
    setJiraConnection: loads.setJiraConnection,
    setJiraProjects: loads.setJiraProjects,
    setJiraLoading: loads.setJiraLoading,
    setSlackConnection: loads.setSlackConnection,
    setSlackChannels: loads.setSlackChannels,
    setSlackLoading: loads.setSlackLoading,
    setLinearConnection: loads.setLinearConnection,
    setLinearSelectableSources: loads.setLinearSelectableSources,
    setLinearLoading: loads.setLinearLoading,
    setConfluenceConnection: loads.setConfluenceConnection,
    setConfluenceSpaces: loads.setConfluenceSpaces,
    setConfluenceLoading: loads.setConfluenceLoading,
    setNotionConnection: loads.setNotionConnection,
    setNotionDatabases: loads.setNotionDatabases,
    setNotionLoading: loads.setNotionLoading,
    setConnectorRepoUrl: loads.setConnectorRepoUrl,
    loadJiraSources: loads.loadJiraSources,
    loadSlackSources: loads.loadSlackSources,
    loadLinearSources: loads.loadLinearSources,
    loadConfluenceSources: loads.loadConfluenceSources,
    loadNotionSources: loads.loadNotionSources,
  };
}

type UseWorkspaceConnectorHandlersArgs = {
  workspace: Workspace;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
  selectedRepoUrl: string | undefined;
  activeConnector: ConnectorConfig | null;
  loads: ConnectorLoads;
  setRepoId: (repoId: string) => void;
  loadRepos: (preferredRepoId?: string) => Promise<void>;
  onWorkspaceSourcesChanged?: () => void;
};

export function useWorkspaceConnectorHandlers({
  workspace,
  handleApiError,
  selectedRepoUrl,
  activeConnector,
  loads,
  setRepoId,
  loadRepos,
  onWorkspaceSourcesChanged,
}: UseWorkspaceConnectorHandlersArgs) {
  const {
    setActiveConnectorId,
    setConnectorStatus,
    setConnectorError,
    connectorRepoUrl,
    connectorRefreshRepo,
    setIndexing,
    setGithubConnection,
    setGithubRepositories,
    setBitbucketConnection,
    setBitbucketRepositories,
    setBitbucketLoading,
    setGitlabConnection,
    setGitlabProjects,
    setGitlabLoading,
    setConnectorRepoUrl,
  } = connectorHandlerBindings(loads);

  const integrations = useWorkspaceConnectorHandlersIntegrations({
    workspace,
    handleApiError,
    loads,
    onWorkspaceSourcesChanged,
  });

  function notifyWorkspaceSourcesChanged() {
    onWorkspaceSourcesChanged?.();
  }

  function openConnectorModal(connectorId: ConnectorId) {
    setActiveConnectorId(connectorId);
    setConnectorStatus("");
    setConnectorError(null);
    if (connectorId === "github" && !connectorRepoUrl) {
      setConnectorRepoUrl(selectedRepoUrl || "");
    }
  }

  function closeConnectorModal() {
    setActiveConnectorId(null);
    setConnectorStatus("");
    setConnectorError(null);
  }

  async function handleGithubConnectorSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    const trimmedUrl = connectorRepoUrl.trim();
    if (!trimmedUrl) {
      return;
    }
    setIndexing(true);
    setConnectorStatus(
      "Cloning and indexing repository. This can take a minute.",
    );
    setConnectorError(null);
    try {
      const result = await postJson<
        { repo_url: string; refresh: boolean },
        IndexResponse
      >(`/api/workspaces/${workspace.workspace_id}/index`, {
        repo_url: trimmedUrl,
        refresh: connectorRefreshRepo,
      });
      setRepoId(result.repo_id);
      const providerName = activeConnector?.name || "provider";
      setConnectorStatus(
        `Repository indexed. Answers will use it only for users with ${providerName} access.`,
      );
      await loadRepos(result.repo_id);
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setIndexing(false);
    }
  }

  function handleGithubConnect() {
    void startOAuthFlow("/api/me/integrations/github/start");
  }

  function handleBitbucketConnect() {
    void startOAuthFlow("/api/me/integrations/bitbucket/start");
  }

  async function handleBitbucketDisconnect() {
    setBitbucketLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<BitbucketConnection>(
        "/api/me/integrations/bitbucket",
      );
      setBitbucketConnection(result);
      setBitbucketRepositories([]);
      setConnectorStatus("Bitbucket disconnected.");
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setBitbucketLoading(false);
    }
  }

  function handleGitlabConnect() {
    void startOAuthFlow("/api/me/integrations/gitlab/start");
  }

  async function handleGitlabDisconnect() {
    setGitlabLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<GitlabConnection>(
        "/api/me/integrations/gitlab",
      );
      setGitlabConnection(result);
      setGitlabProjects([]);
      setConnectorStatus("GitLab disconnected.");
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setGitlabLoading(false);
    }
  }

  async function handleGithubDisconnect() {
    setIndexing(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<GithubConnection>(
        "/api/me/integrations/github",
      );
      setGithubConnection(result);
      setConnectorStatus("GitHub disconnected.");
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setIndexing(false);
    }
  }

  return {
    openConnectorModal,
    closeConnectorModal,
    handleGithubConnectorSubmit,
    handleGithubConnect,
    handleGithubDisconnect,
    handleBitbucketConnect,
    handleBitbucketDisconnect,
    handleGitlabConnect,
    handleGitlabDisconnect,
    ...integrations,
  };
}
