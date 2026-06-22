import { postJson } from "../api";

export function isMockApi(): boolean {
  return import.meta.env.VITE_MOCK_API === "true";
}

function connectorFromStartUrl(startUrl: string): string | null {
  const match = startUrl.match(/\/api\/me\/integrations\/([^/?]+)\/start/);
  return match?.[1] ?? null;
}

export async function startOAuthFlow(startUrl: string): Promise<void> {
  if (!isMockApi()) {
    window.location.assign(startUrl);
    return;
  }

  const connector = connectorFromStartUrl(startUrl);
  if (!connector) {
    console.warn("[mock-api] Could not parse connector from OAuth URL:", startUrl);
    return;
  }

  await postJson<Record<string, never>, unknown>(`/api/mock/connect/${connector}`, {});
  window.location.reload();
}
