import { useRef, useState, type MouseEvent } from "react";

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

const GRAPH_DRAWER_MIN_WIDTH = 320;
const GRAPH_DRAWER_MAX_WIDTH = 960;

function getDefaultGraphDrawerWidth(containerWidth: number) {
  return Math.min(Math.round(containerWidth * 0.7), GRAPH_DRAWER_MAX_WIDTH);
}

function clampGraphDrawerWidth(width: number, containerWidth: number) {
  return Math.max(GRAPH_DRAWER_MIN_WIDTH, Math.min(width, getDefaultGraphDrawerWidth(containerWidth)));
}

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
  const [graphDrawerOpen, setGraphDrawerOpen] = useState(false);
  const [graphDrawerWidth, setGraphDrawerWidth] = useState<number | null>(null);
  const [graphDrawerResizing, setGraphDrawerResizing] = useState(false);
  const mainRef = useRef<HTMLDivElement>(null);
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
    handleViewportReset,
  } = graph;

  function handleConnectConnector(connectorId: ConnectorId) {
    connectors.handleConnectConnector(connectorId);
  }

  function toggleGraph() {
    setGraphDrawerOpen((open) => {
      // Don't pre-set the width on open. The CSS default (width: 70%,
      // max-width: 960px) already matches getDefaultGraphDrawerWidth, and
      // setting the inline px value in the same commit as `is-open` causes
      // a one-frame mismatch the user sees as the drawer "opening at one
      // width then animating toward another". The inline width is only
      // needed once the user manually resizes, which startDrawerResize handles.
      return !open;
    });
  }

  function startDrawerResize(event: MouseEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!mainRef.current) {
      return;
    }

    setGraphDrawerResizing(true);

    function onMouseMove(moveEvent: globalThis.MouseEvent) {
      const currentMain = mainRef.current;
      if (!currentMain) {
        return;
      }
      const mainRect = currentMain.getBoundingClientRect();
      const nextWidth = clampGraphDrawerWidth(mainRect.right - moveEvent.clientX, mainRect.width);
      setGraphDrawerWidth(nextWidth);
    }

    function onMouseUp() {
      setGraphDrawerResizing(false);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    }

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
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
        <div className="graph-workspace-main" ref={mainRef}>
          <WorkspaceChatBox
            messages={messages}
            question={question}
            asking={asking}
            canAsk={canAsk}
            selectedRepo={selectedRepo}
            messageEndRef={messageEndRef}
            onQuestionChange={setQuestion}
            onSubmit={handleAskSubmit}
            graphOpen={graphDrawerOpen}
            onToggleGraph={toggleGraph}
            acceptedDocumentTypes={additionalDocuments.acceptedDocumentTypes}
            onUploadDocument={additionalDocuments.handleFileChange}
          >
            <div
              className={`graph-drawer${graphDrawerOpen ? " is-open" : ""}${graphDrawerResizing ? " is-resizing" : ""}`}
              role="dialog"
              aria-label="Hierarchy graph"
              aria-hidden={!graphDrawerOpen}
              style={{ width: graphDrawerWidth ?? undefined }}
            >
              <div
                className="graph-drawer-resize-handle"
                onMouseDown={startDrawerResize}
                aria-hidden="true"
              >
                <span className="graph-drawer-resize-grip" />
              </div>
              <WorkspaceGraphCanvas
                boardRef={boardRef}
                nodes={nodes}
                visibleNodes={visibleNodes}
                selectedNodeId={selectedNodeId}
                nodeEditAnchor={nodeEditAnchor}
                viewport={viewport}
                edgeSegments={edgeSegments}
                onAddNode={() => setAddNodeModalOpen(true)}
                onZoom={handleZoom}
                onViewportReset={handleViewportReset}
                onBoardMouseDown={handleBoardMouseDown}
                onBoardMouseMove={handleBoardMouseMove}
                onBoardMouseUp={handleBoardMouseUp}
                onNodeClick={handleNodeClick}
                onEditNode={handleOpenEditNode}
              />
            </div>
          </WorkspaceChatBox>
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
