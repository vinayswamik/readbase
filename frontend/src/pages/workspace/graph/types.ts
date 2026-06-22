export type CreateNodeDraft = {
  displayName: string;
  inviteMethod: "email" | "link";
  inviteeEmail: string;
  invitorDesignation: string;
  relation: string;
  reason: string;
  parentNodeId: string;
};
