export function ConnectorDisconnectDialog({
  connectorName,
  open,
  loading,
  onCancel,
  onConfirm,
}: {
  connectorName: string;
  open: boolean;
  loading?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="connector-modal-backdrop connector-disconnect-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !loading) {
          onCancel();
        }
      }}
    >
      <div className="home-disconnect-modal" role="dialog" aria-modal="true" aria-labelledby="connector-disconnect-heading">
        <header className="home-disconnect-header">
          <div>
            <h2 id="connector-disconnect-heading">Disconnect {connectorName}</h2>
            <p>This removes your account connection for all workspaces.</p>
          </div>
          <button
            type="button"
            className="connector-close-button"
            aria-label="Close disconnect warning"
            disabled={loading}
            onClick={onCancel}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
            </svg>
          </button>
        </header>
        <div className="home-disconnect-body">
          <div className="home-disconnect-warning">
            <strong>You will lose access to all {connectorName} data.</strong>
            <span>Existing workspace sources may stop syncing until you connect again.</span>
          </div>
        </div>
        <div className="home-disconnect-actions">
          <button type="button" className="modal-cancel-button" disabled={loading} onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="danger-button" disabled={loading} onClick={onConfirm}>
            {loading ? "Disconnecting..." : "Disconnect"}
          </button>
        </div>
      </div>
    </div>
  );
}
