import { useEffect, useMemo, useState, type ChangeEvent, type MouseEvent } from "react";

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
import { WorkspaceAdditionalDocumentsSection } from "./WorkspaceAdditionalDocumentsSection";
import type { WorkspaceAdditionalDocument } from "./workspaceAdditionalDocuments";

export function WorkspaceSourcesPanel({
  workspace,
  refreshKey = 0,
  collapsed = false,
  onToggleCollapsed,
  onConnect,
  onManage,
  additionalDocuments,
  onManageDocument,
  onSessionExpired,
}: {
  workspace: Workspace;
  refreshKey?: number;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  onConnect: (connectorId: ConnectorId) => void;
  onManage: (connectorId: ConnectorId, event: MouseEvent<HTMLButtonElement>) => void;
  additionalDocuments: {
    documents: WorkspaceAdditionalDocument[];
    loading: boolean;
    uploading: boolean;
    mutating: boolean;
    error: string | null;
    acceptedDocumentTypes: string;
    managedDocumentId: string | null;
    onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  };
  onManageDocument: (document: WorkspaceAdditionalDocument, event: MouseEvent<HTMLButtonElement>) => void;
  onSessionExpired: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overviewInput, setOverviewInput] = useState<WorkspaceSourcesInput | null>(null);
  const [expandedHolders, setExpandedHolders] = useState<Partial<Record<ConnectorId, boolean>>>({});
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setOverviewInput(null);
    setExpandedHolders({});
    setSearchQuery("");

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
  }, [onSessionExpired, workspace.workspace_id]);

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

  const allHolders = useMemo(() => {
    if (!overviewInput) {
      return [];
    }
    return buildConnectorSourcesHolders(overviewInput);
  }, [overviewInput]);

  const holders = useMemo(
    () => filterSourcesModalHolders(allHolders, searchQuery),
    [allHolders, searchQuery],
  );

  const connectedHolders = useMemo(
    () => allHolders.filter((holder) => holder.connected),
    [allHolders],
  );

  const hasConnectorHolders = !loading && !error && holders.length > 0;
  const connectorsEmpty = !loading && !error && holders.length === 0;

  function handleExpandPanel() {
    if (collapsed) {
      onToggleCollapsed?.();
    }
  }

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

  return (
    <aside
      className={`workspace-sources-panel${collapsed ? " collapsed" : ""}`}
      aria-labelledby="workspace-sources-heading"
    >
      <button
        type="button"
        className="workspace-sources-panel-collapse-toggle"
        aria-expanded={!collapsed}
        aria-controls="workspace-sources-panel-content"
        aria-label={collapsed ? "Expand sources panel" : "Collapse sources panel"}
        onClick={() => onToggleCollapsed?.()}
      >
        <PanelCollapseIcon collapsed={collapsed} />
      </button>
      <div className="workspace-sources-panel-body">
        <div
          className="workspace-sources-panel-rail"
          aria-label="Connected connectors"
          aria-hidden={!collapsed}
        >
          {loading ? (
            <span className="workspace-sources-rail-empty" aria-hidden="true" />
          ) : connectedHolders.length === 0 ? (
            <span className="workspace-sources-rail-empty" aria-hidden="true" />
          ) : (
            connectedHolders.map((holder) => (
              <button
                key={holder.connector.id}
                type="button"
                className="workspace-sources-rail-connector"
                aria-label={`Expand sources and open ${holder.connector.name}`}
                title={holder.connector.name}
                onClick={handleExpandPanel}
                tabIndex={collapsed ? 0 : -1}
              >
                <ConnectorLogo connectorId={holder.connector.id} />
              </button>
            ))
          )}
        </div>
        <div
          id="workspace-sources-panel-content"
          className={`workspace-sources-panel-shell${connectorsEmpty ? " connectors-empty" : ""}`}
          aria-hidden={collapsed}
        >
          <header className="workspace-sources-header">
            <div className="workspace-sources-header-copy">
              <h2 id="workspace-sources-heading">Sources</h2>
              <p>Connect and manage accounts.</p>
            </div>
          </header>
          <div className="workspace-sources-search-row">
            <label className="workspace-sources-search-field">
              <span className="workspace-sources-search-icon" aria-hidden="true">
                <SearchIcon />
              </span>
              <input
                type="search"
                className="workspace-sources-search-input"
                value={searchQuery}
                placeholder="Search connectors"
                aria-label="Search connectors"
                onChange={(event) => setSearchQuery(event.target.value)}
              />
              {searchQuery ? (
                <button
                  type="button"
                  className="workspace-sources-search-clear"
                  aria-label="Clear search"
                  onClick={() => setSearchQuery("")}
                >
                  <ClearIcon />
                </button>
              ) : null}
            </label>
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
                  onManage={(event) => onManage(holder.connector.id, event)}
                />
              ))
            )}
          </div>
          <WorkspaceAdditionalDocumentsSection
            documents={additionalDocuments.documents}
            loading={additionalDocuments.loading}
            uploading={additionalDocuments.uploading}
            mutating={additionalDocuments.mutating}
            error={additionalDocuments.error}
            acceptedDocumentTypes={additionalDocuments.acceptedDocumentTypes}
            managedDocumentId={additionalDocuments.managedDocumentId}
            onFileChange={additionalDocuments.onFileChange}
            onManageDocument={onManageDocument}
          />
        </div>
      </div>
    </aside>
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
  onManage: (event: MouseEvent<HTMLButtonElement>) => void;
}) {
  const sourceCount = holder.sources.length;
  const sourceCountLabel =
    sourceCount > 0 ? `${sourceCount} source${sourceCount === 1 ? "" : "s"}` : null;
  const connectionStatusLabel = holder.connected ? "Connected" : "Disconnected";
  const isSlack = holder.connector.id === "slack";
  const hasSources = holder.sources.length > 0;

  return (
    <section
      className={`workspace-sources-holder${expanded ? " expanded" : ""}${isSlack ? " slack-sources" : ""}`}
    >
      <div className="workspace-sources-holder-header">
        <div className="workspace-sources-holder-leading">
          <button
            type="button"
            className="workspace-sources-toggle"
            aria-expanded={expanded}
            aria-controls={`workspace-sources-panel-${holder.connector.id}`}
            aria-label={hasSources ? `Toggle ${holder.connector.name} sources` : undefined}
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
          </button>
          <ConnectorLogo connectorId={holder.connector.id} />
          <span className="workspace-sources-holder-name">{holder.connector.name}</span>
          <span
            className={`workspace-sources-status-dot${holder.connected ? " connected" : " disconnected"}`}
            role="status"
            tabIndex={0}
            aria-label={connectionStatusLabel}
            data-tooltip={connectionStatusLabel}
          />
          {sourceCountLabel ? (
            <span className="workspace-sources-count">{sourceCountLabel}</span>
          ) : null}
        </div>
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
          <button type="button" className="workspace-sources-connect" onClick={onConnect}>
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

function PanelCollapseIcon({ collapsed }: { collapsed: boolean }) {
  const strokeProps = {
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 1.35,
  };

  return (
    <svg viewBox="0 0 16 16" focusable="false" aria-hidden="true">
      {collapsed ? (
        <>
          <path d="M5 4 8 8 5 12" {...strokeProps} />
          <path d="M9 4 12 8 9 12" {...strokeProps} />
        </>
      ) : (
        <>
          <path d="M11 4 8 8 11 12" {...strokeProps} />
          <path d="M7 4 4 8 7 12" {...strokeProps} />
        </>
      )}
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M16.2 16.2 21 21"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}

function ClearIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M8.5 8.5l7 7M15.5 8.5l-7 7"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}
