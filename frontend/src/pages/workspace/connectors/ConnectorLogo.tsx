import type { ConnectorId } from "./connectors";

export function ConnectorLogo({ connectorId }: { connectorId: ConnectorId }) {
  if (connectorId === "slack") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path fill="#36C5F0" d="M11.4 3.2a3.2 3.2 0 0 1 6.4 0v6.4h-6.4z" />
          <path fill="#36C5F0" d="M3.2 11.4a3.2 3.2 0 0 1 0-6.4h3.2v6.4z" />
          <path fill="#2EB67D" d="M28.8 11.4a3.2 3.2 0 0 1 0 6.4h-3.2v-6.4z" />
          <path fill="#2EB67D" d="M20.6 3.2a3.2 3.2 0 0 1 6.4 0v3.2h-6.4z" />
          <path fill="#ECB22E" d="M20.6 28.8a3.2 3.2 0 0 1-6.4 0v-6.4h6.4z" />
          <path fill="#ECB22E" d="M28.8 20.6a3.2 3.2 0 0 1 0 6.4h-6.4v-6.4z" />
          <path fill="#E01E5A" d="M3.2 20.6a3.2 3.2 0 0 1 0-6.4h6.4v6.4z" />
          <path fill="#E01E5A" d="M11.4 28.8a3.2 3.2 0 0 1-6.4 0v-3.2h6.4z" />
        </svg>
      </span>
    );
  }

  if (connectorId === "teams") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <rect x="12" y="7" width="16" height="17" rx="3.2" fill="#6264A7" />
          <circle cx="23.8" cy="6.8" r="3.2" fill="#7B83EB" />
          <circle cx="26.5" cy="14.2" r="2.5" fill="#5059C9" />
          <path fill="#5059C9" d="M18.6 13.2h10.1v5.1a5 5 0 0 1-10.1 0z" />
          <rect x="4" y="10" width="15.4" height="14.6" rx="2.2" fill="#4B53BC" />
          <path fill="#fff" d="M8 14.1h7.4v1.7h-2.7v6.1h-2v-6.1H8z" />
        </svg>
      </span>
    );
  }

  if (connectorId === "github") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path
            fill="#24292F"
            d="M16 2.5c-7.5 0-13.6 6-13.6 13.5 0 6 3.9 11.1 9.3 12.9.7.1.9-.3.9-.7v-2.4c-3.8.8-4.6-1.6-4.6-1.6-.6-1.5-1.5-1.9-1.5-1.9-1.2-.8.1-.8.1-.8 1.4.1 2.1 1.4 2.1 1.4 1.2 2.1 3.2 1.5 3.9 1.2.1-.9.5-1.5.9-1.8-3-.3-6.2-1.5-6.2-6.7 0-1.5.5-2.7 1.4-3.7-.1-.3-.6-1.7.1-3.6 0 0 1.1-.4 3.7 1.4 1.1-.3 2.2-.5 3.4-.5s2.3.2 3.4.5c2.6-1.8 3.7-1.4 3.7-1.4.7 1.9.3 3.3.1 3.6.9 1 1.4 2.2 1.4 3.7 0 5.2-3.2 6.4-6.2 6.7.5.4.9 1.3.9 2.6v3.8c0 .4.2.8.9.7 5.4-1.8 9.3-6.9 9.3-12.9C29.6 8.5 23.5 2.5 16 2.5z"
          />
        </svg>
      </span>
    );
  }

  if (connectorId === "gitlab") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path fill="#E24329" d="M16 28.6 22 10H10z" />
          <path fill="#FC6D26" d="M16 28.6 4.4 10h5.6zM16 28.6 27.6 10H22z" />
          <path fill="#FCA326" d="M4.4 10 2.7 15.2c-.2.7 0 1.5.7 1.9L16 28.6zM27.6 10l1.7 5.2c.2.7 0 1.5-.7 1.9L16 28.6z" />
          <path fill="#E24329" d="M10 10 12.4 3c.2-.7 1.2-.7 1.4 0L16 10zM22 10 19.6 3c-.2-.7-1.2-.7-1.4 0L16 10z" />
        </svg>
      </span>
    );
  }

  if (connectorId === "bitbucket") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path fill="#2684FF" d="M4.4 5.6c-.5 0-.9.5-.8 1l3.3 19.9c.1.6.6 1 1.2 1h15.7c.5 0 1-.4 1.1-.9l3.5-20c.1-.6-.3-1-.8-1z" />
          <path fill="#0052CC" d="M19.8 20.2h-7.5l-1.1-8.4h10z" />
        </svg>
      </span>
    );
  }

  if (connectorId === "linear") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <rect width="32" height="32" rx="8" fill="#5E6AD2" />
          <path fill="#fff" d="M7 19.7 19.7 7h4.1L7 23.8zM7 25.6 25.6 7H28L9.4 25.6zM7 13.9 13.9 7H18L7 18zM12.2 26l13.4-13.4V17L16.6 26z" />
        </svg>
      </span>
    );
  }

  if (connectorId === "confluence") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path fill="#2684FF" d="M9.4 21.7c-1.1 1.8-.8 4.1.8 5.4 1.6 1.2 3.9.9 5.1-.8l7.3-10.4c1.1-1.6.8-3.8-.8-5l-2.1-1.6-3 4.2 1.5 1.1z" />
          <path fill="#0052CC" d="M22.6 10.3c1.1-1.8.8-4.1-.8-5.4-1.6-1.2-3.9-.9-5.1.8L9.4 16.1c-1.1 1.6-.8 3.8.8 5l2.1 1.6 3-4.2-1.5-1.1z" />
        </svg>
      </span>
    );
  }

  if (connectorId === "notion") {
    return (
      <span className="connector-logo" aria-hidden="true">
        <svg viewBox="0 0 100 100" focusable="false">
          <path
            fill="#fff"
            d="M6.017 4.313l55.333-4.087c6.797-.583 8.543-.19 12.817 2.917l17.663 12.443c2.913 2.14 3.883 2.723 3.883 5.053v68.243c0 4.277-1.553 6.807-6.99 7.193L24.467 99.967c-4.08.193-6.023-.39-8.16-3.113L3.3 79.94c-2.333-3.113-3.3-5.443-3.3-8.167V11.113c0-3.497 1.553-6.413 6.017-6.8z"
          />
          <path
            fill="#000"
            fillRule="evenodd"
            clipRule="evenodd"
            d="M61.35.227l-55.333 4.087C1.553 4.7 0 7.617 0 11.113v60.66c0 2.723.967 5.053 3.3 8.167l13.007 16.913c2.137 2.723 4.08 3.307 8.16 3.113l64.257-3.89c5.433-.387 6.99-2.917 6.99-7.193V20.64c0-2.21-.873-2.847-3.443-4.733L74.167 3.143c-4.273-3.107-6.02-3.5-12.817-2.917zM25.92 19.523c-5.247.353-6.437.433-9.417-1.99L8.927 11.507c-.77-.78-.383-1.753 1.557-1.947l53.193-3.887c4.467-.39 6.793 1.167 8.54 2.527l9.123 6.61c.39.197 1.36 1.36.193 1.36l-54.933 3.307-.68.047zM19.803 88.3V30.367c0-2.53.777-3.697 3.103-3.893L86 22.78c2.14-.193 3.107 1.167 3.107 3.693v57.547c0 2.53-.39 4.67-3.883 4.863l-60.377 3.5c-3.493.193-5.043-.97-5.043-4.083zm59.6-54.827c.387 1.75 0 3.5-1.75 3.7l-2.91.577v42.773c-2.527 1.36-4.853 2.137-6.797 2.137-3.107 0-3.883-.973-6.21-3.887l-19.03-29.94v28.967l6.02 1.363s0 3.5-4.857 3.5l-13.39.777c-.39-.78 0-2.723 1.357-3.11l3.497-.97v-38.3L30.48 40.667c-.39-1.75.58-4.277 3.3-4.473l14.367-.967 19.8 30.327v-26.83l-5.047-.58c-.39-2.143 1.163-3.7 3.103-3.89l13.4-.78z"
          />
        </svg>
      </span>
    );
  }

  return (
    <span className="connector-logo" aria-hidden="true">
      <svg viewBox="0 0 32 32" focusable="false">
        <path fill="#2684FF" d="M16 3 29 16 16 29 3 16z" />
        <path fill="#0052CC" d="M16 8.5 23.5 16 16 23.5 8.5 16z" />
        <path fill="#fff" d="M16 12.2 19.8 16 16 19.8 12.2 16z" />
      </svg>
    </span>
  );
}

