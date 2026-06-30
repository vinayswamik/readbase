import { ReadbaseLogoIcon } from "./ReadbaseLogoIcon";

export function ReadbaseLogo({
  onClick,
  iconOnly = false,
}: {
  onClick?: () => void;
  iconOnly?: boolean;
}) {
  const logo = (
    <>
      <span className="brand-logo-icon-wrap">
        <ReadbaseLogoIcon className="brand-logo-icon" />
      </span>
      {iconOnly ? null : <span className="brand-logo-text">readbase</span>}
    </>
  );

  const className = iconOnly
    ? onClick
      ? "brand-logo brand-logo--icon-only brand-logo-button"
      : "brand-logo brand-logo--icon-only"
    : onClick
      ? "brand-logo brand-logo-button"
      : "brand-logo";

  if (!onClick) {
    return (
      <span className={className} aria-label="Readbase">
        {logo}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={className}
      onClick={onClick}
      aria-label="Back to workspaces"
    >
      {logo}
    </button>
  );
}
