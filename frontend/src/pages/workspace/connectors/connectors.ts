export type ConnectorId = "jira" | "slack" | "teams" | "github" | "bitbucket" | "gitlab" | "confluence" | "linear";
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
  { id: "jira", name: "Jira", category: "project-management" },
  { id: "linear", name: "Linear", category: "project-management" },
  { id: "slack", name: "Slack", category: "discussions" },
  { id: "teams", name: "Microsoft Teams", category: "discussions" },
];

export const CONNECTOR_CATEGORY_ORDER: Array<{ id: ConnectorCategoryId; label: string }> = [
  { id: "codebase", label: "Codebase" },
  { id: "project-management", label: "Project management" },
  { id: "discussions", label: "Discussions" },
];
