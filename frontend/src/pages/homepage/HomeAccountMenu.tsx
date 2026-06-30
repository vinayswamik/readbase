import { useCallback, useRef, useState } from "react";

import type { AuthUser } from "../../types";
import { useDismissOnOutsideInteraction } from "./useDismissOnOutsideInteraction";

export function HomeAccountMenu({
  user,
  loading,
  onLogout,
}: {
  user: AuthUser;
  loading: boolean;
  onLogout: () => void;
}) {
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement | null>(null);
  const handleDismissAccountMenu = useCallback(() => setAccountMenuOpen(false), []);

  useDismissOnOutsideInteraction(accountMenuOpen, accountMenuRef, handleDismissAccountMenu);

  const accountInitial = (user.name || user.email || "U").trim().charAt(0).toUpperCase();

  return (
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
  );
}
