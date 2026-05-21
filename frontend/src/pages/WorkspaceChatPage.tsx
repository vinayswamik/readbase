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
  BitbucketConnection,
  BitbucketRepositoriesResponse,
  BitbucketRepository,
  ChatMessage,
  ConfluenceConnection,
  ConfluenceSpace,
  ConfluenceSpacesResponse,
  CreateHierarchyNodeResponse,
  GitlabConnection,
  GitlabProject,
  GitlabProjectsResponse,
  GithubConnection,
  GithubRepositoriesResponse,
  GithubRepository,
  HierarchyAssignableUser,
  HierarchyConnection,
  HierarchyGraphResponse,
  HierarchyNode,
  IndexedRepo,
  IndexResponse,
  JiraConnection,
  JiraProject,
  JiraProjectsResponse,
  LinearConnection,
  LinearSelectableSource,
  LinearSelectableSourcesResponse,
  ReposResponse,
  SlackChannel,
  SlackChannelsResponse,
  SlackConnection,
  SourceMatch,
  Workspace,
  WorkspaceJiraSource,
  WorkspaceJiraSourcesResponse,
  WorkspaceConfluenceSource,
  WorkspaceConfluenceSourcesResponse,
  WorkspaceLinearSource,
  WorkspaceLinearSourcesResponse,
  WorkspaceSlackSource,
  WorkspaceSlackSourcesResponse,
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
const GRAPH_VIEW_BUFFER = 360;
const GRAPH_LAYOUT_START_X = 80;
const GRAPH_LAYOUT_START_Y = 80;
const GRAPH_LAYOUT_HORIZONTAL_GAP = 220;
const GRAPH_LAYOUT_VERTICAL_GAP = 150;
const GRAPH_LAYOUT_ROOT_GAP = 1.2;

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
  const [activeConnectorId, setActiveConnectorId] = useState<ConnectorId | null>(null);
  const [connectorRepoUrl, setConnectorRepoUrl] = useState("");
  const [connectorRefreshRepo, setConnectorRefreshRepo] = useState(false);
  const [connectorMembers, setConnectorMembers] = useState<WorkspaceMember[]>([]);
  const [connectorStatus, setConnectorStatus] = useState("");
  const [connectorError, setConnectorError] = useState<string | null>(null);
  const [connectorMembersLoading, setConnectorMembersLoading] = useState(false);
  const [githubConnection, setGithubConnection] = useState<GithubConnection | null>(null);
  const [githubRepositories, setGithubRepositories] = useState<GithubRepository[]>([]);
  const [githubRepositoryQuery, setGithubRepositoryQuery] = useState("");
  const [githubRepositoriesLoading, setGithubRepositoriesLoading] = useState(false);
  const [bitbucketConnection, setBitbucketConnection] = useState<BitbucketConnection | null>(null);
  const [bitbucketRepositories, setBitbucketRepositories] = useState<BitbucketRepository[]>([]);
  const [bitbucketRepositoryQuery, setBitbucketRepositoryQuery] = useState("");
  const [bitbucketLoading, setBitbucketLoading] = useState(false);
  const [gitlabConnection, setGitlabConnection] = useState<GitlabConnection | null>(null);
  const [gitlabProjects, setGitlabProjects] = useState<GitlabProject[]>([]);
  const [gitlabProjectQuery, setGitlabProjectQuery] = useState("");
  const [gitlabLoading, setGitlabLoading] = useState(false);
  const [jiraConnection, setJiraConnection] = useState<JiraConnection | null>(null);
  const [jiraSources, setJiraSources] = useState<WorkspaceJiraSource[]>([]);
  const [jiraProjects, setJiraProjects] = useState<JiraProject[]>([]);
  const [jiraProjectQuery, setJiraProjectQuery] = useState("");
  const [jiraLoading, setJiraLoading] = useState(false);
  const [slackConnection, setSlackConnection] = useState<SlackConnection | null>(null);
  const [slackSources, setSlackSources] = useState<WorkspaceSlackSource[]>([]);
  const [slackChannels, setSlackChannels] = useState<SlackChannel[]>([]);
  const [slackChannelQuery, setSlackChannelQuery] = useState("");
  const [slackSelectedTeamId, setSlackSelectedTeamId] = useState("");
  const [slackLoading, setSlackLoading] = useState(false);
  const [linearConnection, setLinearConnection] = useState<LinearConnection | null>(null);
  const [linearSources, setLinearSources] = useState<WorkspaceLinearSource[]>([]);
  const [linearSelectableSources, setLinearSelectableSources] = useState<LinearSelectableSource[]>([]);
  const [linearQuery, setLinearQuery] = useState("");
  const [linearLoading, setLinearLoading] = useState(false);
  const [confluenceConnection, setConfluenceConnection] = useState<ConfluenceConnection | null>(null);
  const [confluenceSources, setConfluenceSources] = useState<WorkspaceConfluenceSource[]>([]);
  const [confluenceSpaces, setConfluenceSpaces] = useState<ConfluenceSpace[]>([]);
  const [confluenceQuery, setConfluenceQuery] = useState("");
  const [confluenceLoading, setConfluenceLoading] = useState(false);
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
    () => getVisibleNodes(graphNodes, viewport, boardSize, selectedNodeId),
    [boardSize, graphNodes, selectedNodeId, viewport],
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
        .filter((segment): segment is EdgeSegment => Boolean(segment)),
    [connections, graphNodeById, visibleNodeIds],
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

  const loadConnectorMembers = useCallback(async () => {
    setConnectorMembersLoading(true);
    setConnectorError(null);
    try {
      const result = await fetchJson<WorkspaceMembersResponse>(
        `/api/workspaces/${workspace.workspace_id}/members`,
      );
      setConnectorMembers(result.members || []);
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConnectorMembersLoading(false);
    }
  }, [handleApiError, workspace.workspace_id]);

  const loadGithubConnection = useCallback(async () => {
    try {
      const result = await fetchJson<GithubConnection>("/api/me/integrations/github");
      setGithubConnection(result);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError]);

  const loadGithubRepositories = useCallback(
    async (query = "") => {
      setGithubRepositoriesLoading(true);
      try {
        const params = query.trim() ? `?query=${encodeURIComponent(query.trim())}` : "";
        const result = await fetchJson<GithubRepositoriesResponse>(`/api/me/integrations/github/repos${params}`);
        setGithubRepositories(result.repositories || []);
      } catch (error) {
        handleApiError(error, setConnectorError);
      } finally {
        setGithubRepositoriesLoading(false);
      }
    },
    [handleApiError],
  );

  const loadBitbucketConnection = useCallback(async () => {
    try {
      const result = await fetchJson<BitbucketConnection>("/api/me/integrations/bitbucket");
      setBitbucketConnection(result);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError]);

  const loadBitbucketRepositories = useCallback(
    async (query = "") => {
      setBitbucketLoading(true);
      try {
        const params = query.trim() ? `?query=${encodeURIComponent(query.trim())}` : "";
        const result = await fetchJson<BitbucketRepositoriesResponse>(`/api/me/integrations/bitbucket/repos${params}`);
        setBitbucketRepositories(result.repositories || []);
      } catch (error) {
        handleApiError(error, setConnectorError);
      } finally {
        setBitbucketLoading(false);
      }
    },
    [handleApiError],
  );

  const loadGitlabConnection = useCallback(async () => {
    try {
      const result = await fetchJson<GitlabConnection>("/api/me/integrations/gitlab");
      setGitlabConnection(result);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError]);

  const loadGitlabProjects = useCallback(
    async (query = "") => {
      setGitlabLoading(true);
      try {
        const params = query.trim() ? `?query=${encodeURIComponent(query.trim())}` : "";
        const result = await fetchJson<GitlabProjectsResponse>(`/api/me/integrations/gitlab/projects${params}`);
        setGitlabProjects(result.projects || []);
      } catch (error) {
        handleApiError(error, setConnectorError);
      } finally {
        setGitlabLoading(false);
      }
    },
    [handleApiError],
  );

  const loadJiraConnection = useCallback(async () => {
    try {
      const result = await fetchJson<JiraConnection>("/api/me/integrations/jira");
      setJiraConnection(result);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError]);

  const loadJiraSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceJiraSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/jira/sources`,
      );
      setJiraSources(result.sources || []);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);

  const loadJiraProjects = useCallback(
    async (query = "") => {
      setJiraLoading(true);
      try {
        const params = query.trim() ? `?query=${encodeURIComponent(query.trim())}` : "";
        const result = await fetchJson<JiraProjectsResponse>(
          `/api/workspaces/${workspace.workspace_id}/jira/projects${params}`,
        );
        setJiraProjects(result.projects || []);
      } catch (error) {
        handleApiError(error, setConnectorError);
      } finally {
        setJiraLoading(false);
      }
    },
    [handleApiError, workspace.workspace_id],
  );

  const loadSlackConnection = useCallback(async () => {
    try {
      const result = await fetchJson<SlackConnection>("/api/me/integrations/slack");
      setSlackConnection(result);
      setSlackSelectedTeamId((currentTeamId) => currentTeamId || result.teams?.[0]?.team_id || "");
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError]);

  const loadSlackSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceSlackSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/slack/sources`,
      );
      setSlackSources(result.sources || []);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);

  const loadSlackChannels = useCallback(
    async (teamId: string, query = "") => {
      if (!teamId) {
        setSlackChannels([]);
        return;
      }
      setSlackLoading(true);
      try {
        const params = new URLSearchParams({ team_id: teamId });
        if (query.trim()) {
          params.set("query", query.trim());
        }
        const result = await fetchJson<SlackChannelsResponse>(
          `/api/me/integrations/slack/channels?${params.toString()}`,
        );
        setSlackChannels(result.channels || []);
      } catch (error) {
        handleApiError(error, setConnectorError);
      } finally {
        setSlackLoading(false);
      }
    },
    [handleApiError],
  );

  const loadLinearConnection = useCallback(async () => {
    try {
      const result = await fetchJson<LinearConnection>("/api/me/integrations/linear");
      setLinearConnection(result);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError]);

  const loadLinearSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceLinearSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/linear/sources`,
      );
      setLinearSources(result.sources || []);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);

  const loadLinearSelectableSources = useCallback(
    async (query = "") => {
      setLinearLoading(true);
      try {
        const params = query.trim() ? `?query=${encodeURIComponent(query.trim())}` : "";
        const result = await fetchJson<LinearSelectableSourcesResponse>(`/api/me/integrations/linear/sources${params}`);
        setLinearSelectableSources(result.sources || []);
      } catch (error) {
        handleApiError(error, setConnectorError);
      } finally {
        setLinearLoading(false);
      }
    },
    [handleApiError],
  );

  const loadConfluenceConnection = useCallback(async () => {
    try {
      const result = await fetchJson<ConfluenceConnection>("/api/me/integrations/confluence");
      setConfluenceConnection(result);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError]);

  const loadConfluenceSources = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspaceConfluenceSourcesResponse>(
        `/api/workspaces/${workspace.workspace_id}/confluence/sources`,
      );
      setConfluenceSources(result.sources || []);
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }, [handleApiError, workspace.workspace_id]);

  const loadConfluenceSpaces = useCallback(
    async (query = "") => {
      setConfluenceLoading(true);
      try {
        const params = query.trim() ? `?query=${encodeURIComponent(query.trim())}` : "";
        const result = await fetchJson<ConfluenceSpacesResponse>(`/api/me/integrations/confluence/spaces${params}`);
        setConfluenceSpaces(result.spaces || []);
      } catch (error) {
        handleApiError(error, setConnectorError);
      } finally {
        setConfluenceLoading(false);
      }
    },
    [handleApiError],
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
    void loadRepos();
    void loadGraph();
    void loadGithubConnection();
    void loadBitbucketConnection();
    void loadGitlabConnection();
    void loadJiraConnection();
    void loadJiraSources();
    void loadSlackConnection();
    void loadSlackSources();
    void loadLinearConnection();
    void loadLinearSources();
    void loadConfluenceConnection();
    void loadConfluenceSources();
  }, [loadBitbucketConnection, loadConfluenceConnection, loadConfluenceSources, loadGithubConnection, loadGitlabConnection, loadGraph, loadJiraConnection, loadJiraSources, loadLinearConnection, loadLinearSources, loadRepos, loadSlackConnection, loadSlackSources]);

  useEffect(() => {
    if (activeConnectorId) {
      void loadConnectorMembers();
    }
    if (activeConnectorId === "github") {
      void loadGithubConnection();
      if (githubConnection?.connected) {
        void loadGithubRepositories(githubRepositoryQuery);
      }
    }
    if (activeConnectorId === "bitbucket") {
      void loadBitbucketConnection();
      if (bitbucketConnection?.connected) {
        void loadBitbucketRepositories(bitbucketRepositoryQuery);
      }
    }
    if (activeConnectorId === "gitlab") {
      void loadGitlabConnection();
      if (gitlabConnection?.connected) {
        void loadGitlabProjects(gitlabProjectQuery);
      }
    }
    if (activeConnectorId === "jira") {
      void loadJiraConnection();
      void loadJiraSources();
      if (jiraConnection?.connected) {
        void loadJiraProjects(jiraProjectQuery);
      }
    }
    if (activeConnectorId === "slack") {
      void loadSlackConnection();
      void loadSlackSources();
      if (slackConnection?.connected && slackSelectedTeamId) {
        void loadSlackChannels(slackSelectedTeamId, slackChannelQuery);
      }
    }
    if (activeConnectorId === "linear") {
      void loadLinearConnection();
      void loadLinearSources();
      if (linearConnection?.connected) {
        void loadLinearSelectableSources(linearQuery);
      }
    }
    if (activeConnectorId === "confluence") {
      void loadConfluenceConnection();
      void loadConfluenceSources();
      if (confluenceConnection?.connected) {
        void loadConfluenceSpaces(confluenceQuery);
      }
    }
  }, [activeConnectorId, bitbucketConnection?.connected, bitbucketRepositoryQuery, confluenceConnection?.connected, confluenceQuery, githubConnection?.connected, githubRepositoryQuery, gitlabConnection?.connected, gitlabProjectQuery, jiraConnection?.connected, jiraProjectQuery, linearConnection?.connected, linearQuery, loadBitbucketConnection, loadBitbucketRepositories, loadConfluenceConnection, loadConfluenceSources, loadConfluenceSpaces, loadConnectorMembers, loadGithubConnection, loadGithubRepositories, loadGitlabConnection, loadGitlabProjects, loadJiraConnection, loadJiraProjects, loadJiraSources, loadLinearConnection, loadLinearSelectableSources, loadLinearSources, loadSlackChannels, loadSlackConnection, loadSlackSources, slackChannelQuery, slackConnection?.connected, slackSelectedTeamId]);

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
      const providerName = activeConnector?.name || "provider";
      setConnectorStatus(`Repository indexed. Answers will use it only for users with ${providerName} access.`);
      await loadRepos(result.repo_id);
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setIndexing(false);
    }
  }

  function handleGithubConnect() {
    window.location.assign("/api/me/integrations/github/start");
  }

  function handleBitbucketConnect() {
    window.location.assign("/api/me/integrations/bitbucket/start");
  }

  async function handleBitbucketDisconnect() {
    setBitbucketLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<BitbucketConnection>("/api/me/integrations/bitbucket");
      setBitbucketConnection(result);
      setBitbucketRepositories([]);
      setConnectorStatus("Bitbucket disconnected.");
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setBitbucketLoading(false);
    }
  }

  function handleGitlabConnect() {
    window.location.assign("/api/me/integrations/gitlab/start");
  }

  async function handleGitlabDisconnect() {
    setGitlabLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<GitlabConnection>("/api/me/integrations/gitlab");
      setGitlabConnection(result);
      setGitlabProjects([]);
      setConnectorStatus("GitLab disconnected.");
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setGitlabLoading(false);
    }
  }

  async function handleGithubDisconnect() {
    setIndexing(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<GithubConnection>("/api/me/integrations/github");
      setGithubConnection(result);
      setConnectorStatus("GitHub disconnected.");
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setIndexing(false);
    }
  }

  function handleJiraConnect() {
    window.location.assign("/api/me/integrations/jira/start");
  }

  async function handleJiraDisconnect() {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<JiraConnection>("/api/me/integrations/jira");
      setJiraConnection(result);
      setJiraProjects([]);
      setConnectorStatus("Jira disconnected.");
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setJiraLoading(false);
    }
  }

  async function handleAddJiraProject(project: JiraProject) {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      await postJson<JiraProject, WorkspaceJiraSource>(
        `/api/workspaces/${workspace.workspace_id}/jira/sources`,
        project,
      );
      setConnectorStatus(`${project.project_key} added to this workspace.`);
      await loadJiraSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setJiraLoading(false);
    }
  }

  async function handleSyncJiraSource(sourceId: string) {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceJiraSource>(
        `/api/workspaces/${workspace.workspace_id}/jira/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Jira source synced.");
      await loadJiraSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadJiraSources();
    } finally {
      setJiraLoading(false);
    }
  }

  async function handleRemoveJiraSource(sourceId: string) {
    setJiraLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceJiraSource>(
        `/api/workspaces/${workspace.workspace_id}/jira/sources/${sourceId}`,
      );
      setConnectorStatus("Jira source removed.");
      await loadJiraSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setJiraLoading(false);
    }
  }

  function handleSlackConnect() {
    window.location.assign("/api/me/integrations/slack/start");
  }

  async function handleSlackDisconnect(teamId?: string) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      const params = teamId ? `?team_id=${encodeURIComponent(teamId)}` : "";
      const result = await deleteJson<SlackConnection>(`/api/me/integrations/slack${params}`);
      setSlackConnection(result);
      setSlackChannels([]);
      setSlackSelectedTeamId(result.teams?.[0]?.team_id || "");
      setConnectorStatus("Slack disconnected.");
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }

  async function handleAddSlackChannel(channel: SlackChannel) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      await postJson<SlackChannel, WorkspaceSlackSource>(
        `/api/workspaces/${workspace.workspace_id}/slack/sources`,
        channel,
      );
      setConnectorStatus(`#${channel.channel_name} added to this workspace.`);
      await loadSlackSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }

  async function handleSyncSlackSource(sourceId: string) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceSlackSource>(
        `/api/workspaces/${workspace.workspace_id}/slack/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Slack source synced.");
      await loadSlackSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadSlackSources();
    } finally {
      setSlackLoading(false);
    }
  }

  async function handleRemoveSlackSource(sourceId: string) {
    setSlackLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceSlackSource>(
        `/api/workspaces/${workspace.workspace_id}/slack/sources/${sourceId}`,
      );
      setConnectorStatus("Slack source removed.");
      await loadSlackSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setSlackLoading(false);
    }
  }

  function handleLinearConnect() {
    window.location.assign("/api/me/integrations/linear/start");
  }

  async function handleLinearDisconnect() {
    setLinearLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<LinearConnection>("/api/me/integrations/linear");
      setLinearConnection(result);
      setLinearSelectableSources([]);
      setConnectorStatus("Linear disconnected.");
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setLinearLoading(false);
    }
  }

  async function handleAddLinearSource(source: LinearSelectableSource) {
    setLinearLoading(true);
    setConnectorError(null);
    try {
      await postJson<LinearSelectableSource, WorkspaceLinearSource>(
        `/api/workspaces/${workspace.workspace_id}/linear/sources`,
        source,
      );
      setConnectorStatus(`${source.project_name || source.team_name} added to this workspace.`);
      await loadLinearSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setLinearLoading(false);
    }
  }

  async function handleSyncLinearSource(sourceId: string) {
    setLinearLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceLinearSource>(
        `/api/workspaces/${workspace.workspace_id}/linear/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Linear source synced.");
      await loadLinearSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadLinearSources();
    } finally {
      setLinearLoading(false);
    }
  }

  async function handleRemoveLinearSource(sourceId: string) {
    setLinearLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceLinearSource>(
        `/api/workspaces/${workspace.workspace_id}/linear/sources/${sourceId}`,
      );
      setConnectorStatus("Linear source removed.");
      await loadLinearSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setLinearLoading(false);
    }
  }

  function handleConfluenceConnect() {
    window.location.assign("/api/me/integrations/confluence/start");
  }

  async function handleConfluenceDisconnect() {
    setConfluenceLoading(true);
    setConnectorError(null);
    try {
      const result = await deleteJson<ConfluenceConnection>("/api/me/integrations/confluence");
      setConfluenceConnection(result);
      setConfluenceSpaces([]);
      setConnectorStatus("Confluence disconnected.");
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConfluenceLoading(false);
    }
  }

  async function handleAddConfluenceSpace(space: ConfluenceSpace) {
    setConfluenceLoading(true);
    setConnectorError(null);
    try {
      await postJson<ConfluenceSpace, WorkspaceConfluenceSource>(
        `/api/workspaces/${workspace.workspace_id}/confluence/sources`,
        space,
      );
      setConnectorStatus(`${space.space_key} added to this workspace.`);
      await loadConfluenceSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConfluenceLoading(false);
    }
  }

  async function handleSyncConfluenceSource(sourceId: string) {
    setConfluenceLoading(true);
    setConnectorError(null);
    try {
      await postJson<undefined, WorkspaceConfluenceSource>(
        `/api/workspaces/${workspace.workspace_id}/confluence/sources/${sourceId}/sync`,
      );
      setConnectorStatus("Confluence source synced.");
      await loadConfluenceSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
      await loadConfluenceSources();
    } finally {
      setConfluenceLoading(false);
    }
  }

  async function handleRemoveConfluenceSource(sourceId: string) {
    setConfluenceLoading(true);
    setConnectorError(null);
    try {
      await deleteJson<WorkspaceConfluenceSource>(
        `/api/workspaces/${workspace.workspace_id}/confluence/sources/${sourceId}`,
      );
      setConnectorStatus("Confluence source removed.");
      await loadConfluenceSources();
    } catch (error) {
      handleApiError(error, setConnectorError);
    } finally {
      setConfluenceLoading(false);
    }
  }

  async function handleConnectorManagerToggle(member: WorkspaceMember) {
    setConnectorError(null);
    try {
      const updated = await patchJson<{ connector_manager: boolean }, WorkspaceMember>(
        `/api/workspaces/${workspace.workspace_id}/members/${encodeURIComponent(member.email)}/connector-manager`,
        { connector_manager: !member.connector_manager },
      );
      setConnectorMembers((currentMembers) =>
        currentMembers.map((currentMember) =>
          currentMember.email === updated.email ? updated : currentMember,
        ),
      );
    } catch (error) {
      handleApiError(error, setConnectorError);
    }
  }

  async function handleAskSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
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
        { repo_id?: string; question: string; top_k: number },
        AskResponse
      >(`/api/workspaces/${workspace.workspace_id}/ask`, {
        repo_id: repoId || undefined,
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

  function handleNodeClick(event: MouseEvent<HTMLButtonElement>, node: HierarchyNode) {
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

  const canAsk = Boolean(question.trim() && !asking);
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
        <ConnectorSetupModal
          connector={activeConnector}
          repoUrl={connectorRepoUrl}
          refreshRepo={connectorRefreshRepo}
          members={connectorMembers}
          loadingMembers={connectorMembersLoading}
          indexing={indexing}
          status={connectorStatus}
          error={connectorError}
          githubConnection={githubConnection}
          githubRepositories={githubRepositories}
          githubRepositoryQuery={githubRepositoryQuery}
          githubRepositoriesLoading={githubRepositoriesLoading}
          bitbucketConnection={bitbucketConnection}
          bitbucketRepositories={bitbucketRepositories}
          bitbucketRepositoryQuery={bitbucketRepositoryQuery}
          bitbucketLoading={bitbucketLoading}
          gitlabConnection={gitlabConnection}
          gitlabProjects={gitlabProjects}
          gitlabProjectQuery={gitlabProjectQuery}
          gitlabLoading={gitlabLoading}
          jiraConnection={jiraConnection}
          jiraSources={jiraSources}
          jiraProjects={jiraProjects}
          jiraProjectQuery={jiraProjectQuery}
          jiraLoading={jiraLoading}
          slackConnection={slackConnection}
          slackSources={slackSources}
          slackChannels={slackChannels}
          slackChannelQuery={slackChannelQuery}
          slackSelectedTeamId={slackSelectedTeamId}
          slackLoading={slackLoading}
          linearConnection={linearConnection}
          linearSources={linearSources}
          linearSelectableSources={linearSelectableSources}
          linearQuery={linearQuery}
          linearLoading={linearLoading}
          confluenceConnection={confluenceConnection}
          confluenceSources={confluenceSources}
          confluenceSpaces={confluenceSpaces}
          confluenceQuery={confluenceQuery}
          confluenceLoading={confluenceLoading}
          canManageWorkspace={workspace.can_manage}
          onRepoUrlChange={setConnectorRepoUrl}
          onGithubRepositoryQueryChange={setGithubRepositoryQuery}
          onGithubRepositorySearch={() => loadGithubRepositories(githubRepositoryQuery)}
          onBitbucketRepositoryQueryChange={setBitbucketRepositoryQuery}
          onBitbucketRepositorySearch={() => loadBitbucketRepositories(bitbucketRepositoryQuery)}
          onGitlabProjectQueryChange={setGitlabProjectQuery}
          onGitlabProjectSearch={() => loadGitlabProjects(gitlabProjectQuery)}
          onRefreshRepoChange={setConnectorRefreshRepo}
          onSubmit={handleGithubConnectorSubmit}
          onGithubConnect={handleGithubConnect}
          onGithubDisconnect={handleGithubDisconnect}
          onBitbucketConnect={handleBitbucketConnect}
          onBitbucketDisconnect={handleBitbucketDisconnect}
          onGitlabConnect={handleGitlabConnect}
          onGitlabDisconnect={handleGitlabDisconnect}
          onJiraConnect={handleJiraConnect}
          onJiraDisconnect={handleJiraDisconnect}
          onJiraProjectQueryChange={setJiraProjectQuery}
          onJiraProjectSearch={() => loadJiraProjects(jiraProjectQuery)}
          onAddJiraProject={handleAddJiraProject}
          onSyncJiraSource={handleSyncJiraSource}
          onRemoveJiraSource={handleRemoveJiraSource}
          onSlackConnect={handleSlackConnect}
          onSlackDisconnect={handleSlackDisconnect}
          onSlackTeamChange={setSlackSelectedTeamId}
          onSlackChannelQueryChange={setSlackChannelQuery}
          onSlackChannelSearch={() => loadSlackChannels(slackSelectedTeamId, slackChannelQuery)}
          onAddSlackChannel={handleAddSlackChannel}
          onSyncSlackSource={handleSyncSlackSource}
          onRemoveSlackSource={handleRemoveSlackSource}
          onLinearConnect={handleLinearConnect}
          onLinearDisconnect={handleLinearDisconnect}
          onLinearQueryChange={setLinearQuery}
          onLinearSearch={() => loadLinearSelectableSources(linearQuery)}
          onAddLinearSource={handleAddLinearSource}
          onSyncLinearSource={handleSyncLinearSource}
          onRemoveLinearSource={handleRemoveLinearSource}
          onConfluenceConnect={handleConfluenceConnect}
          onConfluenceDisconnect={handleConfluenceDisconnect}
          onConfluenceQueryChange={setConfluenceQuery}
          onConfluenceSearch={() => loadConfluenceSpaces(confluenceQuery)}
          onAddConfluenceSpace={handleAddConfluenceSpace}
          onSyncConfluenceSource={handleSyncConfluenceSource}
          onRemoveConfluenceSource={handleRemoveConfluenceSource}
          onConnectorManagerToggle={handleConnectorManagerToggle}
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

function layoutHierarchyNodes(
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
    if (!nodeIds.has(connection.parent_node_id) || !nodeIds.has(connection.child_node_id)) {
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

function findParentNodeId(
  nodeId: string | null,
  connections: HierarchyConnection[],
): string {
  if (!nodeId) {
    return "";
  }
  return connections.find((connection) => connection.child_node_id === nodeId)?.parent_node_id ?? "";
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
