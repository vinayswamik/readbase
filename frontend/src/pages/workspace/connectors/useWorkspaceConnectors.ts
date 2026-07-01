import { isMockApi, mockConnectConnector, startOAuthFlow } from "../../../mock/dev";
import type { Workspace } from "../../../types";
import { buildConnectorStartUrl, type ConnectorId } from "./connectors";
import type { ConnectorLoads } from "./useWorkspaceConnectorData";
import {
  reloadConnectorConnection,
  useWorkspaceConnectorHandlers,
} from "./useWorkspaceConnectorHandlers";
import { useWorkspaceConnectorRuntime } from "./useWorkspaceConnectorRuntime";

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

export type { ConnectorLoads };
