import { useState } from "react";

import type { AuthUser, Workspace } from "../../types";
import { AppToast } from "../../components/AppToast";
import { WorkspaceChatBox } from "../WorkspaceChatBox";
import { WorkspaceGraphCanvas } from "../WorkspaceGraphCanvas";
import type { ConnectorId } from "./connectors/connectors";
import { WorkspaceSourcesPanel } from "./WorkspaceSourcesPanel";
import { useWorkspaceApiError, useWorkspaceChat, useWorkspaceRepos } from "./chat/useWorkspaceReposAndChat";
import { useWorkspaceConnectors } from "./connectors/useWorkspaceConnectors";
import { GraphAddNodeModal, GraphEditNodeModal } from "./graph/GraphNodeModals";
import { useWorkspaceGraph } from "./graph/useWorkspaceGraph";
import { useWorkspaceAdditionalDocuments } from "./useWorkspaceAdditionalDocuments";

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

  function handleConnectConnector(connectorId: ConnectorId) {
    connectors.handleConnectConnector(connectorId);
  }

  const appToastMessage =
    connectors.connectorError ||
    connectors.connectorStatus ||
    graphStatus ||
    repoListError ||
    null;
  const appToastIsError = Boolean(connectors.connectorError || repoListError);

  return (
    <section className="graph-workspace">
      <div className="graph-workspace-layout">
        <WorkspaceSourcesPanel
          workspace={workspace}
          refreshKey={sourcesRefreshKey}
          collapsed={!sourcesPanelOpen}
          onToggleCollapsed={() => setSourcesPanelOpen((open) => !open)}
          onConnect={handleConnectConnector}
          additionalDocuments={{
            documents: additionalDocuments.documents,
            loading: additionalDocuments.loading,
            uploading: additionalDocuments.uploading,
            error: additionalDocuments.error,
            acceptedDocumentTypes: additionalDocuments.acceptedDocumentTypes,
            onFileChange: additionalDocuments.handleFileChange,
          }}
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
