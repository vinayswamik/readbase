import { memo, useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import type { HierarchyNode, IndexedRepo } from "../../types";
import type { CreateNodeDraft } from "./graph/types";

const MAX_PICKER_RESULTS = 20;

export function buildInviteJoinUrl(joinPath: string | null | undefined, joinToken?: string | null): string {
  const path = joinPath || (joinToken ? `/?join=${joinToken}` : "");
  if (!path) {
    return "";
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${window.location.origin}${path.startsWith("/") ? path : `/${path}`}`;
}

export function RepoList({
  repos,
  selectedRepoId,
  error,
  onSelect,
}: {
  repos: IndexedRepo[];
  selectedRepoId: string | null;
  error: string | null;
  onSelect: (repo: IndexedRepo) => void;
}) {
  if (error) {
    return <div className="status-text">{error}</div>;
  }

  if (!repos.length) {
    return <div className="status-text">No indexed repositories yet.</div>;
  }

  return (
    <div className="repo-list">
      {repos.map((repo) => (
        <button
          key={repo.repo_id}
          type="button"
          className={`repo-item${repo.repo_id === selectedRepoId ? " active" : ""}`}
          onClick={() => onSelect(repo)}
        >
          <span className="repo-url">{repo.repo_url}</span>
          <span className="repo-meta">
            {repo.file_count} files, {repo.chunk_count} chunks
          </span>
        </button>
      ))}
    </div>
  );
}

export function CreateNodeForm({
  canManageWorkspace,
  disabled,
  parentOptions,
  ownNode,
  onCreate,
  onCreated,
}: {
  canManageWorkspace: boolean;
  disabled: boolean;
  parentOptions: HierarchyNode[];
  ownNode: HierarchyNode | null;
  onCreate: (draft: CreateNodeDraft) => Promise<boolean | string>;
  onCreated?: (result: boolean | string) => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [inviteMethod, setInviteMethod] = useState<"email" | "link">("email");
  const [inviteeEmail, setInviteeEmail] = useState("");
  const [invitorDesignation, setInvitorDesignation] = useState("");
  const [relation, setRelation] = useState("");
  const [reason, setReason] = useState("");
  const [parentNodeId, setParentNodeId] = useState("");
  const [createdJoinUrl, setCreatedJoinUrl] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  const handleParentNodeChange = useCallback((nextParentNodeId: string) => {
    setParentNodeId(nextParentNodeId);
  }, []);

  useEffect(() => {
    if (!canManageWorkspace) {
      setParentNodeId(ownNode?.node_id ?? "");
      return;
    }
    if (parentNodeId && !parentOptions.some((node) => node.node_id === parentNodeId)) {
      setParentNodeId("");
    }
  }, [canManageWorkspace, ownNode, parentNodeId, parentOptions]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCopyStatus(null);
    const result = await onCreate({
      displayName,
      inviteMethod,
      inviteeEmail,
      invitorDesignation,
      relation,
      reason,
      parentNodeId,
    });
    if (result === false) {
      return;
    }
    onCreated?.(result);
    if (typeof result === "string") {
      setCreatedJoinUrl(result);
    }
    setDisplayName("");
    setInviteeEmail("");
    setInvitorDesignation("");
    setRelation("");
    setReason("");
    if (canManageWorkspace) {
      setParentNodeId("");
    }
  }

  useEffect(() => {
    if (inviteMethod === "email") {
      setCreatedJoinUrl(null);
      setCopyStatus(null);
    }
  }, [inviteMethod]);

  const needsOwnNode = !canManageWorkspace && !ownNode;
  const canCreate = Boolean(
    !disabled &&
      !needsOwnNode &&
      displayName.trim() &&
      relation.trim() &&
      reason.trim() &&
      (canManageWorkspace || parentNodeId) &&
      (inviteMethod === "link" || inviteeEmail.trim()),
  );

  async function handleCopyJoinUrl() {
    if (!createdJoinUrl) {
      return;
    }
    try {
      await navigator.clipboard.writeText(createdJoinUrl);
      setCopyStatus("Invite link copied.");
    } catch {
      setCopyStatus("Could not copy automatically. Select the link and copy it manually.");
    }
  }

  return (
    <form className="graph-control-form" onSubmit={handleSubmit}>
      <label id="inviteMethodLabel">Invite method</label>
      <div className="assign-mode-toggle" role="group" aria-labelledby="inviteMethodLabel">
        <button
          type="button"
          className={inviteMethod === "email" ? "active" : ""}
          disabled={disabled}
          onClick={() => setInviteMethod("email")}
        >
          Email
        </button>
        <button
          type="button"
          className={inviteMethod === "link" ? "active" : ""}
          disabled={disabled}
          onClick={() => setInviteMethod("link")}
        >
          Invite link
        </button>
      </div>

      <label htmlFor="nodeTitle">Display name</label>
      <textarea
        id="nodeTitle"
        value={displayName}
        maxLength={120}
        rows={1}
        placeholder="Role shown on graph"
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        disabled={disabled}
        onChange={(event) => setDisplayName(event.target.value)}
      />

      {inviteMethod === "email" ? (
        <>
          <label htmlFor="inviteeEmail">Invitee email</label>
          <input
            id="inviteeEmail"
            type="email"
            value={inviteeEmail}
            placeholder="colleague@company.com"
            required
            disabled={disabled}
            autoComplete="off"
            onChange={(event) => setInviteeEmail(event.target.value)}
          />
        </>
      ) : (
        <div className="status-text compact">
          Create a shareable link. Anyone signed in with the link can accept and join under the
          role details you enter below.
        </div>
      )}

      <label htmlFor="invitorDesignation">Your designation</label>
      <input
        id="invitorDesignation"
        value={invitorDesignation}
        maxLength={120}
        placeholder="e.g. Engineering manager"
        disabled={disabled}
        onChange={(event) => setInvitorDesignation(event.target.value)}
      />
      <label htmlFor="inviteRelation">Relation in org</label>
      <input
        id="inviteRelation"
        value={relation}
        maxLength={120}
        placeholder="e.g. Direct report, peer on Platform team"
        required
        disabled={disabled}
        onChange={(event) => setRelation(event.target.value)}
      />
      <label htmlFor="inviteReason">Reason</label>
      <textarea
        id="inviteReason"
        value={reason}
        maxLength={2000}
        rows={3}
        placeholder="Why are you adding this person to the workspace?"
        required
        disabled={disabled}
        onChange={(event) => setReason(event.target.value)}
      />

      <label id="parentNodeLabel">Parent</label>
      <ParentNodeSelect
        value={parentNodeId}
        disabled={disabled || !canManageWorkspace}
        canManageWorkspace={canManageWorkspace}
        parentOptions={parentOptions}
        labelId="parentNodeLabel"
        onChange={handleParentNodeChange}
      />

      {needsOwnNode ? (
        <div className="status-text compact">
          You need your own node on the graph before you can invite someone beneath you.
        </div>
      ) : null}

      {createdJoinUrl ? (
        <div className="invite-link-box">
          <label htmlFor="createdJoinUrl">Share this invite link</label>
          <input id="createdJoinUrl" value={createdJoinUrl} readOnly />
          <div className="invite-link-actions">
            <button type="button" className="secondary-action-button" onClick={() => void handleCopyJoinUrl()}>
              Copy link
            </button>
          </div>
          {copyStatus ? <div className="status-text compact">{copyStatus}</div> : null}
        </div>
      ) : null}

      <button type="submit" className="primary-button" disabled={!canCreate}>
        {disabled
          ? "Working..."
          : inviteMethod === "link"
            ? "Create invite link"
            : "Invite and create node"}
      </button>
    </form>
  );
}

export const AssignableUserPicker = memo(function AssignableUserPicker({
  value,
  disabled,
  availableAssignees,
  labelId,
  emptyLabel,
  searchPlaceholder,
  onChange,
}: {
  value: string;
  disabled: boolean;
  availableAssignees: import("../../types").HierarchyAssignableUser[];
  labelId: string;
  emptyLabel: string;
  searchPlaceholder: string;
  onChange: (assignedUserId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const selectedUser = availableAssignees.find((user) => user.user_id === value) ?? null;
  const normalizedQuery = query.trim().toLowerCase();
  const results = useMemo(() => {
    const matches = normalizedQuery
      ? availableAssignees.filter((assignableUser) =>
          `${assignableUser.name} ${assignableUser.email}`.toLowerCase().includes(normalizedQuery),
        )
      : availableAssignees;
    const visible = matches.slice(0, MAX_PICKER_RESULTS);
    if (selectedUser && !visible.some((user) => user.user_id === selectedUser.user_id)) {
      return [selectedUser, ...visible];
    }
    return visible;
  }, [availableAssignees, normalizedQuery, selectedUser]);

  return (
    <div className="compact-picker" aria-labelledby={labelId}>
      <input
        type="search"
        value={query}
        placeholder={searchPlaceholder}
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="picker-current">
        <span>{selectedUser ? selectedUser.name || selectedUser.email : emptyLabel}</span>
        {selectedUser ? (
          <button type="button" disabled={disabled} onClick={() => onChange("")}>
            Clear
          </button>
        ) : null}
      </div>
      {query || !selectedUser ? (
        <div className="picker-results">
          {results.map((assignableUser) => (
            <button
              key={assignableUser.user_id}
              type="button"
              disabled={disabled}
              className={assignableUser.user_id === value ? "active" : ""}
              onClick={() => {
                onChange(assignableUser.user_id);
                setQuery("");
              }}
            >
              {assignableUser.name || assignableUser.email}
            </button>
          ))}
          {!results.length ? <span>No users match.</span> : null}
        </div>
      ) : null}
    </div>
  );
});

export const ParentNodeSelect = memo(function ParentNodeSelect({
  value,
  disabled,
  canManageWorkspace,
  parentOptions,
  labelId,
  onChange,
}: {
  value: string;
  disabled: boolean;
  canManageWorkspace: boolean;
  parentOptions: HierarchyNode[];
  labelId: string;
  onChange: (parentNodeId: string) => void;
}) {
  if (!canManageWorkspace) {
    const ownNode = parentOptions[0] ?? null;
    return (
      <div className="parent-node-readonly" aria-labelledby={labelId}>
        {ownNode ? ownNode.display_name : "Your node"}
      </div>
    );
  }

  return (
    <select
      id="parentNodeSelect"
      aria-labelledby={labelId}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">No parent (root)</option>
      {parentOptions.map((node) => (
        <option key={node.node_id} value={node.node_id}>
          {node.display_name}
        </option>
      ))}
    </select>
  );
});