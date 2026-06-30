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
    notifications: clone(seed.notifications ?? []),
    invites: clone(seed.invites),
    linkInvites: clone(seed.linkInvites),
    graphs: clone(seed.graphs),
    repos: clone(seed.repos),
    connectors: clone(seed.connectors),
    workspaceSources: clone(seed.workspaceSources),
    additionalDocuments: clone(seed.additionalDocuments ?? {}),
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
      const normalizedName = String(name ?? "").trim().replace(/\s+/g, " ");
      const nameKey = normalizedName.toLocaleLowerCase();
      const duplicate = state.workspaces.some(
        (workspace) =>
          workspace.owner_user_id === state.user.id &&
          String(workspace.name ?? "").trim().replace(/\s+/g, " ").toLocaleLowerCase() === nameKey,
      );
      if (duplicate) {
        throw new Error("Workspace name already exists.");
      }
      const workspace = {
        workspace_id: createId("ws"),
        owner_user_id: state.user.id,
        name: normalizedName,
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
    updateWorkspace(workspaceId, name) {
      const workspace = findWorkspace(workspaceId);
      if (!workspace) {
        return null;
      }
      if (!workspace.can_manage) {
        throw new Error("Workspace owner access required.");
      }
      const normalizedName = String(name ?? "").trim().replace(/\s+/g, " ");
      if (!normalizedName) {
        throw new Error("Workspace name is required.");
      }
      if (normalizedName.length > 80) {
        throw new Error("Workspace name must be 80 characters or fewer.");
      }
      const nameKey = normalizedName.toLocaleLowerCase();
      const duplicate = state.workspaces.some(
        (entry) =>
          entry.workspace_id !== workspaceId &&
          entry.owner_user_id === state.user.id &&
          String(entry.name ?? "").trim().replace(/\s+/g, " ").toLocaleLowerCase() === nameKey,
      );
      if (duplicate) {
        throw new Error("Workspace name already exists.");
      }
      workspace.name = normalizedName;
      return workspace;
    },
    leaveWorkspace(workspaceId) {
      const index = state.workspaces.findIndex(
        (workspace) => workspace.workspace_id === workspaceId,
      );
      if (index === -1) {
        return null;
      }
      const [removed] = state.workspaces.splice(index, 1);
      this.recordWorkspaceMemberLeft(removed);
      return removed;
    },
    listNotifications() {
      return {
        notifications: state.notifications
          .filter((notification) => notification.recipient_user_id === state.user.id)
          .sort((left, right) => right.created_at.localeCompare(left.created_at)),
      };
    },
    recordWorkspaceMemberLeft(workspace) {
      if (!workspace || !state.user?.id) {
        return;
      }
      const actorUserId = state.user.id;
      const actorName = state.user.name || "A teammate";
      const recipientId = workspace.owner_user_id;
      if (!recipientId || recipientId === actorUserId) {
        return;
      }
      state.notifications.unshift({
        notification_id: createId("notif"),
        recipient_user_id: recipientId,
        type: "workspace_member_left",
        title: "Member left workspace",
        body: `${actorName} stepped off the workspace. Review shared access if anything still routes through them.`,
        workspace_id: workspace.workspace_id,
        workspace_name: workspace.name,
        actor_user_id: actorUserId,
        actor_name: actorName,
        read: false,
        created_at: nowIso(),
      });
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
    listAdditionalDocuments(workspaceId) {
      const documents = (state.additionalDocuments[workspaceId] ?? []).map((document) => ({
        ...document,
        assigned_user_ids: Array.isArray(document.assigned_user_ids) ? document.assigned_user_ids : [],
      }));
      return { documents };
    },
    addAdditionalDocument(workspaceId, name) {
      const trimmedName = String(name ?? "").trim();
      if (!trimmedName) {
        throw new Error("Document name is required.");
      }
      if (!state.additionalDocuments[workspaceId]) {
        state.additionalDocuments[workspaceId] = [];
      }
      const duplicate = state.additionalDocuments[workspaceId].some(
        (document) => document.name.toLocaleLowerCase() === trimmedName.toLocaleLowerCase(),
      );
      if (duplicate) {
        throw new Error("A document with this name already exists in the workspace.");
      }
      const document = {
        document_id: createId("doc"),
        name: trimmedName,
        created_at: nowIso(),
        uploaded_by_user_id: state.user?.id ?? null,
        assigned_user_ids: [],
      };
      state.additionalDocuments[workspaceId].push(document);
      return { document };
    },
    updateAdditionalDocument(workspaceId, documentId, payload) {
      const documents = state.additionalDocuments[workspaceId] ?? [];
      const document = documents.find((entry) => entry.document_id === documentId);
      if (!document) {
        return null;
      }

      const graph = getGraph(workspaceId);
      const validUserIds = new Set(
        (graph.assignable_users ?? []).map((user) => user.user_id).filter(Boolean),
      );
      const requestedIds = Array.isArray(payload?.assigned_user_ids) ? payload.assigned_user_ids : [];
      const normalizedIds = [...new Set(requestedIds.map((userId) => String(userId).trim()).filter(Boolean))];
      const invalidIds = normalizedIds.filter((userId) => !validUserIds.has(userId));
      if (invalidIds.length) {
        throw new Error("One or more selected users cannot access this document.");
      }

      document.assigned_user_ids = normalizedIds;
      return { document: { ...document, assigned_user_ids: [...normalizedIds] } };
    },
    deleteAdditionalDocument(workspaceId, documentId) {
      const documents = state.additionalDocuments[workspaceId] ?? [];
      const index = documents.findIndex((document) => document.document_id === documentId);
      if (index < 0) {
        return null;
      }
      documents.splice(index, 1);
      return { document_id: documentId };
    },
  };
}
