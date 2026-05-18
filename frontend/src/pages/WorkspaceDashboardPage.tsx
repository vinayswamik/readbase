import { FormEvent, useCallback, useEffect, useState } from "react";

import { deleteJson, fetchJson, getErrorMessage, postJson } from "../api";
import type { Workspace, WorkspacesResponse } from "../types";

export function WorkspaceDashboardPage({
  onSelectWorkspace,
  onSessionExpired,
}: {
  onSelectWorkspace: (workspace: Workspace) => void;
  onSessionExpired: () => void;
}) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceStatus, setWorkspaceStatus] = useState("");
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [deletingWorkspaceId, setDeletingWorkspaceId] = useState<string | null>(null);

  const handleApiError = useCallback(
    (error: unknown, setMessage?: (message: string) => void) => {
      const message = getErrorMessage(error);
      if (setMessage) {
        setMessage(message);
      }
      if (
        message.toLowerCase().includes("session expired") ||
        message.toLowerCase().includes("authentication required")
      ) {
        onSessionExpired();
      }
    },
    [onSessionExpired],
  );

  const loadWorkspaces = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspacesResponse>("/api/workspaces");
      setWorkspaces(result.workspaces || []);
      setWorkspaceError(null);
    } catch (error) {
      handleApiError(error, setWorkspaceError);
    }
  }, [handleApiError]);

  useEffect(() => {
    void loadWorkspaces();
  }, [loadWorkspaces]);

  async function handleWorkspaceSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = workspaceName.trim();
    if (!trimmedName) {
      return;
    }

    setCreatingWorkspace(true);
    setWorkspaceStatus("");
    setWorkspaceError(null);
    try {
      const workspace = await postJson<{ name: string }, Workspace>("/api/workspaces", {
        name: trimmedName,
      });
      setWorkspaceName("");
      setWorkspaceStatus(`Workspace created: ${workspace.name}`);
      await loadWorkspaces();
    } catch (error) {
      handleApiError(error, setWorkspaceError);
    } finally {
      setCreatingWorkspace(false);
    }
  }

  async function handleDeleteWorkspace(workspace: Workspace) {
    const confirmed = window.confirm(
      `Delete workspace "${workspace.name}"?\n\nAll repositories and indexes in this workspace will be permanently removed.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingWorkspaceId(workspace.workspace_id);
    setWorkspaceStatus("");
    setWorkspaceError(null);
    try {
      await deleteJson<Workspace>(`/api/workspaces/${workspace.workspace_id}`);
      setWorkspaceStatus(`Workspace deleted: ${workspace.name}`);
      await loadWorkspaces();
    } catch (error) {
      handleApiError(error, setWorkspaceError);
    } finally {
      setDeletingWorkspaceId(null);
    }
  }

  return (
    <section className="workspace-home">
      <div className="workspace-header">
        <div>
          <h1>Workspaces</h1>
          <p>Choose a workspace to index repositories and ask questions.</p>
        </div>
      </div>

      <form className="workspace-create-form" onSubmit={handleWorkspaceSubmit}>
        <label htmlFor="workspaceName">Workspace name</label>
        <div className="workspace-create-row">
          <input
            id="workspaceName"
            name="workspaceName"
            value={workspaceName}
            placeholder="Project Alpha"
            required
            onChange={(event) => setWorkspaceName(event.target.value)}
          />
          <button type="submit" className="primary-button" disabled={creatingWorkspace}>
            {creatingWorkspace ? "Creating..." : "Create"}
          </button>
        </div>
      </form>

      {workspaceError ? <div className="status-text error-text">{workspaceError}</div> : null}
      {workspaceStatus ? <div className="status-text">{workspaceStatus}</div> : null}

      <WorkspaceList
        workspaces={workspaces}
        deletingWorkspaceId={deletingWorkspaceId}
        onSelect={onSelectWorkspace}
        onDelete={handleDeleteWorkspace}
      />
    </section>
  );
}

function WorkspaceList({
  workspaces,
  deletingWorkspaceId,
  onSelect,
  onDelete,
}: {
  workspaces: Workspace[];
  deletingWorkspaceId: string | null;
  onSelect: (workspace: Workspace) => void;
  onDelete: (workspace: Workspace) => void;
}) {
  if (!workspaces.length) {
    return <div className="status-text">No workspaces yet.</div>;
  }

  return (
    <div className="workspace-list">
      {workspaces.map((workspace) => (
        <div className="workspace-item" key={workspace.workspace_id}>
          <button
            type="button"
            className="workspace-open"
            onClick={() => onSelect(workspace)}
          >
            <span className="workspace-name">{workspace.name}</span>
            <span className="workspace-meta">
              Created {formatWorkspaceDate(workspace.created_at)}
            </span>
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={deletingWorkspaceId === workspace.workspace_id}
            onClick={() => onDelete(workspace)}
          >
            {deletingWorkspaceId === workspace.workspace_id ? "Deleting..." : "Delete"}
          </button>
        </div>
      ))}
    </div>
  );
}

function formatWorkspaceDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}
