import { deleteJson, postJson } from "../../../api";
import { isMockApi, mockConnectConnector, startOAuthFlow, type StartOAuthFlowOptions } from "../../../mock/dev";
import type {
  ConfluenceConnection,
  ConfluenceSpace,
  NotionConnection,
  NotionDatabase,
  JiraProject,
  JiraSite,
  LinearConnection,
  LinearSelectableSource,
  SlackChannel,
  SlackConnection,
  Workspace,
  WorkspaceConfluenceSource,
  WorkspaceNotionSource,
  WorkspaceJiraSource,
  WorkspaceJiraSiteStatus,
  WorkspaceLinearSource,
  WorkspaceSlackSource,
  WorkspaceSlackTeam,
} from "../../../types";
import { buildConnectorStartUrl, type ConnectorId } from "./connectors";
import type { ConnectorLoads } from "./useWorkspaceConnectorData";
import { useWorkspaceConnectorHandlers } from "./useWorkspaceConnectorHandlers";
import { useWorkspaceConnectorRuntime } from "./useWorkspaceConnectorRuntime";

async function reloadConnectorConnection(connectorId: ConnectorId, loads: ConnectorLoads) {
  switch (connectorId) {
    case "github":
      await loads.loadGithubConnection();
      break;
    case "bitbucket":
      await loads.loadBitbucketConnection();
      break;
    case "gitlab":
      await loads.loadGitlabConnection();
      break;
    case "jira":
      await loads.loadJiraConnection();
      break;
    case "slack":
      await loads.loadSlackConnection();
      await loads.loadSlackTeams();
      break;
    case "linear":
      await loads.loadLinearConnection();
      break;
    case "confluence":
      await loads.loadConfluenceConnection();
      break;
    case "notion":
      await loads.loadNotionConnection();
      break;
    case "teams":
      break;
  }
}

function buildMockOAuthOptions(
  connectorId: ConnectorId,
  loads: ConnectorLoads,
  onWorkspaceSourcesChanged?: () => void,
): StartOAuthFlowOptions {
  return {
    connectorId,
    onMockConnected: () => {
      onWorkspaceSourcesChanged?.();
      void reloadConnectorConnection(connectorId, loads);
    },
  };
}

type UseWorkspaceConnectorsArgs = {
  workspace: Workspace;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
  selectedRepoUrl: string | undefined;
  setRepoId: (repoId: string) => void;
  loadRepos: (preferredRepoId?: string) => Promise<void>;
  onWorkspaceSourcesChanged?: () => void;
};

export function useWorkspaceConnectors({
  workspace,
  handleApiError,
  selectedRepoUrl,
  setRepoId,
  loadRepos,
  onWorkspaceSourcesChanged,
}: UseWorkspaceConnectorsArgs) {
  const loads = useWorkspaceConnectorRuntime({ workspace, handleApiError });
  const handlers = useWorkspaceConnectorHandlers({
    workspace,
    handleApiError,
    selectedRepoUrl,
    activeConnector: loads.activeConnector,
    loads,
    setRepoId,
    loadRepos,
    onWorkspaceSourcesChanged,
  });

  async function handleConnectConnector(connectorId: ConnectorId) {
    if (isMockApi()) {
      try {
        await mockConnectConnector(connectorId);
        onWorkspaceSourcesChanged?.();
        await reloadConnectorConnection(connectorId, loads);
      } catch (error) {
        handleApiError(error);
      }
      return;
    }
    void startOAuthFlow(buildConnectorStartUrl(connectorId, workspace.workspace_id));
  }

  return { ...loads, ...handlers, handleConnectConnector };
}

export type UseWorkspaceConnectorHandlersIntegrationsArgs = {
  workspace: Workspace;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
  loads: ConnectorLoads;
  onWorkspaceSourcesChanged?: () => void;
};

export function useWorkspaceConnectorHandlersIntegrations({
  workspace,
  handleApiError,
  loads,
  onWorkspaceSourcesChanged,
}: UseWorkspaceConnectorHandlersIntegrationsArgs) {
  function notifyWorkspaceSourcesChanged() {
    onWorkspaceSourcesChanged?.();
  }

  const {
    setConnectorStatus,
    setConnectorError,
    setJiraLoading,
    setJiraWorkspaceSite,
    setJiraProjects,
    jiraProjectQuery,
    setSlackConnection,
    setSlackChannels,
    setSlackLoading,
    setLinearConnection,
    setLinearSelectableSources,
    setLinearLoading,
    setConfluenceConnection,
    setConfluenceSpaces,
    setConfluenceLoading,
    setNotionConnection,
    setNotionDatabases,
    setNotionLoading,
    loadJiraSources,
    loadJiraWorkspaceSite,
    loadJiraProjects,
    loadSlackSources,
    loadSlackTeams,
    loadLinearSources,
    loadConfluenceSources,
    loadNotionSources,
  } = loads;

  function handleJiraConnect() {
    void startOAuthFlow(
      "/api/me/integrations/jira/start",
      buildMockOAuthOptions("jira", loads, onWorkspaceSourcesChanged),
    );
  }
  async function handleConnectJiraSite(site: JiraSite) {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      const result = await postJson<{ cloud_id: string }, WorkspaceJiraSiteStatus>(
        `/api/workspaces/${workspace.workspace_id}/jira/site`,
        { cloud_id: site.cloud_id },
      );
      setJiraWorkspaceSite(result);
      setConnectorStatus(`${site.name} connected to this workspace.`);
      await loadJiraProjects(jiraProjectQuery);
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setJiraLoading(false);
    }
  }
  async function handleRemoveJiraSite() {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<WorkspaceJiraSiteStatus>(
        `/api/workspaces/${workspace.workspace_id}/jira/site`,
      );
      setJiraWorkspaceSite(result);
      setJiraProjects([]);
      setConnectorStatus("Jira site removed from this workspace.");
      await loadJiraSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setJiraLoading(false);
    }
  }
  async function handleAddJiraProject(project: JiraProject) {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      await postJson<JiraProject, WorkspaceJiraSource>(
        `/api/workspaces/${workspace.workspace_id}/jira/sources`,
        project,
      );
      setConnectorStatus(`${project.project_key} added to this workspace.`);
      await loadJiraSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setJiraLoading(false);
    }
  }
  async function handleRemoveJiraSource(sourceId: string) {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceJiraSource>(
        `/api/workspaces/${workspace.workspace_id}/jira/sources/${sourceId}`,
      );
      setConnectorStatus("Jira source removed.");
      await loadJiraSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setJiraLoading(false);
    }
  }
  function handleSlackConnect() {
    const params = new URLSearchParams({
      workspace_id: workspace.workspace_id,
    });
    void startOAuthFlow(
      `/api/me/integrations/slack/start?${params.toString()}`,
      buildMockOAuthOptions("slack", loads, onWorkspaceSourcesChanged),
    );
  }
  async function handleSlackDisconnect(teamId?: string) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      const params = teamId ? `?team_id=${encodeURIComponent(teamId)}` : "";
      const result = await deleteJson<SlackConnection>(
        `/api/me/integrations/slack${params}`,
      );
      setSlackConnection(result);
      setSlackChannels([]);
      setConnectorStatus(
        teamId ? "Slack workspace removed." : "Slack disconnected.",
      );
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }
  async function handleSlackUnlinkTeam(teamId: string) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceSlackTeam>(
        `/api/workspaces/${workspace.workspace_id}/slack/teams/${encodeURIComponent(teamId)}`,
      );
      setConnectorStatus("Slack workspace removed from this Readbase workspace.");
      setSlackChannels([]);
      await loadSlackTeams();
      await loadSlackSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }
  async function handleAddSlackChannel(channel: SlackChannel) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      await postJson<SlackChannel, WorkspaceSlackSource>(
        `/api/workspaces/${workspace.workspace_id}/slack/sources`,
        channel,
      );
      setConnectorStatus(`#${channel.channel_name} added to this workspace.`);
      await loadSlackSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }
  async function handleRemoveSlackSource(sourceId: string) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceSlackSource>(
        `/api/workspaces/${workspace.workspace_id}/slack/sources/${sourceId}`,
      );
      setConnectorStatus("Slack source removed.");
      await loadSlackSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }
  function handleLinearConnect() {
    void startOAuthFlow(
      "/api/me/integrations/linear/start",
      buildMockOAuthOptions("linear", loads, onWorkspaceSourcesChanged),
    );
  }
  async function handleLinearDisconnect() {
    setLinearLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<LinearConnection>(
        "/api/me/integrations/linear",
      );
      setLinearConnection(result);
      setLinearSelectableSources([]);
      setConnectorStatus("Linear disconnected.");
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setLinearLoading(false);
    }
  }
  async function handleAddLinearSource(source: LinearSelectableSource) {
    setLinearLoading(true);
    setConnectorError(null);
    try {
      await postJson<LinearSelectableSource, WorkspaceLinearSource>(
        `/api/workspaces/${workspace.workspace_id}/linear/sources`,
        source,
      );
      setConnectorStatus(
        `${source.project_name || source.team_name} added to this workspace.`,
      );
      await loadLinearSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setLinearLoading(false);
    }
  }
  async function handleSyncLinearSource(sourceId: string) {
    setLinearLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceLinearSource>(
        `/api/workspaces/${workspace.workspace_id}/linear/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Linear source synced.");
      await loadLinearSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadLinearSources();
    } finally {
      setLinearLoading(false);
    }
  }
  async function handleRemoveLinearSource(sourceId: string) {
    setLinearLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceLinearSource>(
        `/api/workspaces/${workspace.workspace_id}/linear/sources/${sourceId}`,
      );
      setConnectorStatus("Linear source removed.");
      await loadLinearSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setLinearLoading(false);
    }
  }
  function handleConfluenceConnect() {
    void startOAuthFlow(
      "/api/me/integrations/confluence/start",
      buildMockOAuthOptions("confluence", loads, onWorkspaceSourcesChanged),
    );
  }
  async function handleConfluenceDisconnect() {
    setConfluenceLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<ConfluenceConnection>(
        "/api/me/integrations/confluence",
      );
      setConfluenceConnection(result);
      setConfluenceSpaces([]);
      setConnectorStatus("Confluence disconnected.");
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConfluenceLoading(false);
    }
  }
  async function handleAddConfluenceSpace(space: ConfluenceSpace) {
    setConfluenceLoading(true);
    setConnectorError(null);
    try {
      await postJson<ConfluenceSpace, WorkspaceConfluenceSource>(
        `/api/workspaces/${workspace.workspace_id}/confluence/sources`,
        space,
      );
      setConnectorStatus(`${space.space_key} added to this workspace.`);
      await loadConfluenceSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConfluenceLoading(false);
    }
  }
  async function handleSyncConfluenceSource(sourceId: string) {
    setConfluenceLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceConfluenceSource>(
        `/api/workspaces/${workspace.workspace_id}/confluence/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Confluence source synced.");
      await loadConfluenceSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadConfluenceSources();
    } finally {
      setConfluenceLoading(false);
    }
  }
  async function handleRemoveConfluenceSource(sourceId: string) {
    setConfluenceLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceConfluenceSource>(
        `/api/workspaces/${workspace.workspace_id}/confluence/sources/${sourceId}`,
      );
      setConnectorStatus("Confluence source removed.");
      await loadConfluenceSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConfluenceLoading(false);
    }
  }
  function handleNotionConnect() {
    void startOAuthFlow(
      "/api/me/integrations/notion/start",
      buildMockOAuthOptions("notion", loads, onWorkspaceSourcesChanged),
    );
  }
  async function handleNotionDisconnect() {
    setNotionLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<NotionConnection>(
        "/api/me/integrations/notion",
      );
      setNotionConnection(result);
      setNotionDatabases([]);
      setConnectorStatus("Notion disconnected.");
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setNotionLoading(false);
    }
  }
  async function handleAddNotionDatabase(database: NotionDatabase) {
    setNotionLoading(true);
    setConnectorError(null);
    try {
      await postJson<NotionDatabase, WorkspaceNotionSource>(
        `/api/workspaces/${workspace.workspace_id}/notion/sources`,
        database,
      );
      setConnectorStatus(`${database.database_title} added to this workspace.`);
      await loadNotionSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setNotionLoading(false);
    }
  }
  async function handleSyncNotionSource(sourceId: string) {
    setNotionLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceNotionSource>(
        `/api/workspaces/${workspace.workspace_id}/notion/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Notion source synced.");
      await loadNotionSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadNotionSources();
    } finally {
      setNotionLoading(false);
    }
  }
  async function handleRemoveNotionSource(sourceId: string) {
    setNotionLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceNotionSource>(
        `/api/workspaces/${workspace.workspace_id}/notion/sources/${sourceId}`,
      );
      setConnectorStatus("Notion source removed.");
      await loadNotionSources();
      notifyWorkspaceSourcesChanged();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setNotionLoading(false);
    }
  }
  return {
    handleJiraConnect,
    handleConnectJiraSite,
    handleRemoveJiraSite,
    handleAddJiraProject,
    handleRemoveJiraSource,
    handleSlackConnect,
    handleSlackDisconnect,
    handleSlackUnlinkTeam,
    handleAddSlackChannel,
    handleRemoveSlackSource,
    handleLinearConnect,
    handleLinearDisconnect,
    handleAddLinearSource,
    handleSyncLinearSource,
    handleRemoveLinearSource,
    handleConfluenceConnect,
    handleConfluenceDisconnect,
    handleAddConfluenceSpace,
    handleSyncConfluenceSource,
    handleRemoveConfluenceSource,
    handleNotionConnect,
    handleNotionDisconnect,
    handleAddNotionDatabase,
    handleSyncNotionSource,
    handleRemoveNotionSource,
  };
}
