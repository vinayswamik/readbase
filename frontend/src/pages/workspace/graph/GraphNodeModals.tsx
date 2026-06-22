import type { FormEvent, ReactNode } from "react";

import type { HierarchyAssignableUser, HierarchyNode } from "../../../types";
import type { CreateNodeDraft } from "./types";
import {
  AssignableUserPicker,
  CreateNodeForm,
  ParentNodeSelect,
} from "../WorkspacePanelControls";

type GraphModalShellProps = {
  open: boolean;
  title: string;
  description: string;
  onClose: () => void;
  children: ReactNode;
};

function GraphModalShell({ open, title, description, onClose, children }: GraphModalShellProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="connector-modal-backdrop graph-node-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="connector-modal graph-node-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="graph-node-modal-heading"
      >
        <header className="connector-modal-header">
          <div className="connector-modal-title">
            <h2 id="graph-node-modal-heading">{title}</h2>
          </div>
          <button type="button" className="connector-close-button" aria-label="Close" onClick={onClose}>
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
        <div className="connector-modal-body graph-node-modal-body">
          <p className="graph-node-modal-description">{description}</p>
          {children}
        </div>
      </div>
    </div>
  );
}

export function GraphAddNodeModal({
  open,
  canManageWorkspace,
  disabled,
  parentOptions,
  ownNode,
  onClose,
  onCreate,
}: {
  open: boolean;
  canManageWorkspace: boolean;
  disabled: boolean;
  parentOptions: HierarchyNode[];
  ownNode: HierarchyNode | null;
  onClose: () => void;
  onCreate: (draft: CreateNodeDraft) => Promise<boolean | string>;
}) {
  return (
    <GraphModalShell
      open={open}
      title="Add node"
      description="Invite someone and add them to the hierarchy graph."
      onClose={onClose}
    >
      <CreateNodeForm
        canManageWorkspace={canManageWorkspace}
        disabled={disabled}
        parentOptions={parentOptions}
        ownNode={ownNode}
        onCreate={onCreate}
        onCreated={(result) => {
          if (result !== false && typeof result !== "string") {
            onClose();
          }
        }}
      />
    </GraphModalShell>
  );
}

export function GraphEditNodeModal({
  open,
  selectedNode,
  canManageSelectedNode,
  canDeleteSelectedNode,
  canManageWorkspace,
  graphMutating,
  editTitle,
  editAssignedUserId,
  reassignOptions,
  reparentNodeId,
  reparentOptions,
  onClose,
  onEditTitleChange,
  onEditAssignedUserIdChange,
  onUpdateSelectedNode,
  onDeleteSelectedNode,
  onReparentNodeIdChange,
  onReparentSelectedNode,
}: {
  open: boolean;
  selectedNode: HierarchyNode | null;
  canManageSelectedNode: boolean;
  canDeleteSelectedNode: boolean;
  canManageWorkspace: boolean;
  graphMutating: boolean;
  editTitle: string;
  editAssignedUserId: string;
  reassignOptions: HierarchyAssignableUser[];
  reparentNodeId: string;
  reparentOptions: HierarchyNode[];
  onClose: () => void;
  onEditTitleChange: (title: string) => void;
  onEditAssignedUserIdChange: (assignedUserId: string) => void;
  onUpdateSelectedNode: (event: FormEvent<HTMLFormElement>) => void;
  onDeleteSelectedNode: () => void;
  onReparentNodeIdChange: (nodeId: string) => void;
  onReparentSelectedNode: (event: FormEvent<HTMLFormElement>) => void;
}) {
  if (!selectedNode) {
    return null;
  }

  return (
    <GraphModalShell
      open={open}
      title="Edit node"
      description="Update the role, assignment, or parent for this hierarchy node."
      onClose={onClose}
    >
      <form className="graph-control-form" onSubmit={onUpdateSelectedNode}>
        <div className="selected-node-meta">
          <span>{selectedNode.assigned_user_email || "Assigned user"}</span>
          <strong>{selectedNode.display_name}</strong>
        </div>
        <div className="status-text compact">
          Assigned to{" "}
          {selectedNode.assigned_user_name || selectedNode.assigned_user_email || "workspace user"}.
        </div>
        <label htmlFor="modalEditNodeTitle">Display name</label>
        <input
          id="modalEditNodeTitle"
          value={editTitle}
          disabled={graphMutating || !canManageSelectedNode}
          onChange={(event) => onEditTitleChange(event.target.value)}
        />
        <label id="modalEditAssignedUserLabel">Assigned user</label>
        <AssignableUserPicker
          value={editAssignedUserId}
          disabled={graphMutating || !canManageSelectedNode}
          availableAssignees={reassignOptions}
          labelId="modalEditAssignedUserLabel"
          emptyLabel="No assignee selected"
          searchPlaceholder="Search assignable users"
          onChange={onEditAssignedUserIdChange}
        />
        <div className="graph-node-modal-actions">
          <button
            type="submit"
            className="primary-button"
            disabled={
              graphMutating || !canManageSelectedNode || !editTitle.trim() || !editAssignedUserId
            }
          >
            Save changes
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={graphMutating || !canDeleteSelectedNode}
            onClick={onDeleteSelectedNode}
          >
            Delete node
          </button>
        </div>
      </form>

      {canManageWorkspace ? (
        <form className="graph-control-form graph-node-modal-reparent" onSubmit={onReparentSelectedNode}>
          <h3>Parent</h3>
          <p className="status-text compact">Move this node under another node or make it top-level.</p>
          <label id="modalReparentNodeLabel">Parent node</label>
          <ParentNodeSelect
            value={reparentNodeId}
            disabled={graphMutating}
            canManageWorkspace={canManageWorkspace}
            parentOptions={reparentOptions}
            labelId="modalReparentNodeLabel"
            onChange={onReparentNodeIdChange}
          />
          <button type="submit" className="secondary-action-button" disabled={graphMutating}>
            Update parent
          </button>
        </form>
      ) : null}
    </GraphModalShell>
  );
}
