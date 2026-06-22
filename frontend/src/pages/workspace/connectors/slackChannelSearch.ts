import type { SlackChannel } from "../../../types";

export type SlackChannelSearchEntry = {
  channel: SlackChannel;
  channelName: string;
  teamName: string;
};

function tokenizeQuery(query: string): string[] {
  return query.trim().toLowerCase().split(/\s+/).filter(Boolean);
}

export function buildSlackChannelSearchIndex(channels: SlackChannel[]): SlackChannelSearchEntry[] {
  return channels.map((channel) => ({
    channel,
    channelName: channel.channel_name.toLowerCase(),
    teamName: channel.team_name.toLowerCase(),
  }));
}

function scoreToken(token: string, channelName: string, teamName: string): number {
  if (channelName === token) {
    return 100;
  }
  if (channelName.startsWith(token)) {
    return 80;
  }
  if (channelName.split(/[-_.\s]+/).some((word) => word.startsWith(token))) {
    return 65;
  }
  if (channelName.includes(token)) {
    return 45;
  }
  if (teamName.startsWith(token)) {
    return 35;
  }
  if (teamName.includes(token)) {
    return 25;
  }
  return -1;
}

function scoreEntry(entry: SlackChannelSearchEntry, tokens: string[]): number {
  if (tokens.length === 0) {
    return 0;
  }
  let total = 0;
  for (const token of tokens) {
    const tokenScore = scoreToken(token, entry.channelName, entry.teamName);
    if (tokenScore < 0) {
      return -1;
    }
    total += tokenScore;
  }
  return total;
}

function compareEntries(a: SlackChannelSearchEntry, b: SlackChannelSearchEntry): number {
  const teamCmp = a.teamName.localeCompare(b.teamName);
  return teamCmp !== 0 ? teamCmp : a.channelName.localeCompare(b.channelName);
}

export function searchSlackChannelEntries(
  index: SlackChannelSearchEntry[],
  query: string,
  excludeKeys?: ReadonlySet<string>,
): SlackChannel[] {
  const candidates = excludeKeys
    ? index.filter((entry) => !excludeKeys.has(`${entry.channel.team_id}:${entry.channel.channel_id}`))
    : index;

  const tokens = tokenizeQuery(query);
  if (tokens.length === 0) {
    return candidates.slice().sort(compareEntries).map((entry) => entry.channel);
  }

  const scored: Array<{ entry: SlackChannelSearchEntry; score: number }> = [];
  for (const entry of candidates) {
    const score = scoreEntry(entry, tokens);
    if (score >= 0) {
      scored.push({ entry, score });
    }
  }

  scored.sort((a, b) => {
    if (b.score !== a.score) {
      return b.score - a.score;
    }
    return compareEntries(a.entry, b.entry);
  });

  return scored.map(({ entry }) => entry.channel);
}
