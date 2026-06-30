import { useEffect, useRef, useState } from "react";

import { fetchJson, getErrorMessage, postJson } from "./api";
import { authConfigError, authProvider, readAuthCallbackError } from "./config/auth";
import { isMockApi } from "./mock/dev";
import { useAppRoute } from "./navigation/useAppRoute";
import type { AuthUser, SessionResponse } from "./types";

const SESSION_CHECK_INTERVAL_MS = 60_000;
const SESSION_EXPIRED_MESSAGE = "Session expired. Please sign in again.";

function areSameUser(
  currentUser: AuthUser | null,
  nextUser: AuthUser | null | undefined,
): boolean {
  if (!currentUser || !nextUser) {
    return currentUser === nextUser;
  }
  return (
    currentUser.id === nextUser.id &&
    currentUser.email === nextUser.email &&
    currentUser.name === nextUser.name
  );
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const userRef = useRef<AuthUser | null>(null);
  const postAuthRouteSyncedRef = useRef(false);
  const mockMode = isMockApi();
  const [appRoute, navigateApp, replaceAppRoute] = useAppRoute();

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  useEffect(() => {
    if (!mockMode || isLoadingSession || user || appRoute.screen === "login") {
      return;
    }
    replaceAppRoute({ screen: "login" });
  }, [mockMode, isLoadingSession, user, appRoute.screen, replaceAppRoute]);

  useEffect(() => {
    if (!user || isLoadingSession) {
      return;
    }
    const path = window.location.pathname;
    if (path !== "/" && path !== "/login") {
      postAuthRouteSyncedRef.current = true;
      return;
    }
    if (postAuthRouteSyncedRef.current) {
      return;
    }
    postAuthRouteSyncedRef.current = true;
    replaceAppRoute({ screen: "workspaces" });
  }, [user, isLoadingSession, replaceAppRoute]);

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

  async function loadSession({ backgroundCheck = false }: { backgroundCheck?: boolean } = {}) {
    try {
      const session = await fetchJson<SessionResponse>("/api/auth/session");
      if (session.authenticated) {
        setUser((currentUser) =>
          areSameUser(currentUser, session.user ?? null) ? currentUser : session.user ?? null,
        );
        if (!backgroundCheck) {
          setError(readAuthCallbackError());
        }
        return;
      }

      const hadLoggedInUser = Boolean(userRef.current);
      setUser(null);
      if (hadLoggedInUser) {
        setError(SESSION_EXPIRED_MESSAGE);
      } else if (!backgroundCheck) {
        setError(readAuthCallbackError());
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
    if (!authProvider) {
      return;
    }

    setIsSubmitting(true);
    if (mockMode) {
      try {
        if (user) {
          setError(null);
          replaceAppRoute({ screen: "workspaces" });
          return;
        }
        const session = await postJson<Record<string, never>, SessionResponse>(
          "/api/auth/mock-login",
          {},
        );
        setUser(session.user ?? null);
        setError(null);
        replaceAppRoute({ screen: "workspaces" });
      } catch (loginError) {
        setError(getErrorMessage(loginError));
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    window.location.assign(authProvider.startPath);
  }

  async function handleLogout() {
    setIsSubmitting(true);
    try {
      await postJson<undefined, SessionResponse>("/api/auth/logout");
      setUser(null);
      setError(null);
      postAuthRouteSyncedRef.current = false;
      if (mockMode) {
        navigateApp({ screen: "login" });
      } else {
        replaceAppRoute({ screen: "login" });
      }
    } catch (logoutError) {
      setError(getErrorMessage(logoutError));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSessionExpired() {
    setUser(null);
    setError(SESSION_EXPIRED_MESSAGE);
  }

  const showLoginPage = !user || (mockMode && appRoute.screen === "login");

  return {
    user,
    isLoadingSession,
    isSubmitting,
    error,
    authConfigError,
    authProvider,
    mockMode,
    appRoute,
    navigateApp,
    replaceAppRoute,
    showLoginPage,
    handleLogin,
    handleLogout,
    handleSessionExpired,
  };
}
