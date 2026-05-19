import { useEffect, useRef, useState } from "react";

import { fetchJson, getErrorMessage, postJson } from "./api";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import type { AuthUser, SessionResponse } from "./types";

const SESSION_CHECK_INTERVAL_MS = 60_000;

export function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const userRef = useRef<AuthUser | null>(null);

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  useEffect(() => {
    void loadSession();
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }

    const checkSession = () => {
      void loadSession({ backgroundCheck: true });
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        checkSession();
      }
    };
    const handleFocus = () => {
      checkSession();
    };

    const intervalId = window.setInterval(checkSession, SESSION_CHECK_INTERVAL_MS);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", handleFocus);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", handleFocus);
    };
  }, [user]);

  async function loadSession({
    backgroundCheck = false,
  }: {
    backgroundCheck?: boolean;
  } = {}) {
    try {
      const session = await fetchJson<SessionResponse>("/api/auth/session");
      if (session.authenticated) {
        setUser(session.user);
        if (!backgroundCheck) {
          setError(readAuthErrorFromUrl());
        }
        return;
      }

      const hadLoggedInUser = Boolean(userRef.current);
      setUser(null);
      if (hadLoggedInUser) {
        setError("Session expired. Please sign in again.");
      } else if (!backgroundCheck) {
        setError(readAuthErrorFromUrl());
      }
    } catch (sessionError) {
      setUser(null);
      if (!backgroundCheck) {
        setError(getErrorMessage(sessionError));
      }
    } finally {
      if (!backgroundCheck) {
        setIsLoadingSession(false);
      }
    }
  }

  async function handleGoogleLogin(portal: "admin" | "member") {
    setIsSubmitting(true);
    window.location.assign(`/api/auth/google/start?portal=${portal}`);
  }

  async function handleLogout() {
    setIsSubmitting(true);
    try {
      await postJson<undefined, SessionResponse>("/api/auth/logout");
      setUser(null);
      setError(null);
    } catch (logoutError) {
      setError(getErrorMessage(logoutError));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSessionExpired() {
    setUser(null);
    setError("Session expired. Please sign in again.");
  }

  if (isLoadingSession) {
    return null;
  }

  if (user) {
    return (
      <HomePage
        user={user}
        loading={isSubmitting}
        onLogout={handleLogout}
        onSessionExpired={handleSessionExpired}
      />
    );
  }

  return <LoginPage loading={isSubmitting} error={error} onLogin={handleGoogleLogin} />;
}

function readAuthErrorFromUrl(): string | null {
  const url = new URL(window.location.href);
  const authError = url.searchParams.get("auth_error");
  if (!authError) {
    return null;
  }
  url.searchParams.delete("auth_error");
  window.history.replaceState({}, "", url.pathname + url.search);
  if (authError === "admin_not_approved") {
    return "This Google account is not approved for admin login.";
  }
  return "Google sign-in was not completed. Please try again.";
}
