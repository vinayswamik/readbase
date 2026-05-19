export function LoginPage({
  loading,
  error,
  onLogin,
}: {
  loading: boolean;
  error: string | null;
  onLogin: (portal: "admin" | "member") => void;
}) {
  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <header className="login-header">
          <span className="brand-badge">Readbase</span>
          <h1 id="login-title">Choose your login</h1>
          <p>Admins manage workspaces. Members use workspaces they have been added to.</p>
        </header>

        <div className="provider-grid">
          <button
            className="secondary-button"
            type="button"
            onClick={() => onLogin("admin")}
            disabled={loading}
          >
            {loading ? "Signing in..." : "Admin Login"}
          </button>
          <button
            className="secondary-button muted-button"
            type="button"
            onClick={() => onLogin("member")}
            disabled={loading}
          >
            {loading ? "Signing in..." : "Member Login"}
          </button>
        </div>

        {error ? (
          <p className="error-note" role="status" aria-live="polite">
            {error}
          </p>
        ) : null}

        <p className="footer-note">
          Both options use Google sign-in.
        </p>
      </section>
    </main>
  );
}
