import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { useAuth } from "./useAuth";

export function App() {
  const {
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
  } = useAuth();

  if (isLoadingSession) {
    return null;
  }

  const isAuthMisconfigured = Boolean(authConfigError || !authProvider);

  if (isAuthMisconfigured || showLoginPage) {
    return (
      <LoginPage
        configError={authConfigError}
        provider={isAuthMisconfigured ? null : authProvider}
        loading={isAuthMisconfigured ? false : isSubmitting}
        error={isAuthMisconfigured ? null : error}
        onLogin={isAuthMisconfigured ? () => {} : handleLogin}
      />
    );
  }

  return (
    <HomePage
      user={user!}
      loading={isSubmitting}
      onLogout={handleLogout}
      onSessionExpired={handleSessionExpired}
      appRoute={appRoute}
      onNavigate={navigateApp}
      onReplaceNavigate={replaceAppRoute}
    />
  );
}
