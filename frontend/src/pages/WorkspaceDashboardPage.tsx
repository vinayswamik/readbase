import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

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
import {
  isOwnedWorkspaceNameTaken,
  normalizeWorkspaceNameInput,
} from "../workspaceName";

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

  const ownedWorkspaces = workspaces.filter((workspace) => workspace.can_manage);

  const trimmedWorkspaceName = useMemo(
    () => normalizeWorkspaceNameInput(workspaceName),
    [workspaceName],
  );
  const showWorkspaceNameStatus = trimmedWorkspaceName.length > 0;
  const isWorkspaceNameTaken = useMemo(
    () =>
      showWorkspaceNameStatus &&
      isOwnedWorkspaceNameTaken(trimmedWorkspaceName, ownedWorkspaces),
    [ownedWorkspaces, showWorkspaceNameStatus, trimmedWorkspaceName],
  );
  const canCreateWorkspace =
    showWorkspaceNameStatus && !isWorkspaceNameTaken && !creatingWorkspace;

  async function handleWorkspaceSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trimmedWorkspaceName || isWorkspaceNameTaken) {
      return;
    }

    setCreatingWorkspace(true);
    setWorkspaceStatus("");
    setWorkspaceError(null);
    try {
      const workspace = await postJson<{ name: string }, Workspace>("/api/workspaces", {
        name: trimmedWorkspaceName,
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
      `Leave workspace "${workspace.name}"?\n\nYou will lose access until someone invites you again from the organization graph.`,
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

  const joinedWorkspaces = workspaces.filter((workspace) => !workspace.can_manage);

  const workspaceListProps = {
    deletingWorkspaceId,
    leavingWorkspaceId,
    onSelect: onSelectWorkspace,
    onDelete: handleDeleteWorkspace,
    onLeave: handleLeaveWorkspace,
  };

  return (
    <section className="workspace-home">
      <div className="workspace-header">
        <div>
          <h1>Workspaces</h1>
          <p>Create a workspace for your team. Teammates are added when someone invites them from the hierarchy graph.</p>
        </div>
      </div>

      <div className="workspace-body-panel">
        <div className="workspace-body-columns">
          <div className="workspace-body-column workspace-body-column--left">
            <div className="workspace-entry-forms">
              <form className="workspace-create-form" onSubmit={handleWorkspaceSubmit}>
                <label htmlFor="workspaceName">Create Workspace</label>
                <div className="workspace-create-row">
                  <div
                    className={
                      showWorkspaceNameStatus
                        ? "workspace-create-input-wrap workspace-create-input-wrap--with-status"
                        : "workspace-create-input-wrap"
                    }
                  >
                    {showWorkspaceNameStatus ? (
                      <span
                        className={
                          isWorkspaceNameTaken
                            ? "workspace-create-name-status workspace-create-name-status--invalid"
                            : "workspace-create-name-status workspace-create-name-status--valid"
                        }
                        aria-hidden="true"
                      >
                        {isWorkspaceNameTaken ? <WorkspaceNameInvalidIcon /> : <WorkspaceNameValidIcon />}
                      </span>
                    ) : null}
                    <input
                      id="workspaceName"
                      name="workspaceName"
                      value={workspaceName}
                      placeholder="Project Alpha..."
                      required
                      aria-invalid={isWorkspaceNameTaken}
                      aria-describedby={
                        isWorkspaceNameTaken ? "workspaceNameError" : undefined
                      }
                      onChange={(event) => setWorkspaceName(event.target.value)}
                    />
                  </div>
                  <button
                    type="submit"
                    className="solid-button"
                    disabled={!canCreateWorkspace}
                  >
                    {creatingWorkspace ? "Creating..." : "Create"}
                  </button>
                </div>
                {isWorkspaceNameTaken ? (
                  <p id="workspaceNameError" className="workspace-create-name-error" role="alert">
                    You already have a workspace with this name.
                  </p>
                ) : null}
              </form>
            </div>
            <div className="workspace-section-divider" aria-hidden="true" />
            <OwnedWorkspacesSection
              workspaces={ownedWorkspaces}
              {...workspaceListProps}
            />
          </div>

          <div className="workspace-body-divider" aria-hidden="true" />

          <div className="workspace-body-column workspace-body-column--right">
            <JoinedWorkspacesSection
              workspaces={joinedWorkspaces}
              {...workspaceListProps}
            />
          </div>
        </div>
        <AppToast message={workspaceError || workspaceStatus} error={Boolean(workspaceError)} />
      </div>
    </section>
  );
}

function WorkspaceGroupHeader({
  title,
  description,
  variant,
  count,
}: {
  title: string;
  description: string;
  variant: "owned" | "joined";
  count?: number;
}) {
  return (
    <header className="workspace-group-header">
      <div className="workspace-group-header-top">
        <h2 id={`workspace-group-${variant}`}>{title}</h2>
        {count !== undefined ? (
          <span
            className="workspace-group-count"
            aria-label={`${count} ${count === 1 ? "workspace" : "workspaces"}`}
          >
            {count}
          </span>
        ) : null}
      </div>
      <p>{description}</p>
    </header>
  );
}

function OwnedWorkspacesSection({
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
  if (!workspaces.length) {
    return (
      <div className="workspace-owned-section">
        <WorkspaceGroupHeader
          title="My Workspaces"
          description="Workspaces you created. You manage settings and the organization graph."
          variant="owned"
          count={0}
        />
        <p className="status-text">No workspaces yet. Create one above.</p>
      </div>
    );
  }

  return (
    <WorkspaceGroup
      title="My Workspaces"
      description="Workspaces you created. You manage settings and the organization graph."
      variant="owned"
      workspaces={workspaces}
      deletingWorkspaceId={deletingWorkspaceId}
      leavingWorkspaceId={leavingWorkspaceId}
      onSelect={onSelect}
      onDelete={onDelete}
      onLeave={onLeave}
    />
  );
}

function JoinedWorkspacesSection({
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
  if (!workspaces.length) {
    return (
      <div className="workspace-joined-section">
        <WorkspaceGroupHeader
          title="Joined Workspaces"
          description="Workspaces where a teammate invited you."
          variant="joined"
          count={0}
        />
        <p className="status-text">
          No joined workspaces yet. Wait for a teammate to invite you from their workspace graph.
        </p>
      </div>
    );
  }

  return (
    <WorkspaceGroup
      title="Joined Workspaces"
      description="Workspaces where a teammate invited you."
      variant="joined"
      workspaces={workspaces}
      deletingWorkspaceId={deletingWorkspaceId}
      leavingWorkspaceId={leavingWorkspaceId}
      onSelect={onSelect}
      onDelete={onDelete}
      onLeave={onLeave}
    />
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
      <WorkspaceGroupHeader
        title={title}
        description={description}
        variant={variant}
        count={workspaces.length}
      />
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
        className="workspace-item-body"
        onClick={() => onSelect(workspace)}
      >
        <span className="workspace-name">{workspace.name}</span>
        <span className="workspace-meta">
          {workspace.can_manage ? "Created" : "Joined"}{" "}
          {formatWorkspaceDate(workspace.created_at)}
        </span>
      </button>
      <div className="workspace-actions">
        {workspace.can_manage ? (
          <button
            type="button"
            className="workspace-delete-button"
            disabled={isDeleting || isLeaving}
            aria-label={
              isDeleting ? `Deleting ${workspace.name}` : `Delete ${workspace.name}`
            }
            onClick={() => onDelete(workspace)}
          >
            <TrashIcon />
          </button>
        ) : (
          <button
            type="button"
            className="workspace-leave-button"
            disabled={isLeaving || isDeleting}
            aria-label={isLeaving ? `Leaving ${workspace.name}` : `Leave ${workspace.name}`}
            onClick={() => onLeave(workspace)}
          >
            <ExitIcon />
            <span>{isLeaving ? "Leaving..." : "Leave"}</span>
          </button>
        )}
      </div>
    </div>
  );
}

function WorkspaceNameValidIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M7.5 12.5 10 15l6.5-6.5"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.25"
      />
    </svg>
  );
}

function WorkspaceNameInvalidIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M8.5 8.5l7 7M15.5 8.5l-7 7"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="2.25"
      />
    </svg>
  );
}

function formatOrdinalDay(day: number): string {
  if (day >= 11 && day <= 13) {
    return `${day}th`;
  }
  switch (day % 10) {
    case 1:
      return `${day}st`;
    case 2:
      return `${day}nd`;
    case 3:
      return `${day}rd`;
    default:
      return `${day}th`;
  }
}

function formatWorkspaceDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const month = date.toLocaleString("en-US", { month: "long" });
  const day = formatOrdinalDay(date.getDate());
  const year = date.getFullYear();
  return `${month} ${day} ${year}`;
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M4 7h16"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
      <path
        d="M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
      <path
        d="M6.5 7l.75 12.25A1.75 1.75 0 0 0 9 21h6a1.75 1.75 0 0 0 1.75-1.75L17.5 7"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
      <path
        d="M10 11v5.5M14 11v5.5"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}

function ExitIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M10 4H6.5A1.5 1.5 0 0 0 5 5.5v13A1.5 1.5 0 0 0 6.5 20H10"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
      <path
        d="M14 12H20M20 12l-3-3M20 12l-3 3"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}
