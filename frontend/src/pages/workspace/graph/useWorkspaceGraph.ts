import { FormEvent, MouseEvent } from "react";

import { deleteJson, patchJson, postJson } from "../../../api";
import type { CreateHierarchyNodeResponse, HierarchyNode } from "../../../types";
import type { CreateNodeDraft } from "../../WorkspaceLeftPanel";
import { clamp, useWorkspaceGraphModel } from "./useWorkspaceGraphModel";

type UseWorkspaceGraphArgs = {
  workspace: import("../../../types").Workspace;
  user: import("../../../types").AuthUser;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
};

export function useWorkspaceGraph(args: UseWorkspaceGraphArgs) {
  const model = useWorkspaceGraphModel(args);
  const {
    workspace,
    user,
    handleApiError,
    panelOpen,
    setPanelOpen,
    sidebarTab,
    setSidebarTab,
    nodes,
    setNodes,
    connections,
    setConnections,
    graphStatus,
    setGraphStatus,
    graphMutating,
    setGraphMutating,
    selectedNodeId,
    setSelectedNodeId,
    editTitle,
    setEditTitle,
    editAssignedUserId,
    setEditAssignedUserId,
    reparentNodeId,
    setReparentNodeId,
    viewport,
    setViewport,
    panState,
    setPanState,
    createNodeInFlightRef,
    boardRef,
    selectedNode,
    canManageSelectedNode,
    canDeleteSelectedNode,
    queueGraphRefresh,
  } = model;

  async function handleCreateNode(draft: CreateNodeDraft): Promise<boolean> {
    const trimmedTitle = draft.displayName.trim();
    const resolvedParentId = draft.parentNodeId || "";
    if (
      createNodeInFlightRef.current ||
      graphMutating ||
      !trimmedTitle ||
      !draft.assignedUserId ||
      (user.role !== "admin" && !resolvedParentId)
    ) {
      return false;
    }
    createNodeInFlightRef.current = true;
    setGraphMutating(true);
    setGraphStatus("Creating node...");
    try {
      const result = await postJson<
        {
          display_name: string;
          assigned_user_id: string;
          x: number;
          y: number;
          parent_node_id?: string;
        },
        CreateHierarchyNodeResponse
      >(`/api/workspaces/${workspace.workspace_id}/graph/nodes`, {
        display_name: trimmedTitle,
        assigned_user_id: draft.assignedUserId,
        x: 0,
        y: 0,
        parent_node_id: resolvedParentId || undefined,
      });
      setNodes((currentNodes) => [...currentNodes, result.node]);
      const createdConnection = result.connection;
      if (createdConnection) {
        setConnections((currentConnections) => [
          ...currentConnections,
          createdConnection,
        ]);
      }
      setSelectedNodeId(result.node.node_id);
      setGraphStatus("Node created.");
      queueGraphRefresh();
      return true;
    } catch (error) {
      handleApiError(error, setGraphStatus);
      return false;
    } finally {
      createNodeInFlightRef.current = false;
      setGraphMutating(false);
    }
  }
  async function handleUpdateSelectedNode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      graphMutating ||
      !selectedNode ||
      !canManageSelectedNode ||
      !editTitle.trim() ||
      !editAssignedUserId
    ) {
      return;
    }
    setGraphMutating(true);
    setGraphStatus("Saving node...");
    try {
      const updatedNode = await patchJson<
        { display_name: string; assigned_user_id: string },
        HierarchyNode
      >(
        `/api/workspaces/${workspace.workspace_id}/graph/nodes/${selectedNode.node_id}`,
        {
          display_name: editTitle.trim(),
          assigned_user_id: editAssignedUserId,
        },
      );
      setNodes((currentNodes) =>
        currentNodes.map((node) =>
          node.node_id === updatedNode.node_id ? updatedNode : node,
        ),
      );
      setGraphStatus("Node updated.");
      queueGraphRefresh();
    } catch (error) {
      handleApiError(error, setGraphStatus);
    } finally {
      setGraphMutating(false);
    }
  }
  async function handleDeleteSelectedNode() {
    if (graphMutating || !selectedNode || !canDeleteSelectedNode) {
      return;
    }
    const confirmed = window.confirm(
      `Delete node "${selectedNode.display_name}"?`,
    );
    if (!confirmed) {
      return;
    }
    setGraphMutating(true);
    setGraphStatus("Deleting node...");
    try {
      const deletedNode = await deleteJson<HierarchyNode>(
        `/api/workspaces/${workspace.workspace_id}/graph/nodes/${selectedNode.node_id}`,
      );
      setNodes((currentNodes) =>
        currentNodes.filter((node) => node.node_id !== deletedNode.node_id),
      );
      setConnections((currentConnections) =>
        currentConnections.filter(
          (connection) =>
            connection.parent_node_id !== deletedNode.node_id &&
            connection.child_node_id !== deletedNode.node_id,
        ),
      );
      setSelectedNodeId(null);
      setGraphStatus("Node deleted.");
      queueGraphRefresh();
    } catch (error) {
      handleApiError(error, setGraphStatus);
    } finally {
      setGraphMutating(false);
    }
  }
  async function handleReparentSelectedNode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (graphMutating || user.role !== "admin" || !selectedNode) {
      return;
    }
    setGraphMutating(true);
    setGraphStatus("Updating parent...");
    try {
      await patchJson<{ parent_node_id: string }, HierarchyNode>(
        `/api/workspaces/${workspace.workspace_id}/graph/nodes/${selectedNode.node_id}`,
        { parent_node_id: reparentNodeId },
      );
      setConnections((currentConnections) => {
        const withoutIncoming = currentConnections.filter(
          (connection) => connection.child_node_id !== selectedNode.node_id,
        );
        if (!reparentNodeId) {
          return withoutIncoming;
        }
        return [
          ...withoutIncoming,
          {
            connection_id: `local-${reparentNodeId}-${selectedNode.node_id}`,
            workspace_id: workspace.workspace_id,
            parent_node_id: reparentNodeId,
            child_node_id: selectedNode.node_id,
            created_by_user_id: user.id,
            created_at: new Date().toISOString(),
          },
        ];
      });
      setGraphStatus("Parent updated.");
      queueGraphRefresh();
    } catch (error) {
      handleApiError(error, setGraphStatus);
    } finally {
      setGraphMutating(false);
    }
  }
  function handleBoardMouseDown(event: MouseEvent<HTMLDivElement>) {
    if (event.button !== 0) {
      return;
    }
    const target = event.target;
    if (target instanceof Element && target.closest(".graph-node")) {
      return;
    }
    setPanState({
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: viewport.x,
      startY: viewport.y,
    });
  }
  function handleNodeClick(
    event: MouseEvent<HTMLButtonElement>,
    node: HierarchyNode,
  ) {
    event.stopPropagation();
    setSelectedNodeId(node.node_id);
    setSidebarTab("details");
  }
  function handleBoardMouseMove(event: MouseEvent<HTMLDivElement>) {
    if (panState) {
      setViewport((currentViewport) => ({
        ...currentViewport,
        x: panState.startX + event.clientX - panState.startClientX,
        y: panState.startY + event.clientY - panState.startClientY,
      }));
    }
  }
  function handleBoardMouseUp() {
    setPanState(null);
  }
  function handleZoom(delta: number) {
    setViewport((currentViewport) => ({
      ...currentViewport,
      scale: clamp(currentViewport.scale + delta, 0.5, 1.6),
    }));
  }

  return {
    panelOpen,
    setPanelOpen,
    sidebarTab,
    setSidebarTab,
    nodes,
    graphMutating,
    graphStatus,
    graphRevision: model.graphRevision,
    selectedNodeId,
    selectedNode,
    availableAssignees: model.availableAssignees,
    parentOptions: model.parentOptions,
    ownNode: model.ownNode,
    canManageSelectedNode,
    editTitle,
    setEditTitle,
    editAssignedUserId,
    setEditAssignedUserId,
    reassignOptions: model.reassignOptions,
    canDeleteSelectedNode,
    reparentNodeId,
    setReparentNodeId,
    reparentOptions: model.reparentOptions,
    visibleNodes: model.visibleNodes,
    edgeSegments: model.edgeSegments,
    viewport,
    boardRef,
    boardSize: model.boardSize,
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
  };
}
