from __future__ import annotations

from src.backend.application.services.exceptions import ResourceNotFoundError, ValidationError
from src.backend.application.services.confluence_service import filter_confluence_matches_for_user
from src.backend.application.services.notion_service import filter_notion_matches_for_user
from src.backend.application.services.jira_service import filter_jira_matches_for_user
from src.backend.application.services.linear_service import filter_linear_matches_for_user
from src.backend.application.services.repo_service import filter_repo_matches_for_user, list_repositories
from src.backend.application.services.slack_service import filter_slack_matches_for_user
from src.backend.config.settings import DEFAULT_TOP_K
from src.backend.infrastructure.generation.answerer import answer_question
from src.backend.infrastructure.retrieval.retriever import index_exists, load_index, search, search_confluence, search_jira, search_linear, search_notion, search_slack


def ask_repository_question(
    repo_id: str | None,
    question: str,
    top_k: int = DEFAULT_TOP_K,
    workspace_id: str | None = None,
    user_id: str | None = None,
) -> dict:
    normalized_repo_id = repo_id.strip() if isinstance(repo_id, str) else ""
    normalized_question = question.strip()

    if not normalized_question:
        raise ValidationError("question is required.")

    matches: list[dict] = []
    if normalized_repo_id:
        if not index_exists(normalized_repo_id, workspace_id=workspace_id):
            raise ResourceNotFoundError("Repository is not indexed yet.")
        index = load_index(normalized_repo_id, workspace_id=workspace_id)
        matches.extend(search(index, normalized_question, top_k=max(1, top_k)))
    elif workspace_id:
        for repo in list_repositories(workspace_id=workspace_id):
            repo_id_value = repo.get("repo_id")
            if not repo_id_value or not index_exists(repo_id_value, workspace_id=workspace_id):
                continue
            index = load_index(repo_id_value, workspace_id=workspace_id)
            matches.extend(search(index, normalized_question, top_k=max(1, top_k)))
    else:
        raise ValidationError("repo_id is required.")

    if workspace_id:
        matches.extend(search_jira(workspace_id, normalized_question, top_k=max(1, top_k)))
        matches.extend(search_slack(workspace_id, normalized_question, top_k=max(1, top_k)))
        matches.extend(search_linear(workspace_id, normalized_question, top_k=max(1, top_k)))
        matches.extend(search_confluence(workspace_id, normalized_question, top_k=max(1, top_k)))
        matches.extend(search_notion(workspace_id, normalized_question, top_k=max(1, top_k)))
    if user_id:
        matches = filter_repo_matches_for_user(user_id, matches)
        matches = filter_jira_matches_for_user(user_id, matches)
        matches = filter_slack_matches_for_user(user_id, matches, workspace_id=workspace_id)
        matches = filter_linear_matches_for_user(user_id, matches)
        matches = filter_confluence_matches_for_user(user_id, matches)
        matches = filter_notion_matches_for_user(user_id, matches)
    matches = sorted(matches, key=lambda match: float(match.get("score", 0.0)), reverse=True)[: max(1, top_k)]

    answer = answer_question(normalized_question, matches)
    return {
        "repo_id": normalized_repo_id or None,
        "workspace_id": workspace_id,
        "question": normalized_question,
        "answer": answer["answer"],
        "mode": answer["mode"],
        "sources": answer["sources"],
    }
