import type { FormEvent } from "react";

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
  JiraSite,
  LinearConnection,
  LinearSelectableSource,
  SlackChannel,
  SlackConnection,
  WorkspaceJiraSource,
  WorkspaceJiraSiteStatus,
  WorkspaceConfluenceSource,
  WorkspaceNotionSource,
  WorkspaceLinearSource,
  WorkspaceSlackSource,
  WorkspaceSlackTeam,
} from "../../../types";
import type { ConnectorConfig } from "./connectors";

export type ConnectorSetupModalProps = {
  connector: ConnectorConfig;
  repoUrl: string;
  refreshRepo: boolean;
  indexing: boolean;
  status: string;
  error: string | null;
  githubConnection: GithubConnection | null;
  githubRepositories: GithubRepository[];
  githubRepositoryQuery: string;
  githubRepositoriesLoading: boolean;
  bitbucketConnection: BitbucketConnection | null;
  bitbucketRepositories: BitbucketRepository[];
  bitbucketRepositoryQuery: string;
  bitbucketLoading: boolean;
  gitlabConnection: GitlabConnection | null;
  gitlabProjects: GitlabProject[];
  gitlabProjectQuery: string;
  gitlabLoading: boolean;
  jiraConnection: JiraConnection | null;
  jiraSources: WorkspaceJiraSource[];
  jiraProjects: JiraProject[];
  jiraProjectQuery: string;
  jiraLoading: boolean;
  jiraWorkspaceSite: WorkspaceJiraSiteStatus | null;
  slackConnection: SlackConnection | null;
  slackTeams: WorkspaceSlackTeam[];
  slackSources: WorkspaceSlackSource[];
  slackChannels: SlackChannel[];
  slackChannelQuery: string;
  slackLoading: boolean;
  linearConnection: LinearConnection | null;
  linearSources: WorkspaceLinearSource[];
  linearSelectableSources: LinearSelectableSource[];
  linearQuery: string;
  linearLoading: boolean;
  confluenceConnection: ConfluenceConnection | null;
  confluenceSources: WorkspaceConfluenceSource[];
  confluenceSpaces: ConfluenceSpace[];
  confluenceQuery: string;
  confluenceLoading: boolean;
  notionConnection: NotionConnection | null;
  notionSources: WorkspaceNotionSource[];
  notionDatabases: NotionDatabase[];
  notionQuery: string;
  notionLoading: boolean;
  onRepoUrlChange: (repoUrl: string) => void;
  onGithubRepositoryQueryChange: (query: string) => void;
  onGithubRepositorySearch: () => void;
  onBitbucketRepositoryQueryChange: (query: string) => void;
  onBitbucketRepositorySearch: () => void;
  onGitlabProjectQueryChange: (query: string) => void;
  onGitlabProjectSearch: () => void;
  onRefreshRepoChange: (refreshRepo: boolean) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onGithubConnect: () => void;
  onGithubDisconnect: () => void;
  onBitbucketConnect: () => void;
  onBitbucketDisconnect: () => void;
  onGitlabConnect: () => void;
  onGitlabDisconnect: () => void;
  onJiraConnect: () => void;
  onConnectJiraSite: (site: JiraSite) => void;
  onRemoveJiraSite: () => void;
  onJiraProjectQueryChange: (query: string) => void;
  onJiraProjectSearch: () => void;
  onAddJiraProject: (project: JiraProject) => void;
  onSyncJiraSource: (sourceId: string) => void;
  onRemoveJiraSource: (sourceId: string) => void;
  onSlackConnect: () => void;
  onSlackDisconnect: (teamId?: string) => void;
  onSlackUnlinkTeam: (teamId: string) => void;
  onSlackChannelQueryChange: (query: string) => void;
  onAddSlackChannel: (channel: SlackChannel) => void;
  onSyncSlackSource: (sourceId: string) => void;
  onRemoveSlackSource: (sourceId: string) => void;
  onLinearConnect: () => void;
  onLinearDisconnect: () => void;
  onLinearQueryChange: (query: string) => void;
  onLinearSearch: () => void;
  onAddLinearSource: (source: LinearSelectableSource) => void;
  onSyncLinearSource: (sourceId: string) => void;
  onRemoveLinearSource: (sourceId: string) => void;
  onConfluenceConnect: () => void;
  onConfluenceDisconnect: () => void;
  onConfluenceQueryChange: (query: string) => void;
  onConfluenceSearch: () => void;
  onAddConfluenceSpace: (space: ConfluenceSpace) => void;
  onSyncConfluenceSource: (sourceId: string) => void;
  onRemoveConfluenceSource: (sourceId: string) => void;
  onNotionConnect: () => void;
  onNotionDisconnect: () => void;
  onNotionQueryChange: (query: string) => void;
  onNotionSearch: () => void;
  onAddNotionDatabase: (database: NotionDatabase) => void;
  onSyncNotionSource: (sourceId: string) => void;
  onRemoveNotionSource: (sourceId: string) => void;
  onClose: () => void;
};
