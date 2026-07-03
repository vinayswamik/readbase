import type { ReactNode } from "react";

import { AppTopbarWorkspaceTitle } from "./AppTopbarWorkspaceTitle";
import { ReadbaseLogo } from "./ReadbaseLogo";
import type { Workspace } from "../types";

export function AppTopbar({
  sticky = false,
  workspaceNav,
  children,
}: {
  sticky?: boolean;
  workspaceNav?: {
    workspaceId: string;
    name: string;
    canManage: boolean;
    onGoToWorkspaces: () => void;
    onRenamed: (workspace: Workspace) => void;
    onSessionExpired: () => void;
  };
  children?: ReactNode;
}) {
  return (
    <header className={sticky ? "app-topbar app-topbar--sticky" : "app-topbar"}>
      {workspaceNav ? (
        <>
          <ReadbaseLogo iconOnly onClick={workspaceNav.onGoToWorkspaces} />
          <AppTopbarWorkspaceTitle
            workspaceId={workspaceNav.workspaceId}
            name={workspaceNav.name}
            canManage={workspaceNav.canManage}
            onRenamed={workspaceNav.onRenamed}
            onSessionExpired={workspaceNav.onSessionExpired}
          />
        </>
      ) : (
        <ReadbaseLogo />
      )}
      {children ? <div className="app-topbar-trailing">{children}</div> : null}
    </header>
  );
}
