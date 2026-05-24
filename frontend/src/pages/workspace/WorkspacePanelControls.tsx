import { memo, useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import type { AuthUser, HierarchyAssignableUser, HierarchyNode, IndexedRepo } from "../../types";
import type { CreateNodeDraft } from "../WorkspaceLeftPanel";

const MAX_PICKER_RESULTS = 20;

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
  userRole,
  disabled,
  availableAssignees,
  parentOptions,
  ownNode,
  onCreate,
}: {
  userRole: AuthUser["role"];
  disabled: boolean;
  availableAssignees: HierarchyAssignableUser[];
  parentOptions: HierarchyNode[];
  ownNode: HierarchyNode | null;
  onCreate: (draft: CreateNodeDraft) => Promise<boolean>;
}) {
  const [displayName, setDisplayName] = useState("");
  const [assignedUserId, setAssignedUserId] = useState("");
  const [parentNodeId, setParentNodeId] = useState("");
  const handleAssignedUserChange = useCallback((nextAssignedUserId: string) => {
    setAssignedUserId(nextAssignedUserId);
  }, []);
  const handleParentNodeChange = useCallback((nextParentNodeId: string) => {
    setParentNodeId(nextParentNodeId);
  }, []);

  useEffect(() => {
    if (assignedUserId && !availableAssignees.some((user) => user.user_id === assignedUserId)) {
      setAssignedUserId("");
    }
  }, [assignedUserId, availableAssignees]);

  useEffect(() => {
    if (userRole !== "admin") {
      setParentNodeId(ownNode?.node_id ?? "");
      return;
    }
    if (parentNodeId && !parentOptions.some((node) => node.node_id === parentNodeId)) {
      setParentNodeId("");
    }
  }, [ownNode, parentNodeId, parentOptions, userRole]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await onCreate({
      displayName,
      assignedUserId,
      parentNodeId,
    });
    if (created) {
      setDisplayName("");
      setAssignedUserId("");
      if (userRole === "admin") {
        setParentNodeId("");
      }
    }
  }

  const canCreate = Boolean(
    !disabled &&
      displayName.trim() &&
      assignedUserId &&
      (userRole === "admin" || parentNodeId),
  );

  return (
    <form className="graph-control-form" onSubmit={handleSubmit}>
      <label htmlFor="nodeTitle">Display name</label>
      <textarea
        id="nodeTitle"
        value={displayName}
        maxLength={120}
        rows={1}
        placeholder="Name shown on graph"
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        disabled={disabled}
        onChange={(event) => setDisplayName(event.target.value)}
      />
      <label id="assignedUserLabel">Assigned user</label>
      <AssignableUserPicker
        value={assignedUserId}
        disabled={disabled}
        availableAssignees={availableAssignees}
        labelId="assignedUserLabel"
        emptyLabel="No assignee selected"
        searchPlaceholder="Search unassigned users"
        onChange={handleAssignedUserChange}
      />
      <label id="parentNodeLabel">Parent</label>
      <ParentNodeSelect
        value={parentNodeId}
        disabled={disabled || userRole !== "admin"}
        userRole={userRole}
        parentOptions={parentOptions}
        labelId="parentNodeLabel"
        onChange={handleParentNodeChange}
      />
      {availableAssignees.length ? null : (
        <div className="status-text compact">No unassigned logged-in workspace users.</div>
      )}
      <button type="submit" className="primary-button" disabled={!canCreate}>
        {disabled ? "Working..." : "Create node"}
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
  availableAssignees: HierarchyAssignableUser[];
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
  userRole,
  parentOptions,
  labelId,
  onChange,
}: {
  value: string;
  disabled: boolean;
  userRole: AuthUser["role"];
  parentOptions: HierarchyNode[];
  labelId: string;
  onChange: (parentNodeId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const selectedParent = parentOptions.find((node) => node.node_id === value) ?? null;
  const parentMatches = useMemo(
    () =>
      normalizedQuery
        ? parentOptions.filter((node) => {
            const searchable = [
              node.display_name,
              node.assigned_user_name || "",
              node.assigned_user_email || "",
            ]
              .join(" ")
              .toLowerCase();
            return searchable.includes(normalizedQuery);
          })
        : parentOptions,
    [normalizedQuery, parentOptions],
  );
  const filteredParents = useMemo(() => {
    const visible = parentMatches.slice(0, MAX_PICKER_RESULTS);
    if (selectedParent && !visible.some((node) => node.node_id === selectedParent.node_id)) {
      return [selectedParent, ...visible];
    }
    return visible;
  }, [parentMatches, selectedParent]);
  const matchCount = parentMatches.length;

  return (
    <div className="compact-picker" aria-labelledby={labelId}>
      {userRole === "admin" ? (
        <input
          type="search"
          value={query}
          placeholder="Search parent nodes"
          disabled={disabled}
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => setQuery(event.target.value)}
        />
      ) : null}
      <div className="picker-current">
        <span>{selectedParent ? selectedParent.display_name : "No parent"}</span>
        {userRole === "admin" && selectedParent ? (
          <button type="button" disabled={disabled} onClick={() => onChange("")}>
            Clear
          </button>
        ) : null}
      </div>
      {userRole === "admin" && query ? (
        <div className="picker-results">
          {filteredParents.slice(0, MAX_PICKER_RESULTS).map((node) => (
            <button
              key={node.node_id}
              type="button"
              disabled={disabled}
              className={node.node_id === value ? "active" : ""}
              onClick={() => {
                onChange(node.node_id);
                setQuery("");
              }}
            >
              {node.display_name}
            </button>
          ))}
          {!filteredParents.length ? <span>No parent nodes match.</span> : null}
          {matchCount > MAX_PICKER_RESULTS ? (
            <span>Showing {MAX_PICKER_RESULTS} of {matchCount} matches.</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
});
