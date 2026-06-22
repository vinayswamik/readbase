import { useRef, useState } from "react";

import { ConnectorDisconnectDialog } from "./ConnectorDisconnectDialog";
import { ConnectorLogo } from "./ConnectorLogo";
import { JiraConnectorBody } from "./JiraConnectorBody";
import { SlackConnectorBody } from "./SlackConnectorBody";
import { KnowledgeConnectorBody } from "./KnowledgeConnectorBody";
import { RepoChoiceRow } from "./RepoChoiceRow";
import type { ConnectorSetupModalProps } from "./ConnectorSetupModalTypes";

export function ConnectorSetupModal(props: ConnectorSetupModalProps) {
  const {
  connector,
  repoUrl,
  refreshRepo,
  indexing,
  status,
  error,
  githubConnection,
  githubRepositories,
  githubRepositoryQuery,
  githubRepositoriesLoading,
  bitbucketConnection,
  bitbucketRepositories,
  bitbucketRepositoryQuery,
  bitbucketLoading,
  gitlabConnection,
  gitlabProjects,
  gitlabProjectQuery,
  gitlabLoading,
  jiraConnection,
  jiraSources,
  jiraProjects,
  jiraProjectQuery,
  jiraLoading,
  slackConnection,
  slackTeams,
  slackSources,
  slackChannels,
  slackChannelQuery,
  slackLoading,
  linearConnection,
  linearSources,
  linearSelectableSources,
  linearQuery,
  linearLoading,
  confluenceConnection,
  confluenceSources,
  confluenceSpaces,
  confluenceQuery,
  confluenceLoading,
  notionConnection,
  notionSources,
  notionDatabases,
  notionQuery,
  notionLoading,
  onRepoUrlChange,
  onGithubRepositoryQueryChange,
  onGithubRepositorySearch,
  onBitbucketRepositoryQueryChange,
  onBitbucketRepositorySearch,
  onGitlabProjectQueryChange,
  onGitlabProjectSearch,
  onRefreshRepoChange,
  onSubmit,
  onGithubConnect,
  onGithubDisconnect,
  onBitbucketConnect,
  onBitbucketDisconnect,
  onGitlabConnect,
  onGitlabDisconnect,
  onJiraConnect,
  onJiraProjectQueryChange,
  onJiraProjectSearch,
  onAddJiraProject,
  onSyncJiraSource,
  onRemoveJiraSource,
    onSlackConnect,
    onSlackDisconnect,
    onSlackUnlinkTeam,
    onSlackChannelQueryChange,
  onAddSlackChannel,
  onSyncSlackSource,
  onRemoveSlackSource,
  onLinearConnect,
  onLinearDisconnect,
  onLinearQueryChange,
  onLinearSearch,
  onAddLinearSource,
  onSyncLinearSource,
  onRemoveLinearSource,
  onConfluenceConnect,
  onConfluenceDisconnect,
  onConfluenceQueryChange,
  onConfluenceSearch,
  onAddConfluenceSpace,
  onSyncConfluenceSource,
  onRemoveConfluenceSource,
  onNotionConnect,
  onNotionDisconnect,
  onNotionQueryChange,
  onNotionSearch,
  onAddNotionDatabase,
  onSyncNotionSource,
  onRemoveNotionSource,
  onClose,
} = props;
  const [disconnectOpen, setDisconnectOpen] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const pendingDisconnectRef = useRef<(() => void | Promise<void>) | null>(null);

  function requestDisconnect(action: () => void | Promise<void>) {
    pendingDisconnectRef.current = action;
    setDisconnectOpen(true);
  }

  async function confirmDisconnect() {
    const action = pendingDisconnectRef.current;
    if (!action) {
      setDisconnectOpen(false);
      return;
    }
    setDisconnecting(true);
    try {
      await action();
    } finally {
      setDisconnecting(false);
      setDisconnectOpen(false);
      pendingDisconnectRef.current = null;
    }
  }

  const isGithub = connector.id === "github";
  const isBitbucket = connector.id === "bitbucket";
  const isGitlab = connector.id === "gitlab";
  const isJira = connector.id === "jira";
  const isSlack = connector.id === "slack";
  const isLinear = connector.id === "linear";
  const isConfluence = connector.id === "confluence";
  const isNotion = connector.id === "notion";
  const isRepoConnector = isGithub || isBitbucket || isGitlab;
  const repoConnection = isGithub ? githubConnection : isBitbucket ? bitbucketConnection : gitlabConnection;
  const repoConnectedLabel = isGithub
    ? githubConnection?.login || "GitHub connected"
    : isBitbucket
      ? bitbucketConnection?.display_name || bitbucketConnection?.username || "Bitbucket connected"
      : gitlabConnection?.name || gitlabConnection?.username || "GitLab connected";
  const repoConfigured = repoConnection?.configured !== false;
  const isConnected =
    (isRepoConnector && Boolean(repoConnection?.connected)) ||
    (isJira && Boolean(jiraConnection?.connected)) ||
    (isSlack && Boolean(slackTeams.length)) ||
    (isJira && Boolean(jiraConnection?.connected)) ||
    (isLinear && Boolean(linearConnection?.connected)) ||
    (isConfluence && Boolean(confluenceConnection?.connected)) ||
    (isNotion && Boolean(notionConnection?.connected));

  const disconnectAction = isGithub
    ? onGithubDisconnect
    : isBitbucket
      ? onBitbucketDisconnect
      : isGitlab
        ? onGitlabDisconnect
        : isLinear
          ? onLinearDisconnect
          : isSlack
            ? () => onSlackDisconnect()
            : isConfluence
            ? onConfluenceDisconnect
            : isNotion
              ? onNotionDisconnect
              : null;

  return (
    <div
      className="connector-modal-backdrop connector-modal-backdrop-front"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="connector-modal" role="dialog" aria-modal="true" aria-labelledby="connector-modal-heading">
        <header className="connector-modal-header">
          <div className="connector-modal-header-left">
            {isConnected && disconnectAction && !isRepoConnector ? (
              <button
                type="button"
                className="connector-disconnect-button"
                disabled={linearLoading || confluenceLoading || notionLoading || disconnecting}
                onClick={() => requestDisconnect(disconnectAction)}
              >
                Disconnect
              </button>
            ) : null}
          </div>
          <div className="connector-modal-title">
            <ConnectorLogo connectorId={connector.id} />
            <div>
              <h2 id="connector-modal-heading">{connector.name}</h2>
            </div>
          </div>
          <button type="button" className="connector-close-button" aria-label={`Close ${connector.name}`} onClick={onClose}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
            </svg>
          </button>
        </header>

        {isRepoConnector ? (
          <form className="connector-modal-body" onSubmit={onSubmit}>
            <div className="connector-account-row">
              <div>
                <strong>{repoConnection?.connected ? repoConnectedLabel : `${connector.name} account`}</strong>
                <span>
                  {repoConnection?.connected
                    ? `Repository answers are filtered by this ${connector.name} account.`
                    : !repoConfigured
                      ? `${connector.name} OAuth is not configured on the backend.`
                    : `Connect ${connector.name} before indexing or answering from its repositories.`}
                </span>
              </div>
              {repoConnection?.connected ? (
                <span className="connector-account-status">Connected</span>
              ) : (
                <button
                  type="button"
                  className="primary-button"
                  disabled={indexing || !repoConfigured}
                  onClick={isGithub ? onGithubConnect : isBitbucket ? onBitbucketConnect : onGitlabConnect}
                >
                  Connect {connector.name}
                </button>
              )}
            </div>

            {repoConnection?.connected ? (
              <>
                <div className="connector-search-row">
                  <input
                    value={isGithub ? githubRepositoryQuery : isBitbucket ? bitbucketRepositoryQuery : gitlabProjectQuery}
                    placeholder={`Search ${connector.name} repositories`}
                    onChange={(event) =>
                      (isGithub ? onGithubRepositoryQueryChange : isBitbucket ? onBitbucketRepositoryQueryChange : onGitlabProjectQueryChange)(
                        event.target.value,
                      )
                    }
                  />
                  <button
                    type="button"
                    className="secondary-action-button"
                    disabled={githubRepositoriesLoading || bitbucketLoading || gitlabLoading}
                    onClick={isGithub ? onGithubRepositorySearch : isBitbucket ? onBitbucketRepositorySearch : onGitlabProjectSearch}
                  >
                    Search
                  </button>
                </div>

                <section className="connector-access-list">
                  <h3>Available repositories</h3>
                  {(githubRepositoriesLoading || bitbucketLoading || gitlabLoading) &&
                  !(isGithub ? githubRepositories.length : isBitbucket ? bitbucketRepositories.length : gitlabProjects.length) ? (
                    <div className="status-text compact">Loading {connector.name} repositories...</div>
                  ) : null}
                  {!githubRepositoriesLoading && !bitbucketLoading && !gitlabLoading &&
                  !(isGithub ? githubRepositories.length : isBitbucket ? bitbucketRepositories.length : gitlabProjects.length) ? (
                    <div className="status-text compact">No visible {connector.name} repositories found.</div>
                  ) : null}
                  {isGithub
                    ? githubRepositories.slice(0, 8).map((repository) => (
                        <RepoChoiceRow key={repository.id || repository.full_name} label={repository.full_name} isPrivate={repository.private} url={repository.html_url} disabled={indexing} onSelect={onRepoUrlChange} />
                      ))
                    : isBitbucket
                      ? bitbucketRepositories.slice(0, 8).map((repository) => (
                          <RepoChoiceRow key={repository.id || repository.full_name} label={repository.full_name} isPrivate={repository.private} url={repository.clone_url || repository.html_url} disabled={indexing} onSelect={onRepoUrlChange} />
                        ))
                      : gitlabProjects.slice(0, 8).map((project) => (
                          <RepoChoiceRow key={project.id || project.path_with_namespace} label={project.path_with_namespace} isPrivate={project.visibility !== "public"} url={project.clone_url || project.web_url} disabled={indexing} onSelect={onRepoUrlChange} />
                        ))}
                </section>
              </>
            ) : null}

            <label htmlFor="connectorRepoUrl">Git repo to index</label>
            <input
              id="connectorRepoUrl"
              type="url"
              value={repoUrl}
              placeholder={isBitbucket ? "https://bitbucket.org/workspace/repo" : isGitlab ? "https://gitlab.com/group/project" : "https://github.com/owner/repo"}
              required
              onChange={(event) => onRepoUrlChange(event.target.value)}
            />
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={refreshRepo}
                onChange={(event) => onRefreshRepoChange(event.target.checked)}
              />
              <span>Re-clone existing index</span>
            </label>

            <div className="connector-modal-actions connector-modal-actions-with-disconnect">
              {repoConnection?.connected ? (
                <button
                  type="button"
                  className="connector-disconnect-button"
                  disabled={indexing || disconnecting}
                  onClick={() =>
                    requestDisconnect(isGithub ? onGithubDisconnect : isBitbucket ? onBitbucketDisconnect : onGitlabDisconnect)
                  }
                >
                  Disconnect
                </button>
              ) : (
                <span />
              )}
              <div className="connector-modal-actions-primary">
                <button type="button" className="modal-cancel-button" onClick={onClose}>
                  Cancel
                </button>
                <button type="submit" className="primary-button" disabled={indexing || !repoUrl.trim() || !repoConnection?.connected}>
                  {indexing ? "Indexing..." : "Index repo"}
                </button>
              </div>
            </div>
          </form>
        ) : isJira ? (
          <JiraConnectorBody {...props} />
        ) : isSlack ? (
          <SlackConnectorBody {...props} />
        ) : isLinear ? (
          <KnowledgeConnectorBody
            connectorName="Linear"
            connected={Boolean(linearConnection?.connected)}
            configured={linearConnection?.configured !== false}
            accountTitle={linearConnection?.name || "Linear connected"}
            accountDetail={linearConnection?.email || linearConnection?.workspace_name || "Issues are filtered by this Linear account."}
            disconnectedDetail="Connect Linear before adding teams or projects."
            query={linearQuery}
            queryPlaceholder="Search Linear teams or projects"
            loading={linearLoading}
            availableTitle="Available teams and projects"
            emptyAvailableText="No visible Linear teams or projects found."
            workspaceTitle="Workspace Linear sources"
            emptyWorkspaceText="No Linear sources connected to this workspace."
            error={error}
            status={status}
            onConnect={onLinearConnect}
            onDisconnect={() => requestDisconnect(onLinearDisconnect)}
            onQueryChange={onLinearQueryChange}
            onSearch={onLinearSearch}
            onClose={onClose}
            availableRows={linearSelectableSources.slice(0, 8).map((source) => {
              const alreadyAdded = linearSources.some(
                (current) =>
                  current.linear_team_id === source.team_id &&
                  (current.linear_project_id || "") === (source.project_id || ""),
              );
              return (
                <div className="connector-access-row" key={`${source.team_id}:${source.project_id || "team"}`}>
                  <span>{source.project_name || source.team_name}</span>
                  <strong>{source.project_id ? "Project" : "Team"}</strong>
                  <button type="button" className="secondary-action-button compact-button" disabled={linearLoading || alreadyAdded} onClick={() => onAddLinearSource(source)}>
                    {alreadyAdded ? "Added" : "Add"}
                  </button>
                </div>
              );
            })}
            workspaceRows={linearSources.map((source) => (
              <div className="connector-access-row" key={source.source_id}>
                <span>{source.project_name || source.team_name}</span>
                <strong>{source.sync_status}</strong>
                <button type="button" className="secondary-action-button compact-button" disabled={linearLoading} onClick={() => onSyncLinearSource(source.source_id)}>
                  Sync
                </button>
                <button type="button" className="danger-button compact-button" disabled={linearLoading} onClick={() => onRemoveLinearSource(source.source_id)}>
                  Remove
                </button>
              </div>
            ))}
          />
        ) : isConfluence ? (
          <KnowledgeConnectorBody
            connectorName="Confluence"
            connected={Boolean(confluenceConnection?.connected)}
            configured={confluenceConnection?.configured !== false}
            accountTitle={confluenceConnection?.account_name || "Confluence connected"}
            accountDetail={confluenceConnection?.account_email || `${confluenceConnection?.sites.length || 0} site${confluenceConnection?.sites.length === 1 ? "" : "s"} connected`}
            disconnectedDetail="Connect Confluence before adding spaces."
            query={confluenceQuery}
            queryPlaceholder="Search Confluence spaces"
            loading={confluenceLoading}
            availableTitle="Available spaces"
            emptyAvailableText="No visible Confluence spaces found."
            workspaceTitle="Workspace Confluence sources"
            emptyWorkspaceText="No Confluence spaces connected to this workspace."
            error={error}
            status={status}
            onConnect={onConfluenceConnect}
            onDisconnect={() => requestDisconnect(onConfluenceDisconnect)}
            onQueryChange={onConfluenceQueryChange}
            onSearch={onConfluenceSearch}
            onClose={onClose}
            availableRows={confluenceSpaces.slice(0, 8).map((space) => {
              const alreadyAdded = confluenceSources.some(
                (source) => source.cloud_id === space.cloud_id && source.space_id === space.space_id,
              );
              return (
                <div className="connector-access-row" key={`${space.cloud_id}:${space.space_id}`}>
                  <span>{space.space_key} · {space.space_name}</span>
                  <strong>{space.site_name}</strong>
                  <button type="button" className="secondary-action-button compact-button" disabled={confluenceLoading || alreadyAdded} onClick={() => onAddConfluenceSpace(space)}>
                    {alreadyAdded ? "Added" : "Add"}
                  </button>
                </div>
              );
            })}
            workspaceRows={confluenceSources.map((source) => (
              <div className="connector-access-row" key={source.source_id}>
                <span>{source.space_key} · {source.space_name}</span>
                <strong>{source.sync_status}</strong>
                <button type="button" className="secondary-action-button compact-button" disabled={confluenceLoading} onClick={() => onSyncConfluenceSource(source.source_id)}>
                  Sync
                </button>
                <button type="button" className="danger-button compact-button" disabled={confluenceLoading} onClick={() => onRemoveConfluenceSource(source.source_id)}>
                  Remove
                </button>
              </div>
            ))}
          />
        ) : isNotion ? (
          <KnowledgeConnectorBody
            connectorName="Notion"
            connected={Boolean(notionConnection?.connected)}
            configured={notionConnection?.configured !== false}
            accountTitle={notionConnection?.workspace_name || "Notion connected"}
            accountDetail={notionConnection?.owner_name || notionConnection?.workspace_id || "Workspace connected"}
            disconnectedDetail="Connect Notion before adding databases."
            query={notionQuery}
            queryPlaceholder="Search Notion databases"
            loading={notionLoading}
            availableTitle="Available databases"
            emptyAvailableText="No visible Notion databases found."
            workspaceTitle="Workspace Notion sources"
            emptyWorkspaceText="No Notion databases connected to this workspace."
            error={error}
            status={status}
            onConnect={onNotionConnect}
            onDisconnect={() => requestDisconnect(onNotionDisconnect)}
            onQueryChange={onNotionQueryChange}
            onSearch={onNotionSearch}
            onClose={onClose}
            availableRows={notionDatabases.slice(0, 8).map((database) => {
              const alreadyAdded = notionSources.some(
                (source) => source.database_id === database.database_id,
              );
              return (
                <div className="connector-access-row" key={database.database_id}>
                  <span>{database.database_title}</span>
                  <strong>{database.workspace_name}</strong>
                  <button type="button" className="secondary-action-button compact-button" disabled={notionLoading || alreadyAdded} onClick={() => onAddNotionDatabase(database)}>
                    {alreadyAdded ? "Added" : "Add"}
                  </button>
                </div>
              );
            })}
            workspaceRows={notionSources.map((source) => (
              <div className="connector-access-row" key={source.source_id}>
                <span>{source.database_title}</span>
                <strong>{source.sync_status}</strong>
                <button type="button" className="secondary-action-button compact-button" disabled={notionLoading} onClick={() => onSyncNotionSource(source.source_id)}>
                  Sync
                </button>
                <button type="button" className="danger-button compact-button" disabled={notionLoading} onClick={() => onRemoveNotionSource(source.source_id)}>
                  Remove
                </button>
              </div>
            ))}
          />
        ) : (
          <div className="connector-modal-body">
            <div className="empty-panel-state">
              {connector.name} setup fields will be added here.
            </div>
            <div className="connector-modal-actions">
              <button type="button" className="primary-button" onClick={onClose}>
                Done
              </button>
            </div>
          </div>
        )}
      </div>
      <ConnectorDisconnectDialog
        connectorName={connector.name}
        open={disconnectOpen}
        loading={disconnecting}
        onCancel={() => {
          if (!disconnecting) {
            setDisconnectOpen(false);
            pendingDisconnectRef.current = null;
          }
        }}
        onConfirm={() => void confirmDisconnect()}
      />
    </div>
  );
}
