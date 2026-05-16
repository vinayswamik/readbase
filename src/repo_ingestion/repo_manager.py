from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from src.answering.retriever import build_index, delete_index, save_index
from src.repo_ingestion.chunker import chunk_repository
from src.settings import CHROMA_DIR, DATA_DIR, INDEX_DIR, REPOS_DIR


# Domain-specific exception: server.py catches this and returns a clean 400 JSON error.
class RepoError(RuntimeError):
    pass


# Ensure the local data folders exist before cloning or writing indexes.
def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)


# Turn a GitHub URL into a safe local folder/index name. The short hash avoids
# collisions when similar repo paths or URL forms point to different sources.
def repo_id_from_url(repo_url: str) -> str:
    parsed = urlparse(repo_url.strip())
    if parsed.scheme not in {"http", "https", "git", "ssh"}:
        raise RepoError("Use a full GitHub repository URL.")
    if "github.com" not in parsed.netloc.lower():
        raise RepoError("This first version only accepts github.com repository URLs.")

    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", path).strip("-")
    digest = hashlib.sha1(repo_url.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}" if slug else digest


# Local paths get their own stable id so the same folder maps to the same index.
def repo_id_from_local_path(repo_path: Path) -> str:
    resolved = repo_path.resolve()
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", resolved.name).strip("-") or "local-repo"
    digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


# High-level ingestion pipeline: validate URL, clone if needed, chunk files,
# build the retrieval index, save it, then return stats to the UI.
def index_repo(repo_url: str, refresh: bool = False) -> dict:
    ensure_data_dirs()
    repo_id = repo_id_from_url(repo_url)
    repo_path = REPOS_DIR / repo_id
    index_path = INDEX_DIR / f"{repo_id}.json"

    # Refresh means "start over" for this repo, useful after upstream changes.
    if refresh and repo_path.exists():
        shutil.rmtree(repo_path)
    if refresh and index_path.exists():
        index_path.unlink()
    if refresh:
        delete_index(repo_id)

    # Reuse an existing clone unless refresh was requested.
    if not repo_path.exists():
        clone_repo(repo_url, repo_path)

    chunks, file_count = chunk_repository(repo_path)
    index = build_index(
        chunks=chunks,
        repo_url=repo_url,
        repo_id=repo_id,
        file_count=file_count,
    )
    save_index(index, index_path)

    return {
        "repo_id": repo_id,
        "repo_url": repo_url,
        "repo_path": str(repo_path),
        "file_count": file_count,
        "chunk_count": len(chunks),
    }


# Index an already-downloaded local repository path (no cloning).
def index_local_repo(local_repo_path: str, refresh: bool = False) -> dict:
    ensure_data_dirs()
    repo_path = Path(local_repo_path).expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise RepoError("Local repository path does not exist or is not a directory.")

    repo_id = repo_id_from_local_path(repo_path)
    index_path = INDEX_DIR / f"{repo_id}.json"

    if refresh and index_path.exists():
        index_path.unlink()
    if refresh:
        delete_index(repo_id)

    chunks, file_count = chunk_repository(repo_path)
    repo_url = f"local://{repo_path.as_posix()}"
    index = build_index(
        chunks=chunks,
        repo_url=repo_url,
        repo_id=repo_id,
        file_count=file_count,
    )
    save_index(index, index_path)

    return {
        "repo_id": repo_id,
        "repo_url": repo_url,
        "repo_path": str(repo_path),
        "file_count": file_count,
        "chunk_count": len(chunks),
    }


# Shell out to git instead of implementing GitHub download logic ourselves.
# `--depth 1` keeps the first version fast by skipping full commit history.
def clone_repo(repo_url: str, repo_path: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
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


# Read the saved JSON index files and return lightweight repo cards for the sidebar.
def list_indexes() -> list[dict]:
    ensure_data_dirs()
    repos = []
    for path in sorted(INDEX_DIR.glob("*.json")):
        try:
            # Imported here because only this small listing path needs JSON parsing.
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        repos.append(
            {
                "repo_id": data.get("repo_id"),
                "repo_url": data.get("repo_url"),
                "file_count": data.get("file_count", 0),
                "chunk_count": data.get("chunk_count", 0),
            }
        )
    return repos
