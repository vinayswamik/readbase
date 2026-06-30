import { postJson } from "../api";
import type { ConnectorId } from "../pages/workspace/connectors/connectors";

export function isMockApi(): boolean {
  return import.meta.env.VITE_MOCK_API === "true";
}

function connectorFromStartUrl(startUrl: string): ConnectorId | null {
  const match = startUrl.match(/\/api\/me\/integrations\/([^/?]+)\/start/);
  const connector = match?.[1];
  if (!connector) {
    return null;
  }
  return connector as ConnectorId;
}

export async function mockConnectConnector(connectorId: ConnectorId): Promise<void> {
  await postJson<Record<string, never>, unknown>(`/api/mock/connect/${connectorId}`, {});
}

export type StartOAuthFlowOptions = {
  connectorId?: ConnectorId;
  onMockConnected?: () => void;
};

export async function startOAuthFlow(
  startUrl: string,
  options?: StartOAuthFlowOptions,
): Promise<void> {
  if (!isMockApi()) {
    window.location.assign(startUrl);
    return;
  }

  const connector = options?.connectorId ?? connectorFromStartUrl(startUrl);
  if (!connector) {
    throw new Error(`Could not parse connector from OAuth URL: ${startUrl}`);
  }

  await mockConnectConnector(connector);
  options?.onMockConnected?.();
}
