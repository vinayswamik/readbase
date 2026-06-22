import { ReadbaseLogoIcon } from "../components/ReadbaseLogoIcon";

export function LoginPage({
  loading,
  error,
  onLogin,
}: {
  loading: boolean;
  error: string | null;
  onLogin: () => void;
}) {
  return (
    <main className="login-page">
      <header className="login-topbar">
        <span className="login-logo" aria-label="Readbase">
          <span className="login-logo-icon-wrap">
            <ReadbaseLogoIcon className="login-logo-icon" />
          </span>
          <span className="login-logo-text">readbase</span>
        </span>
        <button
          className="login-topbar-button"
          type="button"
          onClick={onLogin}
          disabled={loading}
        >
          {loading ? "Signing in..." : "Login"}
        </button>
      </header>

      <div className="login-page-body">
        <section className="login-panel" aria-labelledby="login-title">
          <header className="login-header">
            <h1 id="login-title">Sign in to readbase</h1>
          </header>

          <div className="provider-grid">
            <button
              className="login-topbar-button"
              type="button"
              onClick={onLogin}
              disabled={loading}
            >
              {loading ? "Signing in..." : "Sign in with your organization"}
            </button>
          </div>

          {error ? (
            <p className="error-note" role="status" aria-live="polite">
              {error}
            </p>
          ) : null}

          <p className="footer-note">
            Your organization&apos;s identity provider keeps your account secure.
          </p>
        </section>
      </div>
    </main>
  );
}
