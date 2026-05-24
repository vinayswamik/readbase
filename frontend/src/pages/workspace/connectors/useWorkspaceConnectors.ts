import { deleteJson, patchJson, postJson } from "../../../api";
import type {
  ConfluenceConnection,
  ConfluenceSpace,
  JiraConnection,
  JiraProject,
  LinearConnection,
  LinearSelectableSource,
  SlackChannel,
  SlackConnection,
  Workspace,
  WorkspaceConfluenceSource,
  WorkspaceJiraSource,
  WorkspaceLinearSource,
  WorkspaceMember,
  WorkspaceSlackSource,
} from "../../../types";
import type { ConnectorLoads } from "./useWorkspaceConnectorData";
import { useWorkspaceConnectorHandlers } from "./useWorkspaceConnectorHandlers";
import { useWorkspaceConnectorRuntime } from "./useWorkspaceConnectorRuntime";

type UseWorkspaceConnectorsArgs = {
  workspace: Workspace;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
  selectedRepoUrl: string | undefined;
  setRepoId: (repoId: string) => void;
  loadRepos: (preferredRepoId?: string) => Promise<void>;
};

export function useWorkspaceConnectors({
  workspace,
  handleApiError,
  selectedRepoUrl,
  setRepoId,
  loadRepos,
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
  });

  return { ...loads, ...handlers };
}

export type UseWorkspaceConnectorHandlersIntegrationsArgs = {
  workspace: Workspace;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
  loads: ConnectorLoads;
};

export function useWorkspaceConnectorHandlersIntegrations({
  workspace,
  handleApiError,
  loads,
}: UseWorkspaceConnectorHandlersIntegrationsArgs) {
  
  const {
    setConnectorStatus,
    setConnectorError,
    setJiraConnection,
    setJiraProjects,
    setJiraLoading,
    setSlackConnection,
    setSlackChannels,
    setSlackLoading,
    setLinearConnection,
    setLinearSelectableSources,
    setLinearLoading,
    setConfluenceConnection,
    setConfluenceSpaces,
    setConfluenceLoading,
    setConnectorMembers,
    loadJiraSources,
    loadSlackSources,
    loadLinearSources,
    loadConfluenceSources,
  } = loads;

  function handleJiraConnect() {
    window.location.assign("/api/me/integrations/jira/start");
  }
  async function handleJiraDisconnect() {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<JiraConnection>(
        "/api/me/integrations/jira",
      );
      setJiraConnection(result);
      setJiraProjects([]);
      setConnectorStatus("Jira disconnected.");
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
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setJiraLoading(false);
    }
  }
  async function handleSyncJiraSource(sourceId: string) {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceJiraSource>(
        `/api/workspaces/${workspace.workspace_id}/jira/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Jira source synced.");
      await loadJiraSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadJiraSources();
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
    window.location.assign(
      `/api/me/integrations/slack/start?${params.toString()}`,
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
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }
  async function handleSyncSlackSource(sourceId: string) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceSlackSource>(
        `/api/workspaces/${workspace.workspace_id}/slack/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Slack source synced.");
      await loadSlackSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadSlackSources();
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
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }
  function handleLinearConnect() {
    window.location.assign("/api/me/integrations/linear/start");
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
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setLinearLoading(false);
    }
  }
  function handleConfluenceConnect() {
    window.location.assign("/api/me/integrations/confluence/start");
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
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConfluenceLoading(false);
    }
  }
  async function handleConnectorManagerToggle(member: WorkspaceMember) {
    setConnectorError(null);
    try {
      const updated = await patchJson<
        { connector_manager: boolean },
        WorkspaceMember
      >(
        `/api/workspaces/${workspace.workspace_id}/members/${encodeURIComponent(member.email)}/connector-manager`,
        { connector_manager: !member.connector_manager },
      );
      setConnectorMembers((currentMembers) =>
        currentMembers.map((currentMember) =>
          currentMember.email === updated.email ? updated : currentMember,
        ),
      );
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }


  return {
    handleJiraConnect,
    handleJiraDisconnect,
    handleAddJiraProject,
    handleSyncJiraSource,
    handleRemoveJiraSource,
    handleSlackConnect,
    handleSlackDisconnect,
    handleAddSlackChannel,
    handleSyncSlackSource,
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
    handleConnectorManagerToggle,
  };
}
