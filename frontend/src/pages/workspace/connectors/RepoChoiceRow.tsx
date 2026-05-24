export function RepoChoiceRow({
  label,
  isPrivate,
  url,
  disabled,
  onSelect,
}: {
  label: string;
  isPrivate: boolean;
  url: string;
  disabled: boolean;
  onSelect: (repoUrl: string) => void;
}) {
  return (
    <div className="connector-access-row">
      <span>{label}</span>
      <strong>{isPrivate ? "Private" : "Public"}</strong>
      <button
        type="button"
        className="secondary-action-button compact-button"
        disabled={disabled || !url}
        onClick={() => onSelect(url)}
      >
        Select
      </button>
    </div>
  );
}

