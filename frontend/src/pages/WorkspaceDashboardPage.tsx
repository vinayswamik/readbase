import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  deleteJson,
  fetchJson,
  getErrorMessage,
  isSessionExpiredMessage,
  postJson,
} from "../api";
import type {
  AuthUser,
  Workspace,
  WorkspaceMember,
  WorkspaceMembersResponse,
  WorkspacesResponse,
} from "../types";

export function WorkspaceDashboardPage({
  user,
  onSelectWorkspace,
  onSessionExpired,
}: {
  user: AuthUser;
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

  return (
    <section className="workspace-home">
      <div className="workspace-header">
        <div>
          <h1>Workspaces</h1>
          <p>
            {user.role === "admin"
              ? "Create workspaces, add members, and open shared codebase Q&A."
              : "Open workspaces where an admin has added your Google account."}
          </p>
        </div>
      </div>

      {user.role === "admin" ? (
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
      ) : null}

      {workspaceError ? <div className="status-text error-text">{workspaceError}</div> : null}
      {workspaceStatus ? <div className="status-text">{workspaceStatus}</div> : null}

      <WorkspaceList
        workspaces={workspaces}
        deletingWorkspaceId={deletingWorkspaceId}
        onSelect={onSelectWorkspace}
        onDelete={handleDeleteWorkspace}
        onSessionExpired={onSessionExpired}
      />
    </section>
  );
}

function WorkspaceList({
  workspaces,
  deletingWorkspaceId,
  onSelect,
  onDelete,
  onSessionExpired,
}: {
  workspaces: Workspace[];
  deletingWorkspaceId: string | null;
  onSelect: (workspace: Workspace) => void;
  onDelete: (workspace: Workspace) => void;
  onSessionExpired: () => void;
}) {
  if (!workspaces.length) {
    return <div className="status-text">No workspaces available for this account.</div>;
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
          {workspace.can_manage ? (
            <div className="workspace-actions">
              <button
                type="button"
                className="danger-button"
                disabled={deletingWorkspaceId === workspace.workspace_id}
                onClick={() => onDelete(workspace)}
              >
                {deletingWorkspaceId === workspace.workspace_id ? "Deleting..." : "Delete"}
              </button>
              <MemberManager
                workspace={workspace}
                onSessionExpired={onSessionExpired}
              />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function MemberManager({
  workspace,
  onSessionExpired,
}: {
  workspace: Workspace;
  onSessionExpired: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleApiError = useCallback(
    (apiError: unknown) => {
      const message = getErrorMessage(apiError);
      setError(message);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    },
    [onSessionExpired],
  );

  const loadMembers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson<WorkspaceMembersResponse>(
        `/api/workspaces/${workspace.workspace_id}/members`,
      );
      setMembers(result.members || []);
    } catch (apiError) {
      handleApiError(apiError);
    } finally {
      setLoading(false);
    }
  }, [handleApiError, workspace.workspace_id]);

  useEffect(() => {
    if (open) {
      void loadMembers();
    }
  }, [loadMembers, open]);

  async function handleAddMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      return;
    }
    setLoading(true);
    setStatus("");
    setError(null);
    try {
      await postJson<{ email: string }, WorkspaceMember>(
        `/api/workspaces/${workspace.workspace_id}/members`,
        { email: trimmedEmail },
      );
      setEmail("");
      setStatus(`Member added: ${trimmedEmail}`);
      await loadMembers();
    } catch (apiError) {
      handleApiError(apiError);
    } finally {
      setLoading(false);
    }
  }

  async function handleRemoveMember(member: WorkspaceMember) {
    setLoading(true);
    setStatus("");
    setError(null);
    try {
      await deleteJson<WorkspaceMember>(
        `/api/workspaces/${workspace.workspace_id}/members/${encodeURIComponent(
          member.email,
        )}`,
      );
      setStatus(`Member removed: ${member.email}`);
      await loadMembers();
    } catch (apiError) {
      handleApiError(apiError);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="member-manager">
      <button
        type="button"
        className="secondary-action-button"
        onClick={() => setOpen((currentOpen) => !currentOpen)}
      >
        {open ? "Hide members" : "Members"}
      </button>

      {open ? (
        <div className="member-panel">
          <form className="member-add-form" onSubmit={handleAddMember}>
            <input
              type="email"
              value={email}
              placeholder="member@example.com"
              required
              onChange={(event) => setEmail(event.target.value)}
            />
            <button type="submit" className="primary-button" disabled={loading}>
              Add
            </button>
          </form>

          {error ? <div className="status-text error-text">{error}</div> : null}
          {status ? <div className="status-text">{status}</div> : null}

          <div className="member-list">
            {members.map((member) => (
              <div className="member-row" key={member.email}>
                <span>{member.email}</span>
                {member.is_owner ? (
                  <span className="workspace-meta">Owner</span>
                ) : (
                  <button
                    type="button"
                    className="danger-button"
                    disabled={loading}
                    onClick={() => handleRemoveMember(member)}
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            {!members.length && !loading ? (
              <div className="status-text">No members yet.</div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function formatWorkspaceDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}
