import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  deleteJson,
  fetchJson,
  getErrorMessage,
  isSessionExpiredMessage,
  postJson,
} from "../api";
import type {
  Workspace,
  WorkspacesResponse,
} from "../types";
import { AppToast } from "../components/AppToast";

export function WorkspaceDashboardPage({
  onSelectWorkspace,
  onSessionExpired,
  onLeaveWorkspace,
}: {
  onSelectWorkspace: (workspace: Workspace) => void;
  onSessionExpired: () => void;
  onLeaveWorkspace?: (workspace: Workspace) => void;
}) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceStatus, setWorkspaceStatus] = useState("");
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [deletingWorkspaceId, setDeletingWorkspaceId] = useState<string | null>(null);
  const [leavingWorkspaceId, setLeavingWorkspaceId] = useState<string | null>(null);

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

  async function handleLeaveWorkspace(workspace: Workspace) {
    const confirmed = window.confirm(
      `Leave workspace "${workspace.name}"?\n\nYou will lose access until someone invites you again from the org graph.`,
    );
    if (!confirmed) {
      return;
    }

    setLeavingWorkspaceId(workspace.workspace_id);
    setWorkspaceStatus("");
    setWorkspaceError(null);
    try {
      await postJson<Record<string, never>, Workspace>(
        `/api/workspaces/${encodeURIComponent(workspace.workspace_id)}/leave`,
        {},
      );
      setWorkspaceStatus(`Left workspace: ${workspace.name}`);
      onLeaveWorkspace?.(workspace);
      await loadWorkspaces();
    } catch (error) {
      handleApiError(error, setWorkspaceError);
    } finally {
      setLeavingWorkspaceId(null);
    }
  }

  return (
    <section className="workspace-home">
      <div className="workspace-header">
        <div>
          <h1>Workspaces</h1>
          <p>Create a workspace for your team. Teammates are added when someone invites them from the hierarchy graph.</p>
        </div>
      </div>

      <div className="workspace-entry-forms">
        <form className="workspace-create-form" onSubmit={handleWorkspaceSubmit}>
          <label htmlFor="workspaceName">Create a workspace</label>
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
      </div>

      <WorkspaceList
        workspaces={workspaces}
        deletingWorkspaceId={deletingWorkspaceId}
        leavingWorkspaceId={leavingWorkspaceId}
        onSelect={onSelectWorkspace}
        onDelete={handleDeleteWorkspace}
        onLeave={handleLeaveWorkspace}
      />
      <AppToast message={workspaceError || workspaceStatus} error={Boolean(workspaceError)} />
    </section>
  );
}

function WorkspaceList({
  workspaces,
  deletingWorkspaceId,
  leavingWorkspaceId,
  onSelect,
  onDelete,
  onLeave,
}: {
  workspaces: Workspace[];
  deletingWorkspaceId: string | null;
  leavingWorkspaceId: string | null;
  onSelect: (workspace: Workspace) => void;
  onDelete: (workspace: Workspace) => void;
  onLeave: (workspace: Workspace) => void;
}) {
  const ownedWorkspaces = workspaces.filter((workspace) => workspace.can_manage);
  const joinedWorkspaces = workspaces.filter((workspace) => !workspace.can_manage);

  if (!workspaces.length) {
    return (
      <div className="status-text">
        No workspaces yet. Create one above, or wait for a teammate to invite you from their workspace graph.
      </div>
    );
  }

  return (
    <div className="workspace-groups">
      {ownedWorkspaces.length ? (
        <WorkspaceGroup
          title="Your workspaces"
          description="Workspaces you created. You manage settings and the org graph."
          variant="owned"
          workspaces={ownedWorkspaces}
          deletingWorkspaceId={deletingWorkspaceId}
          leavingWorkspaceId={leavingWorkspaceId}
          onSelect={onSelect}
          onDelete={onDelete}
          onLeave={onLeave}
        />
      ) : null}
      {joinedWorkspaces.length ? (
        <WorkspaceGroup
          title="Joined workspaces"
          description="Workspaces where a teammate invited you by email from the hierarchy graph."
          variant="joined"
          workspaces={joinedWorkspaces}
          deletingWorkspaceId={deletingWorkspaceId}
          leavingWorkspaceId={leavingWorkspaceId}
          onSelect={onSelect}
          onDelete={onDelete}
          onLeave={onLeave}
        />
      ) : null}
    </div>
  );
}

function WorkspaceGroup({
  title,
  description,
  variant,
  workspaces,
  deletingWorkspaceId,
  leavingWorkspaceId,
  onSelect,
  onDelete,
  onLeave,
}: {
  title: string;
  description: string;
  variant: "owned" | "joined";
  workspaces: Workspace[];
  deletingWorkspaceId: string | null;
  leavingWorkspaceId: string | null;
  onSelect: (workspace: Workspace) => void;
  onDelete: (workspace: Workspace) => void;
  onLeave: (workspace: Workspace) => void;
}) {
  return (
    <section
      className={`workspace-group workspace-group--${variant}`}
      aria-labelledby={`workspace-group-${variant}`}
    >
      <header className="workspace-group-header">
        <div>
          <h2 id={`workspace-group-${variant}`}>{title}</h2>
          <p>{description}</p>
        </div>
        <span className="workspace-group-count">
          {workspaces.length} {workspaces.length === 1 ? "workspace" : "workspaces"}
        </span>
      </header>
      <div className="workspace-list">
        {workspaces.map((workspace) => (
          <WorkspaceListItem
            key={workspace.workspace_id}
            workspace={workspace}
            deletingWorkspaceId={deletingWorkspaceId}
            leavingWorkspaceId={leavingWorkspaceId}
            onSelect={onSelect}
            onDelete={onDelete}
            onLeave={onLeave}
          />
        ))}
      </div>
    </section>
  );
}

function WorkspaceListItem({
  workspace,
  deletingWorkspaceId,
  leavingWorkspaceId,
  onSelect,
  onDelete,
  onLeave,
}: {
  workspace: Workspace;
  deletingWorkspaceId: string | null;
  leavingWorkspaceId: string | null;
  onSelect: (workspace: Workspace) => void;
  onDelete: (workspace: Workspace) => void;
  onLeave: (workspace: Workspace) => void;
}) {
  const isLeaving = leavingWorkspaceId === workspace.workspace_id;
  const isDeleting = deletingWorkspaceId === workspace.workspace_id;

  return (
    <div className="workspace-item">
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
      <div className="workspace-actions">
        {workspace.can_manage ? (
          <button
            type="button"
            className="danger-button"
            disabled={isDeleting || isLeaving}
            onClick={() => onDelete(workspace)}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        ) : (
          <button
            type="button"
            className="secondary-action-button"
            disabled={isLeaving || isDeleting}
            onClick={() => onLeave(workspace)}
          >
            {isLeaving ? "Leaving..." : "Leave"}
          </button>
        )}
      </div>
    </div>
  );
}

function formatWorkspaceDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}
