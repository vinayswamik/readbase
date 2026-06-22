import { useCallback, useMemo, useState } from "react";

import { fetchJson, getErrorMessage, isSessionExpiredMessage, postJson } from "../../api";
import type { WorkspaceInvitesResponse, WorkspaceInviteItem } from "../../types";
import { isPendingInvite } from "./InviteCard";

export function useWorkspaceInvites(onSessionExpired: () => void) {
  const [received, setReceived] = useState<WorkspaceInviteItem[]>([]);
  const [sent, setSent] = useState<WorkspaceInviteItem[]>([]);
  const [linkPreview, setLinkPreview] = useState<WorkspaceInviteItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionInviteId, setActionInviteId] = useState<string | null>(null);

  const displayReceived = useMemo(() => {
    if (!linkPreview) {
      return received;
    }
    if (received.some((invite) => invite.invite_id === linkPreview.invite_id)) {
      return received;
    }
    return [linkPreview, ...received];
  }, [linkPreview, received]);

  const pendingReceived = displayReceived.filter((invite) => isPendingInvite(invite));
  const pendingSent = sent.filter((invite) => isPendingInvite(invite));

  const loadInvites = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson<WorkspaceInvitesResponse>("/api/invites");
      const nextReceived = result.received || [];
      const nextSent = result.sent || [];
      setReceived(nextReceived);
      setSent(nextSent);
      return {
        received: nextReceived,
        sent: nextSent,
        pendingCount: nextReceived.filter((invite) => isPendingInvite(invite)).length,
      };
    } catch (loadError) {
      const message = getErrorMessage(loadError);
      setError(message);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
      return { received: [], sent: [], pendingCount: 0 };
    } finally {
      setLoading(false);
    }
  }, [onSessionExpired]);

  const openLinkInvite = useCallback(
    async (joinToken: string) => {
      setError(null);
      try {
        const preview = await fetchJson<WorkspaceInviteItem>(
          `/api/invites/join/${encodeURIComponent(joinToken.trim())}`,
        );
        setLinkPreview(preview);
        return preview;
      } catch (loadError) {
        const message = getErrorMessage(loadError);
        setError(message);
        setLinkPreview(null);
        if (isSessionExpiredMessage(message)) {
          onSessionExpired();
        }
        return null;
      }
    },
    [onSessionExpired],
  );

  const acceptInvite = useCallback(
    async (inviteId: string) => {
      setActionInviteId(inviteId);
      setError(null);
      try {
        await postJson<Record<string, never>, WorkspaceInviteItem>(
          `/api/invites/${encodeURIComponent(inviteId)}/accept`,
          {},
        );
        setLinkPreview(null);
        await loadInvites();
        return true;
      } catch (actionError) {
        const message = getErrorMessage(actionError);
        setError(message);
        if (isSessionExpiredMessage(message)) {
          onSessionExpired();
        }
        return false;
      } finally {
        setActionInviteId(null);
      }
    },
    [loadInvites, onSessionExpired],
  );

  const rejectInvite = useCallback(
    async (inviteId: string) => {
      setActionInviteId(inviteId);
      setError(null);
      try {
        await postJson<Record<string, never>, WorkspaceInviteItem>(
          `/api/invites/${encodeURIComponent(inviteId)}/reject`,
          {},
        );
        await loadInvites();
        return true;
      } catch (actionError) {
        const message = getErrorMessage(actionError);
        setError(message);
        if (isSessionExpiredMessage(message)) {
          onSessionExpired();
        }
        return false;
      } finally {
        setActionInviteId(null);
      }
    },
    [loadInvites, onSessionExpired],
  );

  const revertInvite = useCallback(
    async (inviteId: string) => {
      setActionInviteId(inviteId);
      setError(null);
      try {
        await postJson<Record<string, never>, WorkspaceInviteItem>(
          `/api/invites/${encodeURIComponent(inviteId)}/revert`,
          {},
        );
        await loadInvites();
        return true;
      } catch (actionError) {
        const message = getErrorMessage(actionError);
        setError(message);
        if (isSessionExpiredMessage(message)) {
          onSessionExpired();
        }
        return false;
      } finally {
        setActionInviteId(null);
      }
    },
    [loadInvites, onSessionExpired],
  );

  return useMemo(
    () => ({
      received: displayReceived,
      sent,
      linkPreview,
      pendingReceived,
      pendingSent,
      loading,
      error,
      actionInviteId,
      loadInvites,
      openLinkInvite,
      acceptInvite,
      rejectInvite,
      revertInvite,
    }),
    [
      displayReceived,
      sent,
      linkPreview,
      pendingReceived,
      pendingSent,
      loading,
      error,
      actionInviteId,
      loadInvites,
      openLinkInvite,
      acceptInvite,
      rejectInvite,
      revertInvite,
    ],
  );
}
