import http from "node:http";
import { createMockStore } from "./store.mjs";

const PORT = Number(process.env.MOCK_API_PORT || 4010);
const store = createMockStore();

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
    });
    req.on("end", () => {
      if (!raw.trim()) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });
}

function matchPath(pattern, pathname) {
  const patternParts = pattern.split("/").filter(Boolean);
  const pathParts = pathname.split("/").filter(Boolean);
  if (patternParts.length !== pathParts.length) {
    return null;
  }
  const params = {};
  for (let index = 0; index < patternParts.length; index += 1) {
    const patternPart = patternParts[index];
    const pathPart = pathParts[index];
    if (patternPart.startsWith(":")) {
      params[patternPart.slice(1)] = decodeURIComponent(pathPart);
      continue;
    }
    if (patternPart !== pathPart) {
      return null;
    }
  }
  return params;
}

async function handleRequest(req, res) {
  const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "127.0.0.1"}`);
  const method = req.method ?? "GET";
  const pathname = url.pathname;

  try {
    if (method === "GET" && pathname === "/api/auth/session") {
      return sendJson(res, 200, store.sessionResponse());
    }

    if (method === "POST" && pathname === "/api/auth/mock-login") {
      return sendJson(res, 200, store.mockLogin());
    }

    if (method === "POST" && pathname === "/api/auth/logout") {
      return sendJson(res, 200, store.logout());
    }

    if (method === "GET" && pathname === "/api/workspaces") {
      return sendJson(res, 200, store.listWorkspaces());
    }

    if (method === "POST" && pathname === "/api/workspaces") {
      const body = await readJsonBody(req);
      const name = String(body.name ?? "").trim();
      if (!name) {
        return sendJson(res, 400, { error: "Workspace name is required." });
      }
      try {
        return sendJson(res, 200, store.createWorkspace(name));
      } catch (error) {
        return sendJson(res, 400, { error: error instanceof Error ? error.message : "Invalid workspace name." });
      }
    }

    let params = matchPath("/api/workspaces/:workspaceId", pathname);
    if (method === "PATCH" && params) {
      try {
        const body = await readJsonBody(req);
        const workspace = store.updateWorkspace(params.workspaceId, body?.name);
        if (!workspace) {
          return sendJson(res, 404, { error: "Workspace not found." });
        }
        return sendJson(res, 200, workspace);
      } catch (error) {
        return sendJson(res, 400, { error: error instanceof Error ? error.message : "Invalid workspace name." });
      }
    }

    if (method === "DELETE" && params) {
      const workspace = store.deleteWorkspace(params.workspaceId);
      if (!workspace) {
        return sendJson(res, 404, { error: "Workspace not found." });
      }
      return sendJson(res, 200, workspace);
    }

    params = matchPath("/api/workspaces/:workspaceId/leave", pathname);
    if (method === "POST" && params) {
      const workspace = store.leaveWorkspace(params.workspaceId);
      if (!workspace) {
        return sendJson(res, 404, { error: "Workspace not found." });
      }
      return sendJson(res, 200, workspace);
    }

    if (method === "GET" && pathname === "/api/invites") {
      return sendJson(res, 200, store.listInvites());
    }

    if (method === "GET" && pathname === "/api/notifications") {
      return sendJson(res, 200, store.listNotifications());
    }

    params = matchPath("/api/invites/join/:joinToken", pathname);
    if (method === "GET" && params) {
      const invite = store.previewLinkInvite(params.joinToken);
      if (!invite) {
        return sendJson(res, 404, { error: "Invite link not found." });
      }
      return sendJson(res, 200, invite);
    }

    params = matchPath("/api/invites/:inviteId/accept", pathname);
    if (method === "POST" && params) {
      const invite = store.updateInviteStatus(params.inviteId, "accepted");
      if (!invite) {
        return sendJson(res, 404, { error: "Invite not found." });
      }
      return sendJson(res, 200, invite);
    }

    params = matchPath("/api/invites/:inviteId/reject", pathname);
    if (method === "POST" && params) {
      const invite = store.updateInviteStatus(params.inviteId, "rejected");
      if (!invite) {
        return sendJson(res, 404, { error: "Invite not found." });
      }
      return sendJson(res, 200, invite);
    }

    params = matchPath("/api/invites/:inviteId/revert", pathname);
    if (method === "POST" && params) {
      const invite = store.updateInviteStatus(params.inviteId, "pending");
      if (!invite) {
        return sendJson(res, 404, { error: "Invite not found." });
      }
      return sendJson(res, 200, invite);
    }

    params = matchPath("/api/workspaces/:workspaceId/graph", pathname);
    if (method === "GET" && params) {
      return sendJson(res, 200, store.getGraph(params.workspaceId));
    }

    params = matchPath("/api/workspaces/:workspaceId/graph/nodes", pathname);
    if (method === "POST" && params) {
      const body = await readJsonBody(req);
      return sendJson(res, 200, store.createGraphNode(params.workspaceId, body));
    }

    params = matchPath("/api/workspaces/:workspaceId/graph/nodes/:nodeId", pathname);
    if (method === "PATCH" && params) {
      const body = await readJsonBody(req);
      const node = store.updateGraphNode(params.workspaceId, params.nodeId, body);
      if (!node) {
        return sendJson(res, 404, { error: "Node not found." });
      }
      return sendJson(res, 200, node);
    }
    if (method === "DELETE" && params) {
      const node = store.deleteGraphNode(params.workspaceId, params.nodeId);
      if (!node) {
        return sendJson(res, 404, { error: "Node not found." });
      }
      return sendJson(res, 200, node);
    }

    params = matchPath("/api/workspaces/:workspaceId/graph/connections", pathname);
    if (method === "POST" && params) {
      const body = await readJsonBody(req);
      return sendJson(res, 200, store.createGraphConnection(params.workspaceId, body));
    }

    params = matchPath("/api/workspaces/:workspaceId/graph/connections/:connectionId", pathname);
    if (method === "DELETE" && params) {
      const connection = store.deleteGraphConnection(params.workspaceId, params.connectionId);
      if (!connection) {
        return sendJson(res, 404, { error: "Connection not found." });
      }
      return sendJson(res, 200, connection);
    }

    params = matchPath("/api/workspaces/:workspaceId/repos", pathname);
    if (method === "GET" && params) {
      return sendJson(res, 200, store.listRepos(params.workspaceId));
    }

    params = matchPath("/api/workspaces/:workspaceId/ask", pathname);
    if (method === "POST" && params) {
      const body = await readJsonBody(req);
      return sendJson(res, 200, store.ask(params.workspaceId, body));
    }

    const connectorNames = [
      "github",
      "bitbucket",
      "gitlab",
      "jira",
      "slack",
      "teams",
      "linear",
      "confluence",
      "notion",
    ];

    for (const connectorName of connectorNames) {
      if (method === "GET" && pathname === `/api/me/integrations/${connectorName}`) {
        return sendJson(res, 200, store.connector(connectorName));
      }
      if (method === "DELETE" && pathname === `/api/me/integrations/${connectorName}`) {
        const connector = store.disconnectConnector(connectorName);
        if (!connector) {
          return sendJson(res, 404, { error: "Connector not found." });
        }
        return sendJson(res, 200, connector);
      }
      if (method === "POST" && pathname === `/api/mock/connect/${connectorName}`) {
        const connector = store.connectConnector(connectorName);
        if (!connector) {
          return sendJson(res, 404, { error: "Connector not found." });
        }
        return sendJson(res, 200, connector);
      }
    }

    if (method === "GET" && pathname === "/api/me/integrations/github/repos") {
      return sendJson(res, 200, store.emptyList("githubRepos"));
    }
    if (method === "GET" && pathname === "/api/me/integrations/bitbucket/repos") {
      return sendJson(res, 200, store.emptyList("bitbucketRepos"));
    }
    if (method === "GET" && pathname === "/api/me/integrations/gitlab/projects") {
      return sendJson(res, 200, store.emptyList("gitlabProjects"));
    }
    if (method === "GET" && pathname === "/api/me/integrations/slack/channels") {
      return sendJson(res, 200, store.emptyList("slackChannels"));
    }
    if (method === "GET" && pathname === "/api/me/integrations/linear/sources") {
      return sendJson(res, 200, store.emptyList("linearSources"));
    }
    if (method === "GET" && pathname === "/api/me/integrations/confluence/spaces") {
      return sendJson(res, 200, store.emptyList("confluenceSpaces"));
    }
    if (method === "GET" && pathname === "/api/me/integrations/notion/databases") {
      return sendJson(res, 200, store.emptyList("notionDatabases"));
    }

    params = matchPath("/api/workspaces/:workspaceId/jira/projects", pathname);
    if (method === "GET" && params) {
      return sendJson(res, 200, store.emptyList("jiraProjects"));
    }

    const sourceKinds = ["jira", "slack", "linear", "confluence", "notion"];
    for (const kind of sourceKinds) {
      params = matchPath(`/api/workspaces/:workspaceId/${kind}/sources`, pathname);
      if (method === "GET" && params) {
        return sendJson(res, 200, store.workspaceSourceList(kind));
      }
      if (method === "POST" && params) {
        return sendJson(res, 200, store.postOk({ source_id: `mock-${kind}-1`, workspace_id: params.workspaceId }));
      }

      params = matchPath(`/api/workspaces/:workspaceId/${kind}/sources/:sourceId`, pathname);
      if (method === "DELETE" && params) {
        return sendJson(res, 200, store.postOk({ source_id: params.sourceId, workspace_id: params.workspaceId }));
      }

      params = matchPath(`/api/workspaces/:workspaceId/${kind}/sources/:sourceId/sync`, pathname);
      if (method === "POST" && params) {
        return sendJson(res, 200, store.postOk({ source_id: params.sourceId, workspace_id: params.workspaceId }));
      }
    }

    params = matchPath("/api/workspaces/:workspaceId/slack/teams", pathname);
    if (method === "GET" && params) {
      return sendJson(res, 200, store.workspaceSlackTeams());
    }

    params = matchPath("/api/workspaces/:workspaceId/slack/teams/:teamId", pathname);
    if (method === "DELETE" && params) {
      return sendJson(res, 200, store.postOk({ team_id: params.teamId }));
    }

    params = matchPath("/api/workspaces/:workspaceId/jira/site", pathname);
    if (method === "GET" && params) {
      return sendJson(res, 200, { configured: false, cloud_id: null, site_name: null, site_url: null });
    }
    if (method === "POST" && params) {
      return sendJson(res, 200, {
        configured: true,
        cloud_id: "jira-cloud-1",
        site_name: "Readbase Jira",
        site_url: "https://readbase.atlassian.net",
      });
    }
    if (method === "DELETE" && params) {
      return sendJson(res, 200, { configured: false, cloud_id: null, site_name: null, site_url: null });
    }

    params = matchPath("/api/workspaces/:workspaceId/documents/:documentId", pathname);
    if (method === "PATCH" && params) {
      try {
        const body = await readJsonBody(req);
        const result = store.updateAdditionalDocument(
          params.workspaceId,
          params.documentId,
          body,
        );
        if (!result) {
          return sendJson(res, 404, { error: "Document not found." });
        }
        return sendJson(res, 200, result);
      } catch (error) {
        return sendJson(res, 400, {
          error: error instanceof Error ? error.message : "Invalid document update.",
        });
      }
    }
    if (method === "DELETE" && params) {
      const result = store.deleteAdditionalDocument(params.workspaceId, params.documentId);
      if (!result) {
        return sendJson(res, 404, { error: "Document not found." });
      }
      return sendJson(res, 200, result);
    }

    params = matchPath("/api/workspaces/:workspaceId/documents", pathname);
    if (method === "GET" && params) {
      return sendJson(res, 200, store.listAdditionalDocuments(params.workspaceId));
    }
    if (method === "POST" && params) {
      try {
        const body = await readJsonBody(req);
        return sendJson(res, 200, store.addAdditionalDocument(params.workspaceId, body.name));
      } catch (error) {
        return sendJson(res, 400, {
          error: error instanceof Error ? error.message : "Invalid document upload.",
        });
      }
    }

    params = matchPath("/api/workspaces/:workspaceId/index", pathname);
    if (method === "POST" && params) {
      const body = await readJsonBody(req);
      return sendJson(res, 200, {
        repo_id: "repo-mock-new",
        workspace_id: params.workspaceId,
        repo_url: body.repo_url ?? "https://github.com/readbase/new-repo",
        default_branch: "main",
        indexed_at: new Date().toISOString(),
        chunk_count: 42,
      });
    }

    if (method === "GET" && pathname === "/api/health/storage") {
      return sendJson(res, 200, { ok: true, mode: "mock" });
    }

    console.warn(`[mock-api] Unhandled ${method} ${pathname}`);
    return sendJson(res, 404, { error: `Mock route not implemented: ${method} ${pathname}` });
  } catch (error) {
    console.error("[mock-api] Request failed", error);
    return sendJson(res, 500, { error: "Mock server error." });
  }
}

const server = http.createServer((req, res) => {
  void handleRequest(req, res);
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[mock-api] Contract mock server listening on http://127.0.0.1:${PORT}`);
  console.log("[mock-api] Edit fixtures in frontend/mock/fixtures.json");
});
