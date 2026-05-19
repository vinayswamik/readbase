import { FormEvent, MouseEvent, memo, useCallback, useEffect, useMemo, useRef, useState } from "react";

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
} from "../types";

const NODE_WIDTH = 168;
const NODE_HEIGHT = 76;
const DRAG_THRESHOLD_PX = 3;
const GRAPH_VIEW_BUFFER = 360;
const MAX_PICKER_RESULTS = 20;

type Viewport = {
  x: number;
  y: number;
  scale: number;
};

type BoardSize = {
  width: number;
  height: number;
};

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

type EdgeSegment = {
  connectionId: string;
  x: number;
  y: number;
  length: number;
  angle: number;
};

type SidebarTab = "repository" | "graph" | "details";

type CreateNodeDraft = {
  displayName: string;
  assignedUserId: string;
  parentNodeId: string;
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
  const [repoUrl, setRepoUrl] = useState("");
  const [refreshRepo, setRefreshRepo] = useState(false);
  const [repoStatus, setRepoStatus] = useState("No repository indexed in this workspace.");
  const [repoListError, setRepoListError] = useState<string | null>(null);
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
  }, [loadGraph, loadRepos]);

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

  async function handleIndexSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedUrl = repoUrl.trim();
    if (!trimmedUrl) {
      return;
    }

    setIndexing(true);
    setRepoStatus("Cloning and indexing repository. This can take a minute.");

    try {
      const result = await postJson<
        { repo_url: string; refresh: boolean },
        IndexResponse
      >(`/api/workspaces/${workspace.workspace_id}/index`, {
        repo_url: trimmedUrl,
        refresh: refreshRepo,
      });
      setRepoId(result.repo_id);
      setRepoStatus(formatRepoStatus(result));
      await loadRepos(result.repo_id);
    } catch (error) {
      handleApiError(error, setRepoStatus);
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
    setRepoUrl(repo.repo_url);
    setRepoStatus(formatRepoStatus(repo));
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

  function handleBoardWheel(event: MouseEvent<HTMLDivElement>) {
    event.preventDefault();
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

        <div className="sidebar-summary" aria-label="Graph summary">
          <div>
            <span>Nodes</span>
            <strong>{nodes.length}</strong>
          </div>
          <div>
            <span>Links</span>
            <strong>{connections.length}</strong>
          </div>
          <div>
            <span>Repos</span>
            <strong>{repos.length}</strong>
          </div>
        </div>

        <div className="control-tabs" role="tablist" aria-label="Workspace control sections">
          <button
            type="button"
            role="tab"
            aria-selected={sidebarTab === "graph"}
            className={sidebarTab === "graph" ? "active" : ""}
            onClick={() => setSidebarTab("graph")}
          >
            Graph
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={sidebarTab === "details"}
            className={sidebarTab === "details" ? "active" : ""}
            onClick={() => setSidebarTab("details")}
          >
            Details
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={sidebarTab === "repository"}
            className={sidebarTab === "repository" ? "active" : ""}
            onClick={() => setSidebarTab("repository")}
          >
            Repos
          </button>
        </div>

        {sidebarTab === "repository" ? (
          <div className="tab-panel" role="tabpanel">
            <section className="tool-section" aria-labelledby="repository-heading">
              <div className="tool-section-header">
                <div>
                  <h2 id="repository-heading">Repository Index</h2>
                  <p>Connect source code for Q&amp;A.</p>
                </div>
              </div>
              <form className="index-form" onSubmit={handleIndexSubmit}>
                <label htmlFor="repoUrl">GitHub URL</label>
                <input
                  id="repoUrl"
                  name="repoUrl"
                  type="url"
                  value={repoUrl}
                  placeholder="https://github.com/owner/repo"
                  required
                  onChange={(event) => setRepoUrl(event.target.value)}
                />
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={refreshRepo}
                    onChange={(event) => setRefreshRepo(event.target.checked)}
                  />
                  <span>Re-clone existing index</span>
                </label>
                <button type="submit" disabled={indexing} className="primary-button">
                  {indexing ? "Indexing..." : "Index repository"}
                </button>
              </form>
              <div className="status-text" aria-live="polite">
                {repoStatus}
              </div>
            </section>

            <section className="tool-section" aria-labelledby="indexed-repos-heading">
              <div className="tool-section-header">
                <div>
                  <h2 id="indexed-repos-heading">Indexed Repos</h2>
                  <p>Select context for the ask widget.</p>
                </div>
              </div>
              <RepoList
                repos={repos}
                selectedRepoId={repoId}
                error={repoListError}
                onSelect={handleRepoSelect}
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
                userRole={user.role}
                disabled={graphMutating}
                availableAssignees={availableAssignees}
                parentOptions={parentOptions}
                ownNode={ownNode}
                onCreate={handleCreateNode}
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
                <form className="graph-control-form" onSubmit={handleUpdateSelectedNode}>
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
                    onChange={(event) => setEditTitle(event.target.value)}
                  />
                  <label id="editAssignedUserLabel">Assigned user</label>
                  <AssignableUserPicker
                    value={editAssignedUserId}
                    disabled={graphMutating || !canManageSelectedNode}
                    availableAssignees={reassignOptions}
                    labelId="editAssignedUserLabel"
                    emptyLabel="No assignee selected"
                    searchPlaceholder="Search assignable users"
                    onChange={setEditAssignedUserId}
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
                    onClick={handleDeleteSelectedNode}
                  >
                    Delete node
                  </button>
                </form>
              ) : (
                <div className="empty-panel-state">Select a node on the board to view details.</div>
              )}
            </section>
            {selectedNode && user.role === "admin" ? (
              <section className="tool-section" aria-labelledby="node-parent-heading">
                <div className="tool-section-header">
                  <div>
                    <h2 id="node-parent-heading">Parent</h2>
                    <p>Move this node under another node or make it top-level.</p>
                  </div>
                </div>
                <form className="graph-control-form" onSubmit={handleReparentSelectedNode}>
                  <label id="reparentNodeLabel">Parent node</label>
                  <ParentNodeSelect
                    value={reparentNodeId}
                    disabled={graphMutating}
                    userRole={user.role}
                    parentOptions={reparentOptions}
                    labelId="reparentNodeLabel"
                    onChange={setReparentNodeId}
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

      <section className="graph-stage" aria-label="Hierarchy graph board">
        <button
          type="button"
          className="panel-toggle"
          aria-expanded={panelOpen}
          onClick={() => setPanelOpen((open) => !open)}
        >
          {panelOpen ? "Hide panel" : "Show panel"}
        </button>
        <div className="graph-toolbar" aria-label="Board controls">
          <button type="button" onClick={() => handleZoom(0.1)}>
            +
          </button>
          <button type="button" onClick={() => handleZoom(-0.1)}>
            -
          </button>
          <button type="button" onClick={() => setViewport({ x: 120, y: 80, scale: 1 })}>
            Reset
          </button>
        </div>
        <div
          ref={boardRef}
          key={graphRevision}
          className="graph-board"
          onMouseDown={handleBoardMouseDown}
          onMouseMove={handleBoardMouseMove}
          onMouseUp={handleBoardMouseUp}
          onMouseLeave={handleBoardMouseUp}
          onWheel={(event) => {
            event.preventDefault();
            handleZoom(event.deltaY > 0 ? -0.08 : 0.08);
          }}
          onContextMenu={(event) => event.preventDefault()}
        >
          {!nodes.length ? (
            <div className="graph-empty">
              {user.role === "admin"
                ? "Create a parent node from the panel to start the hierarchy."
                : "The board is empty. Wait for an admin to create a parent node."}
            </div>
          ) : null}
          <div
            className="graph-canvas"
            style={{
              transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`,
            }}
          >
            <div className="graph-edges">
              {edgeSegments.map((edge) => (
                <GraphEdge key={edge.connectionId} edge={edge} />
              ))}
            </div>
            {visibleNodes.map((node) => (
              <button
                key={node.node_id}
                type="button"
                className={`graph-node${node.node_id === selectedNodeId ? " selected" : ""}`}
                style={{ left: node.x, top: node.y }}
                onMouseDown={(event) => handleNodeMouseDown(event, node)}
              >
                <strong>{node.display_name}</strong>
                <span>{node.assigned_user_name || node.assigned_user_email || "Assigned user"}</span>
              </button>
            ))}
          </div>
        </div>
        {chatOpen ? (
          <ChatOverlay
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
        ) : (
          <button type="button" className="floating-ask-button" onClick={() => setChatOpen(true)}>
            Ask
            {messages.length ? <span>{messages.length}</span> : null}
          </button>
        )}
      </section>
    </section>
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

function ConnectionList({
  connections,
  nodeById,
  user,
  disabled,
  onDelete,
}: {
  connections: HierarchyConnection[];
  nodeById: Map<string, HierarchyNode>;
  user: AuthUser;
  disabled: boolean;
  onDelete: (connection: HierarchyConnection) => void;
}) {
  if (!connections.length) {
    return <div className="status-text">No connections yet.</div>;
  }

  return (
    <div className="connection-list">
      {connections.map((connection) => {
        const parent = nodeById.get(connection.parent_node_id);
        const child = nodeById.get(connection.child_node_id);
        const canDelete = Boolean(child && user.role === "admin");
        return (
          <div className="connection-row" key={connection.connection_id}>
            <span>
              {parent?.display_name || "Missing parent"} {"->"} {child?.display_name || "Missing child"}
            </span>
            <button
              type="button"
              className="danger-button"
              disabled={disabled || !canDelete}
              onClick={() => onDelete(connection)}
            >
              Remove
            </button>
          </div>
        );
      })}
    </div>
  );
}

function GraphEdge({ edge }: { edge: EdgeSegment }) {
  return (
    <div
      className="graph-edge"
      style={{
        left: edge.x,
        top: edge.y,
        width: edge.length,
        transform: `rotate(${edge.angle}rad)`,
      }}
    />
  );
}

function ChatOverlay({
  messages,
  question,
  asking,
  canAsk,
  selectedRepo,
  messageEndRef,
  onQuestionChange,
  onSubmit,
  onClose,
}: {
  messages: ChatMessage[];
  question: string;
  asking: boolean;
  canAsk: boolean;
  selectedRepo: IndexedRepo | null;
  messageEndRef: React.RefObject<HTMLDivElement | null>;
  onQuestionChange: (question: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
}) {
  return (
    <section className="chat-overlay" aria-label="Ask workspace">
      <header className="chat-overlay-header">
        <div>
          <h2>Ask</h2>
          <p>{selectedRepo ? repoLabel(selectedRepo) : "Select a repository first"}</p>
        </div>
        <button type="button" className="secondary-action-button" onClick={onClose}>
          Close
        </button>
      </header>
      <div className="overlay-messages">
        {messages.length ? (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        ) : (
          <article className="message assistant">
            <div className="message-body empty-message">No questions yet.</div>
          </article>
        )}
        <div ref={messageEndRef} />
      </div>
      <form className="ask-form overlay-ask-form" onSubmit={onSubmit}>
        <textarea
          rows={2}
          value={question}
          placeholder={selectedRepo ? `Ask about ${repoLabel(selectedRepo)}` : "Select a repository first"}
          required
          onChange={(event) => onQuestionChange(event.target.value)}
        />
        <button type="submit" disabled={!canAsk} className="primary-button">
          {asking ? "Thinking..." : "Ask"}
        </button>
      </form>
    </section>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="message-body">
        {message.text}
        <SourceList sources={message.sources || []} mode={message.mode || "retrieval"} />
      </div>
    </article>
  );
}

function SourceList({ sources, mode }: { sources: SourceMatch[]; mode: string }) {
  if (!sources.length) {
    return null;
  }

  return (
    <div className="sources">
      {sources.slice(0, 4).map((source) => (
        <div
          key={source.id}
          className={`source${mode === "anthropic" ? " compact" : ""}`}
        >
          <div className="source-title">
            {source.path}:{source.start_line}-{source.end_line} · score{" "}
            {formatScore(source.score)}
          </div>
          {mode !== "anthropic" ? <pre>{source.text}</pre> : null}
        </div>
      ))}
    </div>
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

function formatRepoStatus(repo: IndexedRepo): string {
  return `${repo.file_count} files indexed into ${repo.chunk_count} chunks.`;
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

function repoLabel(repo: IndexedRepo): string {
  return repo.repo_url.replace(/^https?:\/\/github\.com\//, "");
}

function formatScore(score: number): string {
  return Number.isFinite(score) ? score.toFixed(3) : String(score);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
