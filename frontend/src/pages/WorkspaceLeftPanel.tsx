import type { FormEvent } from "react";

import type {
  AuthUser,
  HierarchyAssignableUser,
  HierarchyNode,
  IndexedRepo,
  Workspace,
} from "../types";
import { CONNECTORS, type ConnectorId } from "./workspace/connectors/connectors";
import { ConnectorPanel } from "./workspace/connectors/ConnectorPanel";
import { AssignableUserPicker, CreateNodeForm, ParentNodeSelect, RepoList } from "./workspace/WorkspacePanelControls";

export type SidebarTab = "repository" | "graph" | "details";

export type CreateNodeDraft = {
  displayName: string;
  assignedUserId: string;
  parentNodeId: string;
};

export { CONNECTORS } from "./workspace/connectors/connectors";
export { ConnectorLogo } from "./workspace/connectors/ConnectorLogo";
export { ConnectorSetupModal } from "./workspace/connectors/ConnectorSetupModal";
export type { ConnectorConfig, ConnectorId } from "./workspace/connectors/connectors";

export function WorkspaceLeftPanel({
  workspace,
  mode,
  sidebarTab,
  userRole,
  repos,
  selectedRepoId,
  repoListError,
  graphMutating,
  graphStatus,
  availableAssignees,
  parentOptions,
  ownNode,
  selectedNode,
  canManageSelectedNode,
  editTitle,
  editAssignedUserId,
  reassignOptions,
  canDeleteSelectedNode,
  reparentNodeId,
  reparentOptions,
  onBack,
  onSidebarTabChange,
  onRepoSelect,
  onCreateNode,
  onUpdateSelectedNode,
  onDeleteSelectedNode,
  onEditTitleChange,
  onEditAssignedUserIdChange,
  onReparentNodeIdChange,
  onReparentSelectedNode,
  onOpenConnector,
}: {
  workspace: Workspace;
  mode: string;
  sidebarTab: SidebarTab;
  userRole: AuthUser["role"];
  repos: IndexedRepo[];
  selectedRepoId: string | null;
  repoListError: string | null;
  graphMutating: boolean;
  graphStatus: string;
  availableAssignees: HierarchyAssignableUser[];
  parentOptions: HierarchyNode[];
  ownNode: HierarchyNode | null;
  selectedNode: HierarchyNode | null;
  canManageSelectedNode: boolean;
  editTitle: string;
  editAssignedUserId: string;
  reassignOptions: HierarchyAssignableUser[];
  canDeleteSelectedNode: boolean;
  reparentNodeId: string;
  reparentOptions: HierarchyNode[];
  onBack: () => void;
  onSidebarTabChange: (tab: SidebarTab) => void;
  onRepoSelect: (repo: IndexedRepo) => void;
  onCreateNode: (draft: CreateNodeDraft) => Promise<boolean>;
  onUpdateSelectedNode: (event: FormEvent<HTMLFormElement>) => void;
  onDeleteSelectedNode: () => void;
  onEditTitleChange: (title: string) => void;
  onEditAssignedUserIdChange: (assignedUserId: string) => void;
  onReparentNodeIdChange: (nodeId: string) => void;
  onReparentSelectedNode: (event: FormEvent<HTMLFormElement>) => void;
  onOpenConnector: (connectorId: ConnectorId) => void;
}) {
  return (
    <aside className="graph-sidebar" aria-label="Workspace controls">
      <div className="sidebar-topline">
        <button type="button" className="back-button" onClick={onBack}>
          Back
        </button>
        <span className="status-chip">{mode}</span>
      </div>
      <header className="brand sidebar-brand">
        <div>
          <h1>{workspace.name}</h1>
          <p>Hierarchy graph</p>
        </div>
      </header>

      <ConnectorPanel
        connectors={CONNECTORS}
        onOpen={onOpenConnector}
      />

      <div className="control-tabs" role="tablist" aria-label="Workspace control sections">
        <button
          type="button"
          role="tab"
          aria-selected={sidebarTab === "graph"}
          className={sidebarTab === "graph" ? "active" : ""}
          onClick={() => onSidebarTabChange("graph")}
        >
          Graph
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={sidebarTab === "details"}
          className={sidebarTab === "details" ? "active" : ""}
          onClick={() => onSidebarTabChange("details")}
        >
          Details
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={sidebarTab === "repository"}
          className={sidebarTab === "repository" ? "active" : ""}
          onClick={() => onSidebarTabChange("repository")}
        >
          Repos
        </button>
      </div>

      {sidebarTab === "repository" ? (
        <div className="tab-panel" role="tabpanel">
          <section className="tool-section" aria-labelledby="indexed-repos-heading">
            <div className="tool-section-header">
              <div>
                <h2 id="indexed-repos-heading">Indexed Repos</h2>
                <p>Select context for the ask widget.</p>
              </div>
            </div>
            <RepoList
              repos={repos}
              selectedRepoId={selectedRepoId}
              error={repoListError}
              onSelect={onRepoSelect}
            />
          </section>
        </div>
      ) : null}

      {sidebarTab === "graph" ? (
        <div className="tab-panel" role="tabpanel">
          <section className="tool-section" aria-labelledby="graph-create-heading">
            <div className="tool-section-header">
              <div>
                <h2 id="graph-create-heading">Create Node</h2>
                <p>Add hierarchy entries to the board.</p>
              </div>
            </div>
            <CreateNodeForm
              userRole={userRole}
              disabled={graphMutating}
              availableAssignees={availableAssignees}
              parentOptions={parentOptions}
              ownNode={ownNode}
              onCreate={onCreateNode}
            />
            {graphStatus ? <div className="status-text">{graphStatus}</div> : null}
          </section>
        </div>
      ) : null}

      {sidebarTab === "details" ? (
        <div className="tab-panel" role="tabpanel">
          <section className="tool-section" aria-labelledby="node-actions-heading">
            <div className="tool-section-header">
              <div>
                <h2 id="node-actions-heading">Selected Node</h2>
                <p>Inspect and manage the active node.</p>
              </div>
            </div>
            {selectedNode ? (
              <form className="graph-control-form" onSubmit={onUpdateSelectedNode}>
                <div className="selected-node-meta">
                  <span>{selectedNode.assigned_user_email || "Assigned user"}</span>
                  <strong>{selectedNode.display_name}</strong>
                </div>
                <div className="status-text compact">
                  Assigned to {selectedNode.assigned_user_name || selectedNode.assigned_user_email || "workspace user"}.
                </div>
                <label htmlFor="editNodeTitle">Rename</label>
                <input
                  id="editNodeTitle"
                  value={editTitle}
                  disabled={graphMutating || !canManageSelectedNode}
                  onChange={(event) => onEditTitleChange(event.target.value)}
                />
                <label id="editAssignedUserLabel">Assigned user</label>
                <AssignableUserPicker
                  value={editAssignedUserId}
                  disabled={graphMutating || !canManageSelectedNode}
                  availableAssignees={reassignOptions}
                  labelId="editAssignedUserLabel"
                  emptyLabel="No assignee selected"
                  searchPlaceholder="Search assignable users"
                  onChange={onEditAssignedUserIdChange}
                />
                <button
                  type="submit"
                  className="secondary-action-button"
                  disabled={
                    graphMutating ||
                    !canManageSelectedNode ||
                    !editTitle.trim() ||
                    !editAssignedUserId
                  }
                >
                  Save node
                </button>
                <button
                  type="button"
                  className="danger-button"
                  disabled={graphMutating || !canDeleteSelectedNode}
                  onClick={onDeleteSelectedNode}
                >
                  Delete node
                </button>
              </form>
            ) : (
              <div className="empty-panel-state">Select a node on the board to view details.</div>
            )}
          </section>
          {selectedNode && userRole === "admin" ? (
            <section className="tool-section" aria-labelledby="node-parent-heading">
              <div className="tool-section-header">
                <div>
                  <h2 id="node-parent-heading">Parent</h2>
                  <p>Move this node under another node or make it top-level.</p>
                </div>
              </div>
              <form className="graph-control-form" onSubmit={onReparentSelectedNode}>
                <label id="reparentNodeLabel">Parent node</label>
                <ParentNodeSelect
                  value={reparentNodeId}
                  disabled={graphMutating}
                  userRole={userRole}
                  parentOptions={reparentOptions}
                  labelId="reparentNodeLabel"
                  onChange={onReparentNodeIdChange}
                />
                <button type="submit" className="secondary-action-button" disabled={graphMutating}>
                  Update parent
                </button>
              </form>
            </section>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}
