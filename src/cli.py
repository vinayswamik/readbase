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
from src.backend.application.services.workspace_service import (
    CLI_OWNER_ID,
    create_workspace,
    delete_workspace,
    get_active_workspace,
    resolve_workspace,
    set_active_workspace_id,
)
from src.backend.config.settings import DEFAULT_TOP_K


def main() -> None:
    parser = argparse.ArgumentParser(prog="readbase", description="Readbase CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index a GitHub URL or local path")
    index_parser.add_argument("source", help="GitHub URL or local directory path")
    index_parser.add_argument("--refresh", action="store_true", help="Rebuild the index")
    index_parser.add_argument("--workspace", help="Workspace name or id")

    ask_parser = subparsers.add_parser(
        "ask",
        help="Start interactive Q&A against an indexed repo",
    )
    ask_parser.add_argument("--repo-id", help="Use a specific repo id")
    ask_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Retrieved chunks")
    ask_parser.add_argument("--workspace", help="Workspace name or id")

    for command_name in ("create", "Create"):
        create_parser = subparsers.add_parser(command_name, help="Create a workspace")
        create_parser.add_argument("name", help="Workspace name")

    space_parser = subparsers.add_parser("space", help="Manage workspaces")
    space_parser.add_argument("name", help="Workspace name or id")
    space_parser.add_argument("-del", dest="delete", action="store_true", help="Delete workspace")

    args = parser.parse_args()
    if args.command == "index":
        run_index(args.source, args.refresh, args.workspace)
        return
    if args.command == "ask":
        run_ask_session(args.repo_id, args.top_k, args.workspace)
        return
    if args.command in {"create", "Create"}:
        run_create_workspace(args.name)
        return
    if args.command == "space":
        run_space_command(args.name, args.delete)
        return


def run_create_workspace(name: str) -> None:
    try:
        workspace = create_workspace(CLI_OWNER_ID, name)
    except ValidationError as exc:
        raise SystemExit(f"Workspace creation failed: {exc}") from exc

    set_active_workspace_id(workspace["workspace_id"])
    print("Workspace created")
    print(f"name: {workspace['name']}")
    print(f"workspace_id: {workspace['workspace_id']}")
    print("active: yes")


def run_space_command(name: str, delete: bool) -> None:
    if not delete:
        raise SystemExit('Unsupported space command. To delete, run: readbase space "name" -del')

    try:
        workspace = resolve_workspace(CLI_OWNER_ID, name)
    except ResourceNotFoundError as exc:
        raise SystemExit(f"Workspace not found: {name}") from exc
    except ValidationError as exc:
        raise SystemExit(f"Workspace lookup failed: {exc}") from exc

    print(f'Warning: this will permanently delete workspace "{workspace["name"]}".')
    print("All repositories and indexes inside this workspace will be removed.")
    confirmation = input("Type yes to continue: ").strip()
    if confirmation != "yes":
        print("Delete cancelled.")
        return

    try:
        deleted = delete_workspace(CLI_OWNER_ID, workspace["workspace_id"])
    except ValidationError as exc:
        raise SystemExit(str(exc)) from exc
    print(f'Workspace deleted: {deleted["name"]}')


def run_index(source: str, refresh: bool, workspace_name: str | None = None) -> None:
    workspace = resolve_cli_workspace(workspace_name)
    try:
        if is_github_url(source):
            result = index_repository(
                source,
                refresh=refresh,
                workspace_id=workspace["workspace_id"],
            )
        else:
            result = index_local_repository(
                source,
                refresh=refresh,
                workspace_id=workspace["workspace_id"],
            )
    except ValidationError as exc:
        raise SystemExit(f"Indexing failed: {exc}") from exc

    print("Index complete")
    print(f"workspace: {workspace['name']}")
    print(f"repo_id: {result['repo_id']}")
    print(f"source: {result['repo_url']}")
    print(f"files: {result['file_count']}")
    print(f"chunks: {result['chunk_count']}")


def run_ask_session(
    repo_id: str | None,
    top_k: int,
    workspace_name: str | None = None,
) -> None:
    workspace = resolve_cli_workspace(workspace_name)
    indexes = [
        repo
        for repo in list_repositories(workspace_id=workspace["workspace_id"])
        if repo.get("repo_id")
    ]
    if not indexes:
        raise SystemExit(
            f"No indexed repositories found in workspace {workspace['name']}. "
            "Run: readbase index <url-or-path>"
        )

    chosen_repo_id = repo_id or choose_repo_id(indexes)
    if not chosen_repo_id:
        raise SystemExit("No indexed repositories found. Run: readbase index <url-or-path>")
    print(f"Using workspace: {workspace['name']}")
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
                workspace_id=workspace["workspace_id"],
            )
        except ResourceNotFoundError as exc:
            raise SystemExit(f"Index not found for repo_id: {chosen_repo_id}") from exc
        except ValidationError as exc:
            print(f"Question failed: {exc}")
            continue
        print(f"mode: {response['mode']}")
        print(response["answer"])
        print()


def resolve_cli_workspace(workspace_name: str | None = None) -> dict:
    try:
        if workspace_name:
            return resolve_workspace(CLI_OWNER_ID, workspace_name)
        return get_active_workspace()
    except ResourceNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    except ValidationError as exc:
        raise SystemExit(f"Workspace lookup failed: {exc}") from exc


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
