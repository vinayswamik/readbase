from __future__ import annotations

from src.backend.application.services.exceptions import ResourceNotFoundError, ValidationError
from src.backend.config.settings import DEFAULT_TOP_K
from src.backend.infrastructure.generation.answerer import answer_question
from src.backend.infrastructure.retrieval.retriever import index_exists, load_index, search


def ask_repository_question(
    repo_id: str,
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> dict:
    normalized_repo_id = repo_id.strip()
    normalized_question = question.strip()

    if not normalized_repo_id:
        raise ValidationError("repo_id is required.")
    if not normalized_question:
        raise ValidationError("question is required.")
    if not index_exists(normalized_repo_id):
        raise ResourceNotFoundError("Repository is not indexed yet.")

    index = load_index(normalized_repo_id)
    matches = search(index, normalized_question, top_k=max(1, top_k))
    answer = answer_question(normalized_question, matches)
    return {
        "repo_id": normalized_repo_id,
        "question": normalized_question,
        "answer": answer["answer"],
        "mode": answer["mode"],
        "sources": answer["sources"],
    }
