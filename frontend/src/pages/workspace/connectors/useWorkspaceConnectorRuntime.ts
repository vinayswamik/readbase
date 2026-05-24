import { useEffect, useMemo, useState } from "react";

import type {
  BitbucketConnection,
  BitbucketRepository,
  ConfluenceConnection,
  ConfluenceSpace,
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
  WorkspaceJiraSource,
  WorkspaceLinearSource,
  WorkspaceMember,
  WorkspaceSlackSource,
} from "../../../types";
import { CONNECTORS, type ConnectorId } from "./connectors";
import { slackOauthErrorMessage } from "../chat/useWorkspaceReposAndChat";
import { useWorkspaceConnectorLoaders } from "./useWorkspaceConnectorData";

export function useWorkspaceConnectorState() {
  const [activeConnectorId, setActiveConnectorId] =
    useState<ConnectorId | null>(null);
  const [connectorRepoUrl, setConnectorRepoUrl] = useState("");
  const [connectorRefreshRepo, setConnectorRefreshRepo] = useState(false);
  const [connectorMembers, setConnectorMembers] = useState<WorkspaceMember[]>(
    [],
  );
  const [connectorStatus, setConnectorStatus] = useState("");
  const [connectorError, setConnectorError] = useState<string | null>(null);
  const [connectorMembersLoading, setConnectorMembersLoading] = useState(false);
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
  const [slackConnection, setSlackConnection] =
    useState<SlackConnection | null>(null);
  const [slackSources, setSlackSources] = useState<WorkspaceSlackSource[]>([]);
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

  return {
    activeConnectorId,
    setActiveConnectorId,
    connectorRepoUrl,
    setConnectorRepoUrl,
    connectorRefreshRepo,
    setConnectorRefreshRepo,
    connectorMembers,
    setConnectorMembers,
    connectorMembersLoading,
    setConnectorMembersLoading,
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
    slackConnection,
    setSlackConnection,
    slackSources,
    setSlackSources,
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
    void loaders.loadLinearConnection();
    void loaders.loadLinearSources();
    void loaders.loadConfluenceConnection();
    void loaders.loadConfluenceSources();
  }, [
    loaders.loadBitbucketConnection,
    loaders.loadConfluenceConnection,
    loaders.loadConfluenceSources,
    loaders.loadGithubConnection,
    loaders.loadGitlabConnection,
    loaders.loadJiraConnection,
    loaders.loadJiraSources,
    loaders.loadLinearConnection,
    loaders.loadLinearSources,
    loaders.loadSlackConnection,
    loaders.loadSlackSources,
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
      slackConnected
        ? "Slack workspace connected. Choose channels to add to this Readbase workspace."
        : "",
    );
    state.setConnectorError(slackError ? slackOauthErrorMessage(slackError) : null);
    void loaders.loadSlackConnection();
    void loaders.loadSlackSources();
    url.searchParams.delete("connector");
    url.searchParams.delete("workspace_id");
    url.searchParams.delete("slack_connected");
    url.searchParams.delete("slack_error");
    window.history.replaceState({}, "", url.pathname + url.search);
  }, [loaders.loadSlackConnection, loaders.loadSlackSources, workspace.workspace_id]);
  useEffect(() => {
    if (state.activeConnectorId && state.activeConnectorId !== "slack") {
      void loaders.loadConnectorMembers();
    }
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
      void loaders.loadJiraSources();
      if (state.jiraConnection?.connected) {
        void loaders.loadJiraProjects(state.jiraProjectQuery);
      }
    }
    if (state.activeConnectorId === "slack") {
      void loaders.loadSlackConnection();
      void loaders.loadSlackSources();
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
  }, [
    state.activeConnectorId,
    state.bitbucketConnection?.connected,
    state.bitbucketRepositoryQuery,
    state.confluenceConnection?.connected,
    state.confluenceQuery,
    state.githubConnection?.connected,
    state.githubRepositoryQuery,
    state.gitlabConnection?.connected,
    state.gitlabProjectQuery,
    state.jiraConnection?.connected,
    state.jiraProjectQuery,
    state.linearConnection?.connected,
    state.linearQuery,
    loaders.loadBitbucketConnection,
    loaders.loadBitbucketRepositories,
    loaders.loadConfluenceConnection,
    loaders.loadConfluenceSources,
    loaders.loadConfluenceSpaces,
    loaders.loadConnectorMembers,
    loaders.loadGithubConnection,
    loaders.loadGithubRepositories,
    loaders.loadGitlabConnection,
    loaders.loadGitlabProjects,
    loaders.loadJiraConnection,
    loaders.loadJiraProjects,
    loaders.loadJiraSources,
    loaders.loadLinearConnection,
    loaders.loadLinearSelectableSources,
    loaders.loadLinearSources,
    loaders.loadSlackConnection,
    loaders.loadSlackSources,
    state.slackConnection?.connected,
  ]);
  useEffect(() => {
    if (state.activeConnectorId !== "slack" || !state.slackConnection?.connected) {
      return;
    }
    if (!state.slackChannelQuery.trim()) {
      state.setSlackChannels([]);
      return;
    }
    const searchTimeout = window.setTimeout(() => {
      void loaders.loadSlackChannels(state.slackChannelQuery);
    }, 250);
    return () => window.clearTimeout(searchTimeout);
  }, [
    state.activeConnectorId,
    loaders.loadSlackChannels,
    state.slackChannelQuery,
    state.slackConnection?.connected,
  ]);
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
