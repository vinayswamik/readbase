from __future__ import annotations

import re


def normalize_search_tokens(query: str) -> list[str]:
    return [token for token in query.strip().lower().split() if token]


def score_channel_token(token: str, channel_name: str, team_name: str) -> int:
    normalized_channel = channel_name.lower()
    normalized_team = team_name.lower()
    if normalized_channel == token:
        return 100
    if normalized_channel.startswith(token):
        return 80
    if any(word.startswith(token) for word in re.split(r"[-_.\s]+", normalized_channel) if word):
        return 65
    if token in normalized_channel:
        return 45
    if normalized_team.startswith(token):
        return 35
    if token in normalized_team:
        return 25
    return -1


def score_channel_match(channel_name: str, team_name: str, tokens: list[str]) -> int:
    if not tokens:
        return 0
    total = 0
    for token in tokens:
        token_score = score_channel_token(token, channel_name, team_name)
        if token_score < 0:
            return -1
        total += token_score
    return total


def sort_channels(channels: list[dict]) -> list[dict]:
    return sorted(
        channels,
        key=lambda channel: (
            channel.get("team_name", "").lower(),
            channel.get("channel_name", "").lower(),
        ),
    )


def sort_scored_channels(scored_channels: list[tuple[int, dict]]) -> list[dict]:
    scored_channels.sort(
        key=lambda item: (
            -item[0],
            item[1].get("team_name", "").lower(),
            item[1].get("channel_name", "").lower(),
        )
    )
    return [channel for _, channel in scored_channels]
