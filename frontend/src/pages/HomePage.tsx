import { useEffect, useState, useCallback, useMemo } from "react";

import { fetchJson } from "../api";
import { AppTopbar } from "../components/AppTopbar";
import type { AppRoute } from "../navigation/appRoute";
import type { AuthUser, Workspace, WorkspacesResponse } from "../types";
import { HomeAccountMenu } from "./homepage/HomeAccountMenu";
import { HomeConnectorMarquee } from "./homepage/HomeConnectorMarquee";
import { HomeNotificationsMenu } from "./homepage/HomeNotificationsMenu";
import { InvitesModal } from "./homepage/InvitesModal";
import { isPendingInvite } from "./homepage/InviteCard";
import { useWorkspaceInvites } from "./homepage/useWorkspaceInvites";
import { WorkspaceChatPage } from "./WorkspaceChatPage";
import { WorkspaceDashboardPage } from "./WorkspaceDashboardPage";

export function HomePage({
  user,
  loading,
  onLogout,
  onSessionExpired,
  appRoute,
  onNavigate,
  onReplaceNavigate,
}: {
  user: AuthUser;
  loading: boolean;
  onLogout: () => void;
  onSessionExpired: () => void;
  appRoute: AppRoute;
  onNavigate: (route: AppRoute) => void;
  onReplaceNavigate: (route: AppRoute) => void;
}) {
  const [selectedWorkspace, setSelectedWorkspaceState] = useState<Workspace | null>(null);
  const [invitesOpen, setInvitesOpen] = useState(false);
  const [workspaceRefreshKey, setWorkspaceRefreshKey] = useState(0);
  const invites = useWorkspaceInvites(onSessionExpired);

  function setSelectedWorkspace(workspace: Workspace | null) {
    setSelectedWorkspaceState(workspace);
    if (!workspace) {
      onNavigate({ screen: "workspaces" });
      return;
    }
    setInvitesOpen(false);
    onNavigate({
      screen: "workspace",
      workspaceId: workspace.workspace_id,
    });
  }

  function openInvitesPanel() {
    setInvitesOpen(true);
  }

  function closeInvitesPanel() {
    setInvitesOpen(false);
  }

  const refreshInvites = useCallback(async () => {
    await invites.loadInvites();
  }, [invites.loadInvites]);

  const workspaceSent = useMemo(() => {
    if (!selectedWorkspace) {
      return [];
    }
    return invites.sent.filter((invite) => invite.workspace_id === selectedWorkspace.workspace_id);
  }, [invites.sent, selectedWorkspace]);

  const homePendingReceivedCount = invites.pendingReceived.length;

  const workspaceSentPendingCount = useMemo(
    () => workspaceSent.filter((invite) => isPendingInvite(invite)).length,
    [workspaceSent],
  );

  const invitesModalScope = selectedWorkspace ? "sent" : "received";

  const modalInvites = useMemo(() => {
    if (selectedWorkspace) {
      return {
        ...invites,
        received: [],
        sent: workspaceSent,
      };
    }
    return {
      ...invites,
      sent: [],
    };
  }, [invites, selectedWorkspace, workspaceSent]);

  useEffect(() => {
    if (appRoute.screen !== "login") {
      return;
    }
    onReplaceNavigate({ screen: "workspaces" });
  }, [appRoute.screen, onReplaceNavigate]);

  useEffect(() => {
    if (appRoute.screen === "workspaces") {
      setSelectedWorkspaceState(null);
      setInvitesOpen(false);
      return;
    }

    if (appRoute.screen !== "workspace") {
      return;
    }

    setInvitesOpen(false);

    let cancelled = false;
    void (async () => {
      try {
        const result = await fetchJson<WorkspacesResponse>("/api/workspaces");
        const workspace =
          result.workspaces?.find((entry) => entry.workspace_id === appRoute.workspaceId) ?? null;
        if (!cancelled) {
          setSelectedWorkspaceState(workspace);
          if (!workspace) {
            onNavigate({ screen: "workspaces" });
          }
        }
      } catch {
        if (!cancelled) {
          setSelectedWorkspaceState(null);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [appRoute, onNavigate]);

  useEffect(() => {
    void refreshInvites();
  }, [refreshInvites]);

  useEffect(() => {
    if (!user) {
      return;
    }
    const joinToken = readJoinTokenFromUrl();
    if (!joinToken) {
      return;
    }
    void invites.openLinkInvite(joinToken).then((preview) => {
      if (preview) {
        setSelectedWorkspaceState(null);
        onReplaceNavigate({ screen: "workspaces" });
        setInvitesOpen(true);
      }
    });
  }, [user, invites.openLinkInvite, onReplaceNavigate]);

  useEffect(() => {
    const refreshOnFocus = () => {
      void refreshInvites();
    };
    const refreshOnInviteChange = () => {
      void refreshInvites();
    };
    window.addEventListener("focus", refreshOnFocus);
    window.addEventListener("readbase:invites-changed", refreshOnInviteChange);
    return () => {
      window.removeEventListener("focus", refreshOnFocus);
      window.removeEventListener("readbase:invites-changed", refreshOnInviteChange);
    };
  }, [refreshInvites]);

  const workspaceNav = useMemo(() => {
    if (selectedWorkspace) {
      return {
        workspaceId: selectedWorkspace.workspace_id,
        name: selectedWorkspace.name,
        canManage: selectedWorkspace.can_manage,
        onGoToWorkspaces: () => setSelectedWorkspace(null),
        onRenamed: (workspace: Workspace) => setSelectedWorkspaceState(workspace),
        onSessionExpired,
      };
    }
    if (appRoute.screen !== "workspace") {
      return undefined;
    }
    return {
      workspaceId: appRoute.workspaceId,
      name: "\u00a0",
      canManage: false,
      onGoToWorkspaces: () => setSelectedWorkspace(null),
      onRenamed: () => {},
      onSessionExpired,
    };
  }, [appRoute, onSessionExpired, selectedWorkspace]);

  return (
    <main className="home-page">
      <AppTopbar sticky workspaceNav={workspaceNav}>
        <div className="home-topbar-actions">
          {selectedWorkspace ? (
            <button
              type="button"
              className="secondary-action-button home-sources-button home-invites-button"
              onClick={openInvitesPanel}
            >
              Invites
              {workspaceSentPendingCount ? (
                <span className="home-invites-badge">{workspaceSentPendingCount}</span>
              ) : null}
            </button>
          ) : (
            <button
              type="button"
              className="secondary-action-button home-sources-button home-invites-button"
              onClick={openInvitesPanel}
            >
              Invites
              {homePendingReceivedCount ? (
                <span className="home-invites-badge">{homePendingReceivedCount}</span>
              ) : null}
            </button>
          )}
          <HomeNotificationsMenu onSessionExpired={onSessionExpired} />
          <HomeAccountMenu user={user} loading={loading} onLogout={onLogout} />
        </div>
      </AppTopbar>

      <div className="home-page-main page-body-surface">
        {selectedWorkspace ? (
          <WorkspaceChatPage
            key={selectedWorkspace.workspace_id}
            user={user}
            workspace={selectedWorkspace}
            onBack={() => setSelectedWorkspace(null)}
            onSessionExpired={onSessionExpired}
          />
        ) : appRoute.screen === "workspace" ? null : (
          <div className="home-content-body">
            <WorkspaceDashboardPage
              key={workspaceRefreshKey}
              onSelectWorkspace={setSelectedWorkspace}
              onSessionExpired={onSessionExpired}
              onLeaveWorkspace={(workspace) => {
                if (appRoute.screen === "workspace" && appRoute.workspaceId === workspace.workspace_id) {
                  setSelectedWorkspace(null);
                }
              }}
            />
            <HomeConnectorMarquee />
          </div>
        )}
      </div>
      <InvitesModal
        open={invitesOpen}
        onClose={closeInvitesPanel}
        invites={modalInvites}
        scope={invitesModalScope}
        onInviteChanged={() => setWorkspaceRefreshKey((current) => current + 1)}
      />
    </main>
  );
}

function readJoinTokenFromUrl(): string | null {
  const url = new URL(window.location.href);
  const joinToken = url.searchParams.get("join")?.trim();
  if (!joinToken) {
    return null;
  }
  url.searchParams.delete("join");
  const nextSearch = url.searchParams.toString();
  window.history.replaceState({}, "", `${url.pathname}${nextSearch ? `?${nextSearch}` : ""}${url.hash}`);
  return joinToken;
}
