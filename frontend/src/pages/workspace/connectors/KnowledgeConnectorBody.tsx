import type { ReactNode } from "react";

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
  error,
  status,
  availableRows,
  workspaceRows,
  onConnect,
  onDisconnect,
  onQueryChange,
  onSearch,
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
  error: string | null;
  status: string;
  availableRows: ReactNode[];
  workspaceRows: ReactNode[];
  onConnect: () => void;
  onDisconnect: () => void;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
  onClose: () => void;
}) {
  return (
    <div className="connector-modal-body">
      <div className="connector-account-row">
        <div>
          <strong>{connected ? accountTitle : `${connectorName} account`}</strong>
          <span>{connected ? accountDetail : configured ? disconnectedDetail : `${connectorName} OAuth is not configured on the backend.`}</span>
        </div>
        {connected ? (
          <span className="connector-account-status">Connected</span>
        ) : (
          <button
            type="button"
            className="primary-button"
            disabled={loading || !configured}
            onClick={onConnect}
          >
            {`Connect ${connectorName}`}
          </button>
        )}
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
            <h3>{workspaceTitle}</h3>
            {!workspaceRows.length ? <div className="status-text compact">{emptyWorkspaceText}</div> : null}
            {workspaceRows}
          </section>
        </>
      ) : null}
    </div>
  );
}

