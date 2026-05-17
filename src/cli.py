from __future__ import annotations

import argparse
from urllib.parse import urlparse

from src.backend.application.services.exceptions import ResourceNotFoundError, ValidationError
from src.backend.application.services.question_service import ask_repository_question
from src.backend.application.services.repo_service import (
    index_local_repository,
    index_repository,
    list_repositories,
)
from src.backend.config.settings import DEFAULT_TOP_K


def main() -> None:
    parser = argparse.ArgumentParser(prog="readbase", description="Readbase CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index a GitHub URL or local path")
    index_parser.add_argument("source", help="GitHub URL or local directory path")
    index_parser.add_argument("--refresh", action="store_true", help="Rebuild the index")

    ask_parser = subparsers.add_parser(
        "ask",
        help="Start interactive Q&A against an indexed repo",
    )
    ask_parser.add_argument("--repo-id", help="Use a specific repo id")
    ask_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Retrieved chunks")

    args = parser.parse_args()
    if args.command == "index":
        run_index(args.source, args.refresh)
        return
    if args.command == "ask":
        run_ask_session(args.repo_id, args.top_k)
        return


def run_index(source: str, refresh: bool) -> None:
    try:
        if is_github_url(source):
            result = index_repository(source, refresh=refresh)
        else:
            result = index_local_repository(source, refresh=refresh)
    except ValidationError as exc:
        raise SystemExit(f"Indexing failed: {exc}") from exc

    print("Index complete")
    print(f"repo_id: {result['repo_id']}")
    print(f"source: {result['repo_url']}")
    print(f"files: {result['file_count']}")
    print(f"chunks: {result['chunk_count']}")


def run_ask_session(repo_id: str | None, top_k: int) -> None:
    indexes = [repo for repo in list_repositories() if repo.get("repo_id")]
    if not indexes:
        raise SystemExit("No indexed repositories found. Run: readbase index <url-or-path>")

    chosen_repo_id = repo_id or choose_repo_id(indexes)
    if not chosen_repo_id:
        raise SystemExit("No indexed repositories found. Run: readbase index <url-or-path>")
    print(f"Using repo_id: {chosen_repo_id}")
    print("Q&A started. Type your question and press Enter. Type 'exit' to quit.")
    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        if not question:
            continue
        if question.lower() in {"exit", "quit", ":q"}:
            print("Exiting.")
            return

        try:
            response = ask_repository_question(
                chosen_repo_id,
                question,
                top_k=max(1, top_k),
            )
        except ResourceNotFoundError as exc:
            raise SystemExit(f"Index not found for repo_id: {chosen_repo_id}") from exc
        except ValidationError as exc:
            print(f"Question failed: {exc}")
            continue
        print(f"mode: {response['mode']}")
        print(response["answer"])
        print()


def choose_repo_id(indexes: list[dict]) -> str | None:
    print("Available indexes:")
    for i, repo in enumerate(indexes, start=1):
        print(f"{i}. {repo['repo_id']}  ({repo.get('repo_url', 'unknown source')})")

    while True:
        raw = input("Enter number: ").strip()
        if not raw.isdigit():
            print("Please enter a valid number.")
            continue
        pos = int(raw)
        if 1 <= pos <= len(indexes):
            return indexes[pos - 1]["repo_id"]
        print("Number out of range.")


def is_github_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https", "git", "ssh"}:
        return False
    return "github.com" in parsed.netloc.lower()


if __name__ == "__main__":
    main()
