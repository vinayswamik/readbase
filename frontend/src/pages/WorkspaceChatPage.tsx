import type { AuthUser, Workspace } from "../types";
import { WorkspaceChatPageImpl } from "./workspace/WorkspaceChatPageImpl";

export function WorkspaceChatPage({
  user,
  workspace,
  onBack,
  onSessionExpired,
  sourcesOpen,
  onSourcesOpenChange,
}: {
  user: AuthUser;
  workspace: Workspace;
  onBack: () => void;
  onSessionExpired: () => void;
  sourcesOpen: boolean;
  onSourcesOpenChange: (open: boolean) => void;
}) {
  return (
    <WorkspaceChatPageImpl
      user={user}
      workspace={workspace}
      onBack={onBack}
      onSessionExpired={onSessionExpired}
      sourcesOpen={sourcesOpen}
      onSourcesOpenChange={onSourcesOpenChange}
    />
  );
}
