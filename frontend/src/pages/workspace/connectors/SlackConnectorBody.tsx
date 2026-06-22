import { useDeferredValue, useMemo, useState } from "react";

import type { ConnectorSetupModalProps } from "./ConnectorSetupModalTypes";
import type { SlackChannel, WorkspaceSlackSource, WorkspaceSlackTeam } from "../../../types";
import {
  buildSlackChannelSearchIndex,
  searchSlackChannelEntries,
} from "./slackChannelSearch";
import { SlackUnlinkTeamDialog } from "./SlackUnlinkTeamDialog";

function SlackWorkspaceRow({
  team,
  loading,
  onRequestRemove,
}: {
  team: WorkspaceSlackTeam;
  loading: boolean;
  onRequestRemove: (team: WorkspaceSlackTeam) => void;
}) {
  return (
    <div className="connector-access-row slack-workspace-row">
      <div className="slack-row-main">
        <span className="slack-row-title">{team.team_name}</span>
        {team.team_domain ? (
          <span className="slack-row-url">{team.team_domain}.slack.com</span>
        ) : null}
      </div>
      <button
        type="button"
        className="danger-button compact-button"
        disabled={loading}
        aria-label={`Remove ${team.team_name} from this workspace`}
        onClick={() => onRequestRemove(team)}
      >
        Remove
      </button>
    </div>
  );
}

function SlackChannelRow({
  channelName,
  workspaceName,
  actionLabel,
  actionClassName,
  disabled,
  onAction,
}: {
  channelName: string;
  workspaceName: string;
  actionLabel: string;
  actionClassName: "danger-button" | "secondary-action-button";
  disabled: boolean;
  onAction: () => void;
}) {
  return (
    <div className="connector-access-row slack-channel-row">
      <span className="slack-channel-name">#{channelName}</span>
      <span className="slack-channel-workspace">{workspaceName}</span>
      <button
        type="button"
        className={`${actionClassName} compact-button`}
        disabled={disabled}
        aria-label={`${actionLabel} #${channelName} from ${workspaceName}`}
        onClick={onAction}
      >
        {actionLabel}
      </button>
    </div>
  );
}

export function SlackConnectorBody({
  slackConnection,
  slackTeams,
  slackSources,
  slackChannels,
  slackChannelQuery,
  slackLoading,
  error,
  onSlackConnect,
  onSlackUnlinkTeam,
  onSlackChannelQueryChange,
  onAddSlackChannel,
  onRemoveSlackSource,
}: ConnectorSetupModalProps) {
  const [pendingUnlinkTeam, setPendingUnlinkTeam] = useState<WorkspaceSlackTeam | null>(null);
  const [unlinkingTeam, setUnlinkingTeam] = useState(false);
  const slackConfigured = slackConnection?.configured !== false;
  const hasLinkedWorkspace = slackTeams.length > 0;
  const deferredChannelQuery = useDeferredValue(slackChannelQuery);

  const addedChannelKeys = useMemo(
    () => new Set(slackSources.map((source) => `${source.team_id}:${source.channel_id}`)),
    [slackSources],
  );

  const slackChannelSearchIndex = useMemo(
    () => buildSlackChannelSearchIndex(slackChannels),
    [slackChannels],
  );

  const availableSlackChannels = useMemo(
    () => searchSlackChannelEntries(slackChannelSearchIndex, deferredChannelQuery, addedChannelKeys),
    [addedChannelKeys, deferredChannelQuery, slackChannelSearchIndex],
  );

  async function handleConfirmUnlinkTeam() {
    if (!pendingUnlinkTeam || unlinkingTeam) {
      return;
    }
    setUnlinkingTeam(true);
    try {
      await Promise.resolve(onSlackUnlinkTeam(pendingUnlinkTeam.team_id));
      setPendingUnlinkTeam(null);
    } finally {
      setUnlinkingTeam(false);
    }
  }

  return (
    <div
      className="connector-modal-body slack-connector-body"
      aria-busy={slackLoading}
    >
      {error ? (
        <div
          className="connector-modal-alert error"
          role="alert"
          aria-live="polite"
        >
          {error}
        </div>
      ) : null}

      {!slackConfigured ? (
        <div className="connector-modal-alert error" role="alert">
          Slack OAuth is not configured on the backend.
        </div>
      ) : null}

      <section
        className="connector-access-list slack-workspaces-panel"
        aria-labelledby="slack-workspaces-heading"
      >
        <div className="connector-section-row">
          <h3 id="slack-workspaces-heading" className="slack-section-heading">
            <span>Workspaces</span>
            {slackTeams.length ? (
              <span className="slack-section-count">{slackTeams.length}</span>
            ) : null}
          </h3>
          <div className="connector-section-actions">
            <button
              type="button"
              className="primary-button compact-button"
              disabled={slackLoading || !slackConfigured}
              aria-label="Connect a Slack workspace"
              onClick={onSlackConnect}
            >
              Add workspace
            </button>
          </div>
        </div>

        <div className="slack-section-scroll slack-workspace-list">
          {!hasLinkedWorkspace ? (
            <div className="slack-empty-state">
              <p className="slack-empty-title">No workspaces linked</p>
              <p className="slack-empty-copy">
                Connect a workspace to browse channels and add them here.
              </p>
            </div>
          ) : (
            slackTeams.map((team) => (
              <SlackWorkspaceRow
                key={team.team_id}
                team={team}
                loading={slackLoading || unlinkingTeam}
                onRequestRemove={setPendingUnlinkTeam}
              />
            ))
          )}
        </div>
      </section>

      {hasLinkedWorkspace ? (
        <section
          className="connector-access-list slack-channels-panel"
          aria-labelledby="slack-channels-heading"
        >
          <div className="connector-section-row">
            <h3 id="slack-channels-heading" className="slack-section-heading">
              <span>Channels</span>
              {slackSources.length ? (
                <span className="slack-section-count">{slackSources.length}</span>
              ) : null}
            </h3>
            <div className="connector-section-actions slack-channel-search-wrap">
              <label className="slack-search-label" htmlFor="slack-channel-search">
                Search channels
              </label>
              <input
                id="slack-channel-search"
                className="connector-section-search slack-channel-search"
                type="search"
                value={slackChannelQuery}
                placeholder="Search channels"
                autoComplete="off"
                spellCheck={false}
                disabled={slackLoading}
                onChange={(event) => onSlackChannelQueryChange(event.target.value)}
              />
            </div>
          </div>

          <div className="slack-section-scroll slack-channel-list">
            {slackSources.map((source: WorkspaceSlackSource) => (
              <SlackChannelRow
                key={source.source_id}
                channelName={source.channel_name}
                workspaceName={source.team_name}
                actionLabel="Remove"
                actionClassName="danger-button"
                disabled={slackLoading || source.user_access !== "connected"}
                onAction={() => onRemoveSlackSource(source.source_id)}
              />
            ))}

            {slackSources.length && availableSlackChannels.length ? (
              <div className="connector-result-divider" aria-hidden="true" />
            ) : null}

            {availableSlackChannels.map((channel: SlackChannel) => (
              <SlackChannelRow
                key={`${channel.team_id}:${channel.channel_id}`}
                channelName={channel.channel_name}
                workspaceName={channel.team_name}
                actionLabel="Add"
                actionClassName="secondary-action-button"
                disabled={slackLoading}
                onAction={() => onAddSlackChannel(channel)}
              />
            ))}
          </div>
        </section>
      ) : null}

      <SlackUnlinkTeamDialog
        teamName={pendingUnlinkTeam?.team_name ?? ""}
        teamDomain={pendingUnlinkTeam?.team_domain}
        open={pendingUnlinkTeam !== null}
        loading={unlinkingTeam}
        onCancel={() => {
          if (!unlinkingTeam) {
            setPendingUnlinkTeam(null);
          }
        }}
        onConfirm={() => void handleConfirmUnlinkTeam()}
      />
    </div>
  );
}
