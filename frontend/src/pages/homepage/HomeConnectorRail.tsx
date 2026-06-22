import { useCallback, useEffect, useMemo, useState } from "react";
import type { KeyboardEvent } from "react";

import {
  deleteJson,
  fetchJson,
  getErrorMessage,
  isSessionExpiredMessage,
} from "../../api";
import { startOAuthFlow } from "../../mock/dev";
import type {
  BitbucketConnection,
  ConfluenceConnection,
  NotionConnection,
  GitlabConnection,
  GithubConnection,
  JiraConnection,
  LinearConnection,
  SlackConnection,
  TeamsConnection,
} from "../../types";
import {
  CONNECTORS,
  type ConnectorConfig,
  type ConnectorId,
} from "../workspace/connectors/connectors";
import { ConnectorLogo } from "../workspace/connectors/ConnectorLogo";
import { AppToast } from "../../components/AppToast";

type ConnectionMap = {
  bitbucket: BitbucketConnection | null;
  confluence: ConfluenceConnection | null;
  notion: NotionConnection | null;
  github: GithubConnection | null;
  gitlab: GitlabConnection | null;
  jira: JiraConnection | null;
  linear: LinearConnection | null;
  slack: SlackConnection | null;
  teams: TeamsConnection | null;
};

const EMPTY_CONNECTIONS: ConnectionMap = {
  bitbucket: null,
  confluence: null,
  notion: null,
  github: null,
  gitlab: null,
  jira: null,
  linear: null,
  slack: null,
  teams: null,
};

const CONNECTED_ORDER_STORAGE_KEY = "readbase:homeConnectedConnectorOrder";

export function HomeConnectorRail({
  onSessionExpired,
}: {
  onSessionExpired: () => void;
}) {
  const [connections, setConnections] = useState<ConnectionMap>(EMPTY_CONNECTIONS);
  const [connectedOrder, setConnectedOrder] = useState<ConnectorId[]>(() => readConnectedOrder());
  const [connectionsLoaded, setConnectionsLoaded] = useState(false);
  const [loadingConnectorId, setLoadingConnectorId] = useState<ConnectorId | null>(null);
  const [pendingDisconnectConnector, setPendingDisconnectConnector] = useState<ConnectorConfig | null>(null);
  const [removeDataConfirmation, setRemoveDataConfirmation] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleApiError = useCallback(
    (caughtError: unknown, fallbackMessage?: string) => {
      const message = getErrorMessage(caughtError) || fallbackMessage || "Request failed.";
      setError(message);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    },
    [onSessionExpired],
  );

  const loadConnection = useCallback(
    async (connectorId: ConnectorId) => {
      try {
        const result = await fetchConnectorConnection(connectorId);
        setConnections((currentConnections) => ({
          ...currentConnections,
          [connectorId]: result,
        }));
      } catch (caughtError) {
        handleApiError(caughtError);
      }
    },
    [handleApiError],
  );

  const loadConnections = useCallback(async () => {
    await Promise.all(CONNECTORS.map((connector) => loadConnection(connector.id)));
    setConnectionsLoaded(true);
  }, [loadConnection]);

  useEffect(() => {
    if (!connectionsLoaded) {
      return;
    }

    const url = new URL(window.location.href);
    let recentlyConnected: ConnectorId | null = null;
    for (const connector of CONNECTORS) {
      if (url.searchParams.get(`${connector.id}_connected`) !== "1") {
        continue;
      }
      recentlyConnected = connector.id;
      url.searchParams.delete(`${connector.id}_connected`);
      window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
      break;
    }

    setConnectedOrder((currentOrder) => {
      const syncedOrder = syncConnectedOrder(currentOrder, connections);
      const nextOrder = recentlyConnected
        ? moveConnectorToConnectedEnd(syncedOrder, recentlyConnected)
        : syncedOrder;
      writeConnectedOrder(nextOrder);
      return nextOrder;
    });
  }, [connectionsLoaded, connections]);

  useEffect(() => {
    void loadConnections();
  }, [loadConnections]);

  function handleConnect(connector: ConnectorConfig) {
    if (loadingConnectorId) {
      return;
    }
    const connection = connections[connector.id];
    if (!isConfigured(connector, connection)) {
      setStatus("");
      setError(`${connector.name} OAuth is not configured on the backend.`);
      return;
    }
    connectConnector(connector.id);
  }

  function connectConnector(connectorId: ConnectorId) {
    setLoadingConnectorId(connectorId);
    setStatus("");
    setError(null);
    void startOAuthFlow(`/api/me/integrations/${connectorId}/start`);
  }

  function openDisconnectModal(connector: ConnectorConfig) {
    setPendingDisconnectConnector(connector);
    setRemoveDataConfirmation("");
    setStatus("");
    setError(null);
  }

  function closeDisconnectModal() {
    if (loadingConnectorId) {
      return;
    }
    setPendingDisconnectConnector(null);
    setRemoveDataConfirmation("");
  }

  const connectedConnectors = useMemo(() => {
    const connected = CONNECTORS.filter((connector) => isConnected(connector, connections[connector.id]));
    return connected.sort((left, right) => compareConnectedOrder(left, right, connectedOrder));
  }, [connections, connectedOrder]);

  const disconnectedConnectors = useMemo(
    () => CONNECTORS.filter((connector) => !isConnected(connector, connections[connector.id])),
    [connections],
  );

  function renderConnectorTab(connector: ConnectorConfig) {
    const connected = isConnected(connector, connections[connector.id]);
    const loading = loadingConnectorId === connector.id;
    return (
      <div
        className={`home-connector-tab${connected ? " connected" : ""}${loading ? " loading" : ""}`}
        key={connector.id}
      >
        <span className="home-connector-identity">
          <ConnectorLogo connectorId={connector.id} />
          <span>{connector.name}</span>
        </span>
        <span className="home-connector-actions">
          {connected ? (
            <button
              type="button"
              className="home-connection-state connected"
              disabled={Boolean(loadingConnectorId)}
              onClick={() => openDisconnectModal(connector)}
            >
              {loading ? (
                "Disconnecting..."
              ) : (
                <>
                  <span>Manage</span>
                  <span className="home-manage-arrow" aria-hidden="true">
                    <svg viewBox="0 0 16 16" focusable="false">
                      <path d="M5 4h7v7" />
                      <path d="m4 12 8-8" />
                    </svg>
                  </span>
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              className="home-connection-state disconnected"
              disabled={Boolean(loadingConnectorId)}
              onClick={() => handleConnect(connector)}
            >
              {loading ? "Connecting..." : "Connect"}
            </button>
          )}
        </span>
      </div>
    );
  }

  async function handleDisconnect(connector: ConnectorConfig, removeData: boolean) {
    if (loadingConnectorId) {
      return;
    }
    setLoadingConnectorId(connector.id);
    setStatus("");
    setError(null);
    try {
      const result = await deleteConnectorConnection(connector.id, removeData);
      setConnections((currentConnections) => ({
        ...currentConnections,
        [connector.id]: result,
      }));
      setConnectedOrder((currentOrder) => {
        const nextOrder = currentOrder.filter((connectorId) => connectorId !== connector.id);
        writeConnectedOrder(nextOrder);
        return nextOrder;
      });
      setStatus(removeData ? `${connector.name} disconnected and data removal requested.` : `${connector.name} disconnected.`);
      setPendingDisconnectConnector(null);
      setRemoveDataConfirmation("");
    } catch (caughtError) {
      handleApiError(caughtError);
    } finally {
      setLoadingConnectorId(null);
    }
  }

  return (
    <aside className="home-connector-rail" aria-label="Connectors">
      <div className="home-connector-box">
        <div className="home-connector-title">Connectors</div>
        <div className="home-connector-tabs" aria-label="Connector accounts">
          {connectedConnectors.map(renderConnectorTab)}
          {connectedConnectors.length > 0 && disconnectedConnectors.length > 0 ? (
            <div className="home-connector-divider" role="separator" aria-hidden="true" />
          ) : null}
          {disconnectedConnectors.map(renderConnectorTab)}
        </div>
      </div>
      <AppToast message={error || status} error={Boolean(error)} />
      {pendingDisconnectConnector ? (
        <DisconnectConnectorModal
          connector={pendingDisconnectConnector}
          confirmation={removeDataConfirmation}
          loading={loadingConnectorId === pendingDisconnectConnector.id}
          onConfirmationChange={setRemoveDataConfirmation}
          onDisconnect={() => handleDisconnect(pendingDisconnectConnector, false)}
          onRemoveData={() => handleDisconnect(pendingDisconnectConnector, true)}
          onClose={closeDisconnectModal}
        />
      ) : null}
    </aside>
  );
}

async function fetchConnectorConnection(connectorId: ConnectorId): Promise<ConnectionMap[ConnectorId]> {
  if (connectorId === "github") {
    return fetchJson<GithubConnection>("/api/me/integrations/github");
  }
  if (connectorId === "bitbucket") {
    return fetchJson<BitbucketConnection>("/api/me/integrations/bitbucket");
  }
  if (connectorId === "gitlab") {
    return fetchJson<GitlabConnection>("/api/me/integrations/gitlab");
  }
  if (connectorId === "jira") {
    return fetchJson<JiraConnection>("/api/me/integrations/jira");
  }
  if (connectorId === "slack") {
    return fetchJson<SlackConnection>("/api/me/integrations/slack");
  }
  if (connectorId === "teams") {
    return fetchJson<TeamsConnection>("/api/me/integrations/teams");
  }
  if (connectorId === "linear") {
    return fetchJson<LinearConnection>("/api/me/integrations/linear");
  }
  if (connectorId === "confluence") {
    return fetchJson<ConfluenceConnection>("/api/me/integrations/confluence");
  }
  if (connectorId === "notion") {
    return fetchJson<NotionConnection>("/api/me/integrations/notion");
  }
  return fetchJson<TeamsConnection>("/api/me/integrations/teams");
}

async function deleteConnectorConnection(connectorId: ConnectorId, removeData: boolean): Promise<ConnectionMap[ConnectorId]> {
  const params = removeData ? "?remove_data=true" : "";
  if (connectorId === "github") {
    return deleteJson<GithubConnection>(`/api/me/integrations/github${params}`);
  }
  if (connectorId === "bitbucket") {
    return deleteJson<BitbucketConnection>(`/api/me/integrations/bitbucket${params}`);
  }
  if (connectorId === "gitlab") {
    return deleteJson<GitlabConnection>(`/api/me/integrations/gitlab${params}`);
  }
  if (connectorId === "jira") {
    return deleteJson<JiraConnection>(`/api/me/integrations/jira${params}`);
  }
  if (connectorId === "slack") {
    return deleteJson<SlackConnection>(`/api/me/integrations/slack${params}`);
  }
  if (connectorId === "teams") {
    return deleteJson<TeamsConnection>(`/api/me/integrations/teams${params}`);
  }
  if (connectorId === "linear") {
    return deleteJson<LinearConnection>(`/api/me/integrations/linear${params}`);
  }
  if (connectorId === "confluence") {
    return deleteJson<ConfluenceConnection>(`/api/me/integrations/confluence${params}`);
  }
  if (connectorId === "notion") {
    return deleteJson<NotionConnection>(`/api/me/integrations/notion${params}`);
  }
  return deleteJson<TeamsConnection>(`/api/me/integrations/teams${params}`);
}

function readConnectedOrder(): ConnectorId[] {
  try {
    const storedOrder = window.localStorage.getItem(CONNECTED_ORDER_STORAGE_KEY);
    if (!storedOrder) {
      return [];
    }
    const parsed = JSON.parse(storedOrder);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (connectorId): connectorId is ConnectorId =>
        typeof connectorId === "string" && CONNECTORS.some((connector) => connector.id === connectorId),
    );
  } catch {
    return [];
  }
}

function writeConnectedOrder(order: ConnectorId[]) {
  window.localStorage.setItem(CONNECTED_ORDER_STORAGE_KEY, JSON.stringify(order));
}

function syncConnectedOrder(order: ConnectorId[], connections: ConnectionMap): ConnectorId[] {
  const connectedIds = CONNECTORS.filter((connector) => isConnected(connector, connections[connector.id])).map(
    (connector) => connector.id,
  );
  const nextOrder = order.filter((connectorId) => connectedIds.includes(connectorId));
  for (const connector of CONNECTORS) {
    if (connectedIds.includes(connector.id) && !nextOrder.includes(connector.id)) {
      nextOrder.push(connector.id);
    }
  }
  return nextOrder;
}

function moveConnectorToConnectedEnd(order: ConnectorId[], connectorId: ConnectorId): ConnectorId[] {
  return [...order.filter((currentId) => currentId !== connectorId), connectorId];
}

function compareConnectedOrder(
  left: ConnectorConfig,
  right: ConnectorConfig,
  connectedOrder: ConnectorId[],
): number {
  const leftIndex = connectedOrder.indexOf(left.id);
  const rightIndex = connectedOrder.indexOf(right.id);
  if (leftIndex === -1 && rightIndex === -1) {
    return CONNECTORS.indexOf(left) - CONNECTORS.indexOf(right);
  }
  if (leftIndex === -1) {
    return 1;
  }
  if (rightIndex === -1) {
    return -1;
  }
  return leftIndex - rightIndex;
}

function isConnected(connector: ConnectorConfig, connection: ConnectionMap[ConnectorId]): boolean {
  if (!connection) {
    return false;
  }
  if (connector.id === "slack") {
    return Boolean((connection as SlackConnection).connected && (connection as SlackConnection).teams.length);
  }
  return Boolean((connection as { connected?: boolean }).connected);
}

function isConfigured(connector: ConnectorConfig, connection: ConnectionMap[ConnectorId]): boolean {
  if (!connection || connector.id === "jira") {
    return true;
  }
  const maybeConfigured = (connection as { configured?: boolean }).configured;
  return maybeConfigured !== false;
}

function DisconnectConnectorModal({
  connector,
  confirmation,
  loading,
  onConfirmationChange,
  onDisconnect,
  onRemoveData,
  onClose,
}: {
  connector: ConnectorConfig;
  confirmation: string;
  loading: boolean;
  onConfirmationChange: (value: string) => void;
  onDisconnect: () => void;
  onRemoveData: () => void;
  onClose: () => void;
}) {
  const removeDataConfirmed = confirmation.trim().toLowerCase() === "remove data";

  function handleConfirmationKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (loading) {
      event.preventDefault();
      return;
    }
    if (event.key === "Backspace") {
      event.preventDefault();
      onConfirmationChange(confirmation.slice(0, -1));
      return;
    }
    if (event.key === "Delete") {
      event.preventDefault();
      onConfirmationChange("");
      return;
    }
    if (event.key.length === 1 && !event.metaKey && !event.ctrlKey && !event.altKey) {
      event.preventDefault();
      onConfirmationChange(`${confirmation}${event.key}`.slice(0, "remove data".length));
    }
  }

  return (
    <div
      className="connector-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="home-disconnect-modal" role="dialog" aria-modal="true" aria-labelledby="home-disconnect-heading">
        <header className="home-disconnect-header">
          <div>
            <h2 id="home-disconnect-heading">Disconnect {connector.name}</h2>
            <p>Choose whether to keep workspace data or remove synced data owned by this connection.</p>
          </div>
          <button type="button" className="connector-close-button" aria-label="Close disconnect warning" disabled={loading} onClick={onClose}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
            </svg>
          </button>
        </header>
        <div className="home-disconnect-body">
          <div className="home-disconnect-warning">
            <strong>Disconnect</strong>
            <span>Removes account access but keeps existing workspace sources and indexed data.</span>
          </div>
          <div className="home-disconnect-warning danger">
            <strong>Remove data</strong>
            <span>Also removes workspace sources synced by this connector account where supported.</span>
          </div>
          <label htmlFor="removeDataConfirmation">Type remove data to enable data removal</label>
          <input
            id="removeDataConfirmation"
            name="removeDataConfirmationManual"
            value={confirmation}
            placeholder="remove data"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="none"
            spellCheck={false}
            disabled={loading}
            onChange={() => undefined}
            onKeyDown={handleConfirmationKeyDown}
            onPaste={(event) => event.preventDefault()}
            onDrop={(event) => event.preventDefault()}
            onContextMenu={(event) => event.preventDefault()}
          />
        </div>
        <div className="home-disconnect-actions">
          <button type="button" className="modal-cancel-button" disabled={loading} onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="secondary-action-button" disabled={loading} onClick={onDisconnect}>
            {loading ? "Disconnecting..." : "Disconnect"}
          </button>
          <button type="button" className="danger-button" disabled={loading || !removeDataConfirmed} onClick={onRemoveData}>
            Remove data
          </button>
        </div>
      </div>
    </div>
  );
}
