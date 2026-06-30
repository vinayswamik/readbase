import { AppTopbar } from "../components/AppTopbar";
import type { AuthProvider } from "../config/auth";

type LoginPageProps = {
  provider: AuthProvider | null;
  configError?: string | null;
  loading: boolean;
  error: string | null;
  onLogin: () => void;
};

export function LoginPage({
  provider,
  configError,
  loading,
  error,
  onLogin,
}: LoginPageProps) {
  return (
    <main className="login-page">
      <AppTopbar />

      <div className="page-body-surface">
        <section className="login-panel" aria-labelledby="login-title">
          <h1 id="login-title" className="login-title">
            Sign in to readbase
          </h1>

          {configError ? (
            <p className="login-message login-message--error" role="alert">
              {configError}
            </p>
          ) : (
            <button
              className="login-button"
              type="button"
              onClick={onLogin}
              disabled={loading}
            >
              {loading ? "Signing in..." : provider?.label}
            </button>
          )}

          {error ? (
            <p className="login-message login-message--error" role="status" aria-live="polite">
              {error}
            </p>
          ) : null}

          {!configError && provider ? (
            <p className="login-footer">{provider.footerNote}</p>
          ) : null}
        </section>
      </div>
    </main>
  );
}
