import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchJson } from "../../../api";
import type {
  AuthUser,
  HierarchyAssignableUser,
  HierarchyConnection,
  HierarchyGraphResponse,
  HierarchyNode,
  Workspace,
} from "../../../types";
import type { BoardSize, EdgeSegment, Viewport } from "../../WorkspaceGraphCanvas";
export const NODE_WIDTH = 168;
export const NODE_HEIGHT = 76;
const GRAPH_VIEW_BUFFER = 360;
const GRAPH_LAYOUT_START_X = 80;
const GRAPH_LAYOUT_START_Y = 80;
const GRAPH_LAYOUT_HORIZONTAL_GAP = 220;
const GRAPH_LAYOUT_VERTICAL_GAP = 150;
const GRAPH_LAYOUT_ROOT_GAP = 1.2;

export type PanState = {
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
};

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function computeCenteredViewport(
  nodes: HierarchyNode[],
  boardSize: BoardSize,
  scale = 1,
): Viewport {
  if (boardSize.width <= 0 || boardSize.height <= 0) {
    return { x: 120, y: 80, scale };
  }

  if (!nodes.length) {
    return {
      x: boardSize.width / 2 - (GRAPH_LAYOUT_START_X + NODE_WIDTH / 2) * scale,
      y: boardSize.height / 2 - (GRAPH_LAYOUT_START_Y + NODE_HEIGHT / 2) * scale,
      scale,
    };
  }

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  for (const node of nodes) {
    minX = Math.min(minX, node.x);
    minY = Math.min(minY, node.y);
    maxX = Math.max(maxX, node.x + NODE_WIDTH);
    maxY = Math.max(maxY, node.y + NODE_HEIGHT);
  }

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  return {
    x: boardSize.width / 2 - centerX * scale,
    y: boardSize.height / 2 - centerY * scale,
    scale,
  };
}

export function findParentNodeId(
  nodeId: string | null,
  connections: HierarchyConnection[],
): string {
  if (!nodeId) {
    return "";
  }
  return (
    connections.find((connection) => connection.child_node_id === nodeId)
      ?.parent_node_id ?? ""
  );
}

export function getVisibleNodes(
  nodes: HierarchyNode[],
  viewport: Viewport,
  boardSize: BoardSize,
  selectedNodeId: string | null,
): HierarchyNode[] {
  const width = boardSize.width || 1200;
  const height = boardSize.height || 800;
  const minX = -viewport.x / viewport.scale - GRAPH_VIEW_BUFFER;
  const minY = -viewport.y / viewport.scale - GRAPH_VIEW_BUFFER;
  const maxX = (width - viewport.x) / viewport.scale + GRAPH_VIEW_BUFFER;
  const maxY = (height - viewport.y) / viewport.scale + GRAPH_VIEW_BUFFER;
  return nodes.filter(
    (node) =>
      node.node_id === selectedNodeId ||
      (node.x + NODE_WIDTH >= minX &&
        node.x <= maxX &&
        node.y + NODE_HEIGHT >= minY &&
        node.y <= maxY),
  );
}

export function layoutHierarchyNodes(
  nodes: HierarchyNode[],
  connections: HierarchyConnection[],
): HierarchyNode[] {
  if (!nodes.length) {
    return nodes;
  }
  const nodeIds = new Set(nodes.map((node) => node.node_id));
  const childrenByParent = new Map<string, string[]>();
  const parentByChild = new Map<string, string>();
  for (const connection of connections) {
    if (
      !nodeIds.has(connection.parent_node_id) ||
      !nodeIds.has(connection.child_node_id)
    ) {
      continue;
    }
    childrenByParent.set(connection.parent_node_id, [
      ...(childrenByParent.get(connection.parent_node_id) ?? []),
      connection.child_node_id,
    ]);
    parentByChild.set(connection.child_node_id, connection.parent_node_id);
  }
  const nodeById = new Map(nodes.map((node) => [node.node_id, node]));
  const roots = nodes.filter((node) => !parentByChild.has(node.node_id));
  const subtreeSlots = new Map<string, number>();
  function measureSubtree(nodeId: string): number {
    const cachedSlots = subtreeSlots.get(nodeId);
    if (cachedSlots !== undefined) {
      return cachedSlots;
    }
    const childIds = childrenByParent.get(nodeId) ?? [];
    const slots = Math.max(
      1,
      childIds.reduce((total, childId) => total + measureSubtree(childId), 0),
    );
    subtreeSlots.set(nodeId, slots);
    return slots;
  }
  const positionedNodes = new Map<string, HierarchyNode>();
  function placeSubtree(nodeId: string, leftSlot: number, depth: number) {
    const node = nodeById.get(nodeId);
    if (!node) {
      return;
    }
    const slots = measureSubtree(nodeId);
    const centerSlot = leftSlot + (slots - 1) / 2;
    positionedNodes.set(nodeId, {
      ...node,
      x: GRAPH_LAYOUT_START_X + centerSlot * GRAPH_LAYOUT_HORIZONTAL_GAP,
      y: GRAPH_LAYOUT_START_Y + depth * GRAPH_LAYOUT_VERTICAL_GAP,
    });
    let childLeftSlot = leftSlot;
    for (const childId of childrenByParent.get(nodeId) ?? []) {
      placeSubtree(childId, childLeftSlot, depth + 1);
      childLeftSlot += measureSubtree(childId);
    }
  }
  let nextRootSlot = 0;
  for (const root of roots) {
    placeSubtree(root.node_id, nextRootSlot, 0);
    nextRootSlot += measureSubtree(root.node_id) + GRAPH_LAYOUT_ROOT_GAP;
  }
  return nodes.map((node) => positionedNodes.get(node.node_id) ?? node);
}

export function computeEdgeSegments(
  connections: HierarchyConnection[],
  graphNodeById: Map<string, HierarchyNode>,
  visibleNodeIds: Set<string>,
): EdgeSegment[] {
  return connections
    .filter(
      (connection) =>
        visibleNodeIds.has(connection.parent_node_id) &&
        visibleNodeIds.has(connection.child_node_id),
    )
    .map((connection): EdgeSegment | null => {
      const parent = graphNodeById.get(connection.parent_node_id);
      const child = graphNodeById.get(connection.child_node_id);
      if (!parent || !child) {
        return null;
      }
      const x1 = parent.x + NODE_WIDTH / 2;
      const y1 = parent.y + NODE_HEIGHT;
      const x2 = child.x + NODE_WIDTH / 2;
      const y2 = child.y;
      return {
        connectionId: connection.connection_id,
        x: x1,
        y: y1,
        length: Math.hypot(x2 - x1, y2 - y1),
        angle: Math.atan2(y2 - y1, x2 - x1),
      };
    })
    .filter((segment): segment is EdgeSegment => Boolean(segment));
}



type UseWorkspaceGraphModelArgs = {
  workspace: Workspace;
  user: AuthUser;
  handleApiError: (error: unknown, setMessage?: (message: string) => void) => void;
};

export function useWorkspaceGraphModel({
  workspace,
  user,
  handleApiError,
}: UseWorkspaceGraphModelArgs) {
  const [nodes, setNodes] = useState<HierarchyNode[]>([]);
  const [connections, setConnections] = useState<HierarchyConnection[]>([]);
  const [graphStatus, setGraphStatus] = useState("");
  const [graphMutating, setGraphMutating] = useState(false);
  const [graphRevision, setGraphRevision] = useState(0);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [assignableUsers, setAssignableUsers] = useState<
    HierarchyAssignableUser[]
  >([]);
  const [editTitle, setEditTitle] = useState("");
  const [editAssignedUserId, setEditAssignedUserId] = useState("");
  const [reparentNodeId, setReparentNodeId] = useState("");
  const [viewport, setViewport] = useState<Viewport>({
    x: 120,
    y: 80,
    scale: 1,
  });
  const [boardSize, setBoardSize] = useState<BoardSize>({
    width: 0,
    height: 0,
  });
  const [panState, setPanState] = useState<PanState | null>(null);
  const createNodeInFlightRef = useRef(false);
  const boardRef = useRef<HTMLDivElement | null>(null);
  const queuedGraphRefreshRef = useRef<number | null>(null);
  const shouldCenterViewportRef = useRef(true);
  const [graphLoaded, setGraphLoaded] = useState(false);

  const selectedNode = useMemo(
    () => nodes.find((node) => node.node_id === selectedNodeId) ?? null,
    [nodes, selectedNodeId],
  );
  const graphNodes = useMemo(
    () => layoutHierarchyNodes(nodes, connections),
    [connections, nodes],
  );
  const graphNodeById = useMemo(() => {
    const lookup = new Map<string, HierarchyNode>();
    for (const node of graphNodes) {
      lookup.set(node.node_id, node);
    }
    return lookup;
  }, [graphNodes]);
  const canManageWorkspace = workspace.can_manage;
  const canManageSelectedNode = Boolean(selectedNode && canManageWorkspace);
  const assignedUserIds = useMemo(
    () => new Set(nodes.map((node) => node.assigned_user_id)),
    [nodes],
  );
  const ownNode = useMemo(
    () => nodes.find((node) => node.assigned_user_id === user.id) ?? null,
    [nodes, user.id],
  );
  const availableAssignees = useMemo(
    () =>
      assignableUsers.filter(
        (assignableUser) => !assignedUserIds.has(assignableUser.user_id),
      ),
    [assignableUsers, assignedUserIds],
  );
  const reassignOptions = useMemo(() => {
    const options = new Map<string, HierarchyAssignableUser>();
    for (const assignableUser of assignableUsers) {
      if (
        assignableUser.user_id === selectedNode?.assigned_user_id ||
        !assignedUserIds.has(assignableUser.user_id)
      ) {
        options.set(assignableUser.user_id, assignableUser);
      }
    }
    return Array.from(options.values());
  }, [assignableUsers, assignedUserIds, selectedNode?.assigned_user_id]);
  const parentOptions = useMemo(
    () => (canManageWorkspace ? nodes : ownNode ? [ownNode] : []),
    [canManageWorkspace, nodes, ownNode],
  );
  const reparentOptions = useMemo(
    () =>
      selectedNode
        ? nodes.filter((node) => node.node_id !== selectedNode.node_id)
        : [],
    [nodes, selectedNode],
  );
  const selectedNodeHasChildren = Boolean(
    selectedNode &&
    connections.some(
      (connection) => connection.parent_node_id === selectedNode.node_id,
    ),
  );
  const canDeleteSelectedNode = Boolean(
    selectedNode &&
    (canManageWorkspace ||
      (ownNode &&
        selectedNode.assigned_user_id !== user.id &&
        !selectedNodeHasChildren &&
        connections.some(
          (connection) =>
            connection.parent_node_id === ownNode.node_id &&
            connection.child_node_id === selectedNode.node_id,
        ))),
  );
  const visibleNodes = useMemo(
    () => getVisibleNodes(graphNodes, viewport, boardSize, selectedNodeId),
    [boardSize, graphNodes, selectedNodeId, viewport],
  );
  const visibleNodeIds = useMemo(
    () => new Set(visibleNodes.map((node) => node.node_id)),
    [visibleNodes],
  );
  const edgeSegments = useMemo(
    () => computeEdgeSegments(connections, graphNodeById, visibleNodeIds),
    [connections, graphNodeById, visibleNodeIds],
  );

  const loadGraph = useCallback(async () => {
    try {
      const result = await fetchJson<HierarchyGraphResponse>(
        `/api/workspaces/${workspace.workspace_id}/graph`,
      );
      setNodes(result.nodes || []);
      setConnections(result.connections || []);
      setAssignableUsers(result.assignable_users || []);
      setGraphStatus("");
      setGraphRevision((revision) => revision + 1);
      setGraphLoaded(true);
    } catch (error) {
      handleApiError(error, setGraphStatus);
      setGraphLoaded(true);
    }
  }, [handleApiError, workspace.workspace_id]);

  const centerViewport = useCallback(
    (scale?: number) => {
      setViewport((currentViewport) =>
        computeCenteredViewport(
          graphNodes,
          boardSize,
          scale ?? currentViewport.scale,
        ),
      );
    },
    [boardSize, graphNodes],
  );

  const queueGraphRefresh = useCallback(() => {
    if (queuedGraphRefreshRef.current !== null) {
      window.clearTimeout(queuedGraphRefreshRef.current);
    }
    queuedGraphRefreshRef.current = window.setTimeout(() => {
      queuedGraphRefreshRef.current = null;
      void loadGraph();
    }, 2200);
  }, [loadGraph]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    shouldCenterViewportRef.current = true;
    setGraphLoaded(false);
    setViewport({ x: 120, y: 80, scale: 1 });
  }, [workspace.workspace_id]);

  useEffect(() => {
    if (!shouldCenterViewportRef.current || !graphLoaded) {
      return;
    }
    if (boardSize.width <= 0 || boardSize.height <= 0) {
      return;
    }
    shouldCenterViewportRef.current = false;
    setViewport(computeCenteredViewport(graphNodes, boardSize, 1));
  }, [boardSize, graphLoaded, graphNodes, workspace.workspace_id]);

  useEffect(
    () => () => {
      if (queuedGraphRefreshRef.current !== null) {
        window.clearTimeout(queuedGraphRefreshRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    setEditTitle(selectedNode?.display_name ?? "");
    setEditAssignedUserId(selectedNode?.assigned_user_id ?? "");
    setReparentNodeId(
      findParentNodeId(selectedNode?.node_id ?? null, connections),
    );
  }, [connections, selectedNode]);

  useEffect(() => {
    const board = boardRef.current;
    if (!board) {
      return;
    }
    const updateBoardSize = () => {
      const rect = board.getBoundingClientRect();
      setBoardSize((currentSize) => {
        const nextSize = {
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
        if (
          currentSize.width === nextSize.width &&
          currentSize.height === nextSize.height
        ) {
          return currentSize;
        }
        return nextSize;
      });
    };
    updateBoardSize();
    const resizeObserver = new ResizeObserver(updateBoardSize);
    resizeObserver.observe(board);
    return () => resizeObserver.disconnect();
  }, [graphRevision]);



  return {
    workspace,
    user,
    handleApiError,
    nodes,
    setNodes,
    connections,
    setConnections,
    graphStatus,
    setGraphStatus,
    graphMutating,
    setGraphMutating,
    graphRevision,
    selectedNodeId,
    setSelectedNodeId,
    assignableUsers,
    editTitle,
    setEditTitle,
    editAssignedUserId,
    setEditAssignedUserId,
    reparentNodeId,
    setReparentNodeId,
    viewport,
    setViewport,
    boardSize,
    panState,
    setPanState,
    createNodeInFlightRef,
    boardRef,
    queuedGraphRefreshRef,
    selectedNode,
    graphNodes,
    graphNodeById,
    canManageWorkspace,
    canManageSelectedNode,
    assignedUserIds,
    ownNode,
    availableAssignees,
    reassignOptions,
    parentOptions,
    reparentOptions,
    selectedNodeHasChildren,
    canDeleteSelectedNode,
    visibleNodes,
    edgeSegments,
    loadGraph,
    queueGraphRefresh,
    centerViewport,
  };
}

export type UseWorkspaceGraphModelResult = ReturnType<
  typeof useWorkspaceGraphModel
>;
