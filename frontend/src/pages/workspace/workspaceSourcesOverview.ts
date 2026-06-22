import { fetchJson } from "../../api";
import type {
  BitbucketConnection,
  ConfluenceConnection,
  GitlabConnection,
  GithubConnection,
  IndexedRepo,
  JiraConnection,
  LinearConnection,
  NotionConnection,
  ReposResponse,
  SlackConnection,
  TeamsConnection,
  WorkspaceConfluenceSource,
  WorkspaceConfluenceSourcesResponse,
  WorkspaceJiraSource,
  WorkspaceJiraSourcesResponse,
  WorkspaceLinearSource,
  WorkspaceLinearSourcesResponse,
  WorkspaceNotionSource,
  WorkspaceNotionSourcesResponse,
  WorkspaceSlackSource,
  WorkspaceSlackSourcesResponse,
  WorkspaceSlackTeam,
  WorkspaceSlackTeamsResponse,
} from "../../types";
import { CONNECTORS, type ConnectorConfig, type ConnectorId } from "./connectors/connectors";

export type WorkspaceSourceRow = {
  id: string;
  name: string;
  type: string;
  sortKey: string;
  workspace?: string;
};

export type ConnectorSourcesHolder = {
  connector: ConnectorConfig;
  connected: boolean;
  sources: WorkspaceSourceRow[];
};

type ConnectionMap = {
  github: GithubConnection | null;
  bitbucket: BitbucketConnection | null;
  gitlab: GitlabConnection | null;
  jira: JiraConnection | null;
  slack: SlackConnection | null;
  linear: LinearConnection | null;
  confluence: ConfluenceConnection | null;
  notion: NotionConnection | null;
  teams: TeamsConnection | null;
};

export type WorkspaceSourcesInput = ConnectionMap & {
  repos: IndexedRepo[];
  jiraSources: WorkspaceJiraSource[];
  slackSources: WorkspaceSlackSource[];
  slackTeams: WorkspaceSlackTeam[];
  linearSources: WorkspaceLinearSource[];
  confluenceSources: WorkspaceConfluenceSource[];
  notionSources: WorkspaceNotionSource[];
};

function normalizeSourceList<T>(sources: T[] | T | null | undefined): T[] {
  if (!sources) {
    return [];
  }
  if (Array.isArray(sources)) {
    return sources;
  }
  if (typeof sources === "object") {
    return [sources];
  }
  return [];
}

export async function fetchWorkspaceSourcesInput(workspaceId: string): Promise<WorkspaceSourcesInput> {
  const [
    reposResult,
    jiraSourcesResult,
    slackSourcesResult,
    slackTeamsResult,
    linearSourcesResult,
    confluenceSourcesResult,
    notionSourcesResult,
    githubConnection,
    bitbucketConnection,
    gitlabConnection,
    jiraConnection,
    slackConnection,
    linearConnection,
    confluenceConnection,
    notionConnection,
    teamsConnection,
  ] = await Promise.all([
    safeFetch(`/api/workspaces/${workspaceId}/repos`, { repos: [] } as ReposResponse),
    safeFetch(`/api/workspaces/${workspaceId}/jira/sources`, { sources: [] } as WorkspaceJiraSourcesResponse),
    safeFetch(`/api/workspaces/${workspaceId}/slack/sources`, { sources: [] } as WorkspaceSlackSourcesResponse),
    safeFetch(`/api/workspaces/${workspaceId}/slack/teams`, { teams: [] } as WorkspaceSlackTeamsResponse),
    safeFetch(`/api/workspaces/${workspaceId}/linear/sources`, { sources: [] } as WorkspaceLinearSourcesResponse),
    safeFetch(`/api/workspaces/${workspaceId}/confluence/sources`, { sources: [] } as WorkspaceConfluenceSourcesResponse),
    safeFetch(`/api/workspaces/${workspaceId}/notion/sources`, { sources: [] } as WorkspaceNotionSourcesResponse),
    safeFetch("/api/me/integrations/github", { connected: false, configured: false, scopes: [] } as GithubConnection),
    safeFetch("/api/me/integrations/bitbucket", { connected: false, configured: false, scopes: [] } as BitbucketConnection),
    safeFetch("/api/me/integrations/gitlab", { connected: false, configured: false, scopes: [] } as GitlabConnection),
    safeFetch("/api/me/integrations/jira", { connected: false, scopes: [], sites: [] } as JiraConnection),
    safeFetch("/api/me/integrations/slack", { connected: false, configured: false, teams: [] } as SlackConnection),
    safeFetch("/api/me/integrations/linear", { connected: false, configured: false, scopes: [] } as LinearConnection),
    safeFetch("/api/me/integrations/confluence", { connected: false, configured: false, scopes: [], sites: [] } as ConfluenceConnection),
    safeFetch("/api/me/integrations/notion", { connected: false, configured: false } as NotionConnection),
    safeFetch("/api/me/integrations/teams", { connected: false, configured: false, scopes: [], teams: [] } as TeamsConnection),
  ]);

  return {
    github: githubConnection,
    bitbucket: bitbucketConnection,
    gitlab: gitlabConnection,
    jira: jiraConnection,
    slack: slackConnection,
    linear: linearConnection,
    confluence: confluenceConnection,
    notion: notionConnection,
    teams: teamsConnection,
    repos: normalizeSourceList(reposResult.repos),
    jiraSources: normalizeSourceList(jiraSourcesResult.sources),
    slackSources: normalizeSourceList(slackSourcesResult.sources),
    slackTeams: normalizeSourceList(slackTeamsResult.teams),
    linearSources: normalizeSourceList(linearSourcesResult.sources),
    confluenceSources: normalizeSourceList(confluenceSourcesResult.sources),
    notionSources: normalizeSourceList(notionSourcesResult.sources),
  };
}

async function safeFetch<T>(url: string, fallback: T): Promise<T> {
  try {
    return await fetchJson<T>(url);
  } catch {
    return fallback;
  }
}

export function buildConnectorSourcesHolders(input: WorkspaceSourcesInput): ConnectorSourcesHolder[] {
  return CONNECTORS.map((connector) => {
    const connected = isConnectorConnected(connector.id, input, input);
    return {
      connector,
      connected,
      sources: connected ? sourcesForConnector(connector.id, input) : [],
    };
  });
}

export function filterSourcesModalHolders(
  holders: ConnectorSourcesHolder[],
  query: string,
): ConnectorSourcesHolder[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return holders.filter((holder) => holder.connected);
  }
  return holders.filter((holder) => holder.connector.name.toLowerCase().includes(normalized));
}

function sourcesForConnector(connectorId: ConnectorId, input: WorkspaceSourcesInput): WorkspaceSourceRow[] {
  if (connectorId === "github") {
    return repoSourcesForProvider(input.repos, "github");
  }
  if (connectorId === "gitlab") {
    return repoSourcesForProvider(input.repos, "gitlab");
  }
  if (connectorId === "bitbucket") {
    return repoSourcesForProvider(input.repos, "bitbucket");
  }
  if (connectorId === "jira") {
    return sortSourceRows(
      normalizeSourceList(input.jiraSources).map((source) => ({
        id: source.source_id || `jira:${source.cloud_id}:${source.project_id}`,
        name: source.project_name,
        type: "Project",
        sortKey: source.created_at || source.source_id || `${source.cloud_id}:${source.project_id}`,
      })),
    );
  }
  if (connectorId === "slack") {
    return sortSourceRows(
      normalizeSourceList(input.slackSources).map((source) => ({
        id: source.source_id || `slack:${source.team_id}:${source.channel_id}`,
        name: source.channel_name,
        workspace: source.team_name,
        type: "Channel",
        sortKey: source.created_at || source.source_id || `${source.team_id}:${source.channel_id}`,
      })),
    );
  }
  if (connectorId === "linear") {
    return sortSourceRows(
      normalizeSourceList(input.linearSources).map((source) => ({
        id: source.source_id || `linear:${source.linear_team_id}:${source.linear_project_id || "team"}`,
        name: source.project_name || source.team_name,
        type: source.linear_project_id ? "Project" : "Team",
        sortKey: source.created_at || source.source_id || `${source.linear_team_id}:${source.linear_project_id || "team"}`,
      })),
    );
  }
  if (connectorId === "confluence") {
    return sortSourceRows(
      normalizeSourceList(input.confluenceSources).map((source) => ({
        id: source.source_id || `confluence:${source.cloud_id}:${source.space_id}`,
        name: source.space_name,
        type: "Space",
        sortKey: source.created_at || source.source_id || `${source.cloud_id}:${source.space_id}`,
      })),
    );
  }
  if (connectorId === "notion") {
    return sortSourceRows(
      normalizeSourceList(input.notionSources).map((source) => ({
        id: source.source_id || `notion:${source.notion_workspace_id}:${source.database_id}`,
        name: source.database_title,
        type: "Database",
        sortKey: source.created_at || source.source_id || `${source.notion_workspace_id}:${source.database_id}`,
      })),
    );
  }
  return [];
}

function repoSourcesForProvider(repos: IndexedRepo[], provider: "github" | "gitlab" | "bitbucket"): WorkspaceSourceRow[] {
  return sortSourceRows(
    normalizeSourceList(repos)
      .filter((repo) => repoProvider(repo.repo_url) === provider)
      .map((repo) => ({
        id: repo.repo_id || repo.repo_url,
        name: repoDisplayName(repo.repo_url),
        type: "Code",
        sortKey: repo.repo_id || repo.repo_url,
      })),
  );
}

function sortSourceRows(rows: WorkspaceSourceRow[]): WorkspaceSourceRow[] {
  return [...rows].sort((left, right) => left.sortKey.localeCompare(right.sortKey));
}

function repoDisplayName(repoUrl: string): string {
  try {
    const parsed = new URL(repoUrl);
    return parsed.pathname.replace(/^\/+/, "").replace(/\.git$/, "");
  } catch {
    return repoUrl;
  }
}

function repoProvider(repoUrl: string): "github" | "gitlab" | "bitbucket" | null {
  if (repoUrl.startsWith("local://")) {
    return null;
  }
  try {
    const host = new URL(repoUrl).hostname.toLowerCase();
    if (host === "github.com") {
      return "github";
    }
    if (host === "bitbucket.org") {
      return "bitbucket";
    }
    if (host === "gitlab.com" || host.endsWith(".gitlab.com")) {
      return "gitlab";
    }
  } catch {
    return null;
  }
  return null;
}

export function isConnectorConnected(connectorId: ConnectorId, connections: ConnectionMap, input?: Pick<WorkspaceSourcesInput, "slackTeams">): boolean {
  const connection = connections[connectorId];
  if (!connection) {
    return false;
  }
  if (connectorId === "slack") {
    return Boolean(input?.slackTeams?.length);
  }
  return Boolean((connection as { connected?: boolean }).connected);
}
