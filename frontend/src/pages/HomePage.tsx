import { useEffect, useRef, useState } from "react";

import type { AuthUser, Workspace } from "../types";
import { WorkspaceChatPage } from "./WorkspaceChatPage";
import { WorkspaceDashboardPage } from "./WorkspaceDashboardPage";

export function HomePage({
  user,
  loading,
  onLogout,
  onSessionExpired,
}: {
  user: AuthUser;
  loading: boolean;
  onLogout: () => void;
  onSessionExpired: () => void;
}) {
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement | null>(null);

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
      </header>

      {selectedWorkspace ? (
        <WorkspaceChatPage
          key={selectedWorkspace.workspace_id}
          workspace={selectedWorkspace}
          onBack={() => setSelectedWorkspace(null)}
          onSessionExpired={onSessionExpired}
        />
      ) : (
        <WorkspaceDashboardPage
          onSelectWorkspace={setSelectedWorkspace}
          onSessionExpired={onSessionExpired}
        />
      )}
    </main>
  );
}
