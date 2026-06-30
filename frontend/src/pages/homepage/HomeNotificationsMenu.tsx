import { useCallback, useEffect, useRef, useState } from "react";

import { fetchJson, getErrorMessage, isSessionExpiredMessage } from "../../api";
import type { NotificationItem, NotificationsResponse } from "../../types";
import { useDismissOnOutsideInteraction } from "./useDismissOnOutsideInteraction";

export function HomeNotificationsMenu({
  onSessionExpired,
}: {
  onSessionExpired: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const handleDismissMenu = useCallback(() => setOpen(false), []);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJson<NotificationsResponse>("/api/notifications");
      setNotifications(result.notifications ?? []);
    } catch (caughtError) {
      const message = getErrorMessage(caughtError);
      setError(message);
      if (isSessionExpiredMessage(message)) {
        onSessionExpired();
      }
    } finally {
      setLoading(false);
    }
  }, [onSessionExpired]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    if (!open) {
      return;
    }
    void loadNotifications();
  }, [loadNotifications, open]);

  useDismissOnOutsideInteraction(open, menuRef, handleDismissMenu);

  const unreadCount = notifications.filter((notification) => !notification.read).length;

  return (
    <div className="notifications-menu" ref={menuRef}>
      <button
        type="button"
        className="notifications-trigger"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label="Open notifications"
        onClick={() => setOpen((current) => !current)}
      >
        <BellIcon />
        {unreadCount ? (
          <span className="notifications-trigger-badge" aria-hidden="true">
            {unreadCount}
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="notifications-popover" role="dialog" aria-label="Notifications">
          <header className="notifications-popover-header">
            <h2>Notifications</h2>
          </header>
          {loading ? (
            <p className="notifications-empty">Loading notifications...</p>
          ) : error ? (
            <p className="notifications-error" role="alert">
              {error}
            </p>
          ) : notifications.length ? (
            <ul className="notifications-list">
              {notifications.map((notification) => (
                <li
                  key={notification.notification_id}
                  className={`notifications-item${notification.read ? "" : " unread"}`}
                >
                  <div className="notifications-item-header">
                    <p className="notifications-item-title">
                      {formatNotificationHeader(notification)}
                    </p>
                    <time
                      className="notifications-item-time"
                      dateTime={notification.created_at}
                    >
                      {formatNotificationDate(notification.created_at)}
                    </time>
                  </div>
                  {notification.body ? (
                    <p className="notifications-item-body">{notification.body}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="notifications-empty">No notifications yet.</p>
          )}
        </div>
      ) : null}
    </div>
  );
}

function formatNotificationHeader(notification: NotificationItem): string {
  const actorName = notification.actor_name?.trim()
  const workspaceName = notification.workspace_name?.trim()

  if (actorName && workspaceName) {
    return `${actorName} left ${workspaceName}`
  }

  if (notification.title?.trim() && workspaceName) {
    return `${notification.title.trim()} · ${workspaceName}`
  }

  return notification.title?.trim() || notification.body?.trim() || "Notification"
}

function formatNotificationDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M12 4.75a4.25 4.25 0 0 0-4.25 4.25v2.1c0 .69-.22 1.36-.63 1.92l-.82 1.09A1.25 1.25 0 0 0 7.97 16h8.06a1.25 1.25 0 0 0 1.02-1.89l-.82-1.09a3.25 3.25 0 0 1-.63-1.92v-2.1A4.25 4.25 0 0 0 12 4.75z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
      <path
        d="M10 18.25a2 2 0 0 0 4 0"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}
