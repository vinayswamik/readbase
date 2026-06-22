import { useEffect, useRef, useState, useCallback, useMemo } from "react";

import { fetchJson } from "../api";
import type { AuthUser, Workspace, WorkspacesResponse } from "../types";
import type { MockRoute } from "../mock/navigation";
import { InvitesModal } from "./homepage/InvitesModal";
import { isPendingInvite } from "./homepage/InviteCard";
import { useWorkspaceInvites } from "./homepage/useWorkspaceInvites";
import { WorkspaceChatPage } from "./WorkspaceChatPage";
import { WorkspaceDashboardPage } from "./WorkspaceDashboardPage";

const SELECTED_WORKSPACE_STORAGE_KEY = "readbase:selectedWorkspace";

export function HomePage({
  user,
  loading,
  onLogout,
  onSessionExpired,
  mockRoute,
  onMockNavigate,
}: {
  user: AuthUser;
  loading: boolean;
  onLogout: () => void;
  onSessionExpired: () => void;
  mockRoute?: MockRoute;
  onMockNavigate?: (route: MockRoute) => void;
}) {
  const mockNavigation = Boolean(mockRoute && onMockNavigate);
  const [selectedWorkspace, setSelectedWorkspaceState] = useState<Workspace | null>(() =>
    mockNavigation ? null : readStoredWorkspace(),
  );
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [invitesOpen, setInvitesOpen] = useState(
    () => mockRoute?.screen === "workspace" && mockRoute.panel === "invites",
  );
  const [workspaceRefreshKey, setWorkspaceRefreshKey] = useState(0);
  const [sourcesOpen, setSourcesOpen] = useState(
    () => mockRoute?.screen === "workspace" && mockRoute.panel === "sources",
  );
  const accountMenuRef = useRef<HTMLDivElement | null>(null);
  const invites = useWorkspaceInvites(onSessionExpired);

  function setSelectedWorkspace(workspace: Workspace | null) {
    setSelectedWorkspaceState(workspace);
    if (mockNavigation && onMockNavigate) {
      if (workspace) {
        onMockNavigate({ screen: "workspace", workspaceId: workspace.workspace_id });
      } else {
        onMockNavigate({ screen: "workspaces" });
      }
      return;
    }
    if (workspace) {
      window.sessionStorage.setItem(
        SELECTED_WORKSPACE_STORAGE_KEY,
        JSON.stringify(workspace),
      );
    } else {
      window.sessionStorage.removeItem(SELECTED_WORKSPACE_STORAGE_KEY);
    }
  }

  function openInvitesPanel() {
    setInvitesOpen(true);
    if (mockNavigation && mockRoute?.screen === "workspace" && onMockNavigate) {
      onMockNavigate({
        screen: "workspace",
        workspaceId: mockRoute.workspaceId,
        panel: "invites",
      });
    }
  }

  function closeInvitesPanel() {
    setInvitesOpen(false);
    if (mockNavigation && mockRoute?.screen === "workspace" && onMockNavigate) {
      onMockNavigate({
        screen: "workspace",
        workspaceId: mockRoute.workspaceId,
      });
    }
  }

  function openSourcesPanel() {
    setSourcesOpen(true);
    if (mockNavigation && mockRoute?.screen === "workspace" && onMockNavigate) {
      onMockNavigate({
        screen: "workspace",
        workspaceId: mockRoute.workspaceId,
        panel: "sources",
      });
    }
  }

  function setSourcesPanelOpen(open: boolean) {
    setSourcesOpen(open);
    if (!mockNavigation || mockRoute?.screen !== "workspace" || !onMockNavigate) {
      return;
    }
    onMockNavigate({
      screen: "workspace",
      workspaceId: mockRoute.workspaceId,
      panel: open ? "sources" : undefined,
    });
  }

  const refreshInvites = useCallback(async () => {
    await invites.loadInvites();
  }, [invites.loadInvites]);

  const workspaceReceived = useMemo(() => {
    if (!selectedWorkspace) {
      return [];
    }
    return invites.received.filter(
      (invite) => invite.workspace_id === selectedWorkspace.workspace_id,
    );
  }, [invites.received, selectedWorkspace]);

  const workspaceSent = useMemo(() => {
    if (!selectedWorkspace) {
      return [];
    }
    return invites.sent.filter((invite) => invite.workspace_id === selectedWorkspace.workspace_id);
  }, [invites.sent, selectedWorkspace]);

  const workspacePendingCount = useMemo(
    () =>
      workspaceReceived.filter((invite) => isPendingInvite(invite)).length +
      workspaceSent.filter((invite) => isPendingInvite(invite)).length,
    [workspaceReceived, workspaceSent],
  );

  const modalInvites = useMemo(
    () => ({
      ...invites,
      received: invites.linkPreview ? [invites.linkPreview, ...workspaceReceived] : workspaceReceived,
      sent: workspaceSent,
    }),
    [invites, workspaceReceived, workspaceSent],
  );

  useEffect(() => {
    if (!mockNavigation || !mockRoute) {
      return;
    }

    if (mockRoute.screen === "workspaces") {
      setSelectedWorkspaceState(null);
      setInvitesOpen(false);
      setSourcesOpen(false);
      return;
    }

    if (mockRoute.screen !== "workspace") {
      return;
    }

    setInvitesOpen(mockRoute.panel === "invites");
    setSourcesOpen(mockRoute.panel === "sources");

    let cancelled = false;
    void (async () => {
      try {
        const result = await fetchJson<WorkspacesResponse>("/api/workspaces");
        const workspace =
          result.workspaces?.find((entry) => entry.workspace_id === mockRoute.workspaceId) ?? null;
        if (!cancelled) {
          setSelectedWorkspaceState(workspace);
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
  }, [mockNavigation, mockRoute]);

  useEffect(() => {
    if (!selectedWorkspace) {
      return;
    }
    void refreshInvites();
  }, [refreshInvites, selectedWorkspace?.workspace_id]);

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
        setInvitesOpen(true);
      }
    });
  }, [user, invites.openLinkInvite]);

  useEffect(() => {
    if (!selectedWorkspace) {
      return;
    }
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
  }, [refreshInvites, selectedWorkspace?.workspace_id]);

  useEffect(() => {
    if (!accountMenuOpen) {
      return;
    }
    const handleDocumentClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (!accountMenuRef.current?.contains(target)) {
        setAccountMenuOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setAccountMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [accountMenuOpen]);

  const accountInitial = (user.name || user.email || "U").trim().charAt(0).toUpperCase();

  return (
    <main className="home-page">
      <header className="home-topbar">
        <div>
          <span className="brand-badge">Readbase</span>
          <p className="home-user">
            {selectedWorkspace ? selectedWorkspace.name : "Codebase Q&A workspace"}
          </p>
        </div>
        <div className="home-topbar-actions">
          {selectedWorkspace ? (
            <>
              <button
                type="button"
                className="secondary-action-button home-sources-button home-invites-button"
                onClick={openInvitesPanel}
              >
                Invites
                {workspacePendingCount ? (
                  <span className="home-invites-badge">{workspacePendingCount}</span>
                ) : null}
              </button>
              <button
                type="button"
                className="secondary-action-button home-sources-button"
                onClick={openSourcesPanel}
              >
                Sources
              </button>
            </>
          ) : null}
          <div className="account-menu" ref={accountMenuRef}>
            <button
              type="button"
              className="account-trigger"
              aria-haspopup="menu"
              aria-expanded={accountMenuOpen}
              aria-label="Open account menu"
              onClick={() => setAccountMenuOpen((open) => !open)}
            >
              {accountInitial}
            </button>
            {accountMenuOpen ? (
              <div className="account-popover" role="menu">
                <p className="account-name">{user.name}</p>
                <p className="account-email">{user.email}</p>
                <button
                  type="button"
                  className="account-signout"
                  onClick={onLogout}
                  disabled={loading}
                >
                  {loading ? "Signing out..." : "Sign out"}
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <div className="home-page-main">
        {selectedWorkspace ? (
          <>
            <WorkspaceChatPage
              key={selectedWorkspace.workspace_id}
              user={user}
              workspace={selectedWorkspace}
              onBack={() => setSelectedWorkspace(null)}
              onSessionExpired={onSessionExpired}
              sourcesOpen={sourcesOpen}
              onSourcesOpenChange={setSourcesPanelOpen}
            />
          </>
        ) : (
          <div className="home-content-shell">
            <WorkspaceDashboardPage
              key={workspaceRefreshKey}
              onSelectWorkspace={setSelectedWorkspace}
              onSessionExpired={onSessionExpired}
              onLeaveWorkspace={(workspace) => {
                if (mockNavigation) {
                  return;
                }
                const stored = readStoredWorkspace();
                if (stored?.workspace_id === workspace.workspace_id) {
                  setSelectedWorkspace(null);
                }
              }}
            />
          </div>
        )}
      </div>
      {selectedWorkspace || invites.linkPreview ? (
        <InvitesModal
          open={invitesOpen}
          onClose={closeInvitesPanel}
          invites={modalInvites}
          onInviteChanged={() => setWorkspaceRefreshKey((current) => current + 1)}
        />
      ) : null}
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

function readStoredWorkspace(): Workspace | null {
  try {
    const storedWorkspace = window.sessionStorage.getItem(SELECTED_WORKSPACE_STORAGE_KEY);
    if (!storedWorkspace) {
      return null;
    }
    const parsed = JSON.parse(storedWorkspace) as Partial<Workspace>;
    if (
      typeof parsed.workspace_id === "string" &&
      typeof parsed.owner_user_id === "string" &&
      typeof parsed.name === "string" &&
      typeof parsed.created_at === "string" &&
      typeof parsed.can_manage === "boolean"
    ) {
      return parsed as Workspace;
    }
  } catch {
    window.sessionStorage.removeItem(SELECTED_WORKSPACE_STORAGE_KEY);
  }
  return null;
}
