import { useState } from "react";

import type { AuthUser, Workspace } from "../../types";
import { AppToast } from "../../components/AppToast";
import { WorkspaceChatBox } from "../WorkspaceChatBox";
import { WorkspaceGraphCanvas } from "../WorkspaceGraphCanvas";
import { ConnectorSetupModal } from "./connectors/ConnectorSetupModal";
import type { ConnectorSetupModalProps } from "./connectors/ConnectorSetupModalTypes";
import type { ConnectorId } from "./connectors/connectors";
import { WorkspaceSourcesModal } from "./WorkspaceSourcesModal";
import { useWorkspaceApiError, useWorkspaceChat, useWorkspaceRepos } from "./chat/useWorkspaceReposAndChat";
import { useWorkspaceConnectors } from "./connectors/useWorkspaceConnectors";
import { GraphAddNodeModal, GraphEditNodeModal } from "./graph/GraphNodeModals";
import { useWorkspaceGraph } from "./graph/useWorkspaceGraph";

export function WorkspaceChatPageImpl({
  user,
  workspace,
  onBack,
  onSessionExpired,
  sourcesOpen,
  onSourcesOpenChange,
}: {
  user: AuthUser;
  workspace: Workspace;
  onBack: () => void;
  onSessionExpired: () => void;
  sourcesOpen: boolean;
  onSourcesOpenChange: (open: boolean) => void;
}) {
  const handleApiError = useWorkspaceApiError(onSessionExpired);
  const repos = useWorkspaceRepos({ workspace, onBack, handleApiError });
  const chat = useWorkspaceChat({
    workspace,
    repoId: repos.repoId,
    handleApiError,
  });
  const graph = useWorkspaceGraph({ workspace, user, handleApiError });
  const connectors = useWorkspaceConnectors({
    workspace,
    handleApiError,
    selectedRepoUrl: repos.selectedRepo?.repo_url,
    setRepoId: repos.setRepoId,
    loadRepos: repos.loadRepos,
    onWorkspaceSourcesChanged: () => {
      setSourcesRefreshKey((current) => current + 1);
    },
  });

  const { repoId, repoListError, selectedRepo } = repos;
  const {
    question,
    setQuestion,
    messages,
    asking,
    chatOpen,
    setChatOpen,
    handleAskSubmit,
    canAsk,
    messageEndRef,
  } = chat;
  const {
    addNodeModalOpen,
    setAddNodeModalOpen,
    editNodeModalOpen,
    setEditNodeModalOpen,
    nodeEditAnchor,
    nodes,
    graphMutating,
    graphStatus,
    graphRevision,
    selectedNodeId,
    selectedNode,
    parentOptions,
    ownNode,
    canManageWorkspace,
    canManageSelectedNode,
    editTitle,
    setEditTitle,
    editAssignedUserId,
    setEditAssignedUserId,
    reassignOptions,
    canDeleteSelectedNode,
    reparentNodeId,
    setReparentNodeId,
    reparentOptions,
    visibleNodes,
    edgeSegments,
    viewport,
    boardRef,
    handleCreateNode,
    handleUpdateSelectedNode,
    handleDeleteSelectedNode,
    handleReparentSelectedNode,
    handleBoardMouseDown,
    handleBoardMouseMove,
    handleBoardMouseUp,
    handleNodeClick,
    handleOpenEditNode,
    handleZoom,
    setViewport,
  } = graph;
  const { activeConnector, openConnectorModal, closeConnectorModal, ...connectorModalProps } =
    connectors;
  const [sourcesRefreshKey, setSourcesRefreshKey] = useState(0);

  function handleManageConnector(connectorId: ConnectorId) {
    openConnectorModal(connectorId);
  }

  function handleConnectConnector(connectorId: ConnectorId) {
    connectors.handleConnectConnector(connectorId);
  }

  function handleCloseConnectorModal() {
    closeConnectorModal();
    if (sourcesOpen) {
      setSourcesRefreshKey((current) => current + 1);
    }
  }

  const appToastMessage =
    connectorModalProps.connectorError ||
    connectorModalProps.connectorStatus ||
    graphStatus ||
    repoListError ||
    null;
  const appToastIsError = Boolean(connectorModalProps.connectorError || repoListError);

  const modalProps: ConnectorSetupModalProps = {
    connector: activeConnector!,
    repoUrl: connectorModalProps.connectorRepoUrl,
    refreshRepo: connectorModalProps.connectorRefreshRepo,
    indexing: connectorModalProps.indexing,
    status: connectorModalProps.connectorStatus,
    error: connectorModalProps.connectorError,
    githubConnection: connectorModalProps.githubConnection,
    githubRepositories: connectorModalProps.githubRepositories,
    githubRepositoryQuery: connectorModalProps.githubRepositoryQuery,
    githubRepositoriesLoading: connectorModalProps.githubRepositoriesLoading,
    bitbucketConnection: connectorModalProps.bitbucketConnection,
    bitbucketRepositories: connectorModalProps.bitbucketRepositories,
    bitbucketRepositoryQuery: connectorModalProps.bitbucketRepositoryQuery,
    bitbucketLoading: connectorModalProps.bitbucketLoading,
    gitlabConnection: connectorModalProps.gitlabConnection,
    gitlabProjects: connectorModalProps.gitlabProjects,
    gitlabProjectQuery: connectorModalProps.gitlabProjectQuery,
    gitlabLoading: connectorModalProps.gitlabLoading,
    jiraConnection: connectorModalProps.jiraConnection,
    jiraSources: connectorModalProps.jiraSources,
    jiraProjects: connectorModalProps.jiraProjects,
    jiraProjectQuery: connectorModalProps.jiraProjectQuery,
    jiraLoading: connectorModalProps.jiraLoading,
    jiraWorkspaceSite: connectorModalProps.jiraWorkspaceSite,
    slackConnection: connectorModalProps.slackConnection,
    slackTeams: connectorModalProps.slackTeams,
    slackSources: connectorModalProps.slackSources,
    slackChannels: connectorModalProps.slackChannels,
    slackChannelQuery: connectorModalProps.slackChannelQuery,
    slackLoading: connectorModalProps.slackLoading,
    linearConnection: connectorModalProps.linearConnection,
    linearSources: connectorModalProps.linearSources,
    linearSelectableSources: connectorModalProps.linearSelectableSources,
    linearQuery: connectorModalProps.linearQuery,
    linearLoading: connectorModalProps.linearLoading,
    confluenceConnection: connectorModalProps.confluenceConnection,
    confluenceSources: connectorModalProps.confluenceSources,
    confluenceSpaces: connectorModalProps.confluenceSpaces,
    confluenceQuery: connectorModalProps.confluenceQuery,
    confluenceLoading: connectorModalProps.confluenceLoading,
    notionConnection: connectorModalProps.notionConnection,
    notionSources: connectorModalProps.notionSources,
    notionDatabases: connectorModalProps.notionDatabases,
    notionQuery: connectorModalProps.notionQuery,
    notionLoading: connectorModalProps.notionLoading,
    onRepoUrlChange: connectorModalProps.setConnectorRepoUrl,
    onGithubRepositoryQueryChange: connectorModalProps.setGithubRepositoryQuery,
    onGithubRepositorySearch: () =>
      connectorModalProps.loadGithubRepositories(
        connectorModalProps.githubRepositoryQuery,
      ),
    onBitbucketRepositoryQueryChange:
      connectorModalProps.setBitbucketRepositoryQuery,
    onBitbucketRepositorySearch: () =>
      connectorModalProps.loadBitbucketRepositories(
        connectorModalProps.bitbucketRepositoryQuery,
      ),
    onGitlabProjectQueryChange: connectorModalProps.setGitlabProjectQuery,
    onGitlabProjectSearch: () =>
      connectorModalProps.loadGitlabProjects(connectorModalProps.gitlabProjectQuery),
    onRefreshRepoChange: connectorModalProps.setConnectorRefreshRepo,
    onSubmit: connectorModalProps.handleGithubConnectorSubmit,
    onGithubConnect: connectorModalProps.handleGithubConnect,
    onGithubDisconnect: connectorModalProps.handleGithubDisconnect,
    onBitbucketConnect: connectorModalProps.handleBitbucketConnect,
    onBitbucketDisconnect: connectorModalProps.handleBitbucketDisconnect,
    onGitlabConnect: connectorModalProps.handleGitlabConnect,
    onGitlabDisconnect: connectorModalProps.handleGitlabDisconnect,
    onJiraConnect: connectorModalProps.handleJiraConnect,
    onConnectJiraSite: connectorModalProps.handleConnectJiraSite,
    onRemoveJiraSite: connectorModalProps.handleRemoveJiraSite,
    onJiraProjectQueryChange: connectorModalProps.setJiraProjectQuery,
    onJiraProjectSearch: () =>
      connectorModalProps.loadJiraProjects(connectorModalProps.jiraProjectQuery),
    onAddJiraProject: connectorModalProps.handleAddJiraProject,
    onSyncJiraSource: connectorModalProps.handleSyncJiraSource,
    onRemoveJiraSource: connectorModalProps.handleRemoveJiraSource,
    onSlackConnect: connectorModalProps.handleSlackConnect,
    onSlackDisconnect: connectorModalProps.handleSlackDisconnect,
    onSlackUnlinkTeam: connectorModalProps.handleSlackUnlinkTeam,
    onSlackChannelQueryChange: connectorModalProps.setSlackChannelQuery,
    onAddSlackChannel: connectorModalProps.handleAddSlackChannel,
    onSyncSlackSource: connectorModalProps.handleSyncSlackSource,
    onRemoveSlackSource: connectorModalProps.handleRemoveSlackSource,
    onLinearConnect: connectorModalProps.handleLinearConnect,
    onLinearDisconnect: connectorModalProps.handleLinearDisconnect,
    onLinearQueryChange: connectorModalProps.setLinearQuery,
    onLinearSearch: () =>
      connectorModalProps.loadLinearSelectableSources(
        connectorModalProps.linearQuery,
      ),
    onAddLinearSource: connectorModalProps.handleAddLinearSource,
    onSyncLinearSource: connectorModalProps.handleSyncLinearSource,
    onRemoveLinearSource: connectorModalProps.handleRemoveLinearSource,
    onConfluenceConnect: connectorModalProps.handleConfluenceConnect,
    onConfluenceDisconnect: connectorModalProps.handleConfluenceDisconnect,
    onConfluenceQueryChange: connectorModalProps.setConfluenceQuery,
    onConfluenceSearch: () =>
      connectorModalProps.loadConfluenceSpaces(connectorModalProps.confluenceQuery),
    onAddConfluenceSpace: connectorModalProps.handleAddConfluenceSpace,
    onSyncConfluenceSource: connectorModalProps.handleSyncConfluenceSource,
    onRemoveConfluenceSource: connectorModalProps.handleRemoveConfluenceSource,
    onNotionConnect: connectorModalProps.handleNotionConnect,
    onNotionDisconnect: connectorModalProps.handleNotionDisconnect,
    onNotionQueryChange: connectorModalProps.setNotionQuery,
    onNotionSearch: () =>
      connectorModalProps.loadNotionDatabases(connectorModalProps.notionQuery),
    onAddNotionDatabase: connectorModalProps.handleAddNotionDatabase,
    onSyncNotionSource: connectorModalProps.handleSyncNotionSource,
    onRemoveNotionSource: connectorModalProps.handleRemoveNotionSource,
    onClose: handleCloseConnectorModal,
  };

  return (
    <section className="graph-workspace">
      <WorkspaceGraphCanvas
        workspaceName={workspace.name}
        graphRevision={graphRevision}
        boardRef={boardRef}
        nodes={nodes}
        visibleNodes={visibleNodes}
        selectedNodeId={selectedNodeId}
        nodeEditAnchor={nodeEditAnchor}
        viewport={viewport}
        edgeSegments={edgeSegments}
        chatOpen={chatOpen}
        messageCount={messages.length}
        onBack={onBack}
        onAddNode={() => setAddNodeModalOpen(true)}
        onZoom={handleZoom}
        onViewportReset={() => setViewport({ x: 120, y: 80, scale: 1 })}
        onBoardMouseDown={handleBoardMouseDown}
        onBoardMouseMove={handleBoardMouseMove}
        onBoardMouseUp={handleBoardMouseUp}
        onNodeClick={handleNodeClick}
        onEditNode={handleOpenEditNode}
        onOpenChat={() => setChatOpen(true)}
      >
        {chatOpen ? (
          <WorkspaceChatBox
            messages={messages}
            question={question}
            asking={asking}
            canAsk={canAsk}
            selectedRepo={selectedRepo}
            messageEndRef={messageEndRef}
            onQuestionChange={setQuestion}
            onSubmit={handleAskSubmit}
            onClose={() => setChatOpen(false)}
          />
        ) : null}
      </WorkspaceGraphCanvas>
      <WorkspaceSourcesModal
        open={sourcesOpen}
        workspace={workspace}
        refreshKey={sourcesRefreshKey}
        onClose={() => onSourcesOpenChange(false)}
        onConnect={handleConnectConnector}
        onManage={handleManageConnector}
        onSessionExpired={onSessionExpired}
      />
      {activeConnector ? (
        <ConnectorSetupModal {...modalProps} connector={activeConnector} />
      ) : null}
      <GraphAddNodeModal
        open={addNodeModalOpen}
        canManageWorkspace={canManageWorkspace}
        disabled={graphMutating}
        parentOptions={parentOptions}
        ownNode={ownNode}
        onClose={() => setAddNodeModalOpen(false)}
        onCreate={handleCreateNode}
      />
      <GraphEditNodeModal
        open={editNodeModalOpen}
        selectedNode={selectedNode}
        canManageSelectedNode={canManageSelectedNode}
        canDeleteSelectedNode={canDeleteSelectedNode}
        canManageWorkspace={canManageWorkspace}
        graphMutating={graphMutating}
        editTitle={editTitle}
        editAssignedUserId={editAssignedUserId}
        reassignOptions={reassignOptions}
        reparentNodeId={reparentNodeId}
        reparentOptions={reparentOptions}
        onClose={() => setEditNodeModalOpen(false)}
        onEditTitleChange={setEditTitle}
        onEditAssignedUserIdChange={setEditAssignedUserId}
        onUpdateSelectedNode={handleUpdateSelectedNode}
        onDeleteSelectedNode={handleDeleteSelectedNode}
        onReparentNodeIdChange={setReparentNodeId}
        onReparentSelectedNode={handleReparentSelectedNode}
      />
      <AppToast message={appToastMessage} error={appToastIsError} />
    </section>
  );
}
