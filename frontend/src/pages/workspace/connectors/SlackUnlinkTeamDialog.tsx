export function SlackUnlinkTeamDialog({
  teamName,
  teamDomain,
  open,
  loading,
  onCancel,
  onConfirm,
}: {
  teamName: string;
  teamDomain?: string | null;
  open: boolean;
  loading?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!open) {
    return null;
  }

  const workspaceLabel = teamDomain ? `${teamDomain}.slack.com` : teamName;

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
      <div
        className="home-disconnect-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="slack-unlink-team-heading"
      >
        <header className="home-disconnect-header">
          <div>
            <h2 id="slack-unlink-team-heading">Remove Slack workspace</h2>
            <p>Are you sure you want to remove {workspaceLabel} from this Readbase workspace?</p>
          </div>
          <button
            type="button"
            className="connector-close-button"
            aria-label="Close remove workspace warning"
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
            <strong>Channels from this workspace will be removed.</strong>
            <span>Indexed Slack channels linked to {teamName} will stop syncing in this workspace.</span>
          </div>
        </div>
        <div className="home-disconnect-actions">
          <button type="button" className="modal-cancel-button" disabled={loading} onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="danger-button" disabled={loading} onClick={onConfirm}>
            {loading ? "Removing..." : "Remove workspace"}
          </button>
        </div>
      </div>
    </div>
  );
}
