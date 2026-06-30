import {
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";

import { fetchJson, getErrorMessage, isSessionExpiredMessage, patchJson } from "../api";
import type { Workspace, WorkspacesResponse } from "../types";
import {
  isOwnedWorkspaceNameTaken,
  normalizeWorkspaceNameInput,
  WORKSPACE_NAME_MAX_LENGTH,
} from "../workspaceName";

export function AppTopbarWorkspaceTitle({
  workspaceId,
  name,
  canManage,
  onRenamed,
  onSessionExpired,
}: {
  workspaceId: string;
  name: string;
  canManage: boolean;
  onRenamed: (workspace: Workspace) => void;
  onSessionExpired: () => void;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const editorRef = useRef<HTMLFormElement | null>(null);
  const skipBlurSaveRef = useRef(false);
  const [editing, setEditing] = useState(false);
  const [draftName, setDraftName] = useState(name);
  const [ownedWorkspaces, setOwnedWorkspaces] = useState<Workspace[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const trimmedDraftName = useMemo(() => normalizeWorkspaceNameInput(draftName), [draftName]);
  const showNameStatus = editing && trimmedDraftName.length > 0;
  const isNameUnchanged = trimmedDraftName === normalizeWorkspaceNameInput(name);
  const isNameTaken = useMemo(
    () =>
      showNameStatus &&
      isOwnedWorkspaceNameTaken(trimmedDraftName, ownedWorkspaces, workspaceId),
    [ownedWorkspaces, showNameStatus, trimmedDraftName, workspaceId],
  );

  const loadOwnedWorkspaces = useCallback(async () => {
    try {
      const result = await fetchJson<WorkspacesResponse>("/api/workspaces");
      setOwnedWorkspaces((result.workspaces ?? []).filter((workspace) => workspace.can_manage));
    } catch (error) {
      const message = getErrorMessage(error);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    }
  }, [onSessionExpired]);

  useEffect(() => {
    if (!editing) {
      setDraftName(name);
      setSaveError(null);
    }
  }, [editing, name]);

  useEffect(() => {
    if (!editing) {
      return;
    }
    void loadOwnedWorkspaces();
    inputRef.current?.focus();
    inputRef.current?.select();
  }, [editing, loadOwnedWorkspaces]);

  const handleStartEditing = () => {
    if (!canManage || saving) {
      return;
    }
    setDraftName(name);
    setSaveError(null);
    setEditing(true);
  };

  const handleCancelEditing = useCallback(() => {
    if (saving) {
      return;
    }
    skipBlurSaveRef.current = true;
    setDraftName(name);
    setSaveError(null);
    setEditing(false);
  }, [name, saving]);

  const handleCommitAndClose = useCallback(async () => {
    if (saving) {
      return;
    }
    if (!trimmedDraftName.length || isNameTaken) {
      handleCancelEditing();
      return;
    }
    if (isNameUnchanged) {
      handleCancelEditing();
      return;
    }

    setSaving(true);
    setSaveError(null);
    try {
      const workspace = await patchJson<{ name: string }, Workspace>(
        `/api/workspaces/${encodeURIComponent(workspaceId)}`,
        { name: trimmedDraftName },
      );
      onRenamed(workspace);
      setEditing(false);
    } catch (error) {
      const message = getErrorMessage(error);
      setSaveError(message);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    } finally {
      setSaving(false);
    }
  }, [
    handleCancelEditing,
    isNameTaken,
    isNameUnchanged,
    onRenamed,
    onSessionExpired,
    saving,
    trimmedDraftName,
    workspaceId,
  ]);

  useEffect(() => {
    if (!editing) {
      return;
    }
    const handleDocumentMouseDown = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (editorRef.current?.contains(target)) {
        return;
      }
      skipBlurSaveRef.current = true;
      void handleCommitAndClose();
    };

    document.addEventListener("mousedown", handleDocumentMouseDown);
    return () => {
      document.removeEventListener("mousedown", handleDocumentMouseDown);
    };
  }, [editing, handleCommitAndClose]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void handleCommitAndClose();
  };

  const handleInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      skipBlurSaveRef.current = true;
      handleCancelEditing();
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      void handleCommitAndClose();
    }
  };

  if (!editing) {
    return (
      <div className="app-topbar-workspace-title-row">
        <h1 className="app-topbar-workspace-title" title={name}>
          {name}
        </h1>
        {canManage ? (
          <button
            type="button"
            className="app-topbar-workspace-rename-button"
            onClick={handleStartEditing}
            aria-label={`Rename ${name}`}
          >
            <RenameIcon />
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <form
      ref={editorRef}
      className="app-topbar-workspace-rename-form"
      onSubmit={handleSubmit}
    >
      <div
        className={
          showNameStatus
            ? "app-topbar-workspace-rename-input-wrap app-topbar-workspace-rename-input-wrap--with-status"
            : "app-topbar-workspace-rename-input-wrap"
        }
      >
        {showNameStatus ? (
          <span
            className={
              isNameTaken
                ? "workspace-create-name-status workspace-create-name-status--invalid"
                : "workspace-create-name-status workspace-create-name-status--valid"
            }
            aria-hidden="true"
          >
            {isNameTaken ? <WorkspaceNameInvalidIcon /> : <WorkspaceNameValidIcon />}
          </span>
        ) : null}
        <input
          ref={inputRef}
          id={inputId}
          className="app-topbar-workspace-rename-input"
          value={draftName}
          maxLength={WORKSPACE_NAME_MAX_LENGTH}
          aria-label="Workspace name"
          aria-invalid={isNameTaken}
          aria-describedby={saveError ? `${inputId}-error` : undefined}
          disabled={saving}
          onChange={(event) => setDraftName(event.target.value)}
          onKeyDown={handleInputKeyDown}
          onBlur={() => {
            if (skipBlurSaveRef.current) {
              skipBlurSaveRef.current = false;
              return;
            }
            void handleCommitAndClose();
          }}
        />
      </div>
      {isNameTaken ? (
        <p className="app-topbar-workspace-rename-error" role="alert">
          You already have a workspace with this name.
        </p>
      ) : null}
      {saveError ? (
        <p id={`${inputId}-error`} className="app-topbar-workspace-rename-error" role="alert">
          {saveError}
        </p>
      ) : null}
    </form>
  );
}

function RenameIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 17v3z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
      <path
        d="m13.5 6.5 4 4"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
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
