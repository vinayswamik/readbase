from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from src.backend.config.settings import DATA_DIR
from src.backend.infrastructure.ingestion.chunker import chunk_repository
from src.backend.infrastructure.retrieval.retriever import build_index, delete_index, save_index
from src.backend.infrastructure.storage.context import StorageContext
from src.backend.infrastructure.storage.resolver import resolve_storage


class RepoError(RuntimeError):
    pass


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    resolve_storage(None).ensure_dirs()


def storage_context(workspace_id: str | None = None) -> StorageContext:
    return resolve_storage(workspace_id)


def repo_id_from_url(repo_url: str) -> str:
    parsed = urlparse(repo_url.strip())
    if parsed.scheme not in {"http", "https", "git", "ssh"}:
        raise RepoError("Use a full repository URL.")
    host = (parsed.hostname or "").lower()
    if host not in {"github.com", "bitbucket.org", "gitlab.com"}:
        raise RepoError("Use a github.com, bitbucket.org, or gitlab.com repository URL.")

    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", path).strip("-")
    digest = hashlib.sha1(repo_url.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}" if slug else digest


def repo_id_from_local_path(repo_path: Path) -> str:
    resolved = repo_path.resolve()
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", resolved.name).strip("-") or "local-repo"
    digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


def index_repo(
    repo_url: str,
    refresh: bool = False,
    workspace_id: str | None = None,
    github_token: str | None = None,
    auth_token: str | None = None,
) -> dict:
    ensure_data_dirs()
    storage = storage_context(workspace_id)
    repo_id = repo_id_from_url(repo_url)
    repo_path = storage.repos_dir / repo_id
    index_path = storage.indexes_dir / f"{repo_id}.json"

    if refresh and repo_path.exists():
        shutil.rmtree(repo_path)
    if refresh and index_path.exists():
        index_path.unlink()
    if refresh:
        delete_index(repo_id, workspace_id=workspace_id)

    if not repo_path.exists():
        clone_repo(repo_url, repo_path, auth_token=auth_token or github_token)

    chunks, file_count = chunk_repository(repo_path)
    index = build_index(
        chunks=chunks,
        repo_url=repo_url,
        repo_id=repo_id,
        file_count=file_count,
        workspace_id=workspace_id,
    )
    save_index(index, index_path)

    return {
        "repo_id": repo_id,
        "workspace_id": workspace_id,
        "repo_url": repo_url,
        "repo_path": str(repo_path),
        "file_count": file_count,
        "chunk_count": len(chunks),
    }


def index_local_repo(
    local_repo_path: str,
    refresh: bool = False,
    workspace_id: str | None = None,
) -> dict:
    ensure_data_dirs()
    storage = storage_context(workspace_id)
    repo_path = Path(local_repo_path).expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise RepoError("Local repository path does not exist or is not a directory.")

    repo_id = repo_id_from_local_path(repo_path)
    index_path = storage.indexes_dir / f"{repo_id}.json"

    if refresh and index_path.exists():
        index_path.unlink()
    if refresh:
        delete_index(repo_id, workspace_id=workspace_id)

    chunks, file_count = chunk_repository(repo_path)
    repo_url = f"local://{repo_path.as_posix()}"
    index = build_index(
        chunks=chunks,
        repo_url=repo_url,
        repo_id=repo_id,
        file_count=file_count,
        workspace_id=workspace_id,
    )
    save_index(index, index_path)

    return {
        "repo_id": repo_id,
        "workspace_id": workspace_id,
        "repo_url": repo_url,
        "repo_path": str(repo_path),
        "file_count": file_count,
        "chunk_count": len(chunks),
    }


def clone_repo(repo_url: str, repo_path: Path, github_token: str | None = None, auth_token: str | None = None) -> None:
    token = auth_token or github_token
    command = ["git", "clone", "--depth", "1", repo_url, str(repo_path)]
    if token:
        host = (urlparse(repo_url).hostname or "").lower()
        if not host:
            raise RepoError("Use a full repository URL.")
        command = [
            "git",
            "-c",
            f"http.https://{host}/.extraheader=AUTHORIZATION: bearer {token}",
            "clone",
            "--depth",
            "1",
            repo_url,
            str(repo_path),
        ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise RepoError("Git is not installed or not available on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepoError("Git clone timed out. Try a smaller repository first.") from exc

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git clone failed."
        raise RepoError(message)


def list_indexes(workspace_id: str | None = None) -> list[dict]:
    ensure_data_dirs()
    storage = storage_context(workspace_id)
    repos = []
    seen: set[str] = set()
    for indexes_dir in storage.index_search_dirs():
        for path in sorted(indexes_dir.glob("*.json")):
            if path.name in seen:
                continue
            seen.add(path.name)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            repos.append(
                {
                    "repo_id": data.get("repo_id"),
                    "workspace_id": data.get("workspace_id"),
                    "repo_url": data.get("repo_url"),
                    "file_count": data.get("file_count", 0),
                    "chunk_count": data.get("chunk_count", 0),
                }
            )
    return repos
