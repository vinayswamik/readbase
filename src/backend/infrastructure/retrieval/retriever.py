from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from src.backend.config.settings import (
    CHROMA_DIR,
    DEFAULT_TOP_K,
    EMBEDDING_CACHE_DIR,
    INDEX_DIR,
    WORKSPACES_DIR,
)

# Token pattern for code-ish search. It captures identifiers like create_session
# and numbers, then helper functions split/normalize those tokens further.
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+")
ONNXMiniLM_L6_V2.DOWNLOAD_PATH = EMBEDDING_CACHE_DIR / ONNXMiniLM_L6_V2.MODEL_NAME
EMBEDDING_FUNCTION = DefaultEmbeddingFunction()


# Convert text into searchable terms. Code search benefits from splitting names:
# `create_session` should match questions containing "create" or "session".
def tokenize(value: str) -> list[str]:
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(value):
        token = raw.lower()
        tokens.extend(token_variants(token))
        for part in split_identifier(token):
            tokens.extend(token_variants(part))
    return [token for token in tokens if len(token) > 1]


# Tiny stemming-like helper. It is not linguistically perfect, but it helps
# simple questions match code terms: "sessions" -> "session", "created" -> "create".
def token_variants(token: str) -> list[str]:
    variants = [token]
    if len(token) > 3 and token.endswith("s"):
        variants.append(token[:-1])
    if len(token) > 4 and token.endswith("ed"):
        variants.append(token[:-1])
        variants.append(token[:-2])
    if len(token) > 5 and token.endswith("ing"):
        variants.append(token[:-3])
        variants.append(f"{token[:-3]}e")
    return variants


# Split snake_case/path-like identifiers into smaller pieces. This first version
# focuses on common repo naming patterns rather than full programming-language parsing.
def split_identifier(token: str) -> list[str]:
    parts = re.split(r"[_\-/\.]+", token)
    split_parts: list[str] = []
    for part in parts:
        split_parts.extend(re.findall(r"[a-z]+|[0-9]+", part))
    return [part for part in split_parts if part and part != token]


# Build a persistent ChromaDB index from repo chunks. Chroma's embedding function
# turns code text into semantic vectors; we still store raw text for citations.
def build_index(
    chunks: list[dict],
    repo_url: str,
    repo_id: str,
    file_count: int,
    workspace_id: str | None = None,
) -> dict:
    collection = get_repo_collection(repo_id, workspace_id=workspace_id, recreate=True)
    if chunks:
        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "repo_id": repo_id,
                "workspace_id": workspace_id or "",
                "repo_url": repo_url,
                "source_type": "repo",
                "path": chunk["path"],
                "start_line": int(chunk["start_line"]),
                "end_line": int(chunk["end_line"]),
            }
            for chunk in chunks
        ]
        # Chroma stores ids, source text, metadata, and vectors together. Upsert
        # means the same chunk id can be re-indexed without duplicate records.
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embed_texts([embedding_text(chunk) for chunk in chunks]),
        )

    # The JSON manifest is now only lightweight metadata. Chunks live in Chroma.
    return {
        "repo_id": repo_id,
        "workspace_id": workspace_id,
        "repo_url": repo_url,
        "file_count": file_count,
        "chunk_count": len(chunks),
        "collection": collection_name(repo_id, workspace_id=workspace_id),
        "embedding": "chroma_default",
    }


def build_jira_index(chunks: list[dict], workspace_id: str) -> dict:
    collection = get_repo_collection(jira_collection_id(), workspace_id=workspace_id, recreate=True)
    if chunks:
        collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[
                {
                    "source_type": "jira",
                    "workspace_id": workspace_id,
                    "path": chunk["path"],
                    "start_line": 1,
                    "end_line": 1,
                    "source_url": chunk.get("source_url", ""),
                    "cloud_id": chunk.get("cloud_id", ""),
                    "project_id": chunk.get("project_id", ""),
                    "project_key": chunk.get("project_key", ""),
                    "issue_id": chunk.get("issue_id", ""),
                    "issue_key": chunk.get("issue_key", ""),
                    "item_type": chunk.get("item_type", ""),
                    "item_id": chunk.get("item_id", ""),
                }
                for chunk in chunks
            ],
            embeddings=embed_texts([embedding_text(chunk) for chunk in chunks]),
        )
    return {
        "repo_id": jira_collection_id(),
        "workspace_id": workspace_id,
        "repo_url": "jira://workspace",
        "file_count": len({chunk.get("issue_key") for chunk in chunks}),
        "chunk_count": len(chunks),
        "collection": collection_name(jira_collection_id(), workspace_id=workspace_id),
        "embedding": "chroma_default",
    }


def build_slack_index(chunks: list[dict], workspace_id: str) -> dict:
    collection = get_repo_collection(slack_collection_id(), workspace_id=workspace_id, recreate=True)
    if chunks:
        collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[
                {
                    "source_type": "slack",
                    "workspace_id": workspace_id,
                    "path": chunk["path"],
                    "start_line": 1,
                    "end_line": 1,
                    "source_url": chunk.get("source_url", ""),
                    "team_id": chunk.get("team_id", ""),
                    "team_name": chunk.get("team_name", ""),
                    "channel_id": chunk.get("channel_id", ""),
                    "channel_name": chunk.get("channel_name", ""),
                    "message_ts": chunk.get("message_ts", ""),
                    "thread_ts": chunk.get("thread_ts", ""),
                    "item_type": chunk.get("item_type", ""),
                    "item_id": chunk.get("item_id", ""),
                }
                for chunk in chunks
            ],
            embeddings=embed_texts([embedding_text(chunk) for chunk in chunks]),
        )
    return {
        "repo_id": slack_collection_id(),
        "workspace_id": workspace_id,
        "repo_url": "slack://workspace",
        "file_count": len({chunk.get("channel_id") for chunk in chunks}),
        "chunk_count": len(chunks),
        "collection": collection_name(slack_collection_id(), workspace_id=workspace_id),
        "embedding": "chroma_default",
    }


def build_linear_index(chunks: list[dict], workspace_id: str) -> dict:
    collection = get_repo_collection(linear_collection_id(), workspace_id=workspace_id, recreate=True)
    if chunks:
        collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[
                {
                    "source_type": "linear",
                    "workspace_id": workspace_id,
                    "path": chunk["path"],
                    "start_line": 1,
                    "end_line": 1,
                    "source_url": chunk.get("source_url", ""),
                    "linear_team_id": chunk.get("linear_team_id", ""),
                    "linear_project_id": chunk.get("linear_project_id", ""),
                    "issue_id": chunk.get("issue_id", ""),
                    "issue_key": chunk.get("issue_key", ""),
                    "item_type": chunk.get("item_type", ""),
                    "item_id": chunk.get("item_id", ""),
                }
                for chunk in chunks
            ],
            embeddings=embed_texts([embedding_text(chunk) for chunk in chunks]),
        )
    return source_index_manifest(linear_collection_id(), workspace_id, "linear://workspace", chunks)


def build_confluence_index(chunks: list[dict], workspace_id: str) -> dict:
    collection = get_repo_collection(confluence_collection_id(), workspace_id=workspace_id, recreate=True)
    if chunks:
        collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[
                {
                    "source_type": "confluence",
                    "workspace_id": workspace_id,
                    "path": chunk["path"],
                    "start_line": 1,
                    "end_line": 1,
                    "source_url": chunk.get("source_url", ""),
                    "cloud_id": chunk.get("cloud_id", ""),
                    "space_id": chunk.get("space_id", ""),
                    "space_key": chunk.get("space_key", ""),
                    "page_id": chunk.get("page_id", ""),
                    "item_type": chunk.get("item_type", ""),
                    "item_id": chunk.get("item_id", ""),
                }
                for chunk in chunks
            ],
            embeddings=embed_texts([embedding_text(chunk) for chunk in chunks]),
        )
    return source_index_manifest(confluence_collection_id(), workspace_id, "confluence://workspace", chunks)


def source_index_manifest(repo_id: str, workspace_id: str, repo_url: str, chunks: list[dict]) -> dict:
    return {
        "repo_id": repo_id,
        "workspace_id": workspace_id,
        "repo_url": repo_url,
        "file_count": len({chunk.get("path") for chunk in chunks}),
        "chunk_count": len(chunks),
        "collection": collection_name(repo_id, workspace_id=workspace_id),
        "embedding": "chroma_default",
    }


# Persist lightweight metadata as readable JSON for repo listing and existence checks.
def save_index(index: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2), encoding="utf-8")


# Check whether the manifest exists before trying to query Chroma.
def index_exists(repo_id: str, workspace_id: str | None = None) -> bool:
    return (index_dir_for_workspace(workspace_id) / f"{repo_id}.json").exists()


# Load a previously saved repo manifest when the user asks a question.
def load_index(repo_id: str, workspace_id: str | None = None) -> dict:
    return json.loads(
        (index_dir_for_workspace(workspace_id) / f"{repo_id}.json").read_text(
            encoding="utf-8"
        )
    )


# Delete the Chroma collection for a repo. Refresh uses this so old chunks do not
# survive when a repository is re-cloned and re-indexed.
def delete_index(repo_id: str, workspace_id: str | None = None) -> None:
    try:
        get_chroma_client().delete_collection(collection_name(repo_id, workspace_id=workspace_id))
    except Exception:
        # Chroma raises when the collection does not exist; refresh should remain idempotent.
        return


# Retrieve the best chunks for a question. Chroma runs nearest-neighbor search
# over the stored chunk embeddings and returns source documents + metadata.
def search(index: dict, question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    if not tokenize(question):
        return []

    collection = get_repo_collection(
        index["repo_id"],
        workspace_id=index.get("workspace_id"),
    )
    result = collection.query(
        query_embeddings=embed_texts([question]),
        n_results=max(1, top_k),
        include=["documents", "metadatas", "distances"],
    )
    return normalize_chroma_result(result)


def search_jira(workspace_id: str, question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    return search_workspace_source(jira_collection_id(), workspace_id, question, top_k)


def search_slack(workspace_id: str, question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    return search_workspace_source(slack_collection_id(), workspace_id, question, top_k)


def search_linear(workspace_id: str, question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    return search_workspace_source(linear_collection_id(), workspace_id, question, top_k)


def search_confluence(workspace_id: str, question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    return search_workspace_source(confluence_collection_id(), workspace_id, question, top_k)


def search_workspace_source(collection_id_value: str, workspace_id: str, question: str, top_k: int) -> list[dict]:
    if not tokenize(question):
        return []
    collection = get_repo_collection(collection_id_value, workspace_id=workspace_id)
    try:
        result = collection.query(
            query_embeddings=embed_texts([question]),
            n_results=max(1, top_k),
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []
    return normalize_chroma_result(result)


def jira_collection_id() -> str:
    return "__jira__"


def slack_collection_id() -> str:
    return "__slack__"


def linear_collection_id() -> str:
    return "__linear__"


def confluence_collection_id() -> str:
    return "__confluence__"


# Chroma keeps a persistent SQLite/vector index under .readbase/chroma.
def get_chroma_client() -> chromadb.PersistentClient:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


# Collection names are separate from repo ids because Chroma collection names
# have validation rules. A digest keeps names short and collision-resistant.
def collection_name(repo_id: str, workspace_id: str | None = None) -> str:
    collection_key = f"{workspace_id}:{repo_id}" if workspace_id else repo_id
    digest = hashlib.sha1(collection_key.encode("utf-8")).hexdigest()[:16]
    return f"readbase_{digest}"


# Get or recreate the Chroma collection for one repo.
def get_repo_collection(
    repo_id: str,
    workspace_id: str | None = None,
    recreate: bool = False,
):
    client = get_chroma_client()
    name = collection_name(repo_id, workspace_id=workspace_id)
    if recreate:
        try:
            client.delete_collection(name)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=name,
        metadata={
            "repo_id": repo_id,
            "workspace_id": workspace_id or "",
            "hnsw:space": "cosine",
        },
    )


def index_dir_for_workspace(workspace_id: str | None = None) -> Path:
    if not workspace_id:
        return INDEX_DIR
    index_dir = WORKSPACES_DIR / workspace_id / "indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir


# Include file path in the text that gets embedded because paths encode useful
# code meaning like "auth/session.py" or "api/routes".
def embedding_text(chunk: dict) -> str:
    return f"file: {chunk['path']}\n\n{chunk['text']}"


# Small wrapper keeps Chroma's embedding function in one place.
def embed_texts(texts: list[str]) -> list[list[float]]:
    return [[float(value) for value in vector] for vector in EMBEDDING_FUNCTION(texts)]


# Turn Chroma's nested query result into the flat SourceMatch shape expected by
# the answerer and frontend.
def normalize_chroma_result(result: dict[str, Any]) -> list[dict]:
    ids = first_result_list(result.get("ids"))
    documents = first_result_list(result.get("documents"))
    metadatas = first_result_list(result.get("metadatas"))
    distances = first_result_list(result.get("distances"))

    matches: list[dict] = []
    for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        metadata = metadata or {}
        numeric_distance = float(distance or 0.0)
        matches.append(
            {
                "score": round(1.0 / (1.0 + numeric_distance), 4),
                "id": chunk_id,
                "path": metadata.get("path", ""),
                "start_line": int(metadata.get("start_line", 0)),
                "end_line": int(metadata.get("end_line", 0)),
                "text": document or "",
                "source_type": metadata.get("source_type", "repo") or "repo",
                "repo_id": metadata.get("repo_id") or None,
                "repo_url": metadata.get("repo_url") or None,
                "source_url": metadata.get("source_url") or None,
                "cloud_id": metadata.get("cloud_id") or None,
                "project_id": metadata.get("project_id") or None,
                "project_key": metadata.get("project_key") or None,
                "issue_id": metadata.get("issue_id") or None,
                "issue_key": metadata.get("issue_key") or None,
                "linear_team_id": metadata.get("linear_team_id") or None,
                "linear_project_id": metadata.get("linear_project_id") or None,
                "team_id": metadata.get("team_id") or None,
                "team_name": metadata.get("team_name") or None,
                "channel_id": metadata.get("channel_id") or None,
                "channel_name": metadata.get("channel_name") or None,
                "message_ts": metadata.get("message_ts") or None,
                "thread_ts": metadata.get("thread_ts") or None,
                "space_id": metadata.get("space_id") or None,
                "space_key": metadata.get("space_key") or None,
                "page_id": metadata.get("page_id") or None,
                "item_type": metadata.get("item_type") or None,
                "item_id": metadata.get("item_id") or None,
            }
        )
    return matches


# Chroma returns results as list-per-query. We send one query at a time, so the
# first nested list contains all matches.
def first_result_list(value: Any) -> list:
    if not value:
        return []
    return value[0] if isinstance(value[0], list) else value
