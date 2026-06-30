import { useCallback, useRef, useState, type MouseEvent } from "react";

import type { AuthUser, Workspace } from "../../types";
import { AppToast } from "../../components/AppToast";
import { WorkspaceChatBox } from "../WorkspaceChatBox";
import { WorkspaceGraphCanvas } from "../WorkspaceGraphCanvas";
import { AdditionalDocumentManageContent } from "./AdditionalDocumentManageModal";
import { ConnectorSetupModal } from "./connectors/ConnectorSetupModal";
import type { ConnectorSetupModalProps } from "./connectors/ConnectorSetupModalTypes";
import {
  computeManageAnchorFromButton,
  type ConnectorModalDockAnchor,
} from "./connectors/connectorModalPosition";
import type { ConnectorId } from "./connectors/connectors";
import {
  DockedManageFlyoutShell,
  type DockedManageFlyoutVariant,
} from "./DockedManageFlyoutShell";
import { WorkspaceSourcesPanel } from "./WorkspaceSourcesPanel";
import { useWorkspaceApiError, useWorkspaceChat, useWorkspaceRepos } from "./chat/useWorkspaceReposAndChat";
import { useWorkspaceConnectors } from "./connectors/useWorkspaceConnectors";
import { GraphAddNodeModal, GraphEditNodeModal } from "./graph/GraphNodeModals";
import { useWorkspaceGraph } from "./graph/useWorkspaceGraph";
import { useWorkspaceAdditionalDocuments } from "./useWorkspaceAdditionalDocuments";
import type { WorkspaceAdditionalDocument } from "./workspaceAdditionalDocuments";

type ManageFlyoutKind = DockedManageFlyoutVariant | null;

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
  const [sourcesRefreshKey, setSourcesRefreshKey] = useState(0);
  const [sourcesPanelOpen, setSourcesPanelOpen] = useState(true);
  const [manageFlyoutKind, setManageFlyoutKind] = useState<ManageFlyoutKind>(null);
  const [manageFlyoutAnchor, setManageFlyoutAnchor] = useState<ConnectorModalDockAnchor | null>(null);
  const requestManageFlyoutCloseRef = useRef<(() => void) | null>(null);
  const handleManageFlyoutAnimatedCloseChange = useCallback((requestClose: (() => void) | null) => {
    requestManageFlyoutCloseRef.current = requestClose;
  }, []);
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
  const additionalDocuments = useWorkspaceAdditionalDocuments({
    workspaceId: workspace.workspace_id,
    onSessionExpired,
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
    centerViewport,
  } = graph;
  const { activeConnector, openConnectorModal, closeConnectorModal, ...connectorModalProps } =
    connectors;

  function handleCloseManageFlyout() {
    const closingFlyoutKind = manageFlyoutKind;
    setManageFlyoutKind(null);
    setManageFlyoutAnchor(null);
    closeConnectorModal();
    additionalDocuments.clearManagedDocument();
    if (closingFlyoutKind === "connector") {
      setSourcesRefreshKey((current) => current + 1);
    }
  }

  function handleManageConnector(connectorId: ConnectorId, event: MouseEvent<HTMLButtonElement>) {
    if (manageFlyoutKind === "connector" && activeConnector?.id === connectorId) {
      requestManageFlyoutCloseRef.current?.();
      return;
    }
    setManageFlyoutAnchor(computeManageAnchorFromButton(event.currentTarget));
    setManageFlyoutKind("connector");
    additionalDocuments.clearManagedDocument();
    openConnectorModal(connectorId);
  }

  function handleManageDocument(
    document: WorkspaceAdditionalDocument,
    event: MouseEvent<HTMLButtonElement>,
  ) {
    if (
      manageFlyoutKind === "document" &&
      additionalDocuments.managedDocument?.document_id === document.document_id
    ) {
      requestManageFlyoutCloseRef.current?.();
      return;
    }
    setManageFlyoutAnchor(computeManageAnchorFromButton(event.currentTarget));
    setManageFlyoutKind("document");
    closeConnectorModal();
    additionalDocuments.setManagedDocument(document);
    additionalDocuments.setError(null);
  }

  async function handleDeleteManagedDocument() {
    const deleted = await additionalDocuments.handleDeleteManagedDocument();
    if (deleted) {
      requestManageFlyoutCloseRef.current?.();
    }
  }

  function handleConnectConnector(connectorId: ConnectorId) {
    connectors.handleConnectConnector(connectorId);
  }

  const manageFlyoutOpen = manageFlyoutKind !== null;

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
    onRemoveJiraSource: connectorModalProps.handleRemoveJiraSource,
    onSlackConnect: connectorModalProps.handleSlackConnect,
    onSlackDisconnect: connectorModalProps.handleSlackDisconnect,
    onSlackUnlinkTeam: connectorModalProps.handleSlackUnlinkTeam,
    onSlackChannelQueryChange: connectorModalProps.setSlackChannelQuery,
    onAddSlackChannel: connectorModalProps.handleAddSlackChannel,
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
    onClose: handleCloseManageFlyout,
    onRequestClose: () => requestManageFlyoutCloseRef.current?.(),
  };

  return (
    <section className="graph-workspace">
      <div className="graph-workspace-layout">
        <WorkspaceSourcesPanel
          workspace={workspace}
          refreshKey={sourcesRefreshKey}
          collapsed={!sourcesPanelOpen}
          onToggleCollapsed={() => setSourcesPanelOpen((open) => !open)}
          onConnect={handleConnectConnector}
          onManage={handleManageConnector}
          additionalDocuments={{
            documents: additionalDocuments.documents,
            loading: additionalDocuments.loading,
            uploading: additionalDocuments.uploading,
            mutating: additionalDocuments.mutating,
            error: additionalDocuments.error,
            acceptedDocumentTypes: additionalDocuments.acceptedDocumentTypes,
            managedDocumentId: additionalDocuments.managedDocument?.document_id ?? null,
            onFileChange: additionalDocuments.handleFileChange,
          }}
          onManageDocument={handleManageDocument}
          onSessionExpired={onSessionExpired}
        />
        <div className="graph-workspace-main">
          <WorkspaceGraphCanvas
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
            onAddNode={() => setAddNodeModalOpen(true)}
            onZoom={handleZoom}
            onViewportReset={() => centerViewport(1)}
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
        </div>
      </div>
      <DockedManageFlyoutShell
        open={manageFlyoutOpen}
        variant={manageFlyoutKind === "document" ? "document" : "connector"}
        dockAnchor={manageFlyoutAnchor}
        onClose={handleCloseManageFlyout}
        onAnimatedCloseChange={handleManageFlyoutAnimatedCloseChange}
        modalClassName={manageFlyoutKind === "document" ? "document-manage-modal" : undefined}
        ariaLabelledBy={
          manageFlyoutKind === "document"
            ? "document-manage-modal-heading"
            : "connector-modal-heading"
        }
      >
        {manageFlyoutKind === "connector" && activeConnector ? (
          <ConnectorSetupModal {...modalProps} connector={activeConnector} />
        ) : null}
        {manageFlyoutKind === "document" && additionalDocuments.managedDocument ? (
          <AdditionalDocumentManageContent
            managedDocument={additionalDocuments.managedDocument}
            assignableUsers={additionalDocuments.assignableUsers}
            mutating={additionalDocuments.mutating}
            onRequestClose={() => requestManageFlyoutCloseRef.current?.()}
            onSaveAccess={additionalDocuments.handleSaveAccess}
            onDelete={handleDeleteManagedDocument}
          />
        ) : null}
      </DockedManageFlyoutShell>
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
