import { FormEvent, MouseEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  deleteJson,
  fetchJson,
  getErrorMessage,
  isSessionExpiredMessage,
  patchJson,
  postJson,
} from "../api";
import type {
  AskResponse,
  AuthUser,
  ChatMessage,
  CreateHierarchyNodeResponse,
  HierarchyAssignableUser,
  HierarchyConnection,
  HierarchyGraphResponse,
  HierarchyNode,
  IndexedRepo,
  IndexResponse,
  ReposResponse,
  SourceMatch,
  Workspace,
  WorkspaceConnectorsResponse,
  WorkspaceMember,
  WorkspaceMembersResponse,
} from "../types";
import { WorkspaceChatBox } from "./WorkspaceChatBox";
import {
  WorkspaceGraphCanvas,
  type BoardSize,
  type EdgeSegment,
  type Viewport,
} from "./WorkspaceGraphCanvas";
import {
  CONNECTORS,
  ConnectorSetupModal,
  WorkspaceLeftPanel,
  type ConnectorId,
  type CreateNodeDraft,
  type SidebarTab,
} from "./WorkspaceLeftPanel";

const NODE_WIDTH = 168;
const NODE_HEIGHT = 76;
const DRAG_THRESHOLD_PX = 3;
const GRAPH_VIEW_BUFFER = 360;

type DragState = {
  nodeId: string;
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
  moved: boolean;
};

type PanState = {
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
};

export function WorkspaceChatPage({
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
  const [repoId, setRepoId] = useState<string | null>(null);
  const [repos, setRepos] = useState<IndexedRepo[]>([]);
  const [repoListError, setRepoListError] = useState<string | null>(null);
  const [connectorEnabled, setConnectorEnabled] = useState<Record<ConnectorId, boolean>>({
    jira: false,
    slack: false,
    github: false,
    confluence: false,
    linear: false,
  });
  const [activeConnectorId, setActiveConnectorId] = useState<ConnectorId | null>(null);
  const [connectorRepoUrl, setConnectorRepoUrl] = useState("");
  const [connectorRefreshRepo, setConnectorRefreshRepo] = useState(false);
  const [connectorMembers, setConnectorMembers] = useState<WorkspaceMember[]>([]);
  const [connectorAccessEmails, setConnectorAccessEmails] = useState<string[]>([]);
  const [connectorStatus, setConnectorStatus] = useState("");
  const [connectorError, setConnectorError] = useState<string | null>(null);
  const [connectorMembersLoading, setConnectorMembersLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, setMode] = useState("retrieval");
  const [indexing, setIndexing] = useState(false);
  const [asking, setAsking] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("graph");
  const [chatOpen, setChatOpen] = useState(false);
  const [nodes, setNodes] = useState<HierarchyNode[]>([]);
  const [connections, setConnections] = useState<HierarchyConnection[]>([]);
  const [graphStatus, setGraphStatus] = useState("");
  const [graphMutating, setGraphMutating] = useState(false);
  const [graphRevision, setGraphRevision] = useState(0);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [assignableUsers, setAssignableUsers] = useState<HierarchyAssignableUser[]>([]);
  const [editTitle, setEditTitle] = useState("");
  const [editAssignedUserId, setEditAssignedUserId] = useState("");
  const [reparentNodeId, setReparentNodeId] = useState("");
  const [viewport, setViewport] = useState<Viewport>({ x: 120, y: 80, scale: 1 });
  const [boardSize, setBoardSize] = useState<BoardSize>({ width: 0, height: 0 });
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [panState, setPanState] = useState<PanState | null>(null);
  const createNodeInFlightRef = useRef(false);
  const boardRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const queuedGraphRefreshRef = useRef<number | null>(null);

  const selectedRepo = useMemo(
    () => repos.find((repo) => repo.repo_id === repoId) ?? null,
    [repoId, repos],
  );
  const activeConnector = useMemo(
    () => CONNECTORS.find((connector) => connector.id === activeConnectorId) ?? null,
    [activeConnectorId],
  );
  const selectedNode = useMemo(
    () => nodes.find((node) => node.node_id === selectedNodeId) ?? null,
    [nodes, selectedNodeId],
  );
  const nodeById = useMemo(() => {
    const lookup = new Map<string, HierarchyNode>();
    for (const node of nodes) {
      lookup.set(node.node_id, node);
    }
    return lookup;
  }, [nodes]);
  const canManageSelectedNode = Boolean(
    selectedNode && user.role === "admin",
  );
  const assignedUserIds = useMemo(
    () => new Set(nodes.map((node) => node.assigned_user_id)),
    [nodes],
  );
  const ownNode = useMemo(
    () => nodes.find((node) => node.assigned_user_id === user.id) ?? null,
    [nodes, user.id],
  );
  const availableAssignees = useMemo(
    () => assignableUsers.filter((assignableUser) => !assignedUserIds.has(assignableUser.user_id)),
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
    () => (user.role === "admin" ? nodes : ownNode ? [ownNode] : []),
    [nodes, ownNode, user.role],
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
      connections.some((connection) => connection.parent_node_id === selectedNode.node_id),
  );
  const canDeleteSelectedNode = Boolean(
    selectedNode &&
      (user.role === "admin" ||
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
    () => getVisibleNodes(nodes, viewport, boardSize, selectedNodeId),
    [boardSize, nodes, selectedNodeId, viewport],
  );
  const visibleNodeIds = useMemo(
    () => new Set(visibleNodes.map((node) => node.node_id)),
    [visibleNodes],
  );
  const edgeSegments = useMemo(
    () =>
      connections
        .filter(
          (connection) =>
            visibleNodeIds.has(connection.parent_node_id) &&
            visibleNodeIds.has(connection.child_node_id),
        )
        .map((connection): EdgeSegment | null => {
          const parent = nodeById.get(connection.parent_node_id);
          const child = nodeById.get(connection.child_node_id);
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
        .filter((segment): segment is EdgeSegment => Boolean(segment)),
    [connections, nodeById, visibleNodeIds],
  );

  const handleApiError = useCallback(
    (error: unknown, setMessage?: (message: string) => void) => {
      const message = getErrorMessage(error);
      if (setMessage) {
        setMessage(message);
      }
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    },
    [onSessionExpired],
  );

  const loadRepos = useCallback(
    async (preferredRepoId?: string) => {
      try {
        const result = await fetchJson<ReposResponse>(
          `/api/workspaces/${workspace.workspace_id}/repos`,
        );
        const fetchedRepos = result.repos || [];
        setRepos(fetchedRepos);
        setRepoListError(null);
        setRepoId((currentRepoId) => {
          if (preferredRepoId) {
            return preferredRepoId;
          }
          if (currentRepoId && fetchedRepos.some((repo) => repo.repo_id === currentRepoId)) {
            return currentRepoId;
          }
          return fetchedRepos[0]?.repo_id ?? null;
        });
      } catch (error) {
        handleApiError(error, setRepoListError);
        if (getErrorMessage(error).toLowerCase().includes("workspace not found")) {
          onBack();
        }
      }
    },
    [handleApiError, onBack, workspace.workspace_id],
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
    } catch (error) {
      handleApiError(error, setGraphStatus);
    }
  }, [handleApiError, workspace.workspace_id]);

  const loadConnectorState = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceConnectorsResponse>(
        `/api/workspaces/${workspace.workspace_id}/connectors`,
      );
      setConnectorEnabled(connectorEnabledFromResponse(result));
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);

  const loadConnectorMembers = useCallback(async () => {
    setConnectorMembersLoading(true);
    setConnectorError(null);
    try {
      const result = await fetchJson<WorkspaceMembersResponse>(
        `/api/workspaces/${workspace.workspace_id}/members`,
      );
      const members = result.members || [];
      setConnectorMembers(members);
      setConnectorAccessEmails((currentEmails) => {
        const memberEmails = members.map((member) => member.email);
        if (!currentEmails.length) {
          return memberEmails;
        }
        return currentEmails.filter((email) => memberEmails.includes(email));
      });
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConnectorMembersLoading(false);
    }
  }, [handleApiError, workspace.workspace_id]);

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
    void loadRepos();
    void loadGraph();
    void loadConnectorState();
  }, [loadConnectorState, loadGraph, loadRepos]);

  useEffect(() => {
    if (activeConnectorId) {
      void loadConnectorMembers();
    }
  }, [activeConnectorId, loadConnectorMembers]);

  useEffect(
    () => () => {
      if (queuedGraphRefreshRef.current !== null) {
        window.clearTimeout(queuedGraphRefreshRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, chatOpen]);

  useEffect(() => {
    setEditTitle(selectedNode?.display_name ?? "");
    setEditAssignedUserId(selectedNode?.assigned_user_id ?? "");
    setReparentNodeId(findParentNodeId(selectedNode?.node_id ?? null, connections));
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
        if (currentSize.width === nextSize.width && currentSize.height === nextSize.height) {
          return currentSize;
        }
        return nextSize;
      });
    };
    updateBoardSize();

    const resizeObserver = new ResizeObserver(updateBoardSize);
    resizeObserver.observe(board);
    return () => resizeObserver.disconnect();
  }, [graphRevision, panelOpen]);

  function openConnectorModal(connectorId: ConnectorId) {
    if (!connectorEnabled[connectorId]) {
      return;
    }
    setActiveConnectorId(connectorId);
    setConnectorStatus("");
    setConnectorError(null);
    if (connectorId === "github" && !connectorRepoUrl) {
      setConnectorRepoUrl(selectedRepo?.repo_url || "");
    }
  }

  function closeConnectorModal() {
    setActiveConnectorId(null);
    setConnectorStatus("");
    setConnectorError(null);
  }

  async function handleConnectorToggle(connectorId: ConnectorId) {
    const nextEnabled = !connectorEnabled[connectorId];
    setConnectorEnabled((currentEnabled) => ({
      ...currentEnabled,
      [connectorId]: nextEnabled,
    }));
    if (!nextEnabled && activeConnectorId === connectorId) {
      closeConnectorModal();
    }
    try {
      const result = await patchJson<
        { enabled: boolean },
        { connector_id: string; enabled: boolean }
      >(`/api/workspaces/${workspace.workspace_id}/connectors/${connectorId}`, {
        enabled: nextEnabled,
      });
      setConnectorEnabled((currentEnabled) => ({
        ...currentEnabled,
        [connectorId]: result.enabled,
      }));
    } catch (error) {
      setConnectorEnabled((currentEnabled) => ({
        ...currentEnabled,
        [connectorId]: !nextEnabled,
      }));
      handleApiError(error, setConnectorError);
    }
  }

  function handleConnectorAccessToggle(email: string) {
    setConnectorAccessEmails((currentEmails) =>
      currentEmails.includes(email)
        ? currentEmails.filter((currentEmail) => currentEmail !== email)
        : [...currentEmails, email],
    );
  }

  async function handleGithubConnectorSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedUrl = connectorRepoUrl.trim();
    if (!trimmedUrl) {
      return;
    }

    setIndexing(true);
    setConnectorStatus("Cloning and indexing repository. This can take a minute.");
    setConnectorError(null);

    try {
      const result = await postJson<
        { repo_url: string; refresh: boolean },
        IndexResponse
      >(`/api/workspaces/${workspace.workspace_id}/index`, {
        repo_url: trimmedUrl,
        refresh: connectorRefreshRepo,
      });
      setRepoId(result.repo_id);
      setConnectorStatus(
        `Repository indexed. ${connectorAccessEmails.length} workspace member${
          connectorAccessEmails.length === 1 ? "" : "s"
        } selected for access.`,
      );
      await loadRepos(result.repo_id);
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setIndexing(false);
    }
  }

  async function handleAskSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || !repoId) {
      return;
    }

    setChatOpen(true);
    setMessages((currentMessages) => [
      ...currentMessages,
      createMessage("user", trimmedQuestion),
    ]);
    setQuestion("");
    setAsking(true);

    try {
      const result = await postJson<
        { repo_id: string; question: string; top_k: number },
        AskResponse
      >(`/api/workspaces/${workspace.workspace_id}/ask`, {
        repo_id: repoId,
        question: trimmedQuestion,
        top_k: 8,
      });
      setMode(result.mode);
      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage("assistant", result.answer, result.sources, result.mode),
      ]);
    } catch (error) {
      handleApiError(error, (message) => {
        setMessages((currentMessages) => [
          ...currentMessages,
          createMessage("assistant", message),
        ]);
      });
    } finally {
      setAsking(false);
    }
  }

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

    const position = getNextNodePosition(nodes, connections, Boolean(resolvedParentId), resolvedParentId);
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
        x: position.x,
        y: position.y,
        parent_node_id: resolvedParentId || undefined,
      });
      setNodes((currentNodes) => [...currentNodes, result.node]);
      const createdConnection = result.connection;
      if (createdConnection) {
        setConnections((currentConnections) => [...currentConnections, createdConnection]);
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
      const updatedNode = await patchJson<{ display_name: string; assigned_user_id: string }, HierarchyNode>(
        `/api/workspaces/${workspace.workspace_id}/graph/nodes/${selectedNode.node_id}`,
        { display_name: editTitle.trim(), assigned_user_id: editAssignedUserId },
      );
      setNodes((currentNodes) =>
        currentNodes.map((node) => (node.node_id === updatedNode.node_id ? updatedNode : node)),
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
    const confirmed = window.confirm(`Delete node "${selectedNode.display_name}"?`);
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

  async function persistNodePosition(nodeId: string, x: number, y: number) {
    try {
      const updatedNode = await patchJson<{ x: number; y: number }, HierarchyNode>(
        `/api/workspaces/${workspace.workspace_id}/graph/nodes/${nodeId}`,
        { x, y },
      );
      setNodes((currentNodes) =>
        currentNodes.map((node) => (node.node_id === updatedNode.node_id ? updatedNode : node)),
      );
    } catch (error) {
      handleApiError(error, setGraphStatus);
      void loadGraph();
    }
  }

  function handleRepoSelect(repo: IndexedRepo) {
    setRepoId(repo.repo_id);
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

  function handleNodeMouseDown(event: MouseEvent<HTMLButtonElement>, node: HierarchyNode) {
    event.stopPropagation();
    setSelectedNodeId(node.node_id);
    setSidebarTab("details");
    setDragState({
      nodeId: node.node_id,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: node.x,
      startY: node.y,
      moved: false,
    });
  }

  function handleBoardMouseMove(event: MouseEvent<HTMLDivElement>) {
    if (dragState) {
      const deltaX = event.clientX - dragState.startClientX;
      const deltaY = event.clientY - dragState.startClientY;
      const moved = dragState.moved || Math.hypot(deltaX, deltaY) >= DRAG_THRESHOLD_PX;
      if (!moved) {
        return;
      }
      const nextX = dragState.startX + deltaX / viewport.scale;
      const nextY = dragState.startY + deltaY / viewport.scale;
      if (!dragState.moved) {
        setDragState({ ...dragState, moved: true });
      }
      setNodes((currentNodes) =>
        currentNodes.map((node) =>
          node.node_id === dragState.nodeId ? { ...node, x: nextX, y: nextY } : node,
        ),
      );
      return;
    }
    if (panState) {
      setViewport((currentViewport) => ({
        ...currentViewport,
        x: panState.startX + event.clientX - panState.startClientX,
        y: panState.startY + event.clientY - panState.startClientY,
      }));
    }
  }

  function handleBoardMouseUp(event: MouseEvent<HTMLDivElement>) {
    if (dragState?.moved) {
      const nextX = dragState.startX + (event.clientX - dragState.startClientX) / viewport.scale;
      const nextY = dragState.startY + (event.clientY - dragState.startClientY) / viewport.scale;
      void persistNodePosition(dragState.nodeId, nextX, nextY);
    }
    setDragState(null);
    setPanState(null);
  }

  function handleZoom(delta: number) {
    setViewport((currentViewport) => ({
      ...currentViewport,
      scale: clamp(currentViewport.scale + delta, 0.5, 1.6),
    }));
  }

  const canAsk = Boolean(repoId && question.trim() && !asking);
  return (
    <section className={`graph-workspace${panelOpen ? " panel-open" : " panel-closed"}`}>
      <WorkspaceLeftPanel
        workspace={workspace}
        mode={mode}
        sidebarTab={sidebarTab}
        userRole={user.role}
        repos={repos}
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
        connectorEnabled={connectorEnabled}
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
        onToggleConnector={handleConnectorToggle}
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
        onNodeMouseDown={handleNodeMouseDown}
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
        <ConnectorSetupModal
          connector={activeConnector}
          repoUrl={connectorRepoUrl}
          refreshRepo={connectorRefreshRepo}
          members={connectorMembers}
          accessEmails={connectorAccessEmails}
          loadingMembers={connectorMembersLoading}
          indexing={indexing}
          status={connectorStatus}
          error={connectorError}
          onRepoUrlChange={setConnectorRepoUrl}
          onRefreshRepoChange={setConnectorRefreshRepo}
          onAccessToggle={handleConnectorAccessToggle}
          onSubmit={handleGithubConnectorSubmit}
          onClose={closeConnectorModal}
        />
      ) : null}
    </section>
  );
}

function createMessage(
  role: ChatMessage["role"],
  text: string,
  sources?: SourceMatch[],
  mode?: string,
): ChatMessage {
  return {
    id:
      typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    sources,
    mode,
  };
}

function getNextNodePosition(
  nodes: HierarchyNode[],
  connections: HierarchyConnection[],
  hasParent: boolean,
  parentNodeId: string,
): { x: number; y: number } {
  if (!hasParent) {
    const rootCount = nodes.filter(
      (node) => !connections.some((connection) => connection.child_node_id === node.node_id),
    ).length;
    return { x: 80 + rootCount * 240, y: 80 };
  }

  const parent = nodes.find((node) => node.node_id === parentNodeId);
  if (!parent) {
    return { x: 80, y: 220 };
  }
  const siblingCount = connections.filter(
    (connection) => connection.parent_node_id === parentNodeId,
  ).length;
  return {
    x: parent.x + (siblingCount % 5) * 210 - 210,
    y: parent.y + 150 + Math.floor(siblingCount / 5) * 120,
  };
}

function getVisibleNodes(
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

function findParentNodeId(
  nodeId: string | null,
  connections: HierarchyConnection[],
): string {
  if (!nodeId) {
    return "";
  }
  return connections.find((connection) => connection.child_node_id === nodeId)?.parent_node_id ?? "";
}

function connectorEnabledFromResponse(
  response: WorkspaceConnectorsResponse,
): Record<ConnectorId, boolean> {
  const enabled = CONNECTORS.reduce(
    (currentEnabled, connector) => ({
      ...currentEnabled,
      [connector.id]: false,
    }),
    {} as Record<ConnectorId, boolean>,
  );
  for (const connector of response.connectors || []) {
    if (connector.connector_id in enabled) {
      enabled[connector.connector_id as ConnectorId] = Boolean(connector.enabled);
    }
  }
  return enabled;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
