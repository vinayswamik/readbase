from __future__ import annotations

import argparse
from urllib.parse import urlparse

from src.answering.answerer import answer_question
from src.answering.retriever import index_exists, load_index, search
from src.repo_ingestion.repo_manager import (
    RepoError,
    index_local_repo,
    index_repo,
    list_indexes,
)
from src.settings import DEFAULT_TOP_K


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
            result = index_repo(source, refresh=refresh)
        else:
            result = index_local_repo(source, refresh=refresh)
    except RepoError as exc:
        raise SystemExit(f"Indexing failed: {exc}") from exc

    print("Index complete")
    print(f"repo_id: {result['repo_id']}")
    print(f"source: {result['repo_url']}")
    print(f"files: {result['file_count']}")
    print(f"chunks: {result['chunk_count']}")


def run_ask_session(repo_id: str | None, top_k: int) -> None:
    indexes = [repo for repo in list_indexes() if repo.get("repo_id")]
    if not indexes:
        raise SystemExit("No indexed repositories found. Run: readbase index <url-or-path>")

    chosen_repo_id = repo_id or choose_repo_id(indexes)
    if not chosen_repo_id:
        raise SystemExit("No indexed repositories found. Run: readbase index <url-or-path>")
    if not index_exists(chosen_repo_id):
        raise SystemExit(f"Index not found for repo_id: {chosen_repo_id}")

    index = load_index(chosen_repo_id)
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

        matches = search(index, question, top_k=max(1, top_k))
        response = answer_question(question, matches)
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
