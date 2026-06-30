import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { InviteCard } from "./InviteCard";
import type { useWorkspaceInvites } from "./useWorkspaceInvites";

type InvitesState = ReturnType<typeof useWorkspaceInvites>;

export type InvitesModalScope = "received" | "sent";

export function InvitesModal({
  open,
  onClose,
  invites,
  scope,
  onInviteChanged,
}: {
  open: boolean;
  onClose: () => void;
  invites: InvitesState;
  scope: InvitesModalScope;
  onInviteChanged?: () => void;
}) {
  const {
    received,
    sent,
    loading,
    error,
    actionInviteId,
    loadInvites,
    acceptInvite,
    rejectInvite,
    revertInvite,
  } = invites;

  useEffect(() => {
    if (open) {
      void loadInvites();
    }
  }, [loadInvites, open]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleEscape);
    };
  }, [onClose, open]);

  async function handleReject(inviteId: string) {
    const confirmed = window.confirm("Reject this workspace invite?");
    if (!confirmed) {
      return false;
    }
    const rejected = await rejectInvite(inviteId);
    if (rejected) {
      onInviteChanged?.();
    }
    return rejected;
  }

  async function handleRevert(inviteId: string) {
    const confirmed = window.confirm(
      "Revert this invite? The person will no longer be able to accept it.",
    );
    if (!confirmed) {
      return false;
    }
    const reverted = await revertInvite(inviteId);
    if (reverted) {
      onInviteChanged?.();
    }
    return reverted;
  }

  function handleAccept(inviteId: string) {
    void acceptInvite(inviteId).then((accepted) => {
      if (accepted) {
        onInviteChanged?.();
      }
    });
  }

  if (!open) {
    return null;
  }

  const showContent = received.length > 0 || sent.length > 0 || !loading;
  const showReceived = scope === "received";
  const showSent = scope === "sent";

  return createPortal(
    <div
      className="invites-modal-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <section
        className="invites-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="invites-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="invites-modal-header">
          <div className="invites-modal-header-copy">
            <h2 id="invites-title">Invites</h2>
            <p>
              {showReceived
                ? "Pending invitations sent to you."
                : "Pending invitations you sent from this workspace."}
            </p>
          </div>
          <button
            type="button"
            className="secondary-action-button invites-modal-close"
            onClick={onClose}
            aria-label="Close invites"
          >
            Close
          </button>
        </header>

        {loading ? <div className="status-text invites-modal-status">Loading invites...</div> : null}
        {error ? <div className="status-text error-note invites-modal-status">{error}</div> : null}

        {showContent ? (
          <div className="invites-modal-body">
            {showReceived ? (
              <InviteSection title="Received" invites={received} emptyLabel="No pending invites for you.">
                {(invite) => (
                  <InviteCard
                    invite={invite}
                    variant="received"
                    actionInviteId={actionInviteId}
                    onAccept={handleAccept}
                    onReject={(inviteId) => {
                      void handleReject(inviteId);
                    }}
                  />
                )}
              </InviteSection>
            ) : null}
            {showSent ? (
              <InviteSection title="Sent" invites={sent} emptyLabel="No pending invites sent by you.">
                {(invite) => (
                  <InviteCard
                    invite={invite}
                    variant="sent"
                    actionInviteId={actionInviteId}
                    onRevert={(inviteId) => {
                      void handleRevert(inviteId);
                    }}
                  />
                )}
              </InviteSection>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>,
    document.body,
  );
}

function InviteSection({
  title,
  invites,
  emptyLabel,
  children,
}: {
  title: string;
  invites: Parameters<typeof InviteCard>[0]["invite"][];
  emptyLabel: string;
  children: (invite: Parameters<typeof InviteCard>[0]["invite"]) => ReactNode;
}) {
  return (
    <section className="invite-section">
      <h3>{title}</h3>
      {!invites.length ? (
        <div className="status-text compact">{emptyLabel}</div>
      ) : (
        <div className="invite-list">
          {invites.map((invite) => (
            <div key={invite.invite_id}>{children(invite)}</div>
          ))}
        </div>
      )}
    </section>
  );
}
