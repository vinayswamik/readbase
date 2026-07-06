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
    ? "brand-logo brand-logo--icon-only brand-logo-button"
    : "brand-logo brand-logo-button";

  return (
    <button
      type="button"
      className={className}
      disabled={!onClick}
      onClick={onClick}
      aria-label={iconOnly && onClick ? "Back to workspaces" : "Readbase"}
    >
      {logo}
    </button>
  );
}
