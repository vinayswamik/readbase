export type ConnectorId = "jira" | "slack" | "teams" | "github" | "bitbucket" | "gitlab" | "confluence" | "linear" | "notion";
export type ConnectorCategoryId = "codebase" | "project-management" | "discussions";

export type ConnectorConfig = {
  id: ConnectorId;
  name: string;
  category: ConnectorCategoryId;
};

export const CONNECTORS: ConnectorConfig[] = [
  { id: "github", name: "GitHub", category: "codebase" },
  { id: "gitlab", name: "GitLab", category: "codebase" },
  { id: "bitbucket", name: "Bitbucket", category: "codebase" },
  { id: "confluence", name: "Confluence", category: "project-management" },
  { id: "notion", name: "Notion", category: "project-management" },
  { id: "jira", name: "Jira", category: "project-management" },
  { id: "linear", name: "Linear", category: "project-management" },
  { id: "slack", name: "Slack", category: "discussions" },
  { id: "teams", name: "Microsoft Teams", category: "discussions" },
];

export function buildConnectorStartUrl(connectorId: ConnectorId, workspaceId?: string): string {
  if (connectorId === "slack" && workspaceId) {
    const params = new URLSearchParams({ workspace_id: workspaceId });
    return `/api/me/integrations/slack/start?${params.toString()}`;
  }
  return `/api/me/integrations/${connectorId}/start`;
}

export const CONNECTOR_CATEGORY_ORDER: Array<{ id: ConnectorCategoryId; label: string }> = [
  { id: "codebase", label: "Codebase" },
  { id: "project-management", label: "Project management" },
  { id: "discussions", label: "Discussions" },
];
