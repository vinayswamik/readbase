import { useState } from "react";

import type { ConnectorSetupModalProps } from "./ConnectorSetupModalTypes";

export function SlackConnectorBody({
  slackConnection,
  slackSources,
  slackChannels,
  slackChannelQuery,
  slackLoading,
  error,
  status,
  onSlackConnect,
  onSlackDisconnect,
  onSlackChannelQueryChange,
  onAddSlackChannel,
  onRemoveSlackSource,
}: ConnectorSetupModalProps) {
  const slackChannelSearchActive = Boolean(slackChannelQuery.trim());
  const searchedSlackChannels = slackChannels.slice(0, 12);
  const searchedAddedSlackChannels = searchedSlackChannels.filter((channel) =>
    slackSources.some(
      (source) => source.team_id === channel.team_id && source.channel_id === channel.channel_id,
    ),
  );
  const searchedAvailableSlackChannels = searchedSlackChannels.filter(
    (channel) =>
      !slackSources.some(
        (source) => source.team_id === channel.team_id && source.channel_id === channel.channel_id,
      ),
  );
  const [slackWorkspacesOpen, setSlackWorkspacesOpen] = useState(true);
  const [slackChannelsOpen, setSlackChannelsOpen] = useState(true);

  return (<div className="connector-modal-body">
            <section className="connector-access-list">
              <div className="connector-section-row">
                <button
                  type="button"
                  className="connector-section-toggle"
                  aria-expanded={slackWorkspacesOpen}
                  onClick={() => setSlackWorkspacesOpen((open) => !open)}
                >
                  <span>Workspaces</span>
                  <span
                    className={`connector-section-chevron${slackWorkspacesOpen ? " open" : ""}`}
                    aria-hidden="true"
                  >
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M12.7071 14.7071C12.3166 15.0976 11.6834 15.0976 11.2929 14.7071L6.29289 9.70711C5.90237 9.31658 5.90237 8.68342 6.29289 8.29289C6.68342 7.90237 7.31658 7.90237 7.70711 8.29289L12 12.5858L16.2929 8.29289C16.6834 7.90237 17.3166 7.90237 17.7071 8.29289C18.0976 8.68342 18.0976 9.31658 17.7071 9.70711L12.7071 14.7071Z"
                        fill="currentColor"
                      />
                    </svg>
                  </span>
                </button>
                <div className="connector-section-actions">
                  <button
                    type="button"
                    className="primary-button compact-button"
                    disabled={slackLoading || slackConnection?.configured === false}
                    onClick={onSlackConnect}
                  >
                    Connect
                  </button>
                </div>
              </div>
              <div className={`connector-section-collapse${slackWorkspacesOpen ? " open" : ""}`}>
                <div className="connector-section-scroll">
                  {slackConnection?.configured === false ? (
                    <div className="status-text compact">Slack OAuth is not configured on the backend.</div>
                  ) : null}
                  {slackConnection?.connected ? (
                    slackConnection.teams.map((team) => (
                      <div className="connector-access-row slack-workspace-row" key={team.team_id}>
                        <span>{team.team_name}</span>
                        <button
                          type="button"
                          className="danger-button compact-button"
                          disabled={slackLoading}
                          onClick={() => onSlackDisconnect(team.team_id)}
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="status-text compact">No Slack workspaces connected.</div>
                  )}
                </div>
              </div>
            </section>

            <section className="connector-access-list">
              <div className="connector-section-row">
                <button
                  type="button"
                  className="connector-section-toggle"
                  aria-expanded={slackChannelsOpen}
                  onClick={() => setSlackChannelsOpen((open) => !open)}
                >
                  <span>Channels</span>
                  <span
                    className={`connector-section-chevron${slackChannelsOpen ? " open" : ""}`}
                    aria-hidden="true"
                  >
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M12.7071 14.7071C12.3166 15.0976 11.6834 15.0976 11.2929 14.7071L6.29289 9.70711C5.90237 9.31658 5.90237 8.68342 6.29289 8.29289C6.68342 7.90237 7.31658 7.90237 7.70711 8.29289L12 12.5858L16.2929 8.29289C16.6834 7.90237 17.3166 7.90237 17.7071 8.29289C18.0976 8.68342 18.0976 9.31658 17.7071 9.70711L12.7071 14.7071Z"
                        fill="currentColor"
                      />
                    </svg>
                  </span>
                </button>
                <input
                  className="connector-section-search"
                  type="search"
                  value={slackChannelQuery}
                  placeholder="#engineering"
                  disabled={!slackConnection?.connected}
                  autoComplete="off"
                  spellCheck={false}
                  onChange={(event) => onSlackChannelQueryChange(event.target.value)}
                />
              </div>
              <div className={`connector-section-collapse${slackChannelsOpen ? " open" : ""}`}>
                <div className="connector-section-scroll connector-section-scroll-tall">
                  {slackLoading && slackChannelSearchActive ? <div className="status-text compact">Searching Slack channels...</div> : null}
                  {!slackChannelSearchActive && !slackSources.length ? (
                    <div className="status-text compact">No channels added to this Readbase workspace.</div>
                  ) : null}
                  {slackChannelSearchActive && !slackLoading && !slackChannels.length ? (
                    <div className="status-text compact">No visible Slack channels found.</div>
                  ) : null}
                  {slackChannelSearchActive ? (
                    <>
                      {searchedAddedSlackChannels.map((channel) => {
                        const source = slackSources.find(
                          (currentSource) =>
                            currentSource.team_id === channel.team_id &&
                            currentSource.channel_id === channel.channel_id,
                        );
                        if (!source) {
                          return null;
                        }
                        return (
                          <div className="connector-access-row slack-channel-row" key={`${channel.team_id}:${channel.channel_id}`}>
                            <span>#{channel.channel_name}</span>
                            <strong>{channel.team_name}</strong>
                            <button
                              type="button"
                              className="danger-button compact-button"
                              disabled={slackLoading}
                              onClick={() => onRemoveSlackSource(source.source_id)}
                            >
                              Remove
                            </button>
                          </div>
                        );
                      })}
                      {searchedAddedSlackChannels.length && searchedAvailableSlackChannels.length ? (
                        <div className="connector-result-divider" aria-hidden="true" />
                      ) : null}
                      {searchedAvailableSlackChannels.map((channel) => (
                        <div className="connector-access-row slack-channel-row" key={`${channel.team_id}:${channel.channel_id}`}>
                          <span>#{channel.channel_name}</span>
                          <strong>{channel.team_name}</strong>
                          <button
                            type="button"
                            className="secondary-action-button compact-button"
                            disabled={slackLoading}
                            onClick={() => onAddSlackChannel(channel)}
                          >
                            Add
                          </button>
                        </div>
                      ))}
                    </>
                  ) : (
                    slackSources.map((source) => (
                        <div className="connector-access-row slack-channel-row" key={source.source_id}>
                          <span>#{source.channel_name}</span>
                          <strong>{source.team_name}</strong>
                          <button
                            type="button"
                            className="danger-button compact-button"
                            disabled={slackLoading || source.user_access !== "connected"}
                            onClick={() => onRemoveSlackSource(source.source_id)}
                          >
                            Remove
                          </button>
                        </div>
                    ))
                  )}
                </div>
              </div>

            {error ? <div className="status-text error-text">{error}</div> : null}
            {status ? <div className="status-text">{status}</div> : null}
            </section>
          </div>
  );
}
