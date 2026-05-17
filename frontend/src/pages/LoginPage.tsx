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
      <section className="login-panel" aria-labelledby="login-title">
        <header className="login-header">
          <span className="brand-badge">Readbase</span>
          <h1 id="login-title">Login with Google</h1>
          <p>Use your Google account to continue.</p>
        </header>

        <div className="provider-grid">
          <button
            className="secondary-button"
            type="button"
            onClick={onLogin}
            disabled={loading}
          >
            {loading ? "Signing in..." : "Continue with Google"}
          </button>
        </div>

        {error ? (
          <p className="error-note" role="status" aria-live="polite">
            {error}
          </p>
        ) : null}

        <p className="footer-note">
          Not registered yet? Sign in with Google.
        </p>
      </section>
    </main>
  );
}
