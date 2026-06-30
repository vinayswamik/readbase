import type { Workspace } from "./types";

export const WORKSPACE_NAME_MAX_LENGTH = 80;

export function normalizeWorkspaceNameInput(name: string): string {
  return name.trim().replace(/\s+/g, " ");
}

export function workspaceNameKey(name: string): string {
  return normalizeWorkspaceNameInput(name).toLocaleLowerCase();
}

export function isOwnedWorkspaceNameTaken(
  name: string,
  ownedWorkspaces: Workspace[],
  excludeWorkspaceId?: string,
): boolean {
  const key = workspaceNameKey(name);
  if (!key) {
    return false;
  }
  return ownedWorkspaces.some(
    (workspace) =>
      workspace.workspace_id !== excludeWorkspaceId &&
      workspaceNameKey(workspace.name) === key,
  );
}
