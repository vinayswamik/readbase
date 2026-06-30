export type AuthMode = "IaaS" | "SaaS";

export type AuthProvider = {
  label: string;
  startPath: string;
  footerNote: string;
  callbackErrorMessage: string;
};

const PROVIDERS: Record<AuthMode, AuthProvider> = {
  IaaS: {
    label: "Sign in with your organization",
    startPath: "/api/auth/start",
    footerNote: "Your organization's identity provider keeps your account secure.",
    callbackErrorMessage: "Organization sign-in was not completed. Please try again.",
  },
  SaaS: {
    label: "Sign in with Google",
    startPath: "/api/auth/google/start",
    footerNote: "Sign in with your Google account.",
    callbackErrorMessage: "Google sign-in was not completed. Please try again.",
  },
};

function parseAuthMode(raw: string | undefined): AuthMode | null {
  if (!raw?.trim()) {
    return null;
  }
  const normalized = raw.trim().toLowerCase();
  if (normalized === "iaas") {
    return "IaaS";
  }
  if (normalized === "saas") {
    return "SaaS";
  }
  return null;
}

function loadAuthConfig(): { provider: AuthProvider | null; error: string | null } {
  const raw = import.meta.env.VITE_AUTH_MODE;
  const mode = parseAuthMode(raw);
  if (!mode) {
    const detail = raw?.trim()
      ? `Invalid VITE_AUTH_MODE "${raw}".`
      : "VITE_AUTH_MODE is not set.";
    return {
      provider: null,
      error: `${detail} Use "IaaS" or "SaaS".`,
    };
  }
  return { provider: PROVIDERS[mode], error: null };
}

/** One mode per deploy. Toggle via VITE_AUTH_MODE: IaaS | SaaS */
export const { provider: authProvider, error: authConfigError } = loadAuthConfig();

export function readAuthCallbackError(): string | null {
  const url = new URL(window.location.href);
  const authError = url.searchParams.get("auth_error");
  if (!authError) {
    return null;
  }
  url.searchParams.delete("auth_error");
  window.history.replaceState({}, "", url.pathname + url.search);
  return authProvider?.callbackErrorMessage ?? "Sign-in was not completed. Please try again.";
}
