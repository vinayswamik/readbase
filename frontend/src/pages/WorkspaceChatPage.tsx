import type { AuthUser, Workspace } from "../types";
import { WorkspaceChatPageImpl } from "./workspace/WorkspaceChatPageImpl";

export function WorkspaceChatPage({
  user,
  workspace,
  onBack,
  onSessionExpired,
}: {
  user: AuthUser;
  workspace: Workspace;
  onBack: () => void;
  onSessionExpired: () => void;
}) {
  return (
    <WorkspaceChatPageImpl
      user={user}
      workspace={workspace}
      onBack={onBack}
      onSessionExpired={onSessionExpired}
    />
  );
}
