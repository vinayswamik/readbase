import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import type { HierarchyAssignableUser } from "../../types";
import {
  formatDocumentUploadedAt,
  type WorkspaceAdditionalDocument,
} from "./workspaceAdditionalDocuments";

export function AdditionalDocumentManageContent({
  managedDocument,
  assignableUsers,
  mutating,
  onRequestClose,
  onSaveAccess,
  onDelete,
}: {
  managedDocument: WorkspaceAdditionalDocument;
  assignableUsers: HierarchyAssignableUser[];
  mutating: boolean;
  onRequestClose: () => void;
  onSaveAccess: (assignedUserIds: string[]) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [assignedUserIds, setAssignedUserIds] = useState<string[]>([]);

  useEffect(() => {
    setAssignedUserIds(managedDocument.assigned_user_ids);
  }, [managedDocument]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSaveAccess(assignedUserIds);
  }

  async function handleDeleteClick() {
    const confirmed = window.confirm(`Remove "${managedDocument.name}" from this workspace?`);
    if (!confirmed) {
      return;
    }
    await onDelete();
  }

  return (
    <>
      <header className="connector-modal-header">
        <div className="connector-modal-header-left" />
        <div className="connector-modal-title">
          <DocumentFileIcon />
          <div>
            <h2 id="document-manage-modal-heading">Manage document</h2>
          </div>
        </div>
        <button
          type="button"
          className="connector-close-button"
          aria-label="Close document manager"
          onClick={onRequestClose}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M6 6l12 12M18 6 6 18"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </header>

      <form className="connector-modal-body document-manage-form" onSubmit={(event) => void handleSubmit(event)}>
        <div className="document-manage-meta">
          <strong>{managedDocument.name}</strong>
          <span>Uploaded {formatDocumentUploadedAt(managedDocument.created_at)}</span>
        </div>

        <p className="status-text compact document-manage-access-hint">
          Assign people you have access data for. Only assigned users can reference this document.
        </p>

        <label id="document-access-label">Document access</label>
        <DocumentAccessPicker
          labelId="document-access-label"
          selectedUserIds={assignedUserIds}
          assignableUsers={assignableUsers}
          disabled={mutating}
          onChange={setAssignedUserIds}
        />

        <div className="connector-modal-actions document-manage-actions">
          <button type="submit" className="primary-button" disabled={mutating}>
            Save access
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={mutating}
            onClick={() => void handleDeleteClick()}
          >
            Delete document
          </button>
        </div>
      </form>
    </>
  );
}

function DocumentFileIcon() {
  return (
    <span className="document-manage-modal-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false">
        <path
          d="M8 4.5h5.2L17 8.3V19.5A1.5 1.5 0 0 1 15.5 21h-9A1.5 1.5 0 0 1 5 19.5v-15A1.5 1.5 0 0 1 6.5 3H8v1.5z"
          fill="none"
          stroke="currentColor"
          strokeLinejoin="round"
          strokeWidth="1.75"
        />
        <path
          d="M13 4.5V9h4.5"
          fill="none"
          stroke="currentColor"
          strokeLinejoin="round"
          strokeWidth="1.75"
        />
      </svg>
    </span>
  );
}

function DocumentAccessPicker({
  labelId,
  selectedUserIds,
  assignableUsers,
  disabled,
  onChange,
}: {
  labelId: string;
  selectedUserIds: string[];
  assignableUsers: HierarchyAssignableUser[];
  disabled: boolean;
  onChange: (assignedUserIds: string[]) => void;
}) {
  const [query, setQuery] = useState("");
  const selectedSet = useMemo(() => new Set(selectedUserIds), [selectedUserIds]);
  const normalizedQuery = query.trim().toLowerCase();

  const visibleUsers = useMemo(() => {
    const matches = normalizedQuery
      ? assignableUsers.filter((user) =>
          `${user.name} ${user.email}`.toLowerCase().includes(normalizedQuery),
        )
      : assignableUsers;
    return matches.slice(0, 12);
  }, [assignableUsers, normalizedQuery]);

  const selectedUsers = useMemo(
    () =>
      selectedUserIds
        .map((userId) => assignableUsers.find((user) => user.user_id === userId))
        .filter((user): user is HierarchyAssignableUser => Boolean(user)),
    [assignableUsers, selectedUserIds],
  );

  function handleToggle(userId: string) {
    if (selectedSet.has(userId)) {
      onChange(selectedUserIds.filter((entry) => entry !== userId));
      return;
    }
    onChange([...selectedUserIds, userId]);
  }

  function handleRemoveChip(userId: string) {
    onChange(selectedUserIds.filter((entry) => entry !== userId));
  }

  return (
    <div className="document-access-picker" aria-labelledby={labelId}>
      {selectedUsers.length ? (
        <div className="document-access-chips" aria-label="Assigned users">
          {selectedUsers.map((user) => (
            <button
              key={user.user_id}
              type="button"
              className="document-access-chip"
              disabled={disabled}
              aria-label={`Remove ${user.name || user.email}`}
              onClick={() => handleRemoveChip(user.user_id)}
            >
              <span>{user.name || user.email}</span>
              <span aria-hidden="true">×</span>
            </button>
          ))}
        </div>
      ) : (
        <p className="document-access-empty">No users assigned yet.</p>
      )}

      <input
        type="search"
        value={query}
        placeholder="Search people"
        disabled={disabled || assignableUsers.length === 0}
        autoComplete="off"
        spellCheck={false}
        onChange={(event) => setQuery(event.target.value)}
      />

      <div className="document-access-options">
        {visibleUsers.map((user) => {
          const active = selectedSet.has(user.user_id);
          return (
            <button
              key={user.user_id}
              type="button"
              className={active ? "active" : ""}
              disabled={disabled}
              aria-pressed={active}
              onClick={() => handleToggle(user.user_id)}
            >
              <span className="document-access-check" aria-hidden="true">
                {active ? "✓" : ""}
              </span>
              <span className="document-access-option-copy">
                <strong>{user.name || user.email}</strong>
                <span>{user.email}</span>
              </span>
            </button>
          );
        })}
        {!assignableUsers.length ? (
          <span className="document-access-options-empty">No assignable users in this workspace.</span>
        ) : null}
        {assignableUsers.length > 0 && !visibleUsers.length ? (
          <span className="document-access-options-empty">No users match your search.</span>
        ) : null}
      </div>
    </div>
  );
}
