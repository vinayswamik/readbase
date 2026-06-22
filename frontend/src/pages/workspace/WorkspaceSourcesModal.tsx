import { useEffect, useMemo, useState } from "react";

import { getErrorMessage, isSessionExpiredMessage } from "../../api";
import type { Workspace } from "../../types";
import { ConnectorLogo } from "./connectors/ConnectorLogo";
import type { ConnectorId } from "./connectors/connectors";
import {
  buildConnectorSourcesHolders,
  fetchWorkspaceSourcesInput,
  filterSourcesModalHolders,
  type ConnectorSourcesHolder,
  type WorkspaceSourcesInput,
} from "./workspaceSourcesOverview";

type WorkspaceSourcesModalProps = {
  open: boolean;
  workspace: Workspace;
  refreshKey?: number;
  onClose: () => void;
  onConnect: (connectorId: ConnectorId) => void;
  onManage: (connectorId: ConnectorId) => void;
  onSessionExpired: () => void;
};

export function WorkspaceSourcesModal({
  open,
  workspace,
  refreshKey = 0,
  onClose,
  onConnect,
  onManage,
  onSessionExpired,
}: WorkspaceSourcesModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overviewInput, setOverviewInput] = useState<WorkspaceSourcesInput | null>(null);
  const [expandedHolders, setExpandedHolders] = useState<Partial<Record<ConnectorId, boolean>>>({});
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (!open) {
      setOverviewInput(null);
      setExpandedHolders({});
      setSearchQuery("");
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setOverviewInput(null);
    setExpandedHolders({});

    void fetchWorkspaceSourcesInput(workspace.workspace_id)
      .then((result) => {
        if (!cancelled) {
          setOverviewInput(result);
          const holders = buildConnectorSourcesHolders(result);
          setExpandedHolders(buildInitialExpandedState(holders));
        }
      })
      .catch((caughtError) => {
        if (cancelled) {
          return;
        }
        const message = getErrorMessage(caughtError) || "Failed to load sources.";
        setError(message);
        if (isSessionExpiredMessage(message)) {
          onSessionExpired();
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, onSessionExpired, workspace.workspace_id]);

  useEffect(() => {
    if (refreshKey === 0) {
      return;
    }

    let cancelled = false;

    void fetchWorkspaceSourcesInput(workspace.workspace_id)
      .then((result) => {
        if (!cancelled) {
          setOverviewInput(result);
        }
      })
      .catch((caughtError) => {
        if (cancelled) {
          return;
        }
        const message = getErrorMessage(caughtError) || "Failed to load sources.";
        setError(message);
        if (isSessionExpiredMessage(message)) {
          onSessionExpired();
        }
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey, onSessionExpired, workspace.workspace_id]);

  const holders = useMemo(() => {
    if (!overviewInput) {
      return [];
    }
    return filterSourcesModalHolders(buildConnectorSourcesHolders(overviewInput), searchQuery);
  }, [overviewInput, searchQuery]);

  function toggleHolder(connectorId: ConnectorId) {
    const holder = holders.find((entry) => entry.connector.id === connectorId);
    if (!holder || holder.sources.length === 0) {
      return;
    }
    setExpandedHolders((current) => ({
      ...current,
      [connectorId]: !current[connectorId],
    }));
  }

  if (!open) {
    return null;
  }

  return (
    <div
      className="connector-modal-backdrop workspace-sources-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="workspace-sources-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workspace-sources-heading"
      >
        <header className="workspace-sources-header">
          <div className="workspace-sources-header-copy">
            <h2 id="workspace-sources-heading">Sources</h2>
            <p>Connect accounts and manage indexed content for this workspace.</p>
          </div>
          <button type="button" className="connector-close-button" aria-label="Close sources" onClick={onClose}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
            </svg>
          </button>
        </header>
        <div className="workspace-sources-search-row">
          <input
            type="search"
            value={searchQuery}
            placeholder="Search connectors"
            aria-label="Search connectors"
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </div>
        <div className="workspace-sources-body">
          {loading ? (
            <p className="workspace-sources-empty">Loading sources...</p>
          ) : error ? (
            <p className="workspace-sources-empty">{error}</p>
          ) : holders.length === 0 ? (
            <p className="workspace-sources-empty">
              {searchQuery.trim()
                ? "No connectors match your search."
                : "No connectors connected yet. Search above to connect Slack, Jira, Notion, and more."}
            </p>
          ) : (
            holders.map((holder) => (
              <ConnectorSourcesHolderCard
                key={holder.connector.id}
                holder={holder}
                expanded={Boolean(expandedHolders[holder.connector.id])}
                onToggle={() => toggleHolder(holder.connector.id)}
                onConnect={() => onConnect(holder.connector.id)}
                onManage={() => onManage(holder.connector.id)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ConnectorSourcesHolderCard({
  holder,
  expanded,
  onToggle,
  onConnect,
  onManage,
}: {
  holder: ConnectorSourcesHolder;
  expanded: boolean;
  onToggle: () => void;
  onConnect: () => void;
  onManage: () => void;
}) {
  const sourceCount = holder.sources.length;
  const sourceCountLabel =
    sourceCount > 0
      ? `${sourceCount} source${sourceCount === 1 ? "" : "s"}`
      : holder.connected
        ? "Connected"
        : "Not connected";
  const isSlack = holder.connector.id === "slack";
  const hasSources = holder.sources.length > 0;

  return (
    <section
      className={`workspace-sources-holder${expanded ? " expanded" : ""}${isSlack ? " slack-sources" : ""}`}
    >
      <div className="workspace-sources-holder-header">
        <button
          type="button"
          className="workspace-sources-toggle"
          aria-expanded={expanded}
          aria-controls={`workspace-sources-panel-${holder.connector.id}`}
          onClick={onToggle}
          disabled={!hasSources}
        >
          <span className={`workspace-sources-chevron${expanded ? " open" : ""}`} aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M12.7071 14.7071C12.3166 15.0976 11.6834 15.0976 11.2929 14.7071L6.29289 9.70711C5.90237 9.31658 5.90237 8.68342 6.29289 8.29289C6.68342 7.90237 7.31658 7.90237 7.70711 8.29289L12 12.5858L16.2929 8.29289C16.6834 7.90237 17.3166 7.90237 17.7071 8.29289C18.0976 8.68342 18.0976 9.31658 17.7071 9.70711L12.7071 14.7071Z"
                fill="currentColor"
              />
            </svg>
          </span>
          <ConnectorLogo connectorId={holder.connector.id} />
          <span className="workspace-sources-holder-name">{holder.connector.name}</span>
          <span className={`workspace-sources-count${holder.connected ? "" : " disconnected"}`}>
            {sourceCountLabel}
          </span>
        </button>
        {holder.connected ? (
          <button
            type="button"
            className="home-connection-state connected workspace-sources-manage"
            onClick={onManage}
          >
            <span>Manage</span>
            <span className="home-manage-arrow" aria-hidden="true">
              <svg viewBox="0 0 16 16" focusable="false">
                <path d="M5 4h7v7" />
                <path d="m4 12 8-8" />
              </svg>
            </span>
          </button>
        ) : (
          <button type="button" className="primary-button workspace-sources-connect" onClick={onConnect}>
            Connect
          </button>
        )}
      </div>
      <div
        className={`workspace-sources-collapse${expanded ? " open" : ""}`}
        id={`workspace-sources-panel-${holder.connector.id}`}
        aria-hidden={!expanded}
      >
        <div className="workspace-sources-collapse-inner">
          {hasSources ? (
            <>
              <div className="workspace-source-columns" aria-hidden="true">
                <span>Source</span>
                {isSlack ? <span>Workspace</span> : null}
                <span>Type</span>
              </div>
              <ul className="workspace-sources-holder-rows">
                {holder.sources.map((source, index) => (
                  <li className="workspace-source-row" key={`${source.id}:${index}`}>
                    <span>{source.name}</span>
                    {isSlack ? <span className="workspace-source-workspace">{source.workspace || "—"}</span> : null}
                    <strong>{source.type}</strong>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="workspace-sources-holder-empty">No sources added to this workspace yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function buildInitialExpandedState(holders: ConnectorSourcesHolder[]): Partial<Record<ConnectorId, boolean>> {
  const expanded: Partial<Record<ConnectorId, boolean>> = {};
  for (const holder of holders) {
    expanded[holder.connector.id] = false;
  }
  return expanded;
}
