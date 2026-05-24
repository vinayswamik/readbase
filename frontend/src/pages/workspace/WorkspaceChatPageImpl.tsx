import type { AuthUser, Workspace } from "../../types";
import { WorkspaceChatBox } from "../WorkspaceChatBox";
import { WorkspaceGraphCanvas } from "../WorkspaceGraphCanvas";
import { ConnectorSetupModal } from "./connectors/ConnectorSetupModal";
import type { ConnectorSetupModalProps } from "./connectors/ConnectorSetupModalTypes";
import { WorkspaceLeftPanel } from "../WorkspaceLeftPanel";
import { useWorkspaceApiError, useWorkspaceChat, useWorkspaceRepos } from "./chat/useWorkspaceReposAndChat";
import { useWorkspaceConnectors } from "./connectors/useWorkspaceConnectors";
import { useWorkspaceGraph } from "./graph/useWorkspaceGraph";

export function WorkspaceChatPageImpl({
  user,
  workspace,
  onBack,
  onSessionExpired,
}: {
  user: AuthUser;
  workspace: Workspace;
  onBack: () => void;
  onSessionExpired: () => void;
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
  });

  const {
    repoId,
    repos: repoList,
    repoListError,
    selectedRepo,
    handleRepoSelect,
  } = repos;
  const {
    question,
    setQuestion,
    messages,
    mode,
    asking,
    chatOpen,
    setChatOpen,
    handleAskSubmit,
    canAsk,
    messageEndRef,
  } = chat;
  const {
    panelOpen,
    setPanelOpen,
    sidebarTab,
    setSidebarTab,
    nodes,
    graphMutating,
    graphStatus,
    graphRevision,
    selectedNodeId,
    selectedNode,
    availableAssignees,
    parentOptions,
    ownNode,
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
    handleZoom,
    setViewport,
  } = graph;
  const { activeConnector, openConnectorModal, closeConnectorModal, ...connectorModalProps } =
    connectors;

  const modalProps: ConnectorSetupModalProps = {
    connector: activeConnector!,
    repoUrl: connectorModalProps.connectorRepoUrl,
    refreshRepo: connectorModalProps.connectorRefreshRepo,
    members: connectorModalProps.connectorMembers,
    loadingMembers: connectorModalProps.connectorMembersLoading,
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
    slackConnection: connectorModalProps.slackConnection,
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
    canManageWorkspace: workspace.can_manage,
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
    onJiraDisconnect: connectorModalProps.handleJiraDisconnect,
    onJiraProjectQueryChange: connectorModalProps.setJiraProjectQuery,
    onJiraProjectSearch: () =>
      connectorModalProps.loadJiraProjects(connectorModalProps.jiraProjectQuery),
    onAddJiraProject: connectorModalProps.handleAddJiraProject,
    onSyncJiraSource: connectorModalProps.handleSyncJiraSource,
    onRemoveJiraSource: connectorModalProps.handleRemoveJiraSource,
    onSlackConnect: connectorModalProps.handleSlackConnect,
    onSlackDisconnect: connectorModalProps.handleSlackDisconnect,
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
    onConnectorManagerToggle: connectorModalProps.handleConnectorManagerToggle,
    onClose: closeConnectorModal,
  };

  return (
    <section
      className={`graph-workspace${panelOpen ? " panel-open" : " panel-closed"}`}
    >
      <WorkspaceLeftPanel
        workspace={workspace}
        mode={mode}
        sidebarTab={sidebarTab}
        userRole={user.role}
        repos={repoList}
        selectedRepoId={repoId}
        repoListError={repoListError}
        graphMutating={graphMutating}
        graphStatus={graphStatus}
        availableAssignees={availableAssignees}
        parentOptions={parentOptions}
        ownNode={ownNode}
        selectedNode={selectedNode}
        canManageSelectedNode={canManageSelectedNode}
        editTitle={editTitle}
        editAssignedUserId={editAssignedUserId}
        reassignOptions={reassignOptions}
        canDeleteSelectedNode={canDeleteSelectedNode}
        reparentNodeId={reparentNodeId}
        reparentOptions={reparentOptions}
        onBack={onBack}
        onSidebarTabChange={setSidebarTab}
        onRepoSelect={handleRepoSelect}
        onCreateNode={handleCreateNode}
        onUpdateSelectedNode={handleUpdateSelectedNode}
        onDeleteSelectedNode={handleDeleteSelectedNode}
        onEditTitleChange={setEditTitle}
        onEditAssignedUserIdChange={setEditAssignedUserId}
        onReparentNodeIdChange={setReparentNodeId}
        onReparentSelectedNode={handleReparentSelectedNode}
        onOpenConnector={openConnectorModal}
      />
      <WorkspaceGraphCanvas
        userRole={user.role}
        panelOpen={panelOpen}
        graphRevision={graphRevision}
        boardRef={boardRef}
        nodes={nodes}
        visibleNodes={visibleNodes}
        selectedNodeId={selectedNodeId}
        viewport={viewport}
        edgeSegments={edgeSegments}
        chatOpen={chatOpen}
        messageCount={messages.length}
        onPanelToggle={() => setPanelOpen((open) => !open)}
        onZoom={handleZoom}
        onViewportReset={() => setViewport({ x: 120, y: 80, scale: 1 })}
        onBoardMouseDown={handleBoardMouseDown}
        onBoardMouseMove={handleBoardMouseMove}
        onBoardMouseUp={handleBoardMouseUp}
        onNodeClick={handleNodeClick}
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
      {activeConnector ? (
        <ConnectorSetupModal {...modalProps} connector={activeConnector} />
      ) : null}
    </section>
  );
}
