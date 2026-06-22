export function AppToast({
  message,
  error = false,
}: {
  message?: string | null;
  error?: boolean;
}) {
  if (!message) {
    return null;
  }

  return (
    <div
      key={message}
      className={`app-toast${error ? " error" : ""}`}
      role="status"
      aria-live="polite"
    >
      {message}
    </div>
  );
}
