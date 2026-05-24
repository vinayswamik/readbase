import type { ReactNode } from "react";

import type { WorkspaceMember } from "../../../types";

export function KnowledgeConnectorBody({
  connectorName,
  connected,
  configured,
  accountTitle,
  accountDetail,
  disconnectedDetail,
  query,
  queryPlaceholder,
  loading,
  availableTitle,
  emptyAvailableText,
  workspaceTitle,
  emptyWorkspaceText,
  members,
  loadingMembers,
  canManageWorkspace,
  error,
  status,
  availableRows,
  workspaceRows,
  onConnect,
  onDisconnect,
  onQueryChange,
  onSearch,
  onConnectorManagerToggle,
  onClose,
}: {
  connectorName: string;
  connected: boolean;
  configured: boolean;
  accountTitle: string;
  accountDetail: string;
  disconnectedDetail: string;
  query: string;
  queryPlaceholder: string;
  loading: boolean;
  availableTitle: string;
  emptyAvailableText: string;
  workspaceTitle: string;
  emptyWorkspaceText: string;
  members: WorkspaceMember[];
  loadingMembers: boolean;
  canManageWorkspace: boolean;
  error: string | null;
  status: string;
  availableRows: ReactNode[];
  workspaceRows: ReactNode[];
  onConnect: () => void;
  onDisconnect: () => void;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
  onConnectorManagerToggle: (member: WorkspaceMember) => void;
  onClose: () => void;
}) {
  return (
    <div className="connector-modal-body">
      <div className="connector-account-row">
        <div>
          <strong>{connected ? accountTitle : `${connectorName} account`}</strong>
          <span>{connected ? accountDetail : configured ? disconnectedDetail : `${connectorName} OAuth is not configured on the backend.`}</span>
        </div>
        <button
          type="button"
          className={connected ? "secondary-action-button" : "primary-button"}
          disabled={loading || !configured}
          onClick={connected ? onDisconnect : onConnect}
        >
          {connected ? "Disconnect" : `Connect ${connectorName}`}
        </button>
      </div>

      {connected ? (
        <>
          <div className="connector-search-row">
            <input value={query} placeholder={queryPlaceholder} onChange={(event) => onQueryChange(event.target.value)} />
            <button type="button" className="secondary-action-button" disabled={loading} onClick={onSearch}>
              Search
            </button>
          </div>
          <section className="connector-access-list">
            <h3>{availableTitle}</h3>
            {loading && !availableRows.length ? <div className="status-text compact">Loading...</div> : null}
            {!loading && !availableRows.length ? <div className="status-text compact">{emptyAvailableText}</div> : null}
            {availableRows}
          </section>
          <section className="connector-access-list">
            <h3>Connector managers</h3>
            {loadingMembers ? <div className="status-text compact">Loading workspace users...</div> : null}
            {members.map((member) => (
              <label className="connector-access-row" key={member.email}>
                <input
                  type="checkbox"
                  checked={member.connector_manager}
                  disabled={!canManageWorkspace || member.is_owner}
                  onChange={() => onConnectorManagerToggle(member)}
                />
                <span>{member.email}</span>
                <strong>{member.is_owner ? "Owner" : member.connector_manager ? "Manager" : "Member"}</strong>
              </label>
            ))}
          </section>
          <section className="connector-access-list">
            <h3>{workspaceTitle}</h3>
            {!workspaceRows.length ? <div className="status-text compact">{emptyWorkspaceText}</div> : null}
            {workspaceRows}
          </section>
        </>
      ) : null}

      {error ? <div className="status-text error-text">{error}</div> : null}
      {status ? <div className="status-text">{status}</div> : null}
      <div className="connector-modal-actions">
        <button type="button" className="primary-button" onClick={onClose}>
          Done
        </button>
      </div>
    </div>
  );
}

