export function confirmConnectorDisconnect(connectorName: string): boolean {
  return window.confirm(
    [
      `Disconnect ${connectorName}?`,
      "",
      "This removes your account connection for all workspaces.",
      "",
      `You will lose access to all ${connectorName} data. Existing workspace sources may stop syncing until you connect again.`,
    ].join("\n"),
  );
}

export function confirmSlackWorkspaceRemove(
  teamName: string,
  teamDomain?: string | null,
): boolean {
  const workspaceLabel = teamDomain ? `${teamDomain}.slack.com` : teamName;
  return window.confirm(
    [
      "Remove Slack workspace?",
      "",
      `Are you sure you want to remove ${workspaceLabel} from this Readbase workspace?`,
      "",
      `Channels from this workspace will be removed. Indexed Slack channels linked to ${teamName} will stop syncing in this workspace.`,
    ].join("\n"),
  );
}
