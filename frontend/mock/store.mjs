import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function clone(value) {
  return structuredClone(value);
}

function loadFixtures() {
  const raw = readFileSync(path.join(__dirname, "fixtures.json"), "utf8");
  return JSON.parse(raw);
}

function createId(prefix) {
  return `${prefix}-${Date.now().toString(36)}`;
}

function nowIso() {
  return new Date().toISOString();
}

export function createMockStore() {
  const seed = loadFixtures();
  const state = {
    user: clone(seed.user),
    authenticated: seed.authenticated,
    workspaces: clone(seed.workspaces),
    invites: clone(seed.invites),
    linkInvites: clone(seed.linkInvites),
    graphs: clone(seed.graphs),
    repos: clone(seed.repos),
    connectors: clone(seed.connectors),
    workspaceSources: clone(seed.workspaceSources),
    emptyLists: clone(seed.emptyLists),
  };

  function sessionResponse() {
    return {
      authenticated: state.authenticated,
      user: state.authenticated ? state.user : null,
    };
  }

  function getGraph(workspaceId) {
    if (!state.graphs[workspaceId]) {
      state.graphs[workspaceId] = {
        nodes: [],
        connections: [],
        assignable_users: state.authenticated ? [state.user].map((user) => ({
          user_id: user.id,
          email: user.email,
          name: user.name,
        })) : [],
      };
    }
    return state.graphs[workspaceId];
  }

  function findWorkspace(workspaceId) {
    return state.workspaces.find((workspace) => workspace.workspace_id === workspaceId) ?? null;
  }

  function findInvite(inviteId) {
    const received = state.invites.received.find((invite) => invite.invite_id === inviteId);
    if (received) {
      return { invite: received, bucket: "received" };
    }
    const sent = state.invites.sent.find((invite) => invite.invite_id === inviteId);
    if (sent) {
      return { invite: sent, bucket: "sent" };
    }
    return null;
  }

  return {
    sessionResponse,
    mockLogin() {
      state.authenticated = true;
      return sessionResponse();
    },
    logout() {
      state.authenticated = false;
      return sessionResponse();
    },
    listWorkspaces() {
      return { workspaces: state.workspaces };
    },
    createWorkspace(name) {
      const workspace = {
        workspace_id: createId("ws"),
        owner_user_id: state.user.id,
        name,
        created_at: nowIso(),
        can_manage: true,
      };
      state.workspaces.unshift(workspace);
      return workspace;
    },
    deleteWorkspace(workspaceId) {
      const index = state.workspaces.findIndex((workspace) => workspace.workspace_id === workspaceId);
      if (index === -1) {
        return null;
      }
      const [removed] = state.workspaces.splice(index, 1);
      return removed;
    },
    leaveWorkspace(workspaceId) {
      return deleteWorkspace(workspaceId);
    },
    listInvites() {
      return {
        received: state.invites.received,
        sent: state.invites.sent,
      };
    },
    previewLinkInvite(joinToken) {
      return state.linkInvites[joinToken] ?? null;
    },
    updateInviteStatus(inviteId, status) {
      const found = findInvite(inviteId);
      if (!found) {
        return null;
      }
      found.invite.status = status;
      if (status === "accepted") {
        found.invite.can_accept = false;
        found.invite.can_reject = false;
        found.invite.can_revert = false;
      }
      if (status === "rejected") {
        found.invite.can_accept = false;
        found.invite.can_reject = false;
        found.invite.can_revert = true;
      }
      if (status === "pending") {
        found.invite.can_accept = found.invite.direction === "received";
        found.invite.can_reject = found.invite.direction === "received";
        found.invite.can_revert = found.invite.direction === "sent";
      }
      return found.invite;
    },
    getGraph(workspaceId) {
      return getGraph(workspaceId);
    },
    createGraphNode(workspaceId, body) {
      const graph = getGraph(workspaceId);
      const nodeId = createId("node");
      const timestamp = nowIso();
      const node = {
        node_id: nodeId,
        workspace_id: workspaceId,
        display_name: body.display_name,
        assigned_user_id: state.user.id,
        assigned_user_email: state.user.email,
        assigned_user_name: state.user.name,
        x: body.x ?? 0,
        y: body.y ?? 0,
        created_by_user_id: state.user.id,
        created_at: timestamp,
        updated_at: timestamp,
      };
      graph.nodes.push(node);

      let connection = null;
      if (body.parent_node_id) {
        connection = {
          connection_id: createId("conn"),
          workspace_id: workspaceId,
          parent_node_id: body.parent_node_id,
          child_node_id: nodeId,
          created_at: timestamp,
        };
        graph.connections.push(connection);
      }

      let invite = null;
      if (body.invitee_email || body.invite_method === "link") {
        const inviteId = createId("inv");
        const joinToken = body.invite_method === "link" ? createId("join") : null;
        invite = {
          invite_id: inviteId,
          workspace_id: workspaceId,
          workspace_name: findWorkspace(workspaceId)?.name ?? "Workspace",
          direction: "sent",
          invitee_email: body.invitee_email ?? "",
          invitee_name: body.invitee_email?.split("@")[0] ?? "",
          invitee_user_id: null,
          invitor_user_id: state.user.id,
          invitor_name: state.user.name,
          invitor_designation: body.invitor_designation ?? "",
          relation: body.relation ?? "",
          reason: body.reason ?? "",
          node_display_name: body.display_name,
          node_id: nodeId,
          status: "pending",
          can_accept: false,
          can_reject: false,
          can_revert: true,
          invite_method: body.invite_method ?? "email",
          join_token: joinToken,
          join_path: joinToken ? `/join/${joinToken}` : null,
          created_at: timestamp,
        };
        state.invites.sent.unshift(invite);
        if (joinToken) {
          state.linkInvites[joinToken] = invite;
        }
      }

      return { node, connection, invite };
    },
    updateGraphNode(workspaceId, nodeId, body) {
      const graph = getGraph(workspaceId);
      const node = graph.nodes.find((entry) => entry.node_id === nodeId);
      if (!node) {
        return null;
      }
      if (typeof body.display_name === "string") {
        node.display_name = body.display_name;
      }
      if (typeof body.assigned_user_id === "string") {
        node.assigned_user_id = body.assigned_user_id;
      }
      if (typeof body.x === "number") {
        node.x = body.x;
      }
      if (typeof body.y === "number") {
        node.y = body.y;
      }
      node.updated_at = nowIso();
      return node;
    },
    deleteGraphNode(workspaceId, nodeId) {
      const graph = getGraph(workspaceId);
      const index = graph.nodes.findIndex((entry) => entry.node_id === nodeId);
      if (index === -1) {
        return null;
      }
      const [removed] = graph.nodes.splice(index, 1);
      graph.connections = graph.connections.filter(
        (connection) => connection.parent_node_id !== nodeId && connection.child_node_id !== nodeId,
      );
      return removed;
    },
    createGraphConnection(workspaceId, body) {
      const graph = getGraph(workspaceId);
      const connection = {
        connection_id: createId("conn"),
        workspace_id: workspaceId,
        parent_node_id: body.parent_node_id,
        child_node_id: body.child_node_id,
        created_at: nowIso(),
      };
      graph.connections.push(connection);
      return connection;
    },
    deleteGraphConnection(workspaceId, connectionId) {
      const graph = getGraph(workspaceId);
      const index = graph.connections.findIndex((connection) => connection.connection_id === connectionId);
      if (index === -1) {
        return null;
      }
      const [removed] = graph.connections.splice(index, 1);
      return removed;
    },
    listRepos(workspaceId) {
      return state.repos[workspaceId] ?? { repos: [] };
    },
    ask(workspaceId, body) {
      const repos = state.repos[workspaceId]?.repos ?? [];
      const repo = repos[0] ?? null;
      return {
        repo_id: body.repo_id ?? repo?.repo_id ?? null,
        workspace_id: workspaceId,
        question: body.question ?? "",
        answer:
          "This is a mock answer for UI prototyping. Connect the real backend when you are ready to test retrieval.",
        sources: repo
          ? [
              {
                repo_id: repo.repo_id,
                repo_url: repo.repo_url,
                path: "src/main.ts",
                start_line: 1,
                end_line: 12,
                snippet: "export function main() {\n  console.log('Hello from mock data');\n}",
              },
            ]
          : [],
      };
    },
    connector(name) {
      return state.connectors[name] ?? { connected: false, configured: false };
    },
    connectConnector(name) {
      const connector = state.connectors[name];
      if (!connector) {
        return null;
      }
      connector.connected = true;
      connector.configured = true;
      if (name === "github") {
        connector.github_login = "readbase-dev";
      }
      if (name === "slack") {
        connector.teams = [
          {
            team_id: "T123",
            team_name: "Readbase Demo",
            team_domain: "readbase-demo",
          },
        ];
      }
      if (name === "jira") {
        connector.sites = [
          {
            cloud_id: "jira-cloud-1",
            name: "Readbase Jira",
            url: "https://readbase.atlassian.net",
          },
        ];
      }
      return connector;
    },
    disconnectConnector(name) {
      const connector = state.connectors[name];
      if (!connector) {
        return null;
      }
      connector.connected = false;
      return connector;
    },
    emptyList(name) {
      return state.emptyLists[name] ?? {};
    },
    workspaceSourceList(kind) {
      return { sources: state.workspaceSources[kind] ?? [] };
    },
    workspaceSlackTeams() {
      return { teams: state.workspaceSources.slackTeams ?? [] };
    },
    postOk(body = {}) {
      return body;
    },
  };
}
