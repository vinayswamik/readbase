export function LoginPage() {
  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <header className="login-header">
          <span className="brand-badge">Readbase</span>
          <h1 id="login-title">Login with Google</h1>
          <p>Use your Google account to continue.</p>
        </header>

        <div className="provider-grid">
          <button className="secondary-button" type="button">
            Continue with Google
          </button>
        </div>

        <p className="footer-note">
          Not registered yet? Sign in with Google.
        </p>
      </section>
    </main>
  );
}
