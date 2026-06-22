import { useCallback } from "react";

import { fetchJson } from "../../../api";
import type {
  BitbucketConnection,
  BitbucketRepositoriesResponse,
  ConfluenceConnection,
  ConfluenceSpacesResponse,
  NotionConnection,
  NotionDatabasesResponse,
  GitlabConnection,
  GitlabProjectsResponse,
  GithubConnection,
  GithubRepositoriesResponse,
  JiraConnection,
  JiraProjectsResponse,
  LinearConnection,
  LinearSelectableSourcesResponse,
  SlackChannel,
  SlackChannelsResponse,
  SlackConnection,
  Workspace,
  WorkspaceConfluenceSourcesResponse,
  WorkspaceNotionSourcesResponse,
  WorkspaceJiraSourcesResponse,
  WorkspaceJiraSiteStatus,
  WorkspaceLinearSourcesResponse,
  WorkspaceSlackSourcesResponse,
  WorkspaceSlackTeam,
  WorkspaceSlackTeamsResponse,
  WorkspaceLinearSource,
  WorkspaceConfluenceSource,
  WorkspaceNotionSource,
  WorkspaceSlackSource,
  BitbucketRepository,
  GithubRepository,
  GitlabProject,
  JiraProject,
  ConfluenceSpace,
  NotionDatabase,
  LinearSelectableSource,
} from "../../../types";
import type { ConnectorConfig } from "./connectors";
import type { WorkspaceConnectorState } from "./useWorkspaceConnectorRuntime";

type WorkspaceConnectorLoadersArgs = {
  workspace: Workspace;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
  state: WorkspaceConnectorState;
};

export type ConnectorLoads = WorkspaceConnectorState &
  ReturnType<typeof useWorkspaceConnectorLoaders> & {
    activeConnector: ConnectorConfig | null;
  };

export function useWorkspaceConnectorLoaders({
  workspace,
  handleApiError,
  state,
}: WorkspaceConnectorLoadersArgs) {
  const loadGithubConnection = useCallback(async () => {
    try {
      const result = await fetchJson<GithubConnection>(
        "/api/me/integrations/github",
      );
      state.setGithubConnection(result);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError]);
  const loadGithubRepositories = useCallback(
    async (query = "") => {
      state.setGithubRepositoriesLoading(true);
      try {
        const params = query.trim()
          ? `?query=${encodeURIComponent(query.trim())}`
          : "";
        const result = await fetchJson<GithubRepositoriesResponse>(
          `/api/me/integrations/github/repos${params}`,
        );
        state.setGithubRepositories(result.repositories || []);
      } catch (error) {
        handleApiError(error, state.setConnectorError);
      } finally {
        state.setGithubRepositoriesLoading(false);
      }
    },
    [handleApiError],
  );
  const loadBitbucketConnection = useCallback(async () => {
    try {
      const result = await fetchJson<BitbucketConnection>(
        "/api/me/integrations/bitbucket",
      );
      state.setBitbucketConnection(result);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError]);
  const loadBitbucketRepositories = useCallback(
    async (query = "") => {
      state.setBitbucketLoading(true);
      try {
        const params = query.trim()
          ? `?query=${encodeURIComponent(query.trim())}`
          : "";
        const result = await fetchJson<BitbucketRepositoriesResponse>(
          `/api/me/integrations/bitbucket/repos${params}`,
        );
        state.setBitbucketRepositories(result.repositories || []);
      } catch (error) {
        handleApiError(error, state.setConnectorError);
      } finally {
        state.setBitbucketLoading(false);
      }
    },
    [handleApiError],
  );
  const loadGitlabConnection = useCallback(async () => {
    try {
      const result = await fetchJson<GitlabConnection>(
        "/api/me/integrations/gitlab",
      );
      state.setGitlabConnection(result);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError]);
  const loadGitlabProjects = useCallback(
    async (query = "") => {
      state.setGitlabLoading(true);
      try {
        const params = query.trim()
          ? `?query=${encodeURIComponent(query.trim())}`
          : "";
        const result = await fetchJson<GitlabProjectsResponse>(
          `/api/me/integrations/gitlab/projects${params}`,
        );
        state.setGitlabProjects(result.projects || []);
      } catch (error) {
        handleApiError(error, state.setConnectorError);
      } finally {
        state.setGitlabLoading(false);
      }
    },
    [handleApiError],
  );
  const loadJiraConnection = useCallback(async () => {
    try {
      const result = await fetchJson<JiraConnection>(
        "/api/me/integrations/jira",
      );
      state.setJiraConnection(result);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError]);
  const loadJiraSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceJiraSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/jira/sources`,
      );
      state.setJiraSources(result.sources || []);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);
  const loadJiraWorkspaceSite = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceJiraSiteStatus>(
        `/api/workspaces/${workspace.workspace_id}/jira/site`,
      );
      state.setJiraWorkspaceSite(result);
      if (!result.connected) {
        state.setJiraProjects([]);
      }
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);
  const loadJiraProjects = useCallback(
    async (query = "") => {
      state.setJiraLoading(true);
      try {
        const params = query.trim()
          ? `?query=${encodeURIComponent(query.trim())}`
          : "";
        const result = await fetchJson<JiraProjectsResponse>(
          `/api/workspaces/${workspace.workspace_id}/jira/projects${params}`,
        );
        state.setJiraProjects(result.projects || []);
      } catch (error) {
        handleApiError(error, state.setConnectorError);
      } finally {
        state.setJiraLoading(false);
      }
    },
    [handleApiError, workspace.workspace_id],
  );
  const loadSlackConnection = useCallback(async () => {
    try {
      const result = await fetchJson<SlackConnection>(
        "/api/me/integrations/slack",
      );
      state.setSlackConnection(result);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError]);
  const loadSlackSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceSlackSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/slack/sources`,
      );
      state.setSlackSources(result.sources || []);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);
  const loadSlackTeams = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceSlackTeamsResponse>(
        `/api/workspaces/${workspace.workspace_id}/slack/teams`,
      );
      state.setSlackTeams(result.teams || []);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);
  const loadSlackChannels = useCallback(async () => {
    if (!state.slackTeams.length) {
      state.setSlackChannels([]);
      return;
    }
    state.setSlackLoading(true);
    try {
      const result = await fetchJson<SlackChannelsResponse>(
        `/api/workspaces/${workspace.workspace_id}/slack/channels`,
      );
      state.setSlackChannels(result.channels || []);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    } finally {
      state.setSlackLoading(false);
    }
  }, [handleApiError, state.slackTeams.length, workspace.workspace_id]);
  const loadLinearConnection = useCallback(async () => {
    try {
      const result = await fetchJson<LinearConnection>(
        "/api/me/integrations/linear",
      );
      state.setLinearConnection(result);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError]);
  const loadLinearSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceLinearSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/linear/sources`,
      );
      state.setLinearSources(result.sources || []);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);
  const loadLinearSelectableSources = useCallback(
    async (query = "") => {
      state.setLinearLoading(true);
      try {
        const params = query.trim()
          ? `?query=${encodeURIComponent(query.trim())}`
          : "";
        const result = await fetchJson<LinearSelectableSourcesResponse>(
          `/api/me/integrations/linear/sources${params}`,
        );
        state.setLinearSelectableSources(result.sources || []);
      } catch (error) {
        handleApiError(error, state.setConnectorError);
      } finally {
        state.setLinearLoading(false);
      }
    },
    [handleApiError],
  );
  const loadConfluenceConnection = useCallback(async () => {
    try {
      const result = await fetchJson<ConfluenceConnection>(
        "/api/me/integrations/confluence",
      );
      state.setConfluenceConnection(result);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError]);
  const loadConfluenceSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceConfluenceSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/confluence/sources`,
      );
      state.setConfluenceSources(result.sources || []);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);
  const loadConfluenceSpaces = useCallback(
    async (query = "") => {
      state.setConfluenceLoading(true);
      try {
        const params = query.trim()
          ? `?query=${encodeURIComponent(query.trim())}`
          : "";
        const result = await fetchJson<ConfluenceSpacesResponse>(
          `/api/me/integrations/confluence/spaces${params}`,
        );
        state.setConfluenceSpaces(result.spaces || []);
      } catch (error) {
        handleApiError(error, state.setConnectorError);
      } finally {
        state.setConfluenceLoading(false);
      }
    },
    [handleApiError],
  );
  const loadNotionConnection = useCallback(async () => {
    try {
      const result = await fetchJson<NotionConnection>(
        "/api/me/integrations/notion",
      );
      state.setNotionConnection(result);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError]);
  const loadNotionSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceNotionSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/notion/sources`,
      );
      state.setNotionSources(result.sources || []);
    } catch (error) {
      handleApiError(error, state.setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);
  const loadNotionDatabases = useCallback(
    async (query = "") => {
      state.setNotionLoading(true);
      try {
        const params = query.trim()
          ? `?query=${encodeURIComponent(query.trim())}`
          : "";
        const result = await fetchJson<NotionDatabasesResponse>(
          `/api/me/integrations/notion/databases${params}`,
        );
        state.setNotionDatabases(result.databases || []);
      } catch (error) {
        handleApiError(error, state.setConnectorError);
      } finally {
        state.setNotionLoading(false);
      }
    },
    [handleApiError],
  );


  return {
    loadGithubConnection,
    loadGithubRepositories,
    loadBitbucketConnection,
    loadBitbucketRepositories,
    loadGitlabConnection,
    loadGitlabProjects,
    loadJiraConnection,
    loadJiraSources,
    loadJiraWorkspaceSite,
    loadJiraProjects,
    loadSlackConnection,
    loadSlackSources,
    loadSlackTeams,
    loadSlackChannels,
    loadLinearConnection,
    loadLinearSources,
    loadLinearSelectableSources,
    loadConfluenceConnection,
    loadConfluenceSources,
    loadConfluenceSpaces,
    loadNotionConnection,
    loadNotionSources,
    loadNotionDatabases,
  };
}
