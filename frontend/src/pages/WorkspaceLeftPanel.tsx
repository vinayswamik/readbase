import { memo, useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import type {
  AuthUser,
  BitbucketConnection,
  BitbucketRepository,
  ConfluenceConnection,
  ConfluenceSpace,
  GitlabConnection,
  GitlabProject,
  GithubConnection,
  GithubRepository,
  HierarchyAssignableUser,
  HierarchyNode,
  IndexedRepo,
  JiraConnection,
  JiraProject,
  LinearConnection,
  LinearSelectableSource,
  SlackChannel,
  SlackConnection,
  Workspace,
  WorkspaceJiraSource,
  WorkspaceConfluenceSource,
  WorkspaceLinearSource,
  WorkspaceSlackSource,
  WorkspaceMember,
} from "../types";

const MAX_PICKER_RESULTS = 20;

export type SidebarTab = "repository" | "graph" | "details";
export type ConnectorId = "jira" | "slack" | "github" | "bitbucket" | "gitlab" | "confluence" | "linear";
export type ConnectorCategoryId = "codebase" | "project-management" | "discussions";

export type CreateNodeDraft = {
  displayName: string;
  assignedUserId: string;
  parentNodeId: string;
};

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
];

const CONNECTOR_CATEGORY_ORDER: Array<{ id: ConnectorCategoryId; label: string }> = [
  { id: "codebase", label: "Codebase" },
  { id: "project-management", label: "Project management" },
  { id: "discussions", label: "Discussions" },
];

export function WorkspaceLeftPanel({
  workspace,
  mode,
  sidebarTab,
  userRole,
  repos,
  selectedRepoId,
  repoListError,
  graphMutating,
  graphStatus,
  availableAssignees,
  parentOptions,
  ownNode,
  selectedNode,
  canManageSelectedNode,
  editTitle,
  editAssignedUserId,
  reassignOptions,
  canDeleteSelectedNode,
  reparentNodeId,
  reparentOptions,
  onBack,
  onSidebarTabChange,
  onRepoSelect,
  onCreateNode,
  onUpdateSelectedNode,
  onDeleteSelectedNode,
  onEditTitleChange,
  onEditAssignedUserIdChange,
  onReparentNodeIdChange,
  onReparentSelectedNode,
  onOpenConnector,
}: {
  workspace: Workspace;
  mode: string;
  sidebarTab: SidebarTab;
  userRole: AuthUser["role"];
  repos: IndexedRepo[];
  selectedRepoId: string | null;
  repoListError: string | null;
  graphMutating: boolean;
  graphStatus: string;
  availableAssignees: HierarchyAssignableUser[];
  parentOptions: HierarchyNode[];
  ownNode: HierarchyNode | null;
  selectedNode: HierarchyNode | null;
  canManageSelectedNode: boolean;
  editTitle: string;
  editAssignedUserId: string;
  reassignOptions: HierarchyAssignableUser[];
  canDeleteSelectedNode: boolean;
  reparentNodeId: string;
  reparentOptions: HierarchyNode[];
  onBack: () => void;
  onSidebarTabChange: (tab: SidebarTab) => void;
  onRepoSelect: (repo: IndexedRepo) => void;
  onCreateNode: (draft: CreateNodeDraft) => Promise<boolean>;
  onUpdateSelectedNode: (event: FormEvent<HTMLFormElement>) => void;
  onDeleteSelectedNode: () => void;
  onEditTitleChange: (title: string) => void;
  onEditAssignedUserIdChange: (assignedUserId: string) => void;
  onReparentNodeIdChange: (nodeId: string) => void;
  onReparentSelectedNode: (event: FormEvent<HTMLFormElement>) => void;
  onOpenConnector: (connectorId: ConnectorId) => void;
}) {
  return (
    <aside className="graph-sidebar" aria-label="Workspace controls">
      <div className="sidebar-topline">
        <button type="button" className="back-button" onClick={onBack}>
          Back
        </button>
        <span className="status-chip">{mode}</span>
      </div>
      <header className="brand sidebar-brand">
        <div>
          <h1>{workspace.name}</h1>
          <p>Hierarchy graph</p>
        </div>
      </header>

      <ConnectorPanel
        connectors={CONNECTORS}
        onOpen={onOpenConnector}
      />

      <div className="control-tabs" role="tablist" aria-label="Workspace control sections">
        <button
          type="button"
          role="tab"
          aria-selected={sidebarTab === "graph"}
          className={sidebarTab === "graph" ? "active" : ""}
          onClick={() => onSidebarTabChange("graph")}
        >
          Graph
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={sidebarTab === "details"}
          className={sidebarTab === "details" ? "active" : ""}
          onClick={() => onSidebarTabChange("details")}
        >
          Details
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={sidebarTab === "repository"}
          className={sidebarTab === "repository" ? "active" : ""}
          onClick={() => onSidebarTabChange("repository")}
        >
          Repos
        </button>
      </div>

      {sidebarTab === "repository" ? (
        <div className="tab-panel" role="tabpanel">
          <section className="tool-section" aria-labelledby="indexed-repos-heading">
            <div className="tool-section-header">
              <div>
                <h2 id="indexed-repos-heading">Indexed Repos</h2>
                <p>Select context for the ask widget.</p>
              </div>
            </div>
            <RepoList
              repos={repos}
              selectedRepoId={selectedRepoId}
              error={repoListError}
              onSelect={onRepoSelect}
            />
          </section>
        </div>
      ) : null}

      {sidebarTab === "graph" ? (
        <div className="tab-panel" role="tabpanel">
          <section className="tool-section" aria-labelledby="graph-create-heading">
            <div className="tool-section-header">
              <div>
                <h2 id="graph-create-heading">Create Node</h2>
                <p>Add hierarchy entries to the board.</p>
              </div>
            </div>
            <CreateNodeForm
              userRole={userRole}
              disabled={graphMutating}
              availableAssignees={availableAssignees}
              parentOptions={parentOptions}
              ownNode={ownNode}
              onCreate={onCreateNode}
            />
            {graphStatus ? <div className="status-text">{graphStatus}</div> : null}
          </section>
        </div>
      ) : null}

      {sidebarTab === "details" ? (
        <div className="tab-panel" role="tabpanel">
          <section className="tool-section" aria-labelledby="node-actions-heading">
            <div className="tool-section-header">
              <div>
                <h2 id="node-actions-heading">Selected Node</h2>
                <p>Inspect and manage the active node.</p>
              </div>
            </div>
            {selectedNode ? (
              <form className="graph-control-form" onSubmit={onUpdateSelectedNode}>
                <div className="selected-node-meta">
                  <span>{selectedNode.assigned_user_email || "Assigned user"}</span>
                  <strong>{selectedNode.display_name}</strong>
                </div>
                <div className="status-text compact">
                  Assigned to {selectedNode.assigned_user_name || selectedNode.assigned_user_email || "workspace user"}.
                </div>
                <label htmlFor="editNodeTitle">Rename</label>
                <input
                  id="editNodeTitle"
                  value={editTitle}
                  disabled={graphMutating || !canManageSelectedNode}
                  onChange={(event) => onEditTitleChange(event.target.value)}
                />
                <label id="editAssignedUserLabel">Assigned user</label>
                <AssignableUserPicker
                  value={editAssignedUserId}
                  disabled={graphMutating || !canManageSelectedNode}
                  availableAssignees={reassignOptions}
                  labelId="editAssignedUserLabel"
                  emptyLabel="No assignee selected"
                  searchPlaceholder="Search assignable users"
                  onChange={onEditAssignedUserIdChange}
                />
                <button
                  type="submit"
                  className="secondary-action-button"
                  disabled={
                    graphMutating ||
                    !canManageSelectedNode ||
                    !editTitle.trim() ||
                    !editAssignedUserId
                  }
                >
                  Save node
                </button>
                <button
                  type="button"
                  className="danger-button"
                  disabled={graphMutating || !canDeleteSelectedNode}
                  onClick={onDeleteSelectedNode}
                >
                  Delete node
                </button>
              </form>
            ) : (
              <div className="empty-panel-state">Select a node on the board to view details.</div>
            )}
          </section>
          {selectedNode && userRole === "admin" ? (
            <section className="tool-section" aria-labelledby="node-parent-heading">
              <div className="tool-section-header">
                <div>
                  <h2 id="node-parent-heading">Parent</h2>
                  <p>Move this node under another node or make it top-level.</p>
                </div>
              </div>
              <form className="graph-control-form" onSubmit={onReparentSelectedNode}>
                <label id="reparentNodeLabel">Parent node</label>
                <ParentNodeSelect
                  value={reparentNodeId}
                  disabled={graphMutating}
                  userRole={userRole}
                  parentOptions={reparentOptions}
                  labelId="reparentNodeLabel"
                  onChange={onReparentNodeIdChange}
                />
                <button type="submit" className="secondary-action-button" disabled={graphMutating}>
                  Update parent
                </button>
              </form>
            </section>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}

export function ConnectorSetupModal({
  connector,
  repoUrl,
  refreshRepo,
  members,
  loadingMembers,
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
  slackSources,
  slackChannels,
  slackChannelQuery,
  slackSelectedTeamId,
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
  canManageWorkspace,
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
  onJiraDisconnect,
  onJiraProjectQueryChange,
  onJiraProjectSearch,
  onAddJiraProject,
  onSyncJiraSource,
  onRemoveJiraSource,
  onSlackConnect,
  onSlackDisconnect,
  onSlackTeamChange,
  onSlackChannelQueryChange,
  onSlackChannelSearch,
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
  onConnectorManagerToggle,
  onClose,
}: {
  connector: ConnectorConfig;
  repoUrl: string;
  refreshRepo: boolean;
  members: WorkspaceMember[];
  loadingMembers: boolean;
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
  slackConnection: SlackConnection | null;
  slackSources: WorkspaceSlackSource[];
  slackChannels: SlackChannel[];
  slackChannelQuery: string;
  slackSelectedTeamId: string;
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
  canManageWorkspace: boolean;
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
  onJiraDisconnect: () => void;
  onJiraProjectQueryChange: (query: string) => void;
  onJiraProjectSearch: () => void;
  onAddJiraProject: (project: JiraProject) => void;
  onSyncJiraSource: (sourceId: string) => void;
  onRemoveJiraSource: (sourceId: string) => void;
  onSlackConnect: () => void;
  onSlackDisconnect: (teamId?: string) => void;
  onSlackTeamChange: (teamId: string) => void;
  onSlackChannelQueryChange: (query: string) => void;
  onSlackChannelSearch: () => void;
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
  onConnectorManagerToggle: (member: WorkspaceMember) => void;
  onClose: () => void;
}) {
  const isGithub = connector.id === "github";
  const isBitbucket = connector.id === "bitbucket";
  const isGitlab = connector.id === "gitlab";
  const isJira = connector.id === "jira";
  const isSlack = connector.id === "slack";
  const isLinear = connector.id === "linear";
  const isConfluence = connector.id === "confluence";
  const isRepoConnector = isGithub || isBitbucket || isGitlab;
  const repoConnection = isGithub ? githubConnection : isBitbucket ? bitbucketConnection : gitlabConnection;
  const repoConnectedLabel = isGithub
    ? githubConnection?.login || "GitHub connected"
    : isBitbucket
      ? bitbucketConnection?.display_name || bitbucketConnection?.username || "Bitbucket connected"
      : gitlabConnection?.name || gitlabConnection?.username || "GitLab connected";
  const repoConfigured = repoConnection?.configured !== false;

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
      <div className="connector-modal" role="dialog" aria-modal="true" aria-labelledby="connector-modal-heading">
        <header className="connector-modal-header">
          <div className="connector-modal-title">
            <ConnectorLogo connectorId={connector.id} />
            <div>
              <h2 id="connector-modal-heading">{connector.name}</h2>
              <p>Connector setup</p>
            </div>
          </div>
          <button type="button" className="connector-close-button" aria-label="Close connector setup" onClick={onClose}>
            x
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
                <button
                  type="button"
                  className="secondary-action-button"
                  disabled={indexing || bitbucketLoading || gitlabLoading}
                  onClick={isGithub ? onGithubDisconnect : isBitbucket ? onBitbucketDisconnect : onGitlabDisconnect}
                >
                  Disconnect
                </button>
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

            <section className="connector-access-list">
              <h3>Connector managers</h3>
              {loadingMembers ? <div className="status-text compact">Loading workspace users...</div> : null}
              {members.map((member) => (
                <label className="connector-access-row" key={member.email}>
                  <input
                    type="checkbox"
                    checked={member.connector_manager}
                    disabled={!canManageWorkspace || member.is_owner}
                    onChange={() => onConnectorManagerToggle(member)}
                  />
                  <span>{member.email}</span>
                  <strong>{member.is_owner ? "Owner" : member.connector_manager ? "Manager" : "Member"}</strong>
                </label>
              ))}
            </section>

            {error ? <div className="status-text error-text">{error}</div> : null}
            {status ? <div className="status-text">{status}</div> : null}
            <div className="connector-modal-actions">
              <button type="button" className="secondary-action-button" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="primary-button" disabled={indexing || !repoUrl.trim() || !repoConnection?.connected}>
                {indexing ? "Indexing..." : "Index repo"}
              </button>
            </div>
          </form>
        ) : isJira ? (
          <div className="connector-modal-body">
            <div className="connector-account-row">
              <div>
                <strong>{jiraConnection?.connected ? jiraConnection.account_name || "Jira connected" : "Jira account"}</strong>
                <span>
                  {jiraConnection?.connected
                    ? jiraConnection.account_email || `${jiraConnection.sites.length} site${jiraConnection.sites.length === 1 ? "" : "s"} connected`
                    : "Connect your Atlassian account before adding workspace projects."}
                </span>
              </div>
              {jiraConnection?.connected ? (
                <button type="button" className="secondary-action-button" disabled={jiraLoading} onClick={onJiraDisconnect}>
                  Disconnect
                </button>
              ) : (
                <button type="button" className="primary-button" disabled={jiraLoading} onClick={onJiraConnect}>
                  Connect Jira
                </button>
              )}
            </div>

            {jiraConnection?.connected ? (
              <>
                <div className="connector-search-row">
                  <input
                    value={jiraProjectQuery}
                    placeholder="Search Jira projects"
                    onChange={(event) => onJiraProjectQueryChange(event.target.value)}
                  />
                  <button type="button" className="secondary-action-button" disabled={jiraLoading} onClick={onJiraProjectSearch}>
                    Search
                  </button>
                </div>

                <section className="connector-access-list">
                  <h3>Available projects</h3>
                  {jiraLoading && !jiraProjects.length ? <div className="status-text compact">Loading Jira projects...</div> : null}
                  {!jiraLoading && !jiraProjects.length ? <div className="status-text compact">No visible Jira projects found.</div> : null}
                  {jiraProjects.slice(0, 8).map((project) => {
                    const alreadyAdded = jiraSources.some(
                      (source) => source.cloud_id === project.cloud_id && source.project_id === project.project_id,
                    );
                    return (
                      <div className="connector-access-row" key={`${project.cloud_id}:${project.project_id}`}>
                        <span>{project.project_key} · {project.project_name}</span>
                        <strong>{project.site_name}</strong>
                        <button
                          type="button"
                          className="secondary-action-button compact-button"
                          disabled={jiraLoading || alreadyAdded}
                          onClick={() => onAddJiraProject(project)}
                        >
                          {alreadyAdded ? "Added" : "Add"}
                        </button>
                      </div>
                    );
                  })}
                </section>

                <section className="connector-access-list">
                  <h3>Connector managers</h3>
                  {loadingMembers ? <div className="status-text compact">Loading workspace users...</div> : null}
                  {members.map((member) => (
                    <label className="connector-access-row" key={member.email}>
                      <input
                        type="checkbox"
                        checked={member.connector_manager}
                        disabled={!canManageWorkspace || member.is_owner}
                        onChange={() => onConnectorManagerToggle(member)}
                      />
                      <span>{member.email}</span>
                      <strong>{member.is_owner ? "Owner" : member.connector_manager ? "Manager" : "Member"}</strong>
                    </label>
                  ))}
                </section>

                <section className="connector-access-list">
                  <h3>Workspace Jira sources</h3>
                  {!jiraSources.length ? <div className="status-text compact">No Jira projects connected to this workspace.</div> : null}
                  {jiraSources.map((source) => (
                    <div className="connector-access-row" key={source.source_id}>
                      <span>{source.project_key} · {source.project_name}</span>
                      <strong>{source.sync_status}</strong>
                      <button
                        type="button"
                        className="secondary-action-button compact-button"
                        disabled={jiraLoading}
                        onClick={() => onSyncJiraSource(source.source_id)}
                      >
                        Sync
                      </button>
                      <button
                        type="button"
                        className="danger-button compact-button"
                        disabled={jiraLoading}
                        onClick={() => onRemoveJiraSource(source.source_id)}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </section>
              </>
            ) : null}

            {error ? <div className="status-text error-text">{error}</div> : null}
            {status ? <div className="status-text">{status}</div> : null}
            <div className="connector-modal-actions">
              <button type="button" className="primary-button" onClick={onClose}>
                Done
              </button>
            </div>
          </div>
        ) : isSlack ? (
          <div className="connector-modal-body">
            <div className="connector-account-row">
              <div>
                <strong>{slackConnection?.connected ? "Slack connected" : "Slack account"}</strong>
                <span>
                  {slackConnection?.connected
                    ? `${slackConnection.teams.length} workspace${slackConnection.teams.length === 1 ? "" : "s"} connected`
                    : slackConnection?.configured === false
                      ? "Slack OAuth is not configured on the backend."
                    : "Connect Slack before adding workspace channels."}
                </span>
              </div>
              <button
                type="button"
                className={slackConnection?.connected ? "secondary-action-button" : "primary-button"}
                disabled={slackLoading || slackConnection?.configured === false}
                onClick={slackConnection?.connected ? () => onSlackDisconnect(slackSelectedTeamId || undefined) : onSlackConnect}
              >
                {slackConnection?.connected ? "Disconnect" : "Connect Slack"}
              </button>
            </div>

            {slackConnection?.connected ? (
              <>
                <div className="connector-search-row">
                  <select
                    value={slackSelectedTeamId}
                    onChange={(event) => onSlackTeamChange(event.target.value)}
                  >
                    {slackConnection.teams.map((team) => (
                      <option key={team.team_id} value={team.team_id}>
                        {team.team_name}
                      </option>
                    ))}
                  </select>
                  <input
                    value={slackChannelQuery}
                    placeholder="Search Slack channels"
                    onChange={(event) => onSlackChannelQueryChange(event.target.value)}
                  />
                  <button type="button" className="secondary-action-button" disabled={slackLoading} onClick={onSlackChannelSearch}>
                    Search
                  </button>
                </div>

                <section className="connector-access-list">
                  <h3>Available channels</h3>
                  {slackLoading && !slackChannels.length ? <div className="status-text compact">Loading Slack channels...</div> : null}
                  {!slackLoading && !slackChannels.length ? <div className="status-text compact">No visible Slack channels found.</div> : null}
                  {slackChannels.slice(0, 8).map((channel) => {
                    const alreadyAdded = slackSources.some(
                      (source) => source.team_id === channel.team_id && source.channel_id === channel.channel_id,
                    );
                    return (
                      <div className="connector-access-row" key={`${channel.team_id}:${channel.channel_id}`}>
                        <span>#{channel.channel_name}</span>
                        <strong>{channel.is_private ? "Private" : "Public"}</strong>
                        <button
                          type="button"
                          className="secondary-action-button compact-button"
                          disabled={slackLoading || alreadyAdded}
                          onClick={() => onAddSlackChannel(channel)}
                        >
                          {alreadyAdded ? "Added" : "Add"}
                        </button>
                      </div>
                    );
                  })}
                </section>

                <section className="connector-access-list">
                  <h3>Connector managers</h3>
                  {loadingMembers ? <div className="status-text compact">Loading workspace users...</div> : null}
                  {members.map((member) => (
                    <label className="connector-access-row" key={member.email}>
                      <input
                        type="checkbox"
                        checked={member.connector_manager}
                        disabled={!canManageWorkspace || member.is_owner}
                        onChange={() => onConnectorManagerToggle(member)}
                      />
                      <span>{member.email}</span>
                      <strong>{member.is_owner ? "Owner" : member.connector_manager ? "Manager" : "Member"}</strong>
                    </label>
                  ))}
                </section>

                <section className="connector-access-list">
                  <h3>Workspace Slack sources</h3>
                  {!slackSources.length ? <div className="status-text compact">No Slack channels connected to this workspace.</div> : null}
                  {slackSources.map((source) => (
                    <div className="connector-access-row" key={source.source_id}>
                      <span>#{source.channel_name}</span>
                      <strong>{source.sync_status}</strong>
                      <button
                        type="button"
                        className="secondary-action-button compact-button"
                        disabled={slackLoading}
                        onClick={() => onSyncSlackSource(source.source_id)}
                      >
                        Sync
                      </button>
                      <button
                        type="button"
                        className="danger-button compact-button"
                        disabled={slackLoading}
                        onClick={() => onRemoveSlackSource(source.source_id)}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </section>
              </>
            ) : null}

            {error ? <div className="status-text error-text">{error}</div> : null}
            {status ? <div className="status-text">{status}</div> : null}
            <div className="connector-modal-actions">
              <button type="button" className="primary-button" onClick={onClose}>
                Done
              </button>
            </div>
          </div>
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
            members={members}
            loadingMembers={loadingMembers}
            canManageWorkspace={canManageWorkspace}
            error={error}
            status={status}
            onConnect={onLinearConnect}
            onDisconnect={onLinearDisconnect}
            onQueryChange={onLinearQueryChange}
            onSearch={onLinearSearch}
            onConnectorManagerToggle={onConnectorManagerToggle}
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
            members={members}
            loadingMembers={loadingMembers}
            canManageWorkspace={canManageWorkspace}
            error={error}
            status={status}
            onConnect={onConfluenceConnect}
            onDisconnect={onConfluenceDisconnect}
            onQueryChange={onConfluenceQueryChange}
            onSearch={onConfluenceSearch}
            onConnectorManagerToggle={onConnectorManagerToggle}
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
    </div>
  );
}

function KnowledgeConnectorBody({
  connectorName,
  connected,
  configured,
  accountTitle,
  accountDetail,
  disconnectedDetail,
  query,
  queryPlaceholder,
  loading,
  availableTitle,
  emptyAvailableText,
  workspaceTitle,
  emptyWorkspaceText,
  members,
  loadingMembers,
  canManageWorkspace,
  error,
  status,
  availableRows,
  workspaceRows,
  onConnect,
  onDisconnect,
  onQueryChange,
  onSearch,
  onConnectorManagerToggle,
  onClose,
}: {
  connectorName: string;
  connected: boolean;
  configured: boolean;
  accountTitle: string;
  accountDetail: string;
  disconnectedDetail: string;
  query: string;
  queryPlaceholder: string;
  loading: boolean;
  availableTitle: string;
  emptyAvailableText: string;
  workspaceTitle: string;
  emptyWorkspaceText: string;
  members: WorkspaceMember[];
  loadingMembers: boolean;
  canManageWorkspace: boolean;
  error: string | null;
  status: string;
  availableRows: ReactNode[];
  workspaceRows: ReactNode[];
  onConnect: () => void;
  onDisconnect: () => void;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
  onConnectorManagerToggle: (member: WorkspaceMember) => void;
  onClose: () => void;
}) {
  return (
    <div className="connector-modal-body">
      <div className="connector-account-row">
        <div>
          <strong>{connected ? accountTitle : `${connectorName} account`}</strong>
          <span>{connected ? accountDetail : configured ? disconnectedDetail : `${connectorName} OAuth is not configured on the backend.`}</span>
        </div>
        <button
          type="button"
          className={connected ? "secondary-action-button" : "primary-button"}
          disabled={loading || !configured}
          onClick={connected ? onDisconnect : onConnect}
        >
          {connected ? "Disconnect" : `Connect ${connectorName}`}
        </button>
      </div>

      {connected ? (
        <>
          <div className="connector-search-row">
            <input value={query} placeholder={queryPlaceholder} onChange={(event) => onQueryChange(event.target.value)} />
            <button type="button" className="secondary-action-button" disabled={loading} onClick={onSearch}>
              Search
            </button>
          </div>
          <section className="connector-access-list">
            <h3>{availableTitle}</h3>
            {loading && !availableRows.length ? <div className="status-text compact">Loading...</div> : null}
            {!loading && !availableRows.length ? <div className="status-text compact">{emptyAvailableText}</div> : null}
            {availableRows}
          </section>
          <section className="connector-access-list">
            <h3>Connector managers</h3>
            {loadingMembers ? <div className="status-text compact">Loading workspace users...</div> : null}
            {members.map((member) => (
              <label className="connector-access-row" key={member.email}>
                <input
                  type="checkbox"
                  checked={member.connector_manager}
                  disabled={!canManageWorkspace || member.is_owner}
                  onChange={() => onConnectorManagerToggle(member)}
                />
                <span>{member.email}</span>
                <strong>{member.is_owner ? "Owner" : member.connector_manager ? "Manager" : "Member"}</strong>
              </label>
            ))}
          </section>
          <section className="connector-access-list">
            <h3>{workspaceTitle}</h3>
            {!workspaceRows.length ? <div className="status-text compact">{emptyWorkspaceText}</div> : null}
            {workspaceRows}
          </section>
        </>
      ) : null}

      {error ? <div className="status-text error-text">{error}</div> : null}
      {status ? <div className="status-text">{status}</div> : null}
      <div className="connector-modal-actions">
        <button type="button" className="primary-button" onClick={onClose}>
          Done
        </button>
      </div>
    </div>
  );
}

function RepoChoiceRow({
  label,
  isPrivate,
  url,
  disabled,
  onSelect,
}: {
  label: string;
  isPrivate: boolean;
  url: string;
  disabled: boolean;
  onSelect: (repoUrl: string) => void;
}) {
  return (
    <div className="connector-access-row">
      <span>{label}</span>
      <strong>{isPrivate ? "Private" : "Public"}</strong>
      <button
        type="button"
        className="secondary-action-button compact-button"
        disabled={disabled || !url}
        onClick={() => onSelect(url)}
      >
        Select
      </button>
    </div>
  );
}

function ConnectorPanel({
  connectors,
  onOpen,
}: {
  connectors: ConnectorConfig[];
  onOpen: (connectorId: ConnectorId) => void;
}) {
  const [open, setOpen] = useState(true);
  const groupedConnectors = useMemo(() => {
    const connectorsByCategory = new Map<ConnectorCategoryId, ConnectorConfig[]>();
    for (const connector of connectors) {
      const currentConnectors = connectorsByCategory.get(connector.category) || [];
      currentConnectors.push(connector);
      connectorsByCategory.set(connector.category, currentConnectors);
    }
    return CONNECTOR_CATEGORY_ORDER.map((category) => ({
      ...category,
      connectors: connectorsByCategory.get(category.id) || [],
    })).filter((category) => category.connectors.length);
  }, [connectors]);

  return (
    <section className="connector-panel" aria-labelledby="connectors-heading">
      <button
        type="button"
        className="connector-panel-trigger"
        aria-expanded={open}
        aria-controls="connector-list"
        onClick={() => setOpen((currentOpen) => !currentOpen)}
      >
        <span id="connectors-heading">Connectors</span>
        <span className="connector-chevron" aria-hidden="true">
          {open ? "⌃" : "⌄"}
        </span>
      </button>
      {open ? (
        <div className="connector-list" id="connector-list">
          {groupedConnectors.map((group) => (
            <div className="connector-category-group" key={group.id}>
              <div className="connector-category-heading">{group.label}</div>
              {group.connectors.map((connector) => (
                <button
                  type="button"
                  className="connector-row connector-open"
                  key={connector.id}
                  onClick={() => onOpen(connector.id)}
                >
                  <ConnectorLogo connectorId={connector.id} />
                  <span>{connector.name}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ConnectorLogo({ connectorId }: { connectorId: ConnectorId }) {
  if (connectorId === "slack") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path fill="#36C5F0" d="M11.4 3.2a3.2 3.2 0 0 1 6.4 0v6.4h-6.4z" />
          <path fill="#36C5F0" d="M3.2 11.4a3.2 3.2 0 0 1 0-6.4h3.2v6.4z" />
          <path fill="#2EB67D" d="M28.8 11.4a3.2 3.2 0 0 1 0 6.4h-3.2v-6.4z" />
          <path fill="#2EB67D" d="M20.6 3.2a3.2 3.2 0 0 1 6.4 0v3.2h-6.4z" />
          <path fill="#ECB22E" d="M20.6 28.8a3.2 3.2 0 0 1-6.4 0v-6.4h6.4z" />
          <path fill="#ECB22E" d="M28.8 20.6a3.2 3.2 0 0 1 0 6.4h-6.4v-6.4z" />
          <path fill="#E01E5A" d="M3.2 20.6a3.2 3.2 0 0 1 0-6.4h6.4v6.4z" />
          <path fill="#E01E5A" d="M11.4 28.8a3.2 3.2 0 0 1-6.4 0v-3.2h6.4z" />
        </svg>
      </span>
    );
  }

  if (connectorId === "github") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path
            fill="#24292F"
            d="M16 2.5c-7.5 0-13.6 6-13.6 13.5 0 6 3.9 11.1 9.3 12.9.7.1.9-.3.9-.7v-2.4c-3.8.8-4.6-1.6-4.6-1.6-.6-1.5-1.5-1.9-1.5-1.9-1.2-.8.1-.8.1-.8 1.4.1 2.1 1.4 2.1 1.4 1.2 2.1 3.2 1.5 3.9 1.2.1-.9.5-1.5.9-1.8-3-.3-6.2-1.5-6.2-6.7 0-1.5.5-2.7 1.4-3.7-.1-.3-.6-1.7.1-3.6 0 0 1.1-.4 3.7 1.4 1.1-.3 2.2-.5 3.4-.5s2.3.2 3.4.5c2.6-1.8 3.7-1.4 3.7-1.4.7 1.9.3 3.3.1 3.6.9 1 1.4 2.2 1.4 3.7 0 5.2-3.2 6.4-6.2 6.7.5.4.9 1.3.9 2.6v3.8c0 .4.2.8.9.7 5.4-1.8 9.3-6.9 9.3-12.9C29.6 8.5 23.5 2.5 16 2.5z"
          />
        </svg>
      </span>
    );
  }

  if (connectorId === "linear") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <rect width="32" height="32" rx="8" fill="#5E6AD2" />
          <path fill="#fff" d="M7 19.7 19.7 7h4.1L7 23.8zM7 25.6 25.6 7H28L9.4 25.6zM7 13.9 13.9 7H18L7 18zM12.2 26l13.4-13.4V17L16.6 26z" />
        </svg>
      </span>
    );
  }

  if (connectorId === "confluence") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path fill="#2684FF" d="M9.4 21.7c-1.1 1.8-.8 4.1.8 5.4 1.6 1.2 3.9.9 5.1-.8l7.3-10.4c1.1-1.6.8-3.8-.8-5l-2.1-1.6-3 4.2 1.5 1.1z" />
          <path fill="#0052CC" d="M22.6 10.3c1.1-1.8.8-4.1-.8-5.4-1.6-1.2-3.9-.9-5.1.8L9.4 16.1c-1.1 1.6-.8 3.8.8 5l2.1 1.6 3-4.2-1.5-1.1z" />
        </svg>
      </span>
    );
  }

  return (
    <span className="connector-logo" aria-hidden="true">
      <svg viewBox="0 0 32 32" focusable="false">
        <path fill="#2684FF" d="M16 3 29 16 16 29 3 16z" />
        <path fill="#0052CC" d="M16 8.5 23.5 16 16 23.5 8.5 16z" />
        <path fill="#fff" d="M16 12.2 19.8 16 16 19.8 12.2 16z" />
      </svg>
    </span>
  );
}

function RepoList({
  repos,
  selectedRepoId,
  error,
  onSelect,
}: {
  repos: IndexedRepo[];
  selectedRepoId: string | null;
  error: string | null;
  onSelect: (repo: IndexedRepo) => void;
}) {
  if (error) {
    return <div className="status-text">{error}</div>;
  }

  if (!repos.length) {
    return <div className="status-text">No indexed repositories yet.</div>;
  }

  return (
    <div className="repo-list">
      {repos.map((repo) => (
        <button
          key={repo.repo_id}
          type="button"
          className={`repo-item${repo.repo_id === selectedRepoId ? " active" : ""}`}
          onClick={() => onSelect(repo)}
        >
          <span className="repo-url">{repo.repo_url}</span>
          <span className="repo-meta">
            {repo.file_count} files, {repo.chunk_count} chunks
          </span>
        </button>
      ))}
    </div>
  );
}

function CreateNodeForm({
  userRole,
  disabled,
  availableAssignees,
  parentOptions,
  ownNode,
  onCreate,
}: {
  userRole: AuthUser["role"];
  disabled: boolean;
  availableAssignees: HierarchyAssignableUser[];
  parentOptions: HierarchyNode[];
  ownNode: HierarchyNode | null;
  onCreate: (draft: CreateNodeDraft) => Promise<boolean>;
}) {
  const [displayName, setDisplayName] = useState("");
  const [assignedUserId, setAssignedUserId] = useState("");
  const [parentNodeId, setParentNodeId] = useState("");
  const handleAssignedUserChange = useCallback((nextAssignedUserId: string) => {
    setAssignedUserId(nextAssignedUserId);
  }, []);
  const handleParentNodeChange = useCallback((nextParentNodeId: string) => {
    setParentNodeId(nextParentNodeId);
  }, []);

  useEffect(() => {
    if (assignedUserId && !availableAssignees.some((user) => user.user_id === assignedUserId)) {
      setAssignedUserId("");
    }
  }, [assignedUserId, availableAssignees]);

  useEffect(() => {
    if (userRole !== "admin") {
      setParentNodeId(ownNode?.node_id ?? "");
      return;
    }
    if (parentNodeId && !parentOptions.some((node) => node.node_id === parentNodeId)) {
      setParentNodeId("");
    }
  }, [ownNode, parentNodeId, parentOptions, userRole]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await onCreate({
      displayName,
      assignedUserId,
      parentNodeId,
    });
    if (created) {
      setDisplayName("");
      setAssignedUserId("");
      if (userRole === "admin") {
        setParentNodeId("");
      }
    }
  }

  const canCreate = Boolean(
    !disabled &&
      displayName.trim() &&
      assignedUserId &&
      (userRole === "admin" || parentNodeId),
  );

  return (
    <form className="graph-control-form" onSubmit={handleSubmit}>
      <label htmlFor="nodeTitle">Display name</label>
      <textarea
        id="nodeTitle"
        value={displayName}
        maxLength={120}
        rows={1}
        placeholder="Name shown on graph"
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        disabled={disabled}
        onChange={(event) => setDisplayName(event.target.value)}
      />
      <label id="assignedUserLabel">Assigned user</label>
      <AssignableUserPicker
        value={assignedUserId}
        disabled={disabled}
        availableAssignees={availableAssignees}
        labelId="assignedUserLabel"
        emptyLabel="No assignee selected"
        searchPlaceholder="Search unassigned users"
        onChange={handleAssignedUserChange}
      />
      <label id="parentNodeLabel">Parent</label>
      <ParentNodeSelect
        value={parentNodeId}
        disabled={disabled || userRole !== "admin"}
        userRole={userRole}
        parentOptions={parentOptions}
        labelId="parentNodeLabel"
        onChange={handleParentNodeChange}
      />
      {availableAssignees.length ? null : (
        <div className="status-text compact">No unassigned logged-in workspace users.</div>
      )}
      <button type="submit" className="primary-button" disabled={!canCreate}>
        {disabled ? "Working..." : "Create node"}
      </button>
    </form>
  );
}

const AssignableUserPicker = memo(function AssignableUserPicker({
  value,
  disabled,
  availableAssignees,
  labelId,
  emptyLabel,
  searchPlaceholder,
  onChange,
}: {
  value: string;
  disabled: boolean;
  availableAssignees: HierarchyAssignableUser[];
  labelId: string;
  emptyLabel: string;
  searchPlaceholder: string;
  onChange: (assignedUserId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const selectedUser = availableAssignees.find((user) => user.user_id === value) ?? null;
  const normalizedQuery = query.trim().toLowerCase();
  const results = useMemo(() => {
    const matches = normalizedQuery
      ? availableAssignees.filter((assignableUser) =>
          `${assignableUser.name} ${assignableUser.email}`.toLowerCase().includes(normalizedQuery),
        )
      : availableAssignees;
    const visible = matches.slice(0, MAX_PICKER_RESULTS);
    if (selectedUser && !visible.some((user) => user.user_id === selectedUser.user_id)) {
      return [selectedUser, ...visible];
    }
    return visible;
  }, [availableAssignees, normalizedQuery, selectedUser]);

  return (
    <div className="compact-picker" aria-labelledby={labelId}>
      <input
        type="search"
        value={query}
        placeholder={searchPlaceholder}
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="picker-current">
        <span>{selectedUser ? selectedUser.name || selectedUser.email : emptyLabel}</span>
        {selectedUser ? (
          <button type="button" disabled={disabled} onClick={() => onChange("")}>
            Clear
          </button>
        ) : null}
      </div>
      {query || !selectedUser ? (
        <div className="picker-results">
          {results.map((assignableUser) => (
            <button
              key={assignableUser.user_id}
              type="button"
              disabled={disabled}
              className={assignableUser.user_id === value ? "active" : ""}
              onClick={() => {
                onChange(assignableUser.user_id);
                setQuery("");
              }}
            >
              {assignableUser.name || assignableUser.email}
            </button>
          ))}
          {!results.length ? <span>No users match.</span> : null}
        </div>
      ) : null}
    </div>
  );
});

const ParentNodeSelect = memo(function ParentNodeSelect({
  value,
  disabled,
  userRole,
  parentOptions,
  labelId,
  onChange,
}: {
  value: string;
  disabled: boolean;
  userRole: AuthUser["role"];
  parentOptions: HierarchyNode[];
  labelId: string;
  onChange: (parentNodeId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const selectedParent = parentOptions.find((node) => node.node_id === value) ?? null;
  const parentMatches = useMemo(
    () =>
      normalizedQuery
        ? parentOptions.filter((node) => {
            const searchable = [
              node.display_name,
              node.assigned_user_name || "",
              node.assigned_user_email || "",
            ]
              .join(" ")
              .toLowerCase();
            return searchable.includes(normalizedQuery);
          })
        : parentOptions,
    [normalizedQuery, parentOptions],
  );
  const filteredParents = useMemo(() => {
    const visible = parentMatches.slice(0, MAX_PICKER_RESULTS);
    if (selectedParent && !visible.some((node) => node.node_id === selectedParent.node_id)) {
      return [selectedParent, ...visible];
    }
    return visible;
  }, [parentMatches, selectedParent]);
  const matchCount = parentMatches.length;

  return (
    <div className="compact-picker" aria-labelledby={labelId}>
      {userRole === "admin" ? (
        <input
          type="search"
          value={query}
          placeholder="Search parent nodes"
          disabled={disabled}
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => setQuery(event.target.value)}
        />
      ) : null}
      <div className="picker-current">
        <span>{selectedParent ? selectedParent.display_name : "No parent"}</span>
        {userRole === "admin" && selectedParent ? (
          <button type="button" disabled={disabled} onClick={() => onChange("")}>
            Clear
          </button>
        ) : null}
      </div>
      {userRole === "admin" && query ? (
        <div className="picker-results">
          {filteredParents.slice(0, MAX_PICKER_RESULTS).map((node) => (
            <button
              key={node.node_id}
              type="button"
              disabled={disabled}
              className={node.node_id === value ? "active" : ""}
              onClick={() => {
                onChange(node.node_id);
                setQuery("");
              }}
            >
              {node.display_name}
            </button>
          ))}
          {!filteredParents.length ? <span>No parent nodes match.</span> : null}
          {matchCount > MAX_PICKER_RESULTS ? (
            <span>Showing {MAX_PICKER_RESULTS} of {matchCount} matches.</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
});
