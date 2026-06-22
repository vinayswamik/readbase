import { useEffect, useRef, useState } from "react";

import { fetchJson, getErrorMessage, postJson } from "./api";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { isMockApi } from "./mock/dev";
import { useMockRoute } from "./mock/useMockRoute";
import type { AuthUser, SessionResponse } from "./types";

const SESSION_CHECK_INTERVAL_MS = 60_000;

export function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const userRef = useRef<AuthUser | null>(null);
  const mockMode = isMockApi();
  const [mockRoute, navigateMock] = useMockRoute();

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
        setUser((currentUser) =>
          areSameUser(currentUser, session.user ?? null) ? currentUser : session.user ?? null,
        );
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

  async function handleLogin() {
    setIsSubmitting(true);
    if (isMockApi()) {
      try {
        const session = await postJson<Record<string, never>, SessionResponse>(
          "/api/auth/mock-login",
          {},
        );
        setUser(session.user ?? null);
        setError(null);
        if (mockMode) {
          navigateMock({ screen: "workspaces" });
        }
      } catch (loginError) {
        setError(getErrorMessage(loginError));
      } finally {
        setIsSubmitting(false);
      }
      return;
    }
    window.location.assign("/api/auth/start");
  }

  async function handleLogout() {
    setIsSubmitting(true);
    try {
      await postJson<undefined, SessionResponse>("/api/auth/logout");
      setUser(null);
      setError(null);
      if (mockMode) {
        navigateMock({ screen: "login" });
      }
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

  if (mockMode && mockRoute.screen === "login") {
    return <LoginPage loading={isSubmitting} error={error} onLogin={handleLogin} />;
  }

  if (user) {
    return (
      <HomePage
        user={user}
        loading={isSubmitting}
        onLogout={handleLogout}
        onSessionExpired={handleSessionExpired}
        mockRoute={mockMode ? mockRoute : undefined}
        onMockNavigate={mockMode ? navigateMock : undefined}
      />
    );
  }

  if (mockMode && !isLoadingSession && mockRoute.screen !== "login") {
    return <LoginPage loading={isSubmitting} error={error} onLogin={handleLogin} />;
  }

  return <LoginPage loading={isSubmitting} error={error} onLogin={handleLogin} />;
}

function areSameUser(currentUser: AuthUser | null, nextUser: AuthUser | null | undefined): boolean {
  if (!currentUser || !nextUser) {
    return currentUser === nextUser;
  }
  return (
    currentUser.id === nextUser.id &&
    currentUser.email === nextUser.email &&
    currentUser.name === nextUser.name
  );
}

function readAuthErrorFromUrl(): string | null {
  const url = new URL(window.location.href);
  const authError = url.searchParams.get("auth_error");
  if (!authError) {
    return null;
  }
  url.searchParams.delete("auth_error");
  window.history.replaceState({}, "", url.pathname + url.search);
  return "Organization sign-in was not completed. Please try again.";
}
