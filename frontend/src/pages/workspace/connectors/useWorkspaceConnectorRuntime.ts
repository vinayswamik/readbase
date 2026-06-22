import { useEffect, useMemo, useState } from "react";

import type {
  BitbucketConnection,
  BitbucketRepository,
  ConfluenceConnection,
  ConfluenceSpace,
  NotionConnection,
  NotionDatabase,
  GitlabConnection,
  GitlabProject,
  GithubConnection,
  GithubRepository,
  JiraConnection,
  JiraProject,
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
import { CONNECTORS, type ConnectorId } from "./connectors";
import { slackOauthErrorMessage } from "../chat/useWorkspaceReposAndChat";
import { useWorkspaceConnectorLoaders } from "./useWorkspaceConnectorData";

export function useWorkspaceConnectorState() {
  const [activeConnectorId, setActiveConnectorId] =
    useState<ConnectorId | null>(null);
  const [connectorRepoUrl, setConnectorRepoUrl] = useState("");
  const [connectorRefreshRepo, setConnectorRefreshRepo] = useState(false);
  const [connectorStatus, setConnectorStatus] = useState("");
  const [connectorError, setConnectorError] = useState<string | null>(null);
  const [indexing, setIndexing] = useState(false);
  const [githubConnection, setGithubConnection] =
    useState<GithubConnection | null>(null);
  const [githubRepositories, setGithubRepositories] = useState<
    GithubRepository[]
  >([]);
  const [githubRepositoryQuery, setGithubRepositoryQuery] = useState("");
  const [githubRepositoriesLoading, setGithubRepositoriesLoading] =
    useState(false);
  const [bitbucketConnection, setBitbucketConnection] =
    useState<BitbucketConnection | null>(null);
  const [bitbucketRepositories, setBitbucketRepositories] = useState<
    BitbucketRepository[]
  >([]);
  const [bitbucketRepositoryQuery, setBitbucketRepositoryQuery] = useState("");
  const [bitbucketLoading, setBitbucketLoading] = useState(false);
  const [gitlabConnection, setGitlabConnection] =
    useState<GitlabConnection | null>(null);
  const [gitlabProjects, setGitlabProjects] = useState<GitlabProject[]>([]);
  const [gitlabProjectQuery, setGitlabProjectQuery] = useState("");
  const [gitlabLoading, setGitlabLoading] = useState(false);
  const [jiraConnection, setJiraConnection] = useState<JiraConnection | null>(
    null,
  );
  const [jiraSources, setJiraSources] = useState<WorkspaceJiraSource[]>([]);
  const [jiraProjects, setJiraProjects] = useState<JiraProject[]>([]);
  const [jiraProjectQuery, setJiraProjectQuery] = useState("");
  const [jiraLoading, setJiraLoading] = useState(false);
  const [jiraWorkspaceSite, setJiraWorkspaceSite] = useState<WorkspaceJiraSiteStatus | null>(null);
  const [slackConnection, setSlackConnection] =
    useState<SlackConnection | null>(null);
  const [slackSources, setSlackSources] = useState<WorkspaceSlackSource[]>([]);
  const [slackTeams, setSlackTeams] = useState<WorkspaceSlackTeam[]>([]);
  const [slackChannels, setSlackChannels] = useState<SlackChannel[]>([]);
  const [slackChannelQuery, setSlackChannelQuery] = useState("");
  const [slackLoading, setSlackLoading] = useState(false);
  const [linearConnection, setLinearConnection] =
    useState<LinearConnection | null>(null);
  const [linearSources, setLinearSources] = useState<WorkspaceLinearSource[]>(
    [],
  );
  const [linearSelectableSources, setLinearSelectableSources] = useState<
    LinearSelectableSource[]
  >([]);
  const [linearQuery, setLinearQuery] = useState("");
  const [linearLoading, setLinearLoading] = useState(false);
  const [confluenceConnection, setConfluenceConnection] =
    useState<ConfluenceConnection | null>(null);
  const [confluenceSources, setConfluenceSources] = useState<
    WorkspaceConfluenceSource[]
  >([]);
  const [confluenceSpaces, setConfluenceSpaces] = useState<ConfluenceSpace[]>(
    [],
  );
  const [confluenceQuery, setConfluenceQuery] = useState("");
  const [confluenceLoading, setConfluenceLoading] = useState(false);
  const [notionConnection, setNotionConnection] = useState<NotionConnection | null>(null);
  const [notionSources, setNotionSources] = useState<WorkspaceNotionSource[]>([]);
  const [notionDatabases, setNotionDatabases] = useState<NotionDatabase[]>([]);
  const [notionQuery, setNotionQuery] = useState("");
  const [notionLoading, setNotionLoading] = useState(false);

  return {
    activeConnectorId,
    setActiveConnectorId,
    connectorRepoUrl,
    setConnectorRepoUrl,
    connectorRefreshRepo,
    setConnectorRefreshRepo,
    connectorStatus,
    setConnectorStatus,
    connectorError,
    setConnectorError,
    indexing,
    setIndexing,
    githubConnection,
    setGithubConnection,
    githubRepositories,
    setGithubRepositories,
    githubRepositoryQuery,
    setGithubRepositoryQuery,
    githubRepositoriesLoading,
    setGithubRepositoriesLoading,
    bitbucketConnection,
    setBitbucketConnection,
    bitbucketRepositories,
    setBitbucketRepositories,
    bitbucketRepositoryQuery,
    setBitbucketRepositoryQuery,
    bitbucketLoading,
    setBitbucketLoading,
    gitlabConnection,
    setGitlabConnection,
    gitlabProjects,
    setGitlabProjects,
    gitlabProjectQuery,
    setGitlabProjectQuery,
    gitlabLoading,
    setGitlabLoading,
    jiraConnection,
    setJiraConnection,
    jiraSources,
    setJiraSources,
    jiraProjects,
    setJiraProjects,
    jiraProjectQuery,
    setJiraProjectQuery,
    jiraLoading,
    setJiraLoading,
    jiraWorkspaceSite,
    setJiraWorkspaceSite,
    slackConnection,
    setSlackConnection,
    slackSources,
    setSlackSources,
    slackTeams,
    setSlackTeams,
    slackChannels,
    setSlackChannels,
    slackChannelQuery,
    setSlackChannelQuery,
    slackLoading,
    setSlackLoading,
    linearConnection,
    setLinearConnection,
    linearSources,
    setLinearSources,
    linearSelectableSources,
    setLinearSelectableSources,
    linearQuery,
    setLinearQuery,
    linearLoading,
    setLinearLoading,
    confluenceConnection,
    setConfluenceConnection,
    confluenceSources,
    setConfluenceSources,
    confluenceSpaces,
    setConfluenceSpaces,
    confluenceQuery,
    setConfluenceQuery,
    confluenceLoading,
    setConfluenceLoading,
    notionConnection,
    setNotionConnection,
    notionSources,
    setNotionSources,
    notionDatabases,
    setNotionDatabases,
    notionQuery,
    setNotionQuery,
    notionLoading,
    setNotionLoading,
  };
}

export type WorkspaceConnectorState = ReturnType<
  typeof useWorkspaceConnectorState
>;

type ConnectorLoaders = ReturnType<typeof useWorkspaceConnectorLoaders>;

type Args = {
  workspace: Workspace;
  state: WorkspaceConnectorState;
  loaders: ConnectorLoaders;
};

export function useWorkspaceConnectorEffects({ workspace, state, loaders }: Args) {
  useEffect(() => {
    void loaders.loadGithubConnection();
    void loaders.loadBitbucketConnection();
    void loaders.loadGitlabConnection();
    void loaders.loadJiraConnection();
    void loaders.loadJiraSources();
    void loaders.loadSlackConnection();
    void loaders.loadSlackSources();
    void loaders.loadSlackTeams();
    void loaders.loadLinearConnection();
    void loaders.loadLinearSources();
    void loaders.loadConfluenceConnection();
    void loaders.loadConfluenceSources();
    void loaders.loadNotionConnection();
    void loaders.loadNotionSources();
  }, [
    loaders.loadBitbucketConnection,
    loaders.loadConfluenceConnection,
    loaders.loadConfluenceSources,
    loaders.loadNotionConnection,
    loaders.loadNotionSources,
    loaders.loadGithubConnection,
    loaders.loadGitlabConnection,
    loaders.loadJiraConnection,
    loaders.loadJiraSources,
    loaders.loadLinearConnection,
    loaders.loadLinearSources,
    loaders.loadSlackConnection,
    loaders.loadSlackSources,
    loaders.loadSlackTeams,
  ]);

  useEffect(() => {
    const url = new URL(window.location.href);
    const connector = url.searchParams.get("connector");
    const slackConnected = url.searchParams.get("slack_connected");
    const slackError = url.searchParams.get("slack_error");
    const returnWorkspaceId = url.searchParams.get("workspace_id");
    const isSlackCallback =
      connector === "slack" || Boolean(slackConnected || slackError);
    if (
      !isSlackCallback ||
      (returnWorkspaceId && returnWorkspaceId !== workspace.workspace_id)
    ) {
      return;
    }
    state.setActiveConnectorId("slack");
    state.setConnectorStatus(
      slackConnected === "already"
        ? "This Slack workspace is already connected."
        : slackConnected
          ? "Slack workspace connected. Choose channels to add to this Readbase workspace."
          : "",
    );
    state.setConnectorError(slackError ? slackOauthErrorMessage(slackError) : null);
    void loaders.loadSlackConnection();
    void loaders.loadSlackSources();
    void loaders.loadSlackTeams();
    url.searchParams.delete("connector");
    url.searchParams.delete("workspace_id");
    url.searchParams.delete("slack_connected");
    url.searchParams.delete("slack_error");
    window.history.replaceState({}, "", url.pathname + url.search);
  }, [loaders.loadSlackConnection, loaders.loadSlackSources, loaders.loadSlackTeams, workspace.workspace_id]);
  useEffect(() => {
    if (state.activeConnectorId === "github") {
      void loaders.loadGithubConnection();
      if (state.githubConnection?.connected) {
        void loaders.loadGithubRepositories(state.githubRepositoryQuery);
      }
    }
    if (state.activeConnectorId === "bitbucket") {
      void loaders.loadBitbucketConnection();
      if (state.bitbucketConnection?.connected) {
        void loaders.loadBitbucketRepositories(state.bitbucketRepositoryQuery);
      }
    }
    if (state.activeConnectorId === "gitlab") {
      void loaders.loadGitlabConnection();
      if (state.gitlabConnection?.connected) {
        void loaders.loadGitlabProjects(state.gitlabProjectQuery);
      }
    }
    if (state.activeConnectorId === "jira") {
      void loaders.loadJiraConnection();
      void loaders.loadJiraWorkspaceSite();
      void loaders.loadJiraSources();
      if (state.jiraConnection?.connected && state.jiraWorkspaceSite?.connected) {
        void loaders.loadJiraProjects(state.jiraProjectQuery);
      }
    }
    if (state.activeConnectorId === "slack") {
      void loaders.loadSlackConnection();
      void loaders.loadSlackSources();
      void loaders.loadSlackTeams();
    }
    if (state.activeConnectorId === "linear") {
      void loaders.loadLinearConnection();
      void loaders.loadLinearSources();
      if (state.linearConnection?.connected) {
        void loaders.loadLinearSelectableSources(state.linearQuery);
      }
    }
    if (state.activeConnectorId === "confluence") {
      void loaders.loadConfluenceConnection();
      void loaders.loadConfluenceSources();
      if (state.confluenceConnection?.connected) {
        void loaders.loadConfluenceSpaces(state.confluenceQuery);
      }
    }
    if (state.activeConnectorId === "notion") {
      void loaders.loadNotionConnection();
      void loaders.loadNotionSources();
      if (state.notionConnection?.connected) {
        void loaders.loadNotionDatabases(state.notionQuery);
      }
    }
  }, [
    state.activeConnectorId,
    state.bitbucketConnection?.connected,
    state.bitbucketRepositoryQuery,
    state.confluenceConnection?.connected,
    state.confluenceQuery,
    state.notionConnection?.connected,
    state.notionQuery,
    state.githubConnection?.connected,
    state.githubRepositoryQuery,
    state.gitlabConnection?.connected,
    state.gitlabProjectQuery,
    state.jiraConnection?.connected,
    state.jiraWorkspaceSite?.connected,
    state.jiraProjectQuery,
    state.linearConnection?.connected,
    state.linearQuery,
    loaders.loadBitbucketConnection,
    loaders.loadBitbucketRepositories,
    loaders.loadConfluenceConnection,
    loaders.loadConfluenceSources,
    loaders.loadConfluenceSpaces,
    loaders.loadNotionConnection,
    loaders.loadNotionSources,
    loaders.loadNotionDatabases,
    loaders.loadGithubConnection,
    loaders.loadGithubRepositories,
    loaders.loadGitlabConnection,
    loaders.loadGitlabProjects,
    loaders.loadJiraConnection,
    loaders.loadJiraWorkspaceSite,
    loaders.loadJiraProjects,
    loaders.loadJiraSources,
    loaders.loadLinearConnection,
    loaders.loadLinearSelectableSources,
    loaders.loadLinearSources,
    loaders.loadSlackConnection,
    loaders.loadSlackSources,
    loaders.loadSlackTeams,
  ]);
  useEffect(() => {
    if (state.activeConnectorId !== "slack" || !state.slackTeams.length) {
      return;
    }
    void loaders.loadSlackChannels();
  }, [state.activeConnectorId, loaders.loadSlackChannels, state.slackTeams.length]);
}

type UseWorkspaceConnectorRuntimeArgs = {
  workspace: Workspace;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
};

export function useWorkspaceConnectorRuntime({
  workspace,
  handleApiError,
}: UseWorkspaceConnectorRuntimeArgs) {
  const state = useWorkspaceConnectorState();
  const loaders = useWorkspaceConnectorLoaders({
    workspace,
    handleApiError,
    state,
  });
  useWorkspaceConnectorEffects({ workspace, state, loaders });

  const activeConnector = useMemo(
    () =>
      CONNECTORS.find((connector) => connector.id === state.activeConnectorId) ??
      null,
    [state.activeConnectorId],
  );

  return {
    ...state,
    ...loaders,
    activeConnector,
  };
}
