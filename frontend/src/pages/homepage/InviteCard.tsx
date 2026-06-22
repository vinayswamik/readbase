import { useState } from "react";

import type { WorkspaceInviteItem } from "../../types";
import { buildInviteJoinUrl } from "../workspace/WorkspacePanelControls";

export function inviteStatusKey(invite: WorkspaceInviteItem): string {
  return (invite.status ?? "").trim().toLowerCase();
}

export function isPendingInvite(invite: WorkspaceInviteItem): boolean {
  return inviteStatusKey(invite) === "pending";
}

export function isLinkInvite(invite: WorkspaceInviteItem): boolean {
  return invite.invite_method === "link" || Boolean(invite.join_token);
}

export function canAcceptInvite(invite: WorkspaceInviteItem): boolean {
  return invite.can_accept ?? isPendingInvite(invite);
}

export function canRejectInvite(invite: WorkspaceInviteItem): boolean {
  return invite.can_reject ?? (isPendingInvite(invite) && !isLinkInvite(invite));
}

export function canRevertInvite(invite: WorkspaceInviteItem): boolean {
  return invite.can_revert ?? isPendingInvite(invite);
}

export function InviteCard({
  invite,
  variant,
  actionInviteId,
  onAccept,
  onReject,
  onRevert,
}: {
  invite: WorkspaceInviteItem;
  variant: "received" | "sent";
  actionInviteId?: string | null;
  onAccept?: (inviteId: string) => void;
  onReject?: (inviteId: string) => void;
  onRevert?: (inviteId: string) => void;
}) {
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  const statusKey = inviteStatusKey(invite) || "unknown";
  const isWorking = actionInviteId === invite.invite_id;
  const linkInvite = isLinkInvite(invite);
  const joinUrl = buildInviteJoinUrl(invite.join_path, invite.join_token);
  const showReceivedActions = variant === "received" && Boolean(onAccept);
  const showSentActions = variant === "sent" && Boolean(onRevert);
  const acceptEnabled = canAcceptInvite(invite);
  const rejectEnabled = canRejectInvite(invite);
  const revertEnabled = canRevertInvite(invite);

  async function handleCopyJoinUrl() {
    if (!joinUrl) {
      return;
    }
    try {
      await navigator.clipboard.writeText(joinUrl);
      setCopyStatus("Link copied.");
    } catch {
      setCopyStatus("Could not copy automatically.");
    }
  }

  return (
    <article className={`invite-card invite-card--${variant}`}>
      {showReceivedActions ? (
        <div className="invite-actions invite-actions--prominent">
          <button
            type="button"
            className="primary-button invite-action-button"
            disabled={!acceptEnabled || isWorking}
            onClick={() => onAccept?.(invite.invite_id)}
          >
            {isWorking ? "Working..." : "Accept invite"}
          </button>
          {onReject && rejectEnabled ? (
            <button
              type="button"
              className="secondary-action-button invite-action-button"
              disabled={!rejectEnabled || isWorking}
              onClick={() => onReject(invite.invite_id)}
            >
              Reject
            </button>
          ) : null}
        </div>
      ) : null}
      {showSentActions ? (
        <div className="invite-actions invite-actions--prominent">
          <button
            type="button"
            className="danger-button invite-action-button"
            disabled={!revertEnabled || isWorking}
            onClick={() => onRevert?.(invite.invite_id)}
          >
            {isWorking ? "Working..." : "Revert invite"}
          </button>
        </div>
      ) : null}

      <div className="invite-card-topline">
        <strong>{invite.workspace_name}</strong>
        <span className={`invite-status invite-status--${statusKey}`}>{invite.status || "unknown"}</span>
      </div>
      <dl className="invite-details">
        {variant === "received" ? (
          <div>
            <dt>Invited by</dt>
            <dd>
              {invite.invitor_name}
              {invite.invitor_designation ? ` · ${invite.invitor_designation}` : ""}
            </dd>
          </div>
        ) : (
          <div>
            <dt>Invite type</dt>
            <dd>{linkInvite ? "Shareable link" : `Email · ${invite.invitee_email}`}</dd>
          </div>
        )}
        {linkInvite && variant === "sent" && joinUrl ? (
          <div>
            <dt>Invite link</dt>
            <dd className="invite-link-copy">
              <input value={joinUrl} readOnly aria-label="Invite link" />
              <button type="button" className="secondary-action-button" onClick={() => void handleCopyJoinUrl()}>
                Copy link
              </button>
              {copyStatus ? <span className="invite-link-copy-status">{copyStatus}</span> : null}
            </dd>
          </div>
        ) : null}
        {variant === "received" && linkInvite ? (
          <div>
            <dt>Invite type</dt>
            <dd>Shareable link</dd>
          </div>
        ) : null}
        <div>
          <dt>Relation in org</dt>
          <dd>{invite.relation}</dd>
        </div>
        <div>
          <dt>Reason</dt>
          <dd>{invite.reason}</dd>
        </div>
        <div>
          <dt>Graph role</dt>
          <dd>{invite.node_display_name}</dd>
        </div>
      </dl>
      {showReceivedActions && !acceptEnabled ? (
        <p className="invite-actions-note">This invite is no longer pending.</p>
      ) : null}
      {showSentActions && !revertEnabled ? (
        <p className="invite-actions-note">This invite is no longer pending.</p>
      ) : null}
    </article>
  );
}
